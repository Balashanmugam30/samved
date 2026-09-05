"""Graph Traversal, Bounded Subgraph Extraction & Integrity Layer (Phase 11)."""

from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from app.cases.models import CaseCandidate, CaseEntity, CaseGraph, CaseRelationship
from app.cases.provenance import compute_evidence_hash
from app.cases.temporal import is_edge_active_at, parse_iso_datetime


def extract_subgraph(
    case_graph: CaseGraph,
    focus_entity_ids: Optional[List[str]] = None,
    max_depth: int = 2,
    as_of: Optional[str] = None,
) -> CaseGraph:
    """Extracts a bounded subgraph around focus entities or active graph up to max_depth (bounded 1-4)."""
    depth_limit = max(1, min(max_depth, 4))

    as_of_dt: Optional[datetime] = None
    if as_of:
        try:
            as_of_dt = parse_iso_datetime(as_of)
        except Exception:
            as_of_dt = datetime.now(timezone.utc)

    # Filter active edges
    active_edges = [
        edge for edge in case_graph.edges if is_edge_active_at(edge, as_of_dt)
    ]
    node_map = {n.entity_id: n for n in case_graph.nodes}

    if not focus_entity_ids:
        relevant_node_ids: Set[str] = set()
        for edge in active_edges:
            relevant_node_ids.add(edge.source_entity)
            relevant_node_ids.add(edge.target_entity)

        selected_nodes = [
            n for n in case_graph.nodes if n.entity_id in relevant_node_ids
        ][:200]
        if not selected_nodes and case_graph.nodes:
            selected_nodes = case_graph.nodes[:200]
            selected_node_ids = {n.entity_id for n in selected_nodes}
            selected_edges = [
                e
                for e in active_edges
                if e.source_entity in selected_node_ids
                and e.target_entity in selected_node_ids
            ][:400]
        else:
            selected_node_ids = {n.entity_id for n in selected_nodes}
            selected_edges = [
                e
                for e in active_edges
                if e.source_entity in selected_node_ids
                and e.target_entity in selected_node_ids
            ][:400]

        return CaseGraph(
            case_id=case_graph.case_id,
            nodes=selected_nodes,
            edges=selected_edges,
            candidates=case_graph.candidates,
            total_nodes=len(selected_nodes),
            total_edges=len(selected_edges),
            statistics={
                "depth_applied": 0,
                "as_of": as_of or "now",
                "active_edges_count": len(active_edges),
            },
        )

    # BFS from focus_entity_ids
    visited_nodes: Set[str] = set()
    queue: deque = deque()
    for f_id in focus_entity_ids:
        if f_id in node_map:
            visited_nodes.add(f_id)
            queue.append((f_id, 0))

    adjacency: Dict[str, List[CaseRelationship]] = {}
    for edge in active_edges:
        adjacency.setdefault(edge.source_entity, []).append(edge)
        adjacency.setdefault(edge.target_entity, []).append(edge)

    while queue:
        curr_id, curr_depth = queue.popleft()
        if curr_depth >= depth_limit:
            continue

        for edge in adjacency.get(curr_id, []):
            nbr = (
                edge.target_entity
                if edge.source_entity == curr_id
                else edge.source_entity
            )
            if nbr in node_map and nbr not in visited_nodes:
                visited_nodes.add(nbr)
                queue.append((nbr, curr_depth + 1))

    selected_nodes = [node_map[nid] for nid in visited_nodes if nid in node_map]
    selected_node_ids = {n.entity_id for n in selected_nodes}
    selected_edges = [
        e
        for e in active_edges
        if e.source_entity in selected_node_ids
        and e.target_entity in selected_node_ids
    ]

    return CaseGraph(
        case_id=case_graph.case_id,
        nodes=selected_nodes,
        edges=selected_edges,
        candidates=[
            c
            for c in case_graph.candidates
            if c.source_entity in selected_node_ids
            or c.target_entity in selected_node_ids
        ],
        total_nodes=len(selected_nodes),
        total_edges=len(selected_edges),
        statistics={
            "focus_entities": focus_entity_ids,
            "depth_applied": depth_limit,
            "as_of": as_of or "now",
        },
    )


def get_entity_neighbors(
    case_graph: CaseGraph,
    entity_id: str,
    depth: int = 1,
    as_of: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves direct inbound and outbound relationships and connected entities for a node."""
    subgraph = extract_subgraph(
        case_graph=case_graph,
        focus_entity_ids=[entity_id],
        max_depth=depth,
        as_of=as_of,
    )
    inbound_edges = [e for e in subgraph.edges if e.target_entity == entity_id]
    outbound_edges = [e for e in subgraph.edges if e.source_entity == entity_id]

    neighbor_node_ids = {
        e.source_entity for e in inbound_edges
    } | {
        e.target_entity for e in outbound_edges
    }
    neighbor_nodes = [n for n in subgraph.nodes if n.entity_id in neighbor_node_ids]

    return {
        "entity_id": entity_id,
        "inbound": [e.model_dump() for e in inbound_edges],
        "outbound": [e.model_dump() for e in outbound_edges],
        "neighbors": [n.model_dump() for n in neighbor_nodes],
        "total_neighbors": len(neighbor_nodes),
    }


def verify_integrity(case_graph: CaseGraph) -> Dict[str, Any]:
    """Audits graph integrity: dangling edges, temporal order anomalies, and evidence hash mismatches."""
    node_ids = {n.entity_id for n in case_graph.nodes}
    dangling_edges: List[str] = []
    temporal_anomalies: List[str] = []
    hash_mismatches: List[str] = []
    warnings: List[str] = []

    # Check edges
    for edge in case_graph.edges:
        if edge.source_entity not in node_ids:
            dangling_edges.append(
                f"Edge {edge.edge_id}: source entity '{edge.source_entity}' not in nodes"
            )
        if edge.target_entity not in node_ids:
            dangling_edges.append(
                f"Edge {edge.edge_id}: target entity '{edge.target_entity}' not in nodes"
            )

        # Temporal check
        if edge.valid_to:
            try:
                from_dt = parse_iso_datetime(edge.valid_from)
                to_dt = parse_iso_datetime(edge.valid_to)
                if from_dt > to_dt:
                    temporal_anomalies.append(
                        f"Edge {edge.edge_id}: valid_from ({edge.valid_from}) > valid_to ({edge.valid_to})"
                    )
            except Exception as e:
                warnings.append(
                    f"Edge {edge.edge_id}: datetime parsing issue: {str(e)}"
                )

        # Hash check on evidence
        for ev in edge.evidence:
            if ev.verbatim_excerpt and ev.content_hash:
                computed = compute_evidence_hash(ev.verbatim_excerpt)
                if computed != ev.content_hash:
                    hash_mismatches.append(
                        f"Edge {edge.edge_id} evidence {ev.link_id}: hash mismatch"
                    )

    # Check entity evidence hashes
    for node in case_graph.nodes:
        for ev in node.evidence:
            if ev.verbatim_excerpt and ev.content_hash:
                computed = compute_evidence_hash(ev.verbatim_excerpt)
                if computed != ev.content_hash:
                    hash_mismatches.append(
                        f"Node {node.entity_id} evidence {ev.link_id}: hash mismatch"
                    )

    is_valid = (
        len(dangling_edges) == 0
        and len(temporal_anomalies) == 0
        and len(hash_mismatches) == 0
    )

    return {
        "valid": is_valid,
        "case_id": case_graph.case_id,
        "nodes_count": len(case_graph.nodes),
        "edges_count": len(case_graph.edges),
        "candidates_count": len(case_graph.candidates),
        "dangling_edges": dangling_edges,
        "temporal_anomalies": temporal_anomalies,
        "hash_mismatches": hash_mismatches,
        "warnings": warnings,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
