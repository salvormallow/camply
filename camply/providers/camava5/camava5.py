"""
Camava5 Provider base class.

Camava5 is a proprietary reservation platform by Art Street Interactive,
used by Santa Clara County Parks (gooutsideandplay.org) and potentially
other small agencies.

Architecture notes:

- The backend exposes a single availability endpoint
  `POST /reservation/getresults.asp` that returns every site across
  every park in the agency system in one response (~360 sites for SCCP).
  The `parent_idno` filter is ignored server-side -- we filter by GPS
  bounding box client-side per park.
- No metadata API exists, so the park registry is hardcoded per variation
  (subclass). Each variation overrides `parks` with its park list.
- Availability is queried per single night (arrive/depart one day apart),
  so multi-night searches loop over `search_days`. Unlike UseDirect's
  month-granularity API, there is no per-facility call cost reduction.
"""

from __future__ import annotations

import datetime
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Union

import ratelimit

from camply.containers import CampgroundFacility
from camply.containers.data_containers import AvailableCampsite, CampsiteLocation
from camply.providers.base_provider import BaseProvider, ProviderSearchError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Camava5Park:
    """A single park in a Camava5 agency system.

    Identified by a stable integer `facility_id` we assign (since Camava5
    has no real facility concept -- it's all one pool of sites). The
    `bbox` is how we filter the global response to just this park's sites.
    `park_idno` is the Camava5-internal ID used on the reservation form;
    kept for future use even though the backend ignores it for filtering.
    """

    facility_id: int
    name: str
    bbox: Tuple[float, float, float, float]  # (lat_min, lat_max, lng_min, lng_max)
    park_idno: str

    def contains(self, lat: float, lng: float) -> bool:
        lat_min, lat_max, lng_min, lng_max = self.bbox
        return lat_min < lat < lat_max and lng_min < lng < lng_max


class Camava5Provider(BaseProvider, ABC):
    """Abstract base for Camava5-backed reservation systems.

    Subclass and override: `base_url`, `campground_url`, `state_code`, `parks`.
    """

    # Rate limit: 1 request per second is polite for a legacy ASP backend
    _RATE_LIMIT_CALLS: ClassVar[int] = 1
    _RATE_LIMIT_PERIOD: ClassVar[int] = 1

    GETRESULTS_PATH: ClassVar[str] = "/reservation/getresults.asp"
    CAMPING_PATH: ClassVar[str] = "/reservation/camping"

    # Response states that mean the site is NOT available for booking.
    _UNAVAILABLE_REASONS: ClassVar[frozenset] = frozenset({
        "Booked", "Not Reservable Online", "Not a Campsite",
        "Blocked", "Hold", "Maintenance",
    })

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL for the Camava5 instance (e.g. https://gooutsideandplay.org)"""

    @property
    @abstractmethod
    def campground_url(self) -> str:
        """Public-facing booking URL (shown to users as the place to complete reservations)"""

    @property
    @abstractmethod
    def state_code(self) -> str:
        """Two-letter state code (e.g. 'CA')"""

    @property
    @abstractmethod
    def parks(self) -> Dict[int, Camava5Park]:
        """Hardcoded park registry: facility_id -> Camava5Park"""

    # ------------------------------------------------------------------
    # BaseProvider contract
    # ------------------------------------------------------------------

    def find_campgrounds(
        self,
        search_string: Optional[str] = None,
        rec_area_id: Optional[Union[List[int], int]] = None,
        campground_id: Optional[Union[List[int], int]] = None,
        state: Optional[str] = None,
        verbose: bool = True,
        **kwargs: Any,
    ) -> List[CampgroundFacility]:
        """Return parks filtered by the given criteria.

        Camava5 has no hierarchy -- rec_area_id and campground_id are the
        same namespace (each park is both). We accept either for API
        compatibility with other camply providers.
        """
        state_filter = state or self.state_code
        if state_filter and state_filter.upper() != self.state_code:
            return []

        ids: List[int] = []
        for source in (rec_area_id, campground_id):
            if source is None:
                continue
            if isinstance(source, list):
                ids.extend(int(x) for x in source)
            else:
                ids.append(int(source))

        candidates: List[Camava5Park] = list(self.parks.values())
        if ids:
            candidates = [p for p in candidates if p.facility_id in set(ids)]
        if search_string:
            q = search_string.lower()
            candidates = [p for p in candidates if q in p.name.lower()]

        facilities = [self._park_to_facility(p) for p in candidates]
        if verbose:
            logger.info(f"{len(facilities)} Matching Campgrounds Found")
            for f in facilities:
                logger.info(f"⛰️  {f.facility_name} ({f.facility_id})")
        return facilities

    def search_for_recreation_areas(
        self,
        query: Optional[str] = None,
        state: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Any]:
        """Camava5 has no rec-area / campground hierarchy -- parks are both."""
        from camply.containers.data_containers import RecreationArea
        state_filter = state or self.state_code
        if state_filter and state_filter.upper() != self.state_code:
            return []
        parks = list(self.parks.values())
        if query:
            q = query.lower()
            parks = [p for p in parks if q in p.name.lower()]
        return [
            RecreationArea(
                recreation_area=p.name,
                recreation_area_id=p.facility_id,
                recreation_area_location=f"{self.state_code}",
                coordinates=self._park_center(p),
                description=f"{p.name} (Camava5 / {self.__class__.__name__})",
            )
            for p in parks
        ]

    def get_campsites(
        self,
        campground_id: Union[int, str],
        start_date: datetime.date,
        end_date: datetime.date,
        **kwargs: Any,
    ) -> List[AvailableCampsite]:
        """Fetch available sites at one park over a date range.

        Loops per-night (Camava5's form granularity). Returns one
        AvailableCampsite row per available site per night; the base
        search class consolidates consecutive rows into multi-night stays.
        """
        fid = int(campground_id)
        park = self.parks.get(fid)
        if park is None:
            raise ProviderSearchError(
                f"Unknown Camava5 campground_id {fid}. "
                f"Known: {sorted(self.parks.keys())}"
            )

        campsites: List[AvailableCampsite] = []
        night = start_date
        while night < end_date:
            raw = self._fetch_availability(night)
            for site in raw:
                if not self._is_available_in_park(site, park):
                    continue
                campsites.append(self._build_campsite(site, park, night))
            night = night + datetime.timedelta(days=1)
        return campsites

    def get_campsite_metadata(
        self, facility_ids: List[int]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Return raw site records keyed by facility_id (single call)."""
        today = datetime.date.today()
        raw = self._fetch_availability(today)
        out: Dict[int, List[Dict[str, Any]]] = {fid: [] for fid in facility_ids}
        for site in raw:
            lat = float(site.get("gps_lat") or 0)
            lng = float(site.get("gps_long") or 0)
            for fid in facility_ids:
                park = self.parks.get(fid)
                if park is not None and park.contains(lat, lng):
                    out[fid].append(site)
                    break
        return out

    def validate_campsites(
        self, campsites: List[int], facility_ids: List[int]
    ) -> None:
        """No-op validation. Camava5 doesn't expose a reliable per-site
        metadata endpoint, so we can't pre-verify campsite IDs. The
        availability search will silently ignore unknown ids."""
        return None

    # ------------------------------------------------------------------
    # Camava5-specific helpers
    # ------------------------------------------------------------------

    @ratelimit.sleep_and_retry
    @ratelimit.limits(calls=_RATE_LIMIT_CALLS, period=_RATE_LIMIT_PERIOD)
    def _fetch_availability(self, night: datetime.date) -> List[Dict[str, Any]]:
        """Single availability call: POST the form, return the jsonPadicons list."""
        arrive = self._format_date(night)
        depart = self._format_date(night + datetime.timedelta(days=1))
        response = self.make_http_request_retry(
            url=f"{self.base_url}{self.GETRESULTS_PATH}",
            method="POST",
            data={
                "parent_idno": "0",
                "selected_idno": "0",
                "arrive_date": arrive,
                "depart_date": depart,
                "cust_type_idno": "0",
                "isBuilder": "1",
                "typeUrl": "camping",
                "showsites": "Y",
            },
            headers={
                **self.headers,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{self.base_url}{self.CAMPING_PATH}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        try:
            data = response.json()
        except Exception as e:
            raise ProviderSearchError(
                f"Camava5 availability response was not JSON: {e}"
            ) from e
        return data.get("jsonPadicons", [])

    @staticmethod
    def _format_date(d: datetime.date) -> str:
        """Camava5 requires unpadded M/D/YYYY (strftime %m pads)."""
        return f"{d.month}/{d.day}/{d.year}"

    def _is_available_in_park(self, site: Dict[str, Any], park: Camava5Park) -> bool:
        lat = float(site.get("gps_lat") or 0)
        lng = float(site.get("gps_long") or 0)
        if not park.contains(lat, lng):
            return False
        if site.get("reservable") != "1":
            return False
        if site.get("reason_code") in self._UNAVAILABLE_REASONS:
            return False
        return True

    def _build_campsite(
        self,
        site: Dict[str, Any],
        park: Camava5Park,
        night: datetime.date,
    ) -> AvailableCampsite:
        depart = night + datetime.timedelta(days=1)
        return AvailableCampsite(
            campsite_id=int(site["idno"]),
            booking_date=datetime.datetime.combine(night, datetime.time.min),
            booking_end_date=datetime.datetime.combine(depart, datetime.time.min),
            booking_nights=1,
            campsite_site_name=site.get("name", "").strip() or f"site-{site['idno']}",
            campsite_loop_name=None,
            campsite_type=site.get("type_name"),
            campsite_occupancy=(0, 1),
            campsite_use_type=None,
            availability_status="Available",
            recreation_area=park.name,
            recreation_area_id=park.facility_id,
            facility_name=park.name,
            facility_id=park.facility_id,
            booking_url=f"{self.campground_url}",
            location=CampsiteLocation(
                latitude=float(site["gps_lat"]),
                longitude=float(site["gps_long"]),
            ),
            permitted_equipment=None,
            campsite_attributes=None,
        )

    def _park_to_facility(self, park: Camava5Park) -> CampgroundFacility:
        return CampgroundFacility(
            facility_name=park.name,
            facility_id=park.facility_id,
            recreation_area=park.name,
            recreation_area_id=park.facility_id,
            map_id=None,
            coordinates=self._park_center(park),
        )

    @staticmethod
    def _park_center(park: Camava5Park) -> Tuple[float, float]:
        lat_min, lat_max, lng_min, lng_max = park.bbox
        return ((lat_min + lat_max) / 2, (lng_min + lng_max) / 2)
