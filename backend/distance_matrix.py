import numpy as np
import logging
from graph_loader import load_graph, get_node_coordinates as _get_coords
from typing import List, Optional, Tuple
import os

# Safe import of haversine from graph_loader
from graph_loader import haversine_distance

logger = logging.getLogger(__name__)

def compute_matrix(locations: List[str], place: str = None) -> np.ndarray:
    """
    Compute distance matrix between locations using NetworkX shortest path algorithm.
    """
    import networkx as nx
    
    # Load graph
    target_place = place or "Kuala Lumpur, Malaysia"
    graph = load_graph(target_place)
    
    if graph is None:
        raise ValueError("Graph not available")

    n = len(locations)
    mat = np.full((n, n), np.inf, dtype=np.float64)

    # Convert string node IDs to integers for NetworkX
    processed_locations = []
    for loc in locations:
        try:
            # Try converting to int (OSM node IDs are integers)
            node_id = int(loc)
            if node_id not in graph.nodes:
                logger.warning(f"Node {node_id} not found in graph")
                # Try to find nearest node
                raise ValueError(f"Node {node_id} not in graph")
            processed_locations.append(node_id)
        except ValueError:
            raise ValueError(f"Invalid node ID: {loc}")

    # Compute shortest paths using NetworkX
    for i, src in enumerate(processed_locations):
        for j, dst in enumerate(processed_locations):
            if i == j:
                mat[i][j] = 0.0
            else:
                try:
                    # Compute shortest path length using 'length' edge weight
                    distance = nx.shortest_path_length(graph, src, dst, weight='length')
                    mat[i][j] = distance
                except nx.NetworkXNoPath:
                    mat[i][j] = np.inf
                    logger.warning(f"No path found from {src} to {dst}")
                except Exception as e:
                    mat[i][j] = np.inf
                    logger.error(f"Error computing distance {src}->{dst}: {e}")

    logger.info(f"Computed {n}x{n} distance matrix using place '{target_place}'")
    return mat

def get_node_coordinates(node_id: str, place: str = None) -> Optional[Tuple[float, float]]:
    """Get coordinates for a node ID."""
    from graph_loader import get_node_coordinates as _get_coords
    target_place = place or "Kuala Lumpur, Malaysia"
    graph = load_graph(target_place)
    if graph is None:
        return None
    return _get_coords(graph, node_id)

def validate_locations(locations: List[str], place: str = None) -> List[str]:
    """
    Validate and normalize location node IDs.
    """
    target_place = place or "Kuala Lumpur, Malaysia"
    graph = load_graph(target_place)
    
    if graph is None:
        raise ValueError("Graph not available")
    
    validated = []
    for loc in locations:
        try:
            int_loc = int(loc)
            if int_loc in graph.nodes:
                validated.append(int_loc)
            else:
                raise ValueError(f"Node {int_loc} not in graph")
        except ValueError as e:
            raise ValueError(f"Invalid node ID {loc}: {e}")
    
    return validated

def compute_matrix_with_fallback(locations: List[str], place: str = None):
    """
    Compute a distance matrix and apply production fallbacks to avoid unreachable pairs.
    Fallback behavior is controlled by env var MATRIX_FALLBACK_MODE:
      - 'directed-only': no fallback
      - 'symmetric': use reverse direction if available
      - 'haversine': use great-circle distance * factor for unreachable
      - 'hybrid' (default): try symmetric first, then haversine
    Factor controlled by FALLBACK_DISTANCE_FACTOR (default 1.3).

    Returns (matrix: np.ndarray, metadata: dict)
    """
    mat = compute_matrix(locations, place)
    n = len(locations)

    mode = os.environ.get("MATRIX_FALLBACK_MODE", "hybrid").strip().lower()
    factor = float(os.environ.get("FALLBACK_DISTANCE_FACTOR", "1.3"))

    counts = {"symmetric": 0, "haversine": 0}

    if mode not in ("directed-only", "symmetric", "haversine", "hybrid"):
        logger.warning(f"Unknown MATRIX_FALLBACK_MODE='{mode}', defaulting to 'hybrid'")
        mode = "hybrid"

    # Apply fallbacks
    if mode != "directed-only":
        for i in range(n):
            for j in range(n):
                if i == j:
                    mat[i][j] = 0.0
                    continue
                if np.isinf(mat[i][j]):
                    used = False
                    # Symmetric reuse
                    if mode in ("symmetric", "hybrid") and not np.isinf(mat[j][i]):
                        mat[i][j] = float(mat[j][i])
                        counts["symmetric"] += 1
                        used = True
                    # Haversine fallback
                    if not used and mode in ("haversine", "hybrid"):
                        ci = get_node_coordinates(locations[i])
                        cj = get_node_coordinates(locations[j])
                        if ci and cj and all(v is not None for v in (*ci, *cj)):
                            try:
                                d = haversine_distance(ci[0], ci[1], cj[0], cj[1]) * factor
                                mat[i][j] = float(d)
                                counts["haversine"] += 1
                            except Exception as e:
                                # Leave as inf if haversine fails
                                logger.warning(f"Haversine fallback failed for {locations[i]}->{locations[j]}: {e}")
                                pass

    metadata = {
        "fallback_mode": mode,
        "fallback_factor": factor,
        "fallback_counts": counts,
        "size": n,
    }

    # Log summary
    total_fallbacks = counts["symmetric"] + counts["haversine"]
    if total_fallbacks > 0:
        logger.info(f"Applied fallbacks to {total_fallbacks} entries (symmetric={counts['symmetric']}, haversine={counts['haversine']}), mode={mode}")
    else:
        logger.info(f"No fallbacks applied, mode={mode}")

    return mat, metadata