# Data Model: Provider Engine

## Unified Entities

### 1. `CampsiteDTO` (Pydantic v2 Model)

The primary data object returned by all providers to the worker.

| Field             | Type             | Description                                         |
| ----------------- | ---------------- | --------------------------------------------------- |
| `campsite_id`     | `str`            | Unique ID within the provider (e.g., "12345")       |
| `campsite_name`   | `str`            | Human-readable name of the site                     |
| `campsite_type`   | `CampsiteType`   | Standardized category (TENT, RV, etc.)              |
| `capacity`        | `int`            | Maximum occupancy                                   |
| `available_dates` | `List[date]`     | List of dates available for booking                 |
| `is_electric`     | `bool`           | Whether electrical hookups are present              |
| `is_accessible`   | `bool`           | ADA accessibility status                            |
| `metadata`        | `Dict[str, Any]` | Raw, provider-specific fields for logging/debugging |

### 2. `CampsiteType` (Enum)

- `TENT`: Tent-only sites
- `RV`: RV/Trailer sites with specific hookups
- `CABIN`: Cabins, yurts, or other permanent structures
- `GROUP`: Large group sites
- `OTHER`: Backcountry, boat-in, or miscellaneous

## Provider Contract (ABC)

### `BaseProvider` Attributes

- `id`: `str` (slug, e.g., "recreation_dot_gov")
- `name`: `str` (Display name, e.g., "Recreation.gov")
- `headers`: `Dict[str, str]` (Provider-specific HTTP headers)

### `BaseProvider` Methods

- `find_availabilities(park_id: str, start_date: date, end_date: date) -> List[CampsiteDTO]`
- `sync_metadata() -> None` (Background synchronization of search tables)

## Database Relationships

- **Search Table**: Aggregated view of `Campground` and `RecreationArea` for global search.
- **Provider Table**: Configuration and metadata for each supported booking engine.
