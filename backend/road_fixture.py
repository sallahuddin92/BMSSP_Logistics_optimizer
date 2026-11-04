"""Explicit, checksum-verified local OSM fixtures; no network or pickle loading.

Set ROAD_FIXTURE_ROOT, select place='osm-fixture:seremban-small'. Files are
operator-owned input, not a cryptographically authenticated source of OSM truth.
Native snapshots still copy and validate all routing content on capture.
"""

import hashlib
import json
import os
from pathlib import Path
import threading
from xml.etree.ElementTree import ParseError
import networkx as nx
import osmnx as ox
from native_graph import NativeUnavailable, RoutingBudgetExceeded

REGIONS = ("seremban-small", "seremban-medium", "seremban-port-dickson")
PREFIX = "osm-fixture:"
_lock = threading.RLock()
_cache = {}  # At most three declared fixture graphs; never used for arbitrary paths.


def _read_bounded(path, limit):
    with path.open("rb") as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError(f"{path.name} exceeds {limit} byte input budget")
    return content


def load_fixture(place):
    name = place.removeprefix(PREFIX)
    if not place.startswith(PREFIX) or name not in REGIONS:
        raise NativeUnavailable("Unknown prepared OSM fixture")
    root = os.environ.get("ROAD_FIXTURE_ROOT")
    if not root:
        raise NativeUnavailable(
            "ROAD_FIXTURE_ROOT is not configured; run explicit preparation"
        )
    directory = Path(root).resolve() / name
    try:
        manifest_path = directory / "manifest.json"
        manifest_bytes = _read_bounded(manifest_path, 65536)
        manifest = json.loads(manifest_bytes)
        if (
            manifest["schema"] != 1
            or manifest["region"] != name
            or manifest["graph_file"] != "graph.graphml"
            or manifest["osmnx"] != "1.6.0"
            or manifest["source"]["url"]
            != "https://download.geofabrik.de/asia/malaysia-singapore-brunei-latest.osm.pbf"
            or len(manifest["source"]["sha256"]) != 64
            or not manifest["extraction_utc"]
            or manifest["license"] != "ODbL 1.0"
        ):
            raise ValueError("Unsupported fixture provenance")
        path = directory / "graph.graphml"
        # Always verify bytes: timestamps/object identity cannot certify mutable files.
        content = _read_bounded(path, 128 * 1024**2)
        if hashlib.sha256(content).hexdigest() != manifest["graph_sha256"]:
            raise ValueError("Graph checksum mismatch")
        key = (
            str(directory),
            hashlib.sha256(manifest_bytes).hexdigest(),
            manifest["graph_sha256"],
        )
        with _lock:
            if name in _cache and _cache[name][0] == key:
                return _cache[name][1]
            graph = ox.load_graphml(graphml_str=content.decode("utf-8"))
            from graph_loader import validate_preserved_road_lengths

            validate_preserved_road_lengths(graph)
            if (
                len(graph) != manifest["nodes"]
                or graph.number_of_edges() != manifest["edges"]
                or graph.graph.get("routing_data_origin") != "osm"
                or graph.graph.get("routing_length_policy") != "osmnx_preserved_v1"
                or graph.graph.get("routing_weight_units") != "meters"
            ):
                raise ValueError("Graph provenance/count mismatch")
            from native_graph import SnapshotCache

            snapshot, _ = SnapshotCache().get(graph)
            if snapshot.snapshot_id != manifest["snapshot_id"]:
                raise ValueError("Canonical routing snapshot mismatch")
            graph.graph["road_fixture_provenance"] = manifest
            from dataclasses import replace

            snapshot = replace(
                snapshot, provenance_json=json.dumps(manifest, sort_keys=True)
            )
            _cache[name] = (key, graph, snapshot)
            return graph
    except RoutingBudgetExceeded:
        raise
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        ParseError,
        nx.NetworkXException,
    ) as exc:
        raise NativeUnavailable(
            f"Prepared OSM fixture validation failed: {exc}"
        ) from exc


def load_fixture_snapshot(place):
    """Return the private captured snapshot, never trust the mutable legacy graph.

    Verify current file bytes on every selection; an already returned snapshot
    remains a valid immutable version even if the operator replaces a file later.
    """
    with _lock:
        load_fixture(place)
        return _cache[place.removeprefix(PREFIX)][2]
