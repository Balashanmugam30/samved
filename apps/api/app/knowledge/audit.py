"""Audit logging for document ingestion, version changes, and knowledge retrieval queries."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.knowledge.models import IngestionAuditRecord, KnowledgeSearchResult


class KnowledgeAuditLogger:
    """Thread-safe bounded audit logger for Phase 10 Knowledge operations."""

    def __init__(self, max_records: int = 1000):
        self._max_records = max_records
        self._ingestion_audit: List[IngestionAuditRecord] = []
        self._search_audit: List[KnowledgeSearchResult] = []
        self._lock = asyncio.Lock()

    async def log_ingestion(self, record: IngestionAuditRecord) -> None:
        """Logs an ingestion or document status modification event."""
        async with self._lock:
            self._ingestion_audit.append(record)
            if len(self._ingestion_audit) > self._max_records:
                self._ingestion_audit = self._ingestion_audit[-self._max_records :]

    async def log_search(self, result: KnowledgeSearchResult) -> None:
        """Logs a search query execution and returned citations."""
        async with self._lock:
            self._search_audit.append(result)
            if len(self._search_audit) > self._max_records:
                self._search_audit = self._search_audit[-self._max_records :]

    async def get_ingestion_history(self, limit: int = 50) -> List[IngestionAuditRecord]:
        """Returns recent ingestion audit entries."""
        async with self._lock:
            return list(reversed(self._ingestion_audit[-limit:]))

    async def get_search_history(self, call_id: Optional[str] = None, limit: int = 50) -> List[KnowledgeSearchResult]:
        """Returns recent search query executions, optionally filtered by call_id."""
        async with self._lock:
            if call_id:
                filtered = [s for s in self._search_audit if s.call_id == call_id]
                return list(reversed(filtered[-limit:]))
            return list(reversed(self._search_audit[-limit:]))


# Global audit logger singleton
knowledge_audit_logger = KnowledgeAuditLogger()
