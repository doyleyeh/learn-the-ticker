"""Dormant persistence baseline scaffold.

Revision ID: 20260425_0001
Revises:
Create Date: 2026-04-25 03:56:46 UTC

This intentionally creates no tables. The persistence boundary is present so
future migrations have a deterministic base, while current app behavior remains
fixture-backed and does not use a live database.
"""
from __future__ import annotations

from typing import Sequence


revision: str = "20260425_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
