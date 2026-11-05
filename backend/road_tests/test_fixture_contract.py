"""Input contract tests use a tiny synthetic file, never real-road evidence."""

import hashlib
import json
import networkx as nx
import osmnx as ox
import pytest
from native_graph import SnapshotCache, NativeUnavailable
import road_fixture


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.setenv("ROAD_FIXTURE_ROOT", str(tmp_path))
    directory = tmp_path / "seremban-small"
    directory.mkdir()
    graph = nx.MultiDiGraph(
        crs="EPSG:4326",
        routing_data_origin="osm",
        routing_length_policy="osmnx_preserved_v1",
        routing_weight_units="meters",
    )
    graph.add_node(2**40, x=101.94, y=2.73)
    graph.add_node(2**40 + 1, x=101.95, y=2.73)
    graph.add_edge(2**40, 2**40 + 1, key=0, length=1.0)
    path = directory / "graph.graphml"
    ox.save_graphml(graph, path)
    snapshot, _ = SnapshotCache().get(ox.load_graphml(path))
    manifest = dict(
        schema=1,
        region="seremban-small",
        graph_file="graph.graphml",
        osmnx="1.6.0",
        source=dict(
            url="https://download.geofabrik.de/asia/malaysia-singapore-brunei-latest.osm.pbf",
            sha256="0" * 64,
        ),
        extraction_utc="synthetic-contract-test-only",
        license="ODbL 1.0",
        nodes=2,
        edges=1,
        graph_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        snapshot_id=snapshot.snapshot_id,
    )
    (directory / "manifest.json").write_text(json.dumps(manifest))
    road_fixture._cache.clear()
    return directory, manifest


def test_local_selection_and_checksum(prepared):
    directory, manifest = prepared
    graph = road_fixture.load_fixture("osm-fixture:seremban-small")
    assert len(graph) == 2
    assert road_fixture.load_fixture("osm-fixture:seremban-small") is graph
    with (directory / "graph.graphml").open("ab") as out:
        out.write(b" ")
    with pytest.raises(NativeUnavailable, match="checksum"):
        road_fixture.load_fixture("osm-fixture:seremban-small")


def test_manifest_and_snapshot_tamper(prepared):
    directory, manifest = prepared
    manifest["snapshot_id"] = "bad"
    (directory / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(NativeUnavailable, match="snapshot"):
        road_fixture.load_fixture("osm-fixture:seremban-small")
    manifest["graph_file"] = "../../other.graphml"
    (directory / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(NativeUnavailable, match="provenance"):
        road_fixture.load_fixture("osm-fixture:seremban-small")


def test_no_implicit_download_or_arbitrary_path(monkeypatch):
    monkeypatch.delenv("ROAD_FIXTURE_ROOT", raising=False)
    with pytest.raises(NativeUnavailable, match="not configured"):
        road_fixture.load_fixture("osm-fixture:seremban-small")
    with pytest.raises(NativeUnavailable, match="Unknown"):
        road_fixture.load_fixture("osm-fixture:../../anything")


def test_opt_in_profile_preserves_results():
    import bmssp_native as native

    graph = native.NativeGraph(
        [0, 1, 2], [(0, 0, 1, 1.0), (1, 1, 2, 0.0), (2, 0, 2, 1.0)]
    )
    engine = native.BMSSP2025Engine(graph)
    before = engine.solve(0)
    profiled = engine.solve(0, profile=True)
    after = engine.solve(0)
    assert before.distances == profiled.distances == after.distances
    assert before.path(2) == profiled.path(2) == after.path(2)
    assert all(row["calls"] == 0 for row in before.diagnostics["profile"].values())
    assert (
        profiled.diagnostics["profile"]["recursive_bmssp"]["calls"]
        == profiled.diagnostics["recursive_calls"]
    )
    assert (
        profiled.diagnostics["profile"]["label_creation"]["calls"]
        == profiled.diagnostics["label_nodes_materialized"]
        == 1 + profiled.diagnostics["label_updates"]
    )

    # Logical candidate work remains deterministic; arena publication is now
    # separately counted and excludes rejected/equality-only temporary nodes.
    assert (
        profiled.diagnostics["label_nodes_materialized"]
        < profiled.diagnostics["label_nodes_created"]
    )
    for field in (
        "relaxed_edges",
        "label_nodes_created",
        "label_nodes_materialized",
        "label_updates",
        "equality_relaxations",
    ):
        assert (
            before.diagnostics[field]
            == profiled.diagnostics[field]
            == after.diagnostics[field]
        )


def test_immutable_snapshot_reuse_is_explicit_and_budgeted(prepared, monkeypatch):
    from native_graph import RoutingLimits, RoutingBudgetExceeded

    graph = road_fixture.load_fixture("osm-fixture:seremban-small")
    snapshot = road_fixture.load_fixture_snapshot("osm-fixture:seremban-small")
    a, _ = SnapshotCache().get(snapshot)
    assert a is snapshot
    # Mutable legacy object is separate from the routing input contract.
    graph[2**40][2**40 + 1][0]["length"] = 999.0
    assert road_fixture.load_fixture_snapshot("osm-fixture:seremban-small") is snapshot
    assert (
        snapshot.engine("native_bmssp_2025")[0].solve(2**40).distance(2**40 + 1) == 1.0
    )
    changed, _ = SnapshotCache().get(graph)
    assert changed.snapshot_id != snapshot.snapshot_id
    with pytest.raises(RoutingBudgetExceeded):
        SnapshotCache().get(snapshot, limits=RoutingLimits(max_nodes=1))


def test_prepared_vrp_requires_native_selection(prepared):
    from fastapi.testclient import TestClient
    import api

    client = TestClient(api.app)
    response = client.post(
        "/vrp", json={"locations": ["1", "2"], "place": "osm-fixture:seremban-small"}
    )
    assert response.status_code == 400
    response = client.post(
        "/search-nodes?place=osm-fixture:seremban-small",
        json={"lat": 2.73, "lon": 101.94, "radius": 100},
    )
    assert response.status_code == 400
