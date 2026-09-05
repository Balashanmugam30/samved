"""Test suite for Case Intelligence graph traversal, bounding, and integrity verification."""

import pytest
from app.cases.graph import extract_subgraph, get_entity_neighbors, verify_integrity
from app.cases.models import CaseEntity, CaseGraph, CaseRelationship
from app.schemas.events import ClaimStatus, EntityType, RelationshipType


def test_subgraph_depth_bounding():
    # Construct a chain of 6 nodes: N0 -> N1 -> N2 -> N3 -> N4 -> N5
    nodes = [
        CaseEntity(entity_id=f"n{i}", case_id="case-sub", type=EntityType.PERSON, label=f"Node {i}")
        for i in range(6)
    ]
    edges = [
        CaseRelationship(
            edge_id=f"e{i}",
            case_id="case-sub",
            source_entity=f"n{i}",
            relationship_type=RelationshipType.CONNECTED_TO,
            target_entity=f"n{i+1}",
        )
        for i in range(5)
    ]
    full_graph = CaseGraph(case_id="case-sub", nodes=nodes, edges=edges)

    # Max depth requested = 10, but must be bounded to 4
    subgraph = extract_subgraph(full_graph, focus_entity_ids=["n0"], max_depth=10)
    assert subgraph.statistics["depth_applied"] == 4
    # Nodes reachable within 4 hops from n0 are n0, n1, n2, n3, n4 (5 nodes)
    assert len(subgraph.nodes) == 5
    assert "n5" not in [n.entity_id for n in subgraph.nodes]


def test_neighbor_query():
    n0 = CaseEntity(entity_id="n0", case_id="c1", type=EntityType.PERSON, label="Center")
    n1 = CaseEntity(entity_id="n1", case_id="c1", type=EntityType.PERSON, label="Inbound Peer")
    n2 = CaseEntity(entity_id="n2", case_id="c1", type=EntityType.PERSON, label="Outbound Peer")

    e_in = CaseRelationship(
        edge_id="e-in",
        case_id="c1",
        source_entity="n1",
        relationship_type=RelationshipType.SUPPORTS,
        target_entity="n0",
    )
    e_out = CaseRelationship(
        edge_id="e-out",
        case_id="c1",
        source_entity="n0",
        relationship_type=RelationshipType.CONNECTED_TO,
        target_entity="n2",
    )

    graph = CaseGraph(case_id="c1", nodes=[n0, n1, n2], edges=[e_in, e_out])
    neighbors = get_entity_neighbors(graph, "n0")

    assert len(neighbors["inbound"]) == 1
    assert len(neighbors["outbound"]) == 1
    assert len(neighbors["neighbors"]) == 2


def test_integrity_check_detects_dangling_edges():
    n1 = CaseEntity(entity_id="n1", case_id="c1", type=EntityType.PERSON, label="Valid Node")
    dangling_edge = CaseRelationship(
        edge_id="e-dangling",
        case_id="c1",
        source_entity="n1",
        relationship_type=RelationshipType.CONNECTED_TO,
        target_entity="n-missing",  # Not in nodes list
    )

    graph = CaseGraph(case_id="c1", nodes=[n1], edges=[dangling_edge])
    report = verify_integrity(graph)

    assert report["valid"] is False
    assert len(report["dangling_edges"]) == 1
    assert "n-missing" in report["dangling_edges"][0]
