# Provider Quickstart: Adding a New Booking Engine

## 1. Create Sub-Package

In `backend/packages/providers/providers/`, create a new folder for your provider:

```bash
mkdir -p backend/packages/providers/providers/my_provider
```

## 2. Define Internal Models

Create `models.py` with Pydantic classes that match the provider's API exactly.

- Each API model should include a `to_dto()` method to map to the unified `CampsiteDTO`.

## 3. Implement the Provider

Inherit from `BaseProvider` and fulfill the abstract methods.

```python
from providers.base import BaseProvider
from providers.dto import CampsiteDTO

class MyProvider(BaseProvider):
    @property
    def id(self) -> str:
        return "my_provider"

    async def find_availabilities(self, park_id, start_date, end_date):
        # 1. Fetch from provider API
        # 2. Parse into internal models
        # 3. Call model.to_dto()
        # 4. Return List[CampsiteDTO]
        pass
```

## 4. Automated Tests

Add tests in `backend/packages/providers/tests/`.

- Use `pytest-vcr` to record and playback API interactions.
- Test both `find_availabilities` (scanning) and `sync_metadata` (DB sync).
