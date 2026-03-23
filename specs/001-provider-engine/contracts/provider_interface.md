# Contract: Provider Interface (Internal)

## Purpose

This contract ensures that all booking providers (e.g., Recreation.gov, ReserveCalifornia) expose a standardized interface to the worker, enabling polymorphic scanning.

## ABC Definition (Proposed Python)

```python
class BaseProvider(ABC):
    @property
    @abstractmethod
    def id(self) -> str:
        """Unique slug: e.g., 'recreation_dot_gov'"""

    @abstractmethod
    async def find_availabilities(
        self,
        park_id: str,
        start_date: date,
        end_date: date
    ) -> List[CampsiteDTO]:
        """
        Scan a specific park for availability.
        - Translates API response to unified CampsiteDTO.
        - Handles provider-specific pagination or error backoff.
        """

    @abstractmethod
    async def sync_metadata(self) -> None:
        """
        Background task to refresh park metadata in the database.
        - Updates Search, Campground, and RecreationArea tables.
        - Performs bulk upserts for efficiency.
        """
```

## Data Transfer Objects (DTO)

### `CampsiteDTO` (v1)

Standardized representation of availability across all providers.

```json
{
  "campsite_id": "string",
  "campsite_name": "string",
  "campsite_type": "TENT | RV | CABIN | GROUP | OTHER",
  "capacity": "integer",
  "available_dates": ["YYYY-MM-DD"],
  "is_electric": "boolean",
  "is_accessible": "boolean",
  "metadata": "object"
}
```
