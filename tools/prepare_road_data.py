#!/usr/bin/env python3
"""Bounded, explicit OSM download/extraction. Never called by the application.
Requires OSMnx==1.6.0 and osmium==4.2.0. Datasets stay outside the repository.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import resource
import shutil
import time
import urllib.request
import xml.etree.ElementTree as ET

SOURCE = "https://download.geofabrik.de/asia/malaysia-singapore-brunei-latest.osm.pbf"
REGIONS = {
    "seremban-small": (2.718, 101.925, 2.742, 101.953),
    "seremban-medium": (2.66, 101.86, 2.80, 102.01),
    "seremban-port-dickson": (2.47, 101.76, 2.80, 102.02),
}
BUDGET = 1024**3
RESERVE = 5 * 1024**3
MAX_SOURCE = 300 * 1024**2
MAX_NODES = 1_000_000
MAX_WAYS = 150_000


def digest(path, algorithm="sha256"):
    h = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024**2), b""):
            h.update(chunk)
    return h.hexdigest()


def check_space(root, extra=0):
    used = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
    if used + extra > BUDGET or shutil.disk_usage(root).free - extra < RESERVE:
        raise RuntimeError(
            f"Budget exceeded: used={used}, extra={extra}, budget={BUDGET}, reserve={RESERVE}"
        )


def download(root):
    target = root / "source.osm.pbf"
    metadata = root / "source.json"
    if metadata.exists() and target.exists():
        info = json.loads(metadata.read_text())
        if info["url"] != SOURCE or not 0 < info["bytes"] <= MAX_SOURCE:
            raise RuntimeError(
                "Cached source metadata does not match bounded Geofabrik input"
            )
        if digest(target) != info["sha256"] or target.stat().st_size != info["bytes"]:
            raise RuntimeError("Cached source checksum/size mismatch; refusing reuse")
        return target, info
    if target.exists() or metadata.exists() or target.with_suffix(".partial").exists():
        raise RuntimeError(
            "Incomplete source exists; inspect it explicitly before retrying"
        )
    request = urllib.request.Request(SOURCE, method="HEAD")
    with urllib.request.urlopen(request, timeout=60) as response:
        headers = dict(response.headers)
        size = int(response.headers["Content-Length"])
    if not 0 < size <= MAX_SOURCE:
        raise RuntimeError(f"Source size {size} exceeds {MAX_SOURCE}")
    check_space(root, size)
    with urllib.request.urlopen(SOURCE + ".md5", timeout=60) as response:
        md5 = response.read(4096).decode().split()[0]
    if not re.fullmatch("[0-9a-f]{32}", md5):
        raise RuntimeError("Invalid source MD5 sidecar")
    print(
        f"Downloading {size} bytes; budget {BUDGET}; disk reserve {RESERVE}", flush=True
    )
    start = time.perf_counter()
    partial = target.with_suffix(".partial")
    with urllib.request.urlopen(SOURCE, timeout=60) as response, partial.open(
        "xb"
    ) as out:
        count = 0
        while chunk := response.read(1024**2):
            count += len(chunk)
            if count > size:
                raise RuntimeError("Source grew during download")
            check_space(root, len(chunk))
            out.write(chunk)
    if count != size or digest(partial, "md5") != md5:
        raise RuntimeError("Source changed or download corrupt; partial retained")
    info = dict(
        url=SOURCE,
        headers=headers,
        bytes=count,
        md5=md5,
        sha256=digest(partial),
        downloaded_utc=datetime.now(timezone.utc).isoformat(),
        download_seconds=time.perf_counter() - start,
    )
    partial.rename(target)
    metadata.write_text(json.dumps(info, indent=2))
    return target, info


def prepare(root):
    repository = Path(__file__).resolve().parents[1]
    if (
        root == repository
        or root.is_relative_to(repository)
        or repository.is_relative_to(root)
    ):
        raise RuntimeError(
            "Use a dedicated data directory outside the repository and its ancestors"
        )
    allowed = {
        "source.osm.pbf",
        "source.json",
        "source.osm.partial",
        ".DS_Store",
        *REGIONS,
    }
    if any(path.name not in allowed for path in root.iterdir()):
        raise RuntimeError(
            "Data directory contains unrelated files; use a dedicated directory"
        )
    import osmium
    import osmnx as ox
    import networkx as nx

    if ox.__version__ != "1.6.0":
        raise RuntimeError("Importer requires OSMnx 1.6.0 semantics")
    pbf, source = download(root)
    with osmium.io.Reader(str(pbf)) as reader:
        source["osm_replication_timestamp"] = reader.header().get(
            "osmosis_replication_timestamp"
        )
    complete = True
    for name in REGIONS:
        directory = root / name
        if not (directory / "manifest.json").exists():
            complete = False
            break
        previous = json.loads((directory / "manifest.json").read_text())
        if (
            previous["source"]["sha256"] != source["sha256"]
            or digest(directory / "graph.graphml") != previous["graph_sha256"]
        ):
            raise RuntimeError(
                f"{directory}: existing fixture checksum/source mismatch"
            )
    if complete:
        print(
            "All three source/file-checksum-verified fixtures already exist; no extraction needed",
            flush=True,
        )
        return
    # No nationwide node-location index: only IDs in the declared rectangles.
    sets = {name: set() for name in REGIONS}
    start = time.perf_counter()

    class Bounds(osmium.SimpleHandler):
        def node(self, n):
            for name, (s, w, north, e) in REGIONS.items():
                if s <= n.location.lat <= north and w <= n.location.lon <= e:
                    sets[name].add(n.id)
                    if len(sets[name]) > MAX_NODES:
                        raise RuntimeError(f"{name}: node budget {MAX_NODES} exceeded")

    Bounds().apply_file(str(pbf))
    scan_nodes = time.perf_counter() - start
    print(
        f"Node scan: {scan_nodes:.3f}s; rectangle nodes: {[(k,len(v)) for k,v in sets.items()]}",
        flush=True,
    )
    from osmnx._overpass import _get_osm_filter

    filter_text = _get_osm_filter("drive")
    clauses = re.findall(r'\["([^"\]]+)"(?:!~"([^"]*)")?\]', filter_text)

    def driving(tags):
        return all(
            (
                key in tags
                if not excluded
                else not re.search(excluded, tags.get(key, ""))
            )
            for key, excluded in clauses
        )

    ways = {name: [] for name in REGIONS}
    wanted = set()
    start = time.perf_counter()

    class Ways(osmium.SimpleHandler):
        def way(self, way):
            tags = dict(way.tags)
            if not driving(tags):
                return
            refs = [n.ref for n in way.nodes]
            names = [name for name, ids in sets.items() if not ids.isdisjoint(refs)]
            if names:
                record = (way.id, refs, tags)
                for name in names:
                    ways[name].append(record)
                    if len(ways[name]) > MAX_WAYS:
                        raise RuntimeError(f"{name}: way budget {MAX_WAYS} exceeded")
                wanted.update(refs)
                if len(wanted) > MAX_NODES:
                    raise RuntimeError(f"Complete-way nodes exceed {MAX_NODES}")

    Ways().apply_file(str(pbf))
    scan_ways = time.perf_counter() - start
    print(f"Way scan: {scan_ways:.3f}s; wanted nodes: {len(wanted)}", flush=True)
    sets.clear()
    coords = {}
    start = time.perf_counter()

    class Locations(osmium.SimpleHandler):
        def node(self, n):
            if n.id in wanted:
                coords[n.id] = (n.location.lat, n.location.lon, dict(n.tags))

    Locations().apply_file(str(pbf))
    scan_coords = time.perf_counter() - start
    print(f"Coordinate scan: {scan_coords:.3f}s", flush=True)
    if coords.keys() != wanted:
        raise RuntimeError("Source has missing selected-way node references")
    from native_graph import SnapshotCache

    for name, records in ways.items():
        directory = root / name
        if (directory / "manifest.json").exists():
            previous = json.loads((directory / "manifest.json").read_text())
            if (
                previous["source"]["sha256"] != source["sha256"]
                or digest(directory / "graph.graphml") != previous["graph_sha256"]
            ):
                raise RuntimeError(
                    f"{directory}: existing fixture does not match verified source"
                )
            print(f"Reusing verified {name}", flush=True)
            continue
        directory.mkdir(exist_ok=True)
        check_space(root)
        start = time.perf_counter()
        xml = ET.Element(
            "osm", version="0.6", generator="BMSSP bounded fixture importer"
        )
        ids = {n for _, refs, _ in records for n in refs}
        for node in sorted(ids):
            lat, lon, tags = coords[node]
            element = ET.SubElement(
                xml, "node", id=str(node), lat=str(lat), lon=str(lon)
            )
            for k, v in sorted(tags.items()):
                ET.SubElement(element, "tag", k=k, v=v)
        for way, refs, tags in sorted(records):
            element = ET.SubElement(xml, "way", id=str(way))
            for node in refs:
                ET.SubElement(element, "nd", ref=str(node))
            for k, v in sorted(tags.items()):
                ET.SubElement(element, "tag", k=k, v=v)
        xml_path = directory / "roads.osm"
        xml_bytes = ET.tostring(xml, encoding="utf-8", xml_declaration=True)
        if xml_path.exists():
            if xml_path.read_bytes() != xml_bytes:
                raise RuntimeError(
                    f"{xml_path}: existing extraction differs; refusing overwrite"
                )
        else:
            check_space(root, len(xml_bytes))
            with xml_path.open("xb") as out:
                out.write(xml_bytes)
        graph = ox.graph_from_xml(
            xml_path, bidirectional=False, simplify=False, retain_all=True
        )
        graph = ox.simplification.simplify_graph(graph, remove_rings=False)
        graph.graph.update(
            routing_data_origin="osm",
            routing_length_policy="osmnx_preserved_v1",
            routing_weight_units="meters",
        )
        path = directory / "graph.graphml"
        if path.exists():
            # Reuse an interrupted build only if it represents exactly this XML.
            existing = ox.load_graphml(path)
            from native_graph import _capture, RoutingLimits

            limits = RoutingLimits.from_environment()
            if (
                _capture(existing, "length", limits)[0]
                != _capture(graph, "length", limits)[0]
            ):
                raise RuntimeError(
                    f"{path}: existing graph differs; refusing overwrite"
                )
        else:
            ox.save_graphml(graph, path)
        # Verify serialization preserves adapter identity as well as file bytes.
        loaded = ox.load_graphml(path)
        print(
            f"{name}: {len(loaded)} vertices, {loaded.number_of_edges()} edges; capturing with explicitly configured native limits",
            flush=True,
        )
        snapshot, _ = SnapshotCache().get(loaded)
        manifest = dict(
            schema=1,
            region=name,
            bbox_south_west_north_east=REGIONS[name],
            source=source,
            extraction_utc=datetime.now(timezone.utc).isoformat(),
            osmnx=ox.__version__,
            drive_filter=filter_text,
            graph_file="graph.graphml",
            graph_sha256=digest(path),
            snapshot_id=snapshot.snapshot_id,
            nodes=len(graph),
            edges=graph.number_of_edges(),
            weak_components=nx.number_weakly_connected_components(graph),
            strong_components=nx.number_strongly_connected_components(graph),
            oneway_edges=sum(
                bool(d.get("oneway")) for _, _, d in graph.edges(data=True)
            ),
            parallel_pairs=sum(
                graph.number_of_edges(u, v) > 1 for u, v in set(graph.edges())
            ),
            curved_edges=sum(
                len(d["geometry"].coords) > 2
                for _, _, d in graph.edges(data=True)
                if "geometry" in d
            ),
            max_node_id=max(graph),
            importer_peak_process_rss_bytes=resource.getrusage(
                resource.RUSAGE_SELF
            ).ru_maxrss,
            timings=dict(
                node_scan=scan_nodes,
                way_scan=scan_ways,
                coordinate_scan=scan_coords,
                xml_graph_build_save_validate=time.perf_counter() - start,
            ),
            limits=dict(
                storage_bytes=BUDGET,
                reserve_bytes=RESERVE,
                selected_nodes=MAX_NODES,
                ways=MAX_WAYS,
            ),
            selection="Complete driving ways having at least one OSM node inside rectangle; retained all components and rings. Boundary-clipped workload, not complete regional coverage.",
            unsupported=[
                "turn restrictions",
                "conditional/dynamic access",
                "traffic",
                "travel times",
            ],
            attribution="© OpenStreetMap contributors",
            license="ODbL 1.0",
            license_url="https://www.openstreetmap.org/copyright",
        )
        (directory / "manifest.json").write_text(json.dumps(manifest, indent=2))
        print(json.dumps(manifest), flush=True)
        check_space(root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    prepare(args.output.resolve())
