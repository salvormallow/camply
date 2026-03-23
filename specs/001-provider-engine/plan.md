# Implementation Plan: Provider Engine (BaseProvider ABC)

**Branch**: `001-provider-engine` | **Date**: 2026-03-22 | **Spec**: [/specs/001-provider-engine/spec.md]
**Input**: Feature specification from `/specs/001-provider-engine/spec.md`

## Summary

Implement a standardized Provider Engine by defining the `BaseProvider` Abstract Base Class (ABC) and a unified `CampsiteDTO`. This architecture enables multi-provider support, async-first scanning, and automated metadata synchronization, providing a consistent interface for the Smart Poller worker.

## Technical Context

**Language/Version**: Python 3.12 (managed by `uv`)
**Primary Dependencies**: `FastAPI`, `SQLAlchemy 2.0`, `httpx`, `Pydantic v2`, `structlog`
**Storage**: PostgreSQL (SQLAlchemy + Alembic)
**Testing**: `pytest` with `pytest-vcr` for API mocking
**Target Platform**: Linux / Docker
**Project Type**: Backend Package (`backend/packages/providers`)
**Performance Goals**: Sync 10,000+ park records daily; <1s overhead per availability check.
**Constraints**: All IO MUST be async; 100% type coverage for public interfaces; Standardized exceptions (`ProviderError`, `RateLimitError`, etc.).
**Scale/Scope**: Unified DTO for all providers; isolated provider-specific translation logic.

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

1. **Reliability & Precision**: Standardized `CampsiteDTO` and mandatory API verification in `find_availabilities`. (PASS)
2. **Type Safety & Static Analysis**: Strict Pydantic models (v2) and ABC method signatures. (PASS)
3. **Modern Workflow & Automation**: Integrated into `uv` workspace; all ops via `task`. (PASS)
4. **Monorepos & Separation of Concerns**: Logic isolated in `backend/packages/providers`, separated from worker and API logic. (PASS)
5. **Automated Verification**: Mandates `pytest` and VCR cassettes for all provider implementations. (PASS)

## Project Structure

### Documentation (this feature)

```text
specs/001-provider-engine/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
backend/
└── packages/
    ├── providers/
    │   ├── pyproject.toml
    │   ├── providers/
    │   │   ├── __init__.py
    │   │   ├── base.py          # BaseProvider ABC definition
    │   │   ├── dto.py           # Unified CampsiteDTO & Enums
    │   │   ├── exceptions.py    # Standardized provider exceptions
    │   │   └── recreation_gov/  # First provider migration target
    │   │       ├── __init__.py
    │   │       ├── client.py    # Async API client
    │   │       ├── models.py    # Internal Pydantic models
    │   │       └── provider.py  # Implementation of BaseProvider
    │   └── tests/
    │       ├── conftest.py
    │       ├── test_base_interface.py
    │       └── recreation_gov/
    │           ├── test_scanning.py
    │           └── test_metadata.py
```

**Structure Decision**: Using a specialized package-based structure within `backend/packages/providers`. Each provider gets its own sub-package to encapsulate internal models and API clients, while sharing the common `base.py` and `dto.py`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --------- | ---------- | ------------------------------------ |
| None      | N/A        | N/A                                  |
