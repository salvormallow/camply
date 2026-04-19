"""
Search Implementation: Camava5 (Santa Clara County Parks and others).

Camava5's availability API operates at single-night granularity, unlike
UseDirect's month-granularity. So where SearchUseDirect loops over
`self.search_months` and fetches a month-wide range per facility, we loop
over `self.search_days` and fetch one night at a time.
"""

import logging
import sys
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any, Dict, List, Optional, Type, Union

from camply.containers import AvailableCampsite, RecreationArea, SearchWindow
from camply.containers.data_containers import ListedCampsite
from camply.providers.camava5.variations import SantaClaraCountyParks
from camply.search.base_search import BaseCampingSearch
from camply.utils import logging_utils, make_list
from camply.utils.logging_utils import format_log_string, log_sorted_response

logger = logging.getLogger(__name__)


class SearchCamava5(BaseCampingSearch, ABC):
    """Searches a Camava5-backed reservation system for campsites.

    Each Camava5 agency (e.g. Santa Clara County Parks) gets its own
    subclass that sets `provider_class` to the appropriate variation.
    """

    @property
    @abstractmethod
    def provider_class(self) -> Type[BaseCampingSearch]:
        """Provider variation class (e.g. SantaClaraCountyParks)."""

    def __init__(
        self,
        search_window: Union[SearchWindow, List[SearchWindow]],
        recreation_area: Optional[List[int]] = None,
        weekends_only: bool = False,
        campgrounds: Optional[Union[List[str], str]] = None,
        nights: int = 1,
        **kwargs: Any,
    ) -> None:
        """Initialize search.

        Camava5 has no rec-area / campground hierarchy, so `recreation_area`
        and `campgrounds` behave identically -- either accepts the park's
        facility_id (1-5 for SCCP). Accepting both keeps the camply CLI
        contract uniform across providers.
        """
        super().__init__(
            search_window=search_window,
            weekends_only=weekends_only,
            nights=nights,
            **kwargs,
        )
        self._recreation_area_ids: List[int] = make_list(
            recreation_area or [], coerce=int
        )
        self._campground_ids: List[int] = make_list(campgrounds or [], coerce=int)

        campsites = make_list(kwargs.get("campsites", []), coerce=int) or []
        if campsites:
            self.campsite_finder.validate_campsites(
                campsites=campsites, facility_ids=self._campground_ids
            )

        if not self._campground_ids and not self._recreation_area_ids:
            logger.error(
                f"You must provide a Campground ID or a Recreation Area ID to "
                f"{self.provider_class.__name__}"
            )
            sys.exit(1)

        if self._campground_ids:
            self.campgrounds = self.campsite_finder.find_campgrounds(
                campground_id=self._campground_ids,
                verbose=False,
            )
        else:
            self.campgrounds = self.campsite_finder.find_campgrounds(
                rec_area_id=self._recreation_area_ids,
                verbose=False,
            )
        self.campground_ids = [item.facility_id for item in self.campgrounds]
        if not self.campground_ids:
            logger.error("No Campsites Found Matching Your Search Criteria")
            sys.exit(1)

        if kwargs.get("equipment", ()):
            logger.warning(
                "%s Doesn't Support Equipment, yet 🙂", self.provider_class.__name__
            )

    def get_all_campsites(self, **kwargs: Dict[str, Any]) -> List[AvailableCampsite]:
        """Fetch all available campsites.

        Camava5 is per-night, so we loop days x campgrounds. Unlike
        UseDirect which gets a whole month per API call, we pay one HTTP
        round-trip per night here -- hence the rate-limiter in the
        provider.
        """
        logger.info(f"Searching across {len(self.campgrounds)} campgrounds")
        for campground in self.campgrounds:
            logger.info("    %s", format_log_string(campground))

        campsites_found: List[AvailableCampsite] = []
        for day in self.search_days:
            for campground in self.campgrounds:
                logger.info(
                    f"Searching {campground.facility_name} ({campground.facility_id}) "
                    f"for {day.strftime('%Y-%m-%d (%a)')}"
                )
                campsites = self.campsite_finder.get_campsites(
                    campground_id=campground.facility_id,
                    start_date=day.date() if hasattr(day, "date") else day,
                    end_date=(day.date() if hasattr(day, "date") else day)
                    + timedelta(days=1),
                )
                logger.info(
                    f"\t{logging_utils.get_emoji(campsites)}\t"
                    f"{len(campsites)} sites available"
                )
                campsites_found += campsites

        campsite_df = self.campsites_to_df(campsites=campsites_found)
        campsite_df_validated = self._filter_date_overlap(campsites=campsite_df)
        consolidated = self._consolidate_campsites(
            campsite_df=campsite_df_validated, nights=self.nights
        )
        return self.df_to_campsites(campsite_df=consolidated)

    @classmethod
    def find_recreation_areas(
        cls,
        search_string: Optional[str] = None,
        **kwargs: Any,
    ) -> List[RecreationArea]:
        """List Camava5 recreation areas (== parks)."""
        rec_areas = cls.provider_class().search_for_recreation_areas(
            query=search_string,
            state=kwargs.get("state"),
        )
        logger.info(f"{len(rec_areas)} Matching Recreation Areas Found")
        log_sorted_response(rec_areas)
        return rec_areas

    def list_campsite_units(self) -> List[ListedCampsite]:
        """List individual sites across the chosen campgrounds.

        Camava5 has no static unit metadata endpoint -- we use the
        availability-response payload from a single call to enumerate
        sites. Identity is the site's `idno`.
        """
        raw_by_facility = self.campsite_finder.get_campsite_metadata(
            facility_ids=self.campground_ids
        )
        listed: List[ListedCampsite] = []
        for fid, sites in raw_by_facility.items():
            for s in sites:
                listed.append(
                    ListedCampsite(
                        id=int(s["idno"]),
                        name=s.get("name", "").strip() or f"site-{s['idno']}",
                        facility_id=fid,
                    )
                )
        self.log_listed_campsites(campsites=listed, facilities=self.campgrounds)
        return listed


class SearchSantaClaraCountyParks(SearchCamava5):
    """Search Santa Clara County Parks (gooutsideandplay.org).

    CLI: `camply campsites --provider SantaClaraCountyParks --campground 1 ...`
    Campground IDs 1-5 map to: 1=Uvas, 2=Coyote Lake, 3=Joseph Grant,
    4=Mt Madonna, 5=Sanborn Skyline.
    """

    provider_class = SantaClaraCountyParks
