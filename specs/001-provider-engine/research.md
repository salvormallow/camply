# Research: Provider Engine (BaseProvider ABC)

## Summary

The current `BaseProvider` implementation focuses on metadata synchronization and search table population. It lacks the core scanning interface (`find_availabilities`) and the unified data transfer object (`CampsiteDTO`) required for the Smart Poller architecture.

## Findings

### 1. Connection Management

- **Decision**: Providers will use a shared `httpx.AsyncClient` managed by the provider instance.
- **Rationale**: Reusing connections is critical for scanning performance (10k+ park records).
- **Alternatives**: Initializing a new client per request was rejected due to overhead and potential socket exhaustion.

### 2. Bulk Database Operations

- **Decision**: Continue using SQLAlchemy's `insert().from_select()` for metadata sync.
- **Rationale**: This is an efficient way to transfer data from internal tables (`Campground`, `RecreationArea`) to the `Search` table without loading all records into Python memory.

### 3. Unified DTO Translation

- **Decision**: Every provider implementation must include a translation layer to convert raw API models to `CampsiteDTO`.
- **Rationale**: Decouples the core worker logic from the volatile nature of external provider APIs.

### 4. Concurrency Patterns

- **Decision**: Use `asyncio.Semaphore` when performing bulk metadata sync from external APIs to avoid hitting rate limits or overwhelming the local event loop.
- **Rationale**: Ensures "politeness" while maintaining throughput.

## Resolved Unknowns

- **Question**: How to handle 10k+ records in `sync_metadata`?
- **Answer**: Leverage database-level joins and `from_select` statements as seen in the existing `populate_search_table` logic. For external API calls, batch requests using `asyncio.gather` with a semaphore.
