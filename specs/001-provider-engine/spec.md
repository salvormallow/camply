# Feature Specification: Provider Engine (BaseProvider ABC)

**Feature Branch**: `001-provider-engine`
**Created**: 2026-03-22
**Status**: Draft
**Input**: User description: "Implement the Provider Engine as described in docs/agents/CHECKLIST.md section 1.2, including defining the BaseProvider ABC and standardizing core methods."

## Clarifications

### Session 2026-03-22

- Q: What standardized exceptions should be used? → A: ProviderError, RateLimitError, AuthError, InvalidParkError
- Q: Who is responsible for database updates in `sync_metadata`? → A: Provider handles database updates directly
- Q: What are the standardized values for `CampsiteType`? → A: TENT, RV, CABIN, GROUP, OTHER
- Q: How should translation errors be handled? → A: Log error and skip malformed record
- Q: What is the expected frequency for `sync_metadata`? → A: Daily (subject to future change)

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Provider Implementation (Priority: P1)

As a developer, I want to add a new campsite booking provider to the system by implementing a standardized interface so that the core scanning engine can interact with it without knowing its internal details.

**Why this priority**: Fundamental requirement for the multi-provider architecture. It enables scaling the system to support more booking sites.

**Independent Test**: Can be tested by creating a mock provider that inherits from `BaseProvider` and verifying it can be instantiated and called by a test script.

**Acceptance Scenarios**:

1. **Given** a new class inheriting from `BaseProvider`, **When** all abstract methods are implemented, **Then** the class can be instantiated successfully.
2. **Given** a class inheriting from `BaseProvider`, **When** any abstract method is missing, **Then** a `TypeError` is raised upon instantiation.

---

### User Story 2 - Availability Scanning (Priority: P1)

As the Smart Poller system, I want to call a standardized `find_availabilities` method on any provider so that I can retrieve availability data in a unified format regardless of the source API.

**Why this priority**: Essential for the core functionality of the application (finding campsites).

**Independent Test**: Can be fully tested by calling `find_availabilities` on a mock provider and asserting the return type is a list of `CampsiteDTO` objects.

**Acceptance Scenarios**:

1. **Given** a provider instance, **When** `find_availabilities` is called with valid parameters, **Then** it returns a list of `CampsiteDTO` objects.
2. **Given** a provider instance, **When** the source API returns an error, **Then** the provider handles it gracefully or raises a standardized exception.

---

### User Story 3 - Metadata Synchronization (Priority: P2)

As a system administrator, I want the system to periodically sync park and campground metadata from providers so that users can search for the latest available locations in the UI.

**Why this priority**: Important for keeping the local database up-to-date and providing a good search experience.

**Independent Test**: Can be tested by calling `sync_metadata` on a mock provider and verifying it performs the expected database operations (e.g., updating search tables).

**Acceptance Scenarios**:

1. **Given** a provider instance, **When** `sync_metadata` is called, **Then** it fetches the latest metadata from the provider and updates the relevant database tables.
2. **Given** a provider instance, **When** `sync_metadata` fails due to network issues, **Then** it logs the error and does not corrupt existing data.

---

### Edge Cases

- **Rate Limiting**: Provider MUST raise `RateLimitError` when throttled by the source API.
- **Invalid Park IDs**: Provider MUST raise `InvalidParkError` when `find_availabilities` is called with a park ID that doesn't exist.
- **Authentication**: Provider MUST raise `AuthError` when API credentials are invalid.
- **Stale Metadata**: How does the system handle metadata that hasn't been updated in a long time?
- **Translation Errors**: Provider SHOULD log the error and skip individual records that cannot be mapped to `CampsiteDTO`.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST define `BaseProvider` as an Abstract Base Class (ABC) in `backend/packages/providers`.
- **FR-002**: `BaseProvider` MUST have an `id` property (unique slug) to identify the provider.
- **FR-003**: `BaseProvider` MUST define an async `find_availabilities(park_id, start_date, end_date)` method.
- **FR-004**: `find_availabilities` MUST return a list of `CampsiteDTO` objects.
- **FR-005**: `BaseProvider` MUST define an async `sync_metadata()` method that directly performs database updates (upserts) for background synchronization.
- **FR-006**: System MUST define a unified `CampsiteDTO` Pydantic model with standard fields (campsite_id, campsite_name, campsite_type, capacity, available_dates, is_electric, is_accessible, metadata).
- **FR-007**: All IO-bound operations within provider implementations MUST be asynchronous using `httpx` or similar.
- **FR-008**: System MUST define a core set of exceptions (`ProviderError`, `RateLimitError`, `AuthError`, `InvalidParkError`) that all providers MUST use.

### Key Entities _(include if feature involves data)_

- **BaseProvider**: The abstract interface defining the contract for all campsite booking providers.
- **CampsiteDTO**: The unified Data Transfer Object representing campsite availability across all providers.
- **CampsiteType**: An Enum defining standard campsite types: `TENT`, `RV`, `CABIN`, `GROUP`, `OTHER`.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: A developer can implement a new provider by fulfilling the `BaseProvider` interface in under 4 hours (excluding API research).
- **SC-002**: 100% of providers return the exact same `CampsiteDTO` structure for availability results.
- **SC-003**: Metadata synchronization can process 10,000+ park records on a daily basis without blocking the main event loop.
- **SC-004**: System can support multiple active providers concurrently without resource contention.
