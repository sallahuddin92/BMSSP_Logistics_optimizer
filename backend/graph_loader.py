import osmnx as ox
import networkx as nx
import pickle
import os
import logging
from pathlib import Path
import math

logger = logging.getLogger(__name__)

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees).
    Returns distance in meters.
    """
    # Convert decimal degrees to radians
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in meters
    r = 6371000
    return c * r

# Global graph cache
_current_graph = None
_current_place = None

CACHE_DIR = os.getenv("GRAPH_CACHE_DIR", "/app/cache")
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

def get_cache_file(place: str) -> str:
    """Get cache file path for a place."""
    safe_name = place.replace(" ", "_").replace(",", "")
    return os.path.join(CACHE_DIR, f"graph_{safe_name}.pkl")

def save_graph_to_cache(place: str, graph):
    """Save graph to cache file."""
    try:
        cache_file = get_cache_file(place)
        with open(cache_file, 'wb') as f:
            pickle.dump(graph, f)
        logger.info(f"Saved graph to cache: {cache_file}")
    except Exception as e:
        logger.warning(f"Failed to save graph to cache: {e}")

def load_graph_from_cache(place: str):
    """Load graph from cache file."""
    try:
        cache_file = get_cache_file(place)
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                graph = pickle.load(f)
            logger.info(f"Loaded graph from cache: {cache_file}")
            return graph
    except Exception as e:
        logger.warning(f"Failed to load graph from cache: {e}")
    return None

def load_graph(place: str = "Kuala Lumpur, Malaysia", force_reload: bool = False):
    """
    Load OSM graph for routing.
    Returns a NetworkX DiGraph.
    """
    global _current_graph, _current_place
    
    # Return cached if available
    if not force_reload and _current_place == place and _current_graph is not None:
        logger.info(f"Using already loaded graph for '{place}'")
        return _current_graph
    
    # Try loading from cache
    if not force_reload:
        cached_graph = load_graph_from_cache(place)
        if cached_graph is not None:
            _current_graph = cached_graph
            _current_place = place
            logger.info(f"Graph '{place}' loaded from cache with {len(cached_graph.nodes)} nodes")
            return cached_graph
    
    # Load from OSM
    logger.info(f"Loading graph for '{place}' from OpenStreetMap...")
    try:
        # Try loading by place name
        G = ox.graph_from_place(place, network_type='drive', simplify=True)
        logger.info(f"Loaded {len(G.nodes)} nodes and {len(G.edges)} edges")
        
        # Add edge lengths if not present
        G = ox.distance.add_edge_lengths(G)
        
        # Save to cache
        save_graph_to_cache(place, G)
        
        _current_graph = G
        _current_place = place
        
        return G
    except Exception as e:
        logger.error(f"Failed to load graph for '{place}': {str(e)}")
        import traceback
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        
        # Fallback: create a minimal test graph
        logger.warning("Creating minimal test graph as fallback")
        G = create_test_graph()
        _current_graph = G
        _current_place = "test_graph"
        return G

def create_test_graph():
    """Create a minimal test graph for basic functionality."""
    logger.info("Creating minimal test graph...")
    
    # Create a simple 5-node graph
    G = nx.DiGraph()
    
    # Add nodes with coordinates (around Kuala Lumpur)
    nodes = [
        (0, {"y": 3.139, "x": 101.6869}),  # KL City Center
        (1, {"y": 3.150, "x": 101.7000}),  # Northeast
        (2, {"y": 3.130, "x": 101.6800}),  # Southwest
        (3, {"y": 3.145, "x": 101.6900}),  # North
        (4, {"y": 3.135, "x": 101.6850}),  # Center-South
    ]
    
    G.add_nodes_from(nodes)
    
    # Add edges with lengths
    edges = [
        (0, 1, {"length": 2000.0}),
        (1, 0, {"length": 2000.0}),
        (0, 2, {"length": 1500.0}),
        (2, 0, {"length": 1500.0}),
        (0, 3, {"length": 1000.0}),
        (3, 0, {"length": 1000.0}),
        (0, 4, {"length": 800.0}),
        (4, 0, {"length": 800.0}),
        (1, 3, {"length": 1200.0}),
        (3, 1, {"length": 1200.0}),
        (2, 4, {"length": 900.0}),
        (4, 2, {"length": 900.0}),
        (3, 4, {"length": 1100.0}),
        (4, 3, {"length": 1100.0}),
    ]
    
    G.add_edges_from(edges)
    
    logger.info(f"Test graph created with {len(G.nodes)} nodes and {len(G.edges)} edges")
    return G

def get_available_cities():
    """Get list of available cached cities."""
    cities = []
    
    # Check cache directory for saved graphs
    if os.path.exists(CACHE_DIR):
        for filename in os.listdir(CACHE_DIR):
            if filename.startswith("graph_") and filename.endswith(".pkl"):
                city_name = filename[6:-4].replace("_", " ")
                cities.append(city_name)
    
    # Always include default options
    default_cities = [
        "Kuala Lumpur, Malaysia",
        "Singapore, Singapore",
        "Penang, Malaysia",
        "Johor Bahru, Malaysia"
    ]
    
    for city in default_cities:
        if city not in cities:
            cities.append(city)
    
    return cities

def get_node_coordinates(graph, node_id):
    """Get coordinates for a node."""
    if node_id in graph.nodes:
        node_data = graph.nodes[node_id]
        return (node_data.get('y'), node_data.get('x'))
    return None

def get_full_path_coordinates(start_id, end_id, place=None):
    """
    Get full path coordinates between two nodes.
    Returns list of (lat, lon) tuples.
    """
    import networkx as nx
    
    target_place = place or "Kuala Lumpur, Malaysia"
    graph = load_graph(target_place)
    
    if graph is None:
        return []
    
    try:
        # Convert string IDs to integers
        start_node = int(start_id)
        end_node = int(end_id)
        
        # Check if nodes exist
        if start_node not in graph.nodes or end_node not in graph.nodes:
            logger.warning(f"Nodes {start_node} or {end_node} not found in graph")
            return []
        
        # Compute shortest path
        path = nx.shortest_path(graph, start_node, end_node, weight='length')
        
        # Extract coordinates for each node in path
        coordinates = []
        for node in path:
            if 'y' in graph.nodes[node] and 'x' in graph.nodes[node]:
                lat = graph.nodes[node]['y']
                lon = graph.nodes[node]['x']
                coordinates.append([lat, lon])
        
        return coordinates
    except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
        logger.warning(f"No path found between {start_id} and {end_id}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error getting path coordinates: {e}")
        return []

def find_nearest_nodes(lat: float, lon: float, radius: float = 1000, place: str = "Kuala Lumpur, Malaysia"):
    """
    Find nodes within a radius of the given coordinates.
    
    Args:
        lat: Latitude of the center point
        lon: Longitude of the center point
        radius: Search radius in meters
        place: Place name to load the graph for
        
    Returns:
        List of dictionaries with node information
    """
    try:
        # Load graph
        graph = load_graph(place)
        
        if graph is None or len(graph.nodes) == 0:
            logger.warning(f"No graph available for {place}")
            return []
        
        nearby_nodes = []
        
        # Search through all nodes
        for node_id, node_data in graph.nodes(data=True):
            node_lat = node_data.get('y')
            node_lon = node_data.get('x')
            
            if node_lat is None or node_lon is None:
                continue
            
            # Calculate distance from center point
            distance = haversine_distance(lat, lon, node_lat, node_lon)
            
            if distance <= radius:
                nearby_nodes.append({
                    'id': str(node_id),
                    'lat': node_lat,
                    'lon': node_lon,
                    'distance': round(distance, 2)
                })
        
        # Sort by distance
        nearby_nodes.sort(key=lambda x: x['distance'])
        
        logger.info(f"Found {len(nearby_nodes)} nodes within {radius}m of ({lat}, {lon})")
        
        return nearby_nodes
        
    except Exception as e:
        logger.error(f"Error finding nearest nodes: {e}")
        return []


def get_graph_stats(place: str = "Kuala Lumpur, Malaysia") -> dict:
    """
    Get statistics about the loaded graph.
    
    Args:
        place: Name of the place/city
        
    Returns:
        Dictionary with graph statistics (node_count, edge_count)
    """
    try:
        graph = load_graph(place)
        return {
            "node_count": graph.number_of_nodes(),
            "edge_count": graph.number_of_edges(),
            "place": place
        }
    except Exception as e:
        logger.error(f"Error getting graph stats: {e}")
        return {
            "node_count": 0,
            "edge_count": 0,
            "place": place,
            "error": str(e)
        }
