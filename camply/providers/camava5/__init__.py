"""
Camava5 Provider -- booking platform by Art Street Interactive.

Currently powers Santa Clara County Parks (gooutsideandplay.org).
Each county park system running Camava5 should be a variation class
with its own `base_url` and hardcoded park registry.
"""

from camply.providers.camava5.camava5 import Camava5Park, Camava5Provider
from camply.providers.camava5.variations import SantaClaraCountyParks

__all__ = ["Camava5Park", "Camava5Provider", "SantaClaraCountyParks"]
