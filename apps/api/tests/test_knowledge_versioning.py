"""Tests for versioning, superseding, and temporal freshness."""

import pytest
from app.knowledge.models import DocumentStatus, FreshnessStatus
from app.knowledge.versioning import calculate_freshness, is_version_effective


def test_effective_date_validation():
    # Valid within window
    assert is_version_effective(
        effective_from="2022-01-01",
        effective_to="2025-12-31",
        as_of_date="2023-06-15",
    ) is True

    # Expired before query date
    assert is_version_effective(
        effective_from="2020-01-01",
        effective_to="2022-12-31",
        as_of_date="2023-01-01",
    ) is False

    # Query date precedes effective start
    assert is_version_effective(
        effective_from="2024-01-01",
        effective_to=None,
        as_of_date="2023-06-01",
    ) is False

    # Open-ended current version
    assert is_version_effective(
        effective_from="2022-01-01",
        effective_to=None,
        as_of_date="2026-09-01",
    ) is True


def test_freshness_calculation():
    # Active current document
    freshness = calculate_freshness(
        effective_from="2022-01-01",
        effective_to=None,
        status=DocumentStatus.ACTIVE,
        as_of_date="2023-06-01",
    )
    assert freshness == FreshnessStatus.CURRENT

    # Superseded document
    stale_freshness = calculate_freshness(
        effective_from="2020-01-01",
        effective_to="2022-12-31",
        status=DocumentStatus.SUPERSEDED,
        as_of_date="2023-06-01",
    )
    assert stale_freshness == FreshnessStatus.STALE

    # Expired past effective_to
    expired_freshness = calculate_freshness(
        effective_from="2020-01-01",
        effective_to="2021-12-31",
        status=DocumentStatus.ACTIVE,
        as_of_date="2023-06-01",
    )
    assert expired_freshness == FreshnessStatus.EXPIRED
