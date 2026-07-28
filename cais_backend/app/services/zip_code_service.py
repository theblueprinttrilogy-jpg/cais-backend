"""
ZIP code and jurisdiction service for CAIS backend.

This service dynamically maps any U.S. ZIP code or city name to its
jurisdiction (city, county, state) using the `uszipcode` library,
and then verifies regulatory coverage by scanning the Google Drive
folder structure via DriveSyncService.

No static mapping dictionaries are stored in the code; all data is
obtained from external sources (ZIP database, Drive API).
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any, Union

# Third-party library for US ZIP code lookup
try:
    from uszipcode import SearchEngine
except ImportError:
    raise ImportError("uszipcode is required. Install with: pip install uszipcode")

from app.services.drive_sync_service import DriveSyncService
from app.core.config import settings

logger = logging.getLogger(__name__)


class ZipCodeService:
    """
    Dynamic service for ZIP/jurisdiction mapping and regulatory coverage checking.

    The service uses `uszipcode` to convert ZIP codes to city/county/state,
    and then queries Google Drive (via DriveSyncService) to determine if
    federal, state, county, and municipal regulatory files have been ingested.
    No static ZIP-to-jurisdiction mapping is maintained in the code.
    """

    def __init__(self, drive_service: Optional[DriveSyncService] = None):
        """
        Initialise the ZipCodeService.

        Args:
            drive_service: Optional DriveSyncService instance for coverage checks.
                           If not provided, coverage checks will return all False.
        """
        self.drive_service = drive_service
        # Cache: (city, county, state) tuple -> coverage dict
        self._coverage_cache: Dict[tuple, Dict[str, bool]] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(hours=1)

        # Initialise ZIP search engine (downloads database on first use)
        self._zip_search = SearchEngine()

    def set_drive_service(self, drive_service: DriveSyncService) -> None:
        """Set the DriveSyncService instance for dynamic coverage checks."""
        self.drive_service = drive_service

    def get_jurisdiction_from_zip(self, zip_code: str) -> Dict[str, str]:
        """
        Look up city, county, and state for a given U.S. ZIP code.

        Args:
            zip_code: 5-digit ZIP code (or ZIP+4, which will be truncated).

        Returns:
            A dictionary with keys 'city', 'county', 'state'.
            If the ZIP code is not found, all values default to "Unknown".
        """
        # Normalize to 5 digits
        base_zip = zip_code[:5] if zip_code and zip_code[:5].isdigit() else None
        if not base_zip:
            return {"city": "Unknown", "county": "Unknown", "state": "Unknown"}

        # Query the ZIP database
        result = self._zip_search.by_zipcode(base_zip)
        if result is None:
            return {"city": "Unknown", "county": "Unknown", "state": "Unknown"}

        # Extract fields; uszipcode returns 'major_city', 'county', 'state'
        city = result.major_city or result.city or "Unknown"
        county = result.county or "Unknown"
        state = result.state or "Unknown"

        # Handle possible county suffix (e.g., "Los Angeles County" -> "Los Angeles")
        if county.endswith(" County"):
            county = county[:-7]  # remove " County"

        return {"city": city, "county": county, "state": state}

    def get_jurisdiction_from_city(self, city: str, state: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Look up possible counties and states for a given city name.

        Args:
            city: City name.
            state: Optional state abbreviation to narrow results.

        Returns:
            A list of dictionaries, each with 'city', 'county', 'state'.
            If no matches, returns an empty list.
        """
        # uszipcode's SearchEngine can search by city and state.
        # We'll get all ZIP codes for that city, then extract unique city/county/state combos.
        # For efficiency, we can limit to a few results.
        results = []
        try:
            # Search for ZIP codes by city and optionally state
            zip_results = self._zip_search.by_city(city, state=state, returns=None)
            if zip_results:
                seen = set()
                for z in zip_results:
                    cty = z.major_city or z.city or city
                    cty_county = z.county or "Unknown"
                    if cty_county.endswith(" County"):
                        cty_county = cty_county[:-7]
                    st = z.state or "Unknown"
                    key = (cty, cty_county, st)
                    if key not in seen:
                        seen.add(key)
                        results.append({"city": cty, "county": cty_county, "state": st})
        except Exception as e:
            logger.error("Error searching for city %s: %s", city, e)
        return results

    async def _folder_contains_files(self, folder_id: str) -> bool:
        """
        Check if a Drive folder contains at least one file (non-folder item).

        Args:
            folder_id: Google Drive folder ID.

        Returns:
            True if the folder has at least one file (non-folder), False otherwise.
        """
        if not self.drive_service:
            return False
        try:
            files = await self.drive_service.list_files(folder_id, mime_type=None)
            non_folders = [f for f in files if f.get("mimeType") != "application/vnd.google-apps.folder"]
            return len(non_folders) > 0
        except Exception as e:
            logger.error("Error listing files in folder %s: %s", folder_id, e)
            return False

    async def _navigate_to_folder(self, path_parts: List[str]) -> Optional[str]:
        """
        Navigate from the root folder (settings.ROOT_FOLDER_ID) following the path parts.

        Args:
            path_parts: List of folder names to traverse (e.g., ["State", "CA"]).

        Returns:
            The folder ID of the final folder, or None if any part is not found.
        """
        if not self.drive_service:
            return None
        root_id = getattr(settings, "ROOT_FOLDER_ID", None)
        if not root_id:
            logger.warning("ROOT_FOLDER_ID not set; cannot navigate.")
            return None

        current_id = root_id
        for part in path_parts:
            try:
                folders = await self.drive_service.list_files(current_id, mime_type="application/vnd.google-apps.folder")
                found = next((f for f in folders if f["name"] == part), None)
                if not found:
                    return None
                current_id = found["id"]
            except Exception as e:
                logger.error("Error navigating to %s under %s: %s", part, current_id, e)
                return None
        return current_id

    async def _scan_coverage_for_jurisdiction(self, city: str, county: str, state: str) -> Dict[str, bool]:
        """
        Dynamically scan Google Drive for folders corresponding to the given
        jurisdiction levels (federal, state, county, municipal).

        The folder hierarchy is assumed to be:
            root/
                Federal/
                State/<state_abbr>/
                County/<county_name>/
                Municipal/<city_name>/

        If any part is unknown or a folder is missing, that level is marked False.
        A level is considered covered if the folder exists and contains at least one file.

        Returns:
            Dict with keys 'federal', 'state', 'county', 'municipal' and boolean values.
        """
        if not self.drive_service:
            logger.warning("Drive service not set; coverage check unavailable.")
            return {"federal": False, "state": False, "county": False, "municipal": False}

        levels = {
            "federal": ["Federal"],
            "state": ["State", state] if state != "Unknown" else None,
            "county": ["County", county] if county != "Unknown" else None,
            "municipal": ["Municipal", city] if city != "Unknown" else None,
        }

        coverage = {}
        for level, path_parts in levels.items():
            if path_parts is None:
                coverage[level] = False
                continue

            folder_id = await self._navigate_to_folder(path_parts)
            if folder_id is None:
                coverage[level] = False
            else:
                has_files = await self._folder_contains_files(folder_id)
                coverage[level] = has_files

        return coverage

    async def get_coverage_status(self, location: Union[str, Dict[str, str]]) -> Dict[str, bool]:
        """
        Get compliance coverage status for a given ZIP code or jurisdiction dict.

        Args:
            location: Either a ZIP code string, or a dict with 'city', 'county', 'state'.

        Returns:
            Dictionary with boolean flags for federal, state, county, municipal.
        """
        if isinstance(location, str):
            # It's a ZIP code
            jur = self.get_jurisdiction_from_zip(location)
            city, county, state = jur["city"], jur["county"], jur["state"]
        else:
            # Assume dict with keys 'city', 'county', 'state'
            city = location.get("city", "Unknown")
            county = location.get("county", "Unknown")
            state = location.get("state", "Unknown")

        if city == "Unknown" or county == "Unknown" or state == "Unknown":
            # Cannot determine jurisdiction
            return {"federal": False, "state": False, "county": False, "municipal": False}

        # Check cache
        cache_key = (city, county, state)
        if cache_key in self._coverage_cache and self._cache_timestamp and (datetime.utcnow() - self._cache_timestamp) < self._cache_ttl:
            return self._coverage_cache[cache_key]

        # Perform dynamic scan
        coverage = await self._scan_coverage_for_jurisdiction(city, county, state)

        # Update cache
        self._coverage_cache[cache_key] = coverage
        self._cache_timestamp = datetime.utcnow()
        return coverage

    async def is_fully_covered(self, location: Union[str, Dict[str, str]]) -> bool:
        """
        Check if all regulatory levels (federal, state, county, municipal)
        are covered for the given location.

        Returns:
            True if all four levels are covered, False otherwise.
        """
        coverage = await self.get_coverage_status(location)
        return all(coverage.get(level, False) for level in ("federal", "state", "county", "municipal"))

    async def lookup_jurisdiction(self, zip_code: str) -> Dict[str, Any]:
        """
        Look up jurisdictional metadata and coverage for a given ZIP code.

        Args:
            zip_code: ZIP code string (5 digits or ZIP+4).

        Returns:
            A dictionary containing:
                - zip_code: the original ZIP code
                - normalized_zip: the 5-digit base
                - city: municipality name
                - county: county name
                - state: state abbreviation
                - building_authority: placeholder (or derived from city)
                - coverage: dict with boolean flags for federal, state, county, municipal
        """
        # Normalize to 5 digits
        base_zip = zip_code[:5] if zip_code and zip_code[:5].isdigit() else None
        if not base_zip:
            return {
                "zip_code": zip_code,
                "normalized_zip": None,
                "city": "Unknown",
                "county": "Unknown",
                "state": "Unknown",
                "building_authority": "Unknown",
                "coverage": {"federal": False, "state": False, "county": False, "municipal": False},
                "error": "Invalid ZIP code",
            }

        jur = self.get_jurisdiction_from_zip(base_zip)
        city, county, state = jur["city"], jur["county"], jur["state"]
        coverage = await self.get_coverage_status({"city": city, "county": county, "state": state})

        # Derive a building authority name from city (fallback)
        authority = f"{city} Building Department" if city != "Unknown" else "Unknown"

        return {
            "zip_code": zip_code,
            "normalized_zip": base_zip,
            "city": city,
            "county": county,
            "state": state,
            "building_authority": authority,
            "coverage": coverage,
        }

    async def refresh_coverage_cache(self) -> None:
        """
        Refresh coverage cache by scanning all jurisdictions that have been
        discovered in Drive. This helps after adding new documents.
        """
        jurisdictions = await self.discover_jurisdictions()
        for jur in jurisdictions:
            city = jur.get("city", "Unknown")
            county = jur.get("county", "Unknown")
            state = jur.get("state", "Unknown")
            if city != "Unknown" and county != "Unknown" and state != "Unknown":
                coverage = await self._scan_coverage_for_jurisdiction(city, county, state)
                self._coverage_cache[(city, county, state)] = coverage
        self._cache_timestamp = datetime.utcnow()
        logger.info("Refreshed coverage cache for %d jurisdictions.", len(jurisdictions))

    async def discover_jurisdictions(self) -> List[Dict[str, str]]:
        """
        Discover available jurisdictions by scanning Google Drive folder structure.

        Returns a list of dicts with 'city', 'county', 'state' for each found
        jurisdiction where at least one level has files.
        """
        if not self.drive_service:
            return []

        root_id = getattr(settings, "ROOT_FOLDER_ID", None)
        if not root_id:
            return []

        result = []
        # State
        state_folder_id = await self._navigate_to_folder(["State"])
        if state_folder_id:
            states = await self.drive_service.list_files(state_folder_id, mime_type="application/vnd.google-apps.folder")
            for st in states:
                st_name = st["name"]
                # County
                county_folder_id = await self._navigate_to_folder(["County"])
                counties = await self.drive_service.list_files(county_folder_id, mime_type="application/vnd.google-apps.folder") if county_folder_id else []
                for co in counties:
                    co_name = co["name"]
                    # Municipal
                    municipal_folder_id = await self._navigate_to_folder(["Municipal"])
                    cities = await self.drive_service.list_files(municipal_folder_id, mime_type="application/vnd.google-apps.folder") if municipal_folder_id else []
                    for ci in cities:
                        ci_name = ci["name"]
                        # Check if any of these have files
                        coverage = await self._scan_coverage_for_jurisdiction(ci_name, co_name, st_name)
                        if any(coverage.values()):
                            result.append({
                                "city": ci_name,
                                "county": co_name,
                                "state": st_name,
                            })
        return result
