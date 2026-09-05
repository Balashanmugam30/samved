"""Test suite for Case Intelligence concurrent mutations (Phase 11)."""

import asyncio
import pytest
from app.cases.service import CaseService
from app.schemas.events import EntityType, RelationshipType


@pytest.mark.asyncio
async def test_concurrent_entity_and_edge_additions():
    svc = CaseService(auto_seed=False)
    case = await svc.create_case(case_number="CAS-CONC-001")

    # Pre-create root entity
    root = await svc.add_entity(case.case_id, EntityType.PERSON, "Root Caller")

    async def add_leaf(i: int):
        node = await svc.add_entity(case.case_id, EntityType.PERSON, f"Contact {i}")
        edge = await svc.add_relationship(
            case_id=case.case_id,
            source_entity=root.entity_id,
            relationship_type=RelationshipType.CONNECTED_TO,
            target_entity=node.entity_id,
        )
        return node, edge

    results = await asyncio.gather(*[add_leaf(i) for i in range(20)])
    assert len(results) == 20

    graph = await svc.get_graph(case.case_id, max_depth=2)
    assert graph.total_nodes == 21  # root + 20 contacts
    assert graph.total_edges == 20


@pytest.mark.asyncio
async def test_concurrent_candidate_actions():
    svc = CaseService(auto_seed=False)
    case = await svc.create_case(case_number="CAS-CONC-002")

    # Add candidates
    cands = []
    for i in range(10):
        c = await svc.add_candidate(
            case_id=case.case_id,
            source_entity="ent-caller",
            source_label="Caller",
            relationship_type=RelationshipType.CONNECTED_TO,
            target_entity=f"ent-target-{i}",
            target_label=f"Person {i}",
            evidence_excerpt=f"I spoke to person {i}.",
        )
        cands.append(c)

    async def confirm_or_reject(c, index):
        if index % 2 == 0:
            return await svc.confirm_candidate(case.case_id, c.candidate_id)
        else:
            return await svc.reject_candidate(case.case_id, c.candidate_id)

    results = await asyncio.gather(*[confirm_or_reject(c, i) for i, c in enumerate(cands)])
    assert len(results) == 10

    # 5 confirmed, 5 rejected
    graph = await svc.get_graph(case.case_id)
    assert len(graph.edges) == 5
