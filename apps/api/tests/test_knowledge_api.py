"""Tests for Knowledge RAG REST API endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_knowledge_status():
    resp = client.get("/v1/knowledge/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "READY"
    assert "knowledge-index" in data["index_version"]
    assert data["total_documents"] >= 4
    assert len(data["supported_jurisdictions"]) >= 3


def test_list_sources():
    resp = client.get("/v1/knowledge/sources")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sources"] >= 4
    assert len(data["sources"]) >= 4


def test_search_endpoint():
    payload = {
        "query": "One Stop Centre shelter admission",
        "jurisdiction": "INDIA",
        "effective_only": True,
        "max_results": 3,
    }
    resp = client.post("/v1/knowledge/search", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["total_found"] > 0
    assert len(data["citations"]) > 0
    assert data["citations"][0]["citation_id"] != ""


def test_get_document_and_versions_and_citations():
    # First search to get a document ID and citation ID
    search_resp = client.post("/v1/knowledge/search", json={"query": "helpline 181 SOP"})
    assert search_resp.status_code == 200
    results = search_resp.json()["results"]
    assert len(results) > 0

    doc_id = results[0]["document_id"]
    cit_id = results[0]["citation"]["citation_id"]

    # 1. Get document
    doc_resp = client.get(f"/v1/knowledge/documents/{doc_id}")
    assert doc_resp.status_code == 200
    assert doc_resp.json()["document_id"] == doc_id

    # 2. Get document versions
    vers_resp = client.get(f"/v1/knowledge/documents/{doc_id}/versions")
    assert vers_resp.status_code == 200
    assert len(vers_resp.json()) >= 1

    # 3. Get citation
    cit_resp = client.get(f"/v1/knowledge/citations/{cit_id}")
    assert cit_resp.status_code == 200
    assert cit_resp.json()["citation_id"] == cit_id


def test_ingest_endpoint_validation():
    payload = {
        "title": "API Ingested Scheme",
        "publisher": "Legal Department",
        "source_url": "https://gov.in/legal-scheme",
        "content": "# Scheme Title\nEmergency relief of Rs 50,000 for victims.",
        "jurisdiction": "INDIA",
        "version": "1.0",
        "effective_from": "2023-01-01",
    }
    resp = client.post("/v1/knowledge/ingest", json=payload)
    assert resp.status_code == 201
    assert resp.json()["title"] == "API Ingested Scheme"
