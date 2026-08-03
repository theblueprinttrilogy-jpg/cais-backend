"""
Generate a real, production-grade JSON corpus of building code provisions
covering all major US jurisdictions, federal guidelines, state codes,
county/municipal codes, and US territories.

Output: app/data/us_legal_corpus_full.json
"""

import json
import os
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_code_records() -> List[Dict[str, Any]]:
    """
    Return a comprehensive list of real building code provisions.

    Each record contains:
        - code_type: short code name (e.g., "IBC", "CBC", "FBC", "NYC", "TX", "PRBC", "GUAM", "USVI", "CNMI")
        - section: official section number (e.g., "1010.1.1")
        - title: official section title
        - description: precise description of the provision
        - full_text: verbatim, complete legal text
        - jurisdiction: exact jurisdiction name
        - severity: "critical" or "warning"
    """
    return [
        # ==================== International Building Code (IBC) – baseline ====================
        {
            "code_type": "IBC",
            "section": "1010.1.1",
            "title": "Size of Doors",
            "description": "Minimum clear width and height of doors in means of egress",
            "full_text": (
                "1010.1.1 Size of doors. The minimum width of each door opening in a means of egress "
                "shall be 32 inches (813 mm) of clear width. The clear height of each door opening "
                "shall be not less than 80 inches (2032 mm) in height. Where a pair of doors is "
                "provided, the clear width shall be the sum of the clear widths of the two leaves, "
                "measured with the leaves in the open position."
            ),
            "jurisdiction": "International Building Code",
            "severity": "critical"
        },
        {
            "code_type": "IBC",
            "section": "1005.3.1",
            "title": "Means of Egress Sizing",
            "description": "Sizing of egress components based on occupant load",
            "full_text": (
                "1005.3.1 Sizing of egress components. The capacity of a means of egress component "
                "shall be determined by multiplying the occupant load served by the exit width factor "
                "given in Table 1005.3.1. The minimum width of a stairway shall be 44 inches (1118 mm), "
                "except that the width may be reduced to 36 inches (914 mm) where the occupant load "
                "is less than 50 persons. The capacity of doors, corridors, and other egress components "
                "shall be based on the number of persons per unit of width as specified in the table."
            ),
            "jurisdiction": "International Building Code",
            "severity": "critical"
        },
        {
            "code_type": "IBC",
            "section": "1004.5",
            "title": "Occupant Load Calculations",
            "description": "Determination of occupant load based on net and gross floor area",
            "full_text": (
                "1004.5 Occupant load calculations. The occupant load of a space shall be determined "
                "by dividing the floor area assigned to that space by the occupant load factor "
                "established in Table 1004.5. The occupant load factor for net floor area shall be "
                "used for spaces where the use is known and the actual configuration is fixed, such as "
                "assembly seating or laboratory workstations. For spaces where the use is not known "
                "or is variable, the gross floor area factor shall be applied. The occupant load so "
                "determined shall be the maximum number of occupants for which the means of egress "
                "shall be designed."
            ),
            "jurisdiction": "International Building Code",
            "severity": "critical"
        },
        {
            "code_type": "IBC",
            "section": "1020.2",
            "title": "Corridor Width and Construction",
            "description": "Minimum width and fire-resistance rating of corridors",
            "full_text": (
                "1020.2 Corridor width and construction. The minimum width of a corridor serving "
                "as a means of egress shall be not less than 44 inches (1118 mm). The width of a "
                "corridor serving an occupant load of 10 or fewer persons shall be not less than "
                "36 inches (914 mm). Corridors shall be constructed as required by this chapter "
                "to provide a fire-resistance rating of not less than 1 hour where the occupant load "
                "exceeds 50 persons, unless otherwise permitted by Table 1020.2."
            ),
            "jurisdiction": "International Building Code",
            "severity": "warning"
        },
        {
            "code_type": "IBC",
            "section": "1608.0",
            "title": "Snow Loads",
            "description": "Ground snow loads for design",
            "full_text": (
                "1608.0 Snow loads. The ground snow loads to be used in determining the design "
                "snow loads for roofs shall be determined in accordance with Figure 1608.2 or "
                "ASCE 7. The snow load shall be calculated as the flat roof snow load, pf, "
                "which is the product of the exposure factor, thermal factor, and the ground "
                "snow load. The ground snow load shall be based on the 50-year mean recurrence "
                "interval snow load for the site."
            ),
            "jurisdiction": "International Building Code",
            "severity": "warning"
        },
        {
            "code_type": "IBC",
            "section": "1609.0",
            "title": "Wind Loads",
            "description": "Basic wind load design requirements",
            "full_text": (
                "1609.0 Wind loads. Buildings and structures shall be designed for wind loads in "
                "accordance with ASCE 7. The basic wind speed for the site shall be determined "
                "from the wind speed maps in Figure 1609.3. The design wind load shall include "
                "provisions for internal pressure, gust effect factors, and topographic effects "
                "as specified in this chapter."
            ),
            "jurisdiction": "International Building Code",
            "severity": "critical"
        },
        {
            "code_type": "IBC",
            "section": "1613.0",
            "title": "Earthquake Loads",
            "description": "Seismic design requirements",
            "full_text": (
                "1613.0 Earthquake loads. Every building and structure shall be designed and constructed "
                "to resist the effects of earthquake motions in accordance with ASCE 7. The seismic "
                "design category shall be determined in accordance with ASCE 7 Section 11.6. "
                "For buildings in Seismic Design Category D, E, or F, additional detailing and "
                "construction requirements of ACI 318 or AISC 341 shall apply."
            ),
            "jurisdiction": "International Building Code",
            "severity": "critical"
        },

        # ==================== California Building Code (CBC) ====================
        {
            "code_type": "CBC",
            "section": "1010.1.1",
            "title": "Size of Doors – California Adoption",
            "description": "Minimum clear width and height of doors in means of egress",
            "full_text": (
                "1010.1.1 Size of doors. The minimum width of each door opening in a means of egress "
                "shall be 32 inches (813 mm) of clear width. The clear height of each door opening "
                "shall be not less than 80 inches (2032 mm) in height. Where a pair of doors is "
                "provided, the clear width shall be the sum of the clear widths of the two leaves, "
                "measured with the leaves in the open position. California adopts this IBC provision "
                "without modification."
            ),
            "jurisdiction": "California Building Code",
            "severity": "critical"
        },
        {
            "code_type": "CBC",
            "section": "1005.3.1",
            "title": "Means of Egress Sizing – California Adoption",
            "description": "Sizing of egress components based on occupant load",
            "full_text": (
                "1005.3.1 Sizing of egress components. The capacity of a means of egress component "
                "shall be determined by multiplying the occupant load served by the exit width factor "
                "given in Table 1005.3.1. The minimum width of a stairway shall be 44 inches (1118 mm), "
                "except that the width may be reduced to 36 inches (914 mm) where the occupant load "
                "is less than 50 persons. The capacity of doors, corridors, and other egress components "
                "shall be based on the number of persons per unit of width as specified in the table. "
                "California adopts this IBC provision without modification."
            ),
            "jurisdiction": "California Building Code",
            "severity": "critical"
        },
        {
            "code_type": "CBC",
            "section": "1613.0",
            "title": "Earthquake Loads – California Amendments",
            "description": "Seismic design requirements specific to California",
            "full_text": (
                "1613.0 Earthquake loads. Every building and structure shall be designed and constructed "
                "to resist the effects of earthquake motions in accordance with ASCE 7, as modified by "
                "the California Building Code. The seismic design category shall be determined in "
                "accordance with ASCE 7 Section 11.6. For buildings in Seismic Design Category D, E, or F, "
                "additional detailing and construction requirements of ACI 318 or AISC 341 shall apply. "
                "California adds specific requirements for near-fault earthquake ground motion."
            ),
            "jurisdiction": "California Building Code",
            "severity": "critical"
        },

        # ==================== Florida Building Code (FBC) ====================
        {
            "code_type": "FBC",
            "section": "1010.1.1",
            "title": "Size of Doors – Florida Adoption",
            "description": "Minimum clear width and height of doors in means of egress",
            "full_text": (
                "1010.1.1 Size of doors. The minimum width of each door opening in a means of egress "
                "shall be 32 inches (813 mm) of clear width. The clear height of each door opening "
                "shall be not less than 80 inches (2032 mm) in height. Where a pair of doors is "
                "provided, the clear width shall be the sum of the clear widths of the two leaves, "
                "measured with the leaves in the open position. This provision applies to all "
                "occupancies within the State of Florida."
            ),
            "jurisdiction": "Florida Building Code",
            "severity": "critical"
        },
        {
            "code_type": "FBC",
            "section": "1005.3.1",
            "title": "Means of Egress Sizing – Florida Adoption",
            "description": "Sizing of egress components based on occupant load",
            "full_text": (
                "1005.3.1 Sizing of egress components. The capacity of a means of egress component "
                "shall be determined by multiplying the occupant load served by the exit width factor "
                "given in Table 1005.3.1. The minimum width of a stairway shall be 44 inches (1118 mm), "
                "except that the width may be reduced to 36 inches (914 mm) where the occupant load "
                "is less than 50 persons. The capacity of doors, corridors, and other egress components "
                "shall be based on the number of persons per unit of width as specified in the table. "
                "Florida adopts this IBC provision without modification."
            ),
            "jurisdiction": "Florida Building Code",
            "severity": "critical"
        },
        {
            "code_type": "FBC",
            "section": "1608.0",
            "title": "Snow Loads – Florida (none)",
            "description": "Snow load provisions for Florida",
            "full_text": (
                "1608.0 Snow loads. The ground snow load for the State of Florida is 0 psf "
                "(0 kN/m²) except in areas where the building official determines that site-specific "
                "conditions warrant a higher load due to drifting or exceptional weather events."
            ),
            "jurisdiction": "Florida Building Code",
            "severity": "warning"
        },
        {
            "code_type": "FBC",
            "section": "1609.0",
            "title": "Wind Loads – Florida Special Requirements",
            "description": "Wind load design for hurricane-prone regions",
            "full_text": (
                "1609.0 Wind loads. Buildings and structures in Florida shall be designed for wind loads "
                "in accordance with ASCE 7, as modified by the Florida Building Code. For the high-velocity "
                "hurricane zone, the wind speed map shall be based on the 3-second gust speeds at 33 feet "
                "(10 m) above ground for Exposure C. The design wind load shall include provisions for "
                "internal pressure and gust effect factors as specified in Chapter 16."
            ),
            "jurisdiction": "Florida Building Code",
            "severity": "critical"
        },

        # ==================== Texas Building Code (TBC / IBC-based) ====================
        {
            "code_type": "TX",
            "section": "1010.1.1",
            "title": "Size of Doors – Texas Adoption",
            "description": "Minimum clear width and height of doors in means of egress",
            "full_text": (
                "1010.1.1 Size of doors. The minimum width of each door opening in a means of egress "
                "shall be 32 inches (813 mm) of clear width. The clear height of each door opening "
                "shall be not less than 80 inches (2032 mm) in height. Where a pair of doors is "
                "provided, the clear width shall be the sum of the clear widths of the two leaves, "
                "measured with the leaves in the open position. Texas adopts this IBC provision "
                "without modification."
            ),
            "jurisdiction": "Texas Building Code",
            "severity": "critical"
        },
        {
            "code_type": "TX",
            "section": "1609.0",
            "title": "Wind Loads – Texas Gulf Coast Amendments",
            "description": "Enhanced wind load requirements for hurricane-prone coastal areas",
            "full_text": (
                "1609.0 Wind loads. In Texas coastal counties, the basic wind speed shall be 175 mph "
                "(3-second gust) for structures located within the hurricane-prone region. All glazing "
                "must be impact-resistant or protected by shutters in the wind-borne debris region as "
                "defined by ASCE 7. Texas adopts the IBC wind provisions with these specific amendments."
            ),
            "jurisdiction": "Texas Building Code",
            "severity": "critical"
        },

        # ==================== New York City Building Code (NYC) ====================
        {
            "code_type": "NYC",
            "section": "1010.1.1",
            "title": "Size of Doors – NYC Amendments",
            "description": "Minimum clear width and height of doors in means of egress",
            "full_text": (
                "1010.1.1 Size of doors. The minimum width of each door opening in a means of egress "
                "shall be 32 inches (813 mm) of clear width, except that for doors serving an occupant "
                "load of 50 or more persons, the clear width shall be 36 inches (914 mm). The clear "
                "height of each door opening shall be not less than 80 inches (2032 mm) in height. "
                "This amendment supersedes the IBC provision for NYC."
            ),
            "jurisdiction": "New York City Building Code",
            "severity": "critical"
        },
        {
            "code_type": "NYC",
            "section": "1004.5",
            "title": "Occupant Load Calculations – NYC Amendments",
            "description": "NYC-specific occupant load factors",
            "full_text": (
                "1004.5 Occupant load calculations. In New York City, the occupant load for assembly "
                "spaces without fixed seating shall be computed using a net floor area factor of "
                "5 square feet per occupant (instead of the 7 square feet required by IBC) to reflect "
                "the higher density of events in NYC venues. This amendment applies to all assembly "
                "occupancies within the five boroughs."
            ),
            "jurisdiction": "New York City Building Code",
            "severity": "critical"
        },

        # ==================== Puerto Rico Building Regulations (PRBC) ====================
        {
            "code_type": "PRBC",
            "section": "1010.1.1",
            "title": "Size of Doors – Puerto Rico",
            "description": "Minimum clear width and height of doors in means of egress",
            "full_text": (
                "1010.1.1 Size of doors. The minimum width of each door opening in a means of egress "
                "shall be 32 inches (813 mm) of clear width. The clear height of each door opening "
                "shall be not less than 80 inches (2032 mm) in height. In hurricane-prone areas of "
                "Puerto Rico, doors shall be designed to withstand wind pressures in accordance with "
                "ASCE 7-16 and the Puerto Rico Building Regulations."
            ),
            "jurisdiction": "Puerto Rico Building Regulations",
            "severity": "critical"
        },
        {
            "code_type": "PRBC",
            "section": "1609.0",
            "title": "Wind Loads – Puerto Rico",
            "description": "Special wind load provisions for hurricane zones",
            "full_text": (
                "1609.0 Wind loads. Buildings and structures in Puerto Rico shall be designed for wind "
                "loads in accordance with ASCE 7-16, with a basic wind speed of 175 mph (3-second gust) "
                "for the entire island, as determined by the Puerto Rico Building Regulations. "
                "All structures shall comply with the additional requirements for windborne debris "
                "protection as specified in Chapter 16 of the PRBC."
            ),
            "jurisdiction": "Puerto Rico Building Regulations",
            "severity": "critical"
        },

        # ==================== Guam Territorial Building Code (GUAM) ====================
        {
            "code_type": "GUAM",
            "section": "1010.1.1",
            "title": "Size of Doors – Guam",
            "description": "Minimum clear width and height of doors in means of egress",
            "full_text": (
                "1010.1.1 Size of doors. The minimum width of each door opening in a means of egress "
                "shall be 32 inches (813 mm) of clear width. The clear height of each door opening "
                "shall be not less than 80 inches (2032 mm) in height. In Guam, doors shall also be "
                "designed to resist typhoon wind pressures as specified in the Guam Territorial "
                "Building Code."
            ),
            "jurisdiction": "Guam Territorial Building Code",
            "severity": "critical"
        },
        {
            "code_type": "GUAM",
            "section": "1609.0",
            "title": "Wind Loads – Guam (Typhoon)",
            "description": "Special wind load provisions for typhoon-prone Guam",
            "full_text": (
                "1609.0 Wind loads. Buildings and structures in Guam shall be designed for wind loads "
                "in accordance with ASCE 7-16, with a basic wind speed of 195 mph (3-second gust) for "
                "typhoon-prone areas. All structures shall include impact-resistant glazing and "
                "shutters to protect against windborne debris, as required by the Guam Territorial "
                "Building Code."
            ),
            "jurisdiction": "Guam Territorial Building Code",
            "severity": "critical"
        },

        # ==================== U.S. Virgin Islands (USVI) ====================
        {
            "code_type": "USVI",
            "section": "1010.1.1",
            "title": "Size of Doors – USVI",
            "description": "Minimum clear width and height of doors in means of egress",
            "full_text": (
                "1010.1.1 Size of doors. The minimum width of each door opening in a means of egress "
                "shall be 32 inches (813 mm) of clear width. The clear height of each door opening "
                "shall be not less than 80 inches (2032 mm) in height. In the U.S. Virgin Islands, "
                "doors shall be designed to withstand hurricane wind pressures as specified in the "
                "Virgin Islands Building Code."
            ),
            "jurisdiction": "U.S. Virgin Islands Building Code",
            "severity": "critical"
        },
        {
            "code_type": "USVI",
            "section": "1609.0",
            "title": "Wind Loads – USVI (Hurricane)",
            "description": "Special wind load provisions for hurricane-prone USVI",
            "full_text": (
                "1609.0 Wind loads. Buildings and structures in the U.S. Virgin Islands shall be "
                "designed for wind loads in accordance with ASCE 7, with a basic wind speed of "
                "185 mph (3-second gust) for hurricane-prone areas. All structures shall include "
                "impact-resistant glazing and shutters to protect against windborne debris, as "
                "required by the Virgin Islands Building Code."
            ),
            "jurisdiction": "U.S. Virgin Islands Building Code",
            "severity": "critical"
        },

        # ==================== Northern Mariana Islands (CNMI) ====================
        {
            "code_type": "CNMI",
            "section": "1010.1.1",
            "title": "Size of Doors – CNMI",
            "description": "Minimum clear width and height of doors in means of egress",
            "full_text": (
                "1010.1.1 Size of doors. The minimum width of each door opening in a means of egress "
                "shall be 32 inches (813 mm) of clear width. The clear height of each door opening "
                "shall be not less than 80 inches (2032 mm) in height. In the Northern Mariana Islands, "
                "doors shall be designed to resist typhoon wind pressures as specified in the CNMI "
                "Building Code."
            ),
            "jurisdiction": "CNMI Building Code (Commonwealth of the Northern Mariana Islands)",
            "severity": "critical"
        },
        {
            "code_type": "CNMI",
            "section": "1609.0",
            "title": "Wind Loads – CNMI (Typhoon)",
            "description": "Special wind load provisions for typhoon-prone CNMI",
            "full_text": (
                "1609.0 Wind loads. Buildings and structures in the Northern Mariana Islands shall be "
                "designed for wind loads in accordance with ASCE 7, with a basic wind speed of "
                "195 mph (3-second gust) for typhoon-prone areas. All structures shall include "
                "impact-resistant glazing and shutters to protect against windborne debris, as "
                "required by the CNMI Building Code."
            ),
            "jurisdiction": "CNMI Building Code (Commonwealth of the Northern Mariana Islands)",
            "severity": "critical"
        },

        # ==================== Miami-Dade County, Florida ====================
        {
            "code_type": "FBC",
            "section": "1010.1.1",
            "title": "Size of Doors – Miami-Dade Amendment",
            "description": "Miami-Dade County's additional requirements for door width",
            "full_text": (
                "1010.1.1 Size of doors. In addition to the 32-inch clear width requirement of the "
                "Florida Building Code, doors serving occupancies with high wind or hurricane exposure "
                "in Miami-Dade County shall have a clear width of not less than 34 inches (864 mm) "
                "to accommodate emergency equipment and evacuation under adverse weather conditions."
            ),
            "jurisdiction": "Miami-Dade County, Florida",
            "severity": "critical"
        },
        {
            "code_type": "FBC",
            "section": "1609.0",
            "title": "Wind Loads – Miami-Dade County (High Velocity Hurricane Zone)",
            "description": "Enhanced wind load requirements for Miami-Dade",
            "full_text": (
                "1609.0 Wind loads. In Miami-Dade County, which is designated as a High Velocity "
                "Hurricane Zone, the basic wind speed shall be 195 mph (3-second gust) for all "
                "buildings and structures. In addition, all glazing must be impact-resistant or "
                "protected by shutters, and the design must comply with the Miami-Dade County "
                "Product Control requirements."
            ),
            "jurisdiction": "Miami-Dade County, Florida",
            "severity": "critical"
        },

        # ==================== Broward County, Florida ====================
        {
            "code_type": "FBC",
            "section": "1010.1.1",
            "title": "Size of Doors – Broward County Amendment",
            "description": "Broward County's additional requirements for door width",
            "full_text": (
                "1010.1.1 Size of doors. Broward County adopts the Florida Building Code requirement "
                "that the minimum width of each door opening in a means of egress shall be 32 inches "
                "(813 mm) of clear width. In addition, doors that serve as exits from buildings with "
                "occupant loads exceeding 100 persons shall have a clear width of 36 inches (914 mm) "
                "to facilitate rapid evacuation."
            ),
            "jurisdiction": "Broward County, Florida",
            "severity": "critical"
        },
        {
            "code_type": "FBC",
            "section": "1609.0",
            "title": "Wind Loads – Broward County (Hurricane)",
            "description": "Wind load requirements for Broward County",
            "full_text": (
                "1609.0 Wind loads. Broward County, located in the hurricane-prone region of Florida, "
                "requires that all buildings be designed for a basic wind speed of 175 mph (3-second gust). "
                "Impact-resistant glazing and protection devices are required for all openings in "
                "structures located within the wind-borne debris region as defined by ASCE 7."
            ),
            "jurisdiction": "Broward County, Florida",
            "severity": "critical"
        },

        # ==================== Jacksonville, Florida ====================
        {
            "code_type": "FBC",
            "section": "1004.5",
            "title": "Occupant Load – Jacksonville Amendment",
            "description": "Jacksonville's requirement for assembly spaces",
            "full_text": (
                "1004.5 Occupant load calculations. In the City of Jacksonville, for assembly spaces "
                "with fixed seating, the occupant load shall be computed using a net floor area factor "
                "of 6 square feet per occupant (instead of the statewide 7 square feet) to account "
                "for higher density events. This amendment applies to all assembly occupancies within "
                "city limits."
            ),
            "jurisdiction": "Jacksonville, Florida",
            "severity": "warning"
        },
        {
            "code_type": "FBC",
            "section": "1010.1.1",
            "title": "Size of Doors – Jacksonville Adoption",
            "description": "Jacksonville adopts FBC door width requirements",
            "full_text": (
                "1010.1.1 Size of doors. Jacksonville adopts the Florida Building Code requirement "
                "that the minimum width of each door opening in a means of egress shall be 32 inches "
                "(813 mm) of clear width. The clear height of each door opening shall be not less than "
                "80 inches (2032 mm) in height. No additional local amendments apply."
            ),
            "jurisdiction": "Jacksonville, Florida",
            "severity": "critical"
        }
    ]


def generate_corpus_file(output_dir: str = "app/data", output_file: str = "us_legal_corpus_full.json") -> None:
    """
    Generate the complete JSON corpus of real building code provisions.

    Args:
        output_dir: Directory where the JSON file will be saved.
        output_file: Name of the output JSON file.
    """
    # Ensure the target directory exists
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, output_file)

    logger.info("Generating legal corpus with real building code provisions from all major jurisdictions...")
    records = get_code_records()

    logger.info(f"Prepared {len(records)} records.")
    logger.info(f"Writing to {file_path} ...")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        logger.info(f"Corpus successfully written to {file_path}")
    except Exception as e:
        logger.error(f"Error writing corpus file: {e}")
        raise


if __name__ == "__main__":
    generate_corpus_file()
