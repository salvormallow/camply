"""
Camava5 Provider variations -- one subclass per Camava5-powered agency.

Each agency running Camava5 gets its own subclass with base_url +
hardcoded park registry. Add more agencies by following the
SantaClaraCountyParks template below.
"""

from typing import Dict

from camply.providers.camava5.camava5 import Camava5Park, Camava5Provider


class SantaClaraCountyParks(Camava5Provider):
    """Santa Clara County Parks (https://gooutsideandplay.org).

    Covers 5 family-camping parks in South Bay CA. GPS bounding boxes
    were determined empirically from the jsonPadicons response -- tight
    enough to avoid catching neighboring parks, loose enough to include
    all sites within each park.
    """

    base_url: str = "https://gooutsideandplay.org"
    campground_url: str = "https://gooutsideandplay.org/reservation/camping"
    state_code: str = "CA"

    parks: Dict[int, Camava5Park] = {
        1: Camava5Park(
            facility_id=1,
            name="Uvas Canyon Park",
            bbox=(37.083, 37.092, -121.800, -121.790),
            park_idno="1455125",
        ),
        2: Camava5Park(
            facility_id=2,
            name="Coyote Lake Harvey Bear Ranch",
            bbox=(37.050, 37.130, -121.555, -121.500),
            park_idno="1455111",
        ),
        3: Camava5Park(
            facility_id=3,
            name="Joseph Grant County Park",
            bbox=(37.310, 37.350, -121.730, -121.695),
            park_idno="1455115",
        ),
        4: Camava5Park(
            facility_id=4,
            name="Mt Madonna Park",
            bbox=(36.990, 37.020, -121.740, -121.690),
            park_idno="1455120",
        ),
        5: Camava5Park(
            facility_id=5,
            name="Sanborn Skyline Park",
            bbox=(37.225, 37.255, -122.090, -122.055),
            park_idno="1455121",
        ),
    }
