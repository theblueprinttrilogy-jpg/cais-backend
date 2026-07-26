#!/usr/bin/env python3
"""
Descarga del Diccionario en Inglés
Fuente: ASTM E631 - Standard Terminology for Building Constructions
"""

import json
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("~/PROMETHEUS/src/dashboard/provisional/web/dictionaries/en").expanduser()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def build_en_dictionary():
    """Construir diccionario en inglés"""
    
    # ASTM E631 - Terminología estándar
    en_terms = {
        "Structural Elements": [
            "beam", "girder", "column", "post", "pile", "caisson",
            "foundation", "footing", "grade_beam", "mat_foundation",
            "slab", "slab_on_grade", "elevated_slab", "post_tensioned_slab",
            "wall", "bearing_wall", "non_bearing_wall", "shear_wall",
            "curtain_wall", "party_wall", "retaining_wall",
            "frame", "moment_frame", "braced_frame", "space_frame",
            "truss", "joist", "rafter", "purlin", "girt",
            "diaphragm", "floor_diaphragm", "roof_diaphragm",
            "brace", "cross_brace", "knee_brace", "wind_brace",
            "tie", "anchor", "hold_down", "base_plate",
            "lally_column", "tube", "angle", "channel", "wide_flange"
        ],
        "Materials": [
            "concrete", "reinforced_concrete", "prestressed_concrete",
            "steel", "structural_steel", "rebar", "wire_mesh",
            "wood", "lumber", "timber", "plywood", "osb",
            "masonry", "brick", "block", "stone",
            "glass", "tempered_glass", "laminated_glass", "insulated_glass",
            "composite", "fiber_composite", "polymer",
            "aluminum", "copper", "bronze", "stainless_steel",
            "asphalt", "bitumen", "tar", "sealant",
            "insulation", "fiberglass", "foam", "cellulose",
            "gypsum", "plaster", "stucco", "mortar",
            "grout", "epoxy", "adhesive", "fastener",
            "nail", "screw", "bolt", "rivet", "weld"
        ],
        "Construction": [
            "excavation", "trenching", "backfilling", "compaction",
            "grading", "site_preparation", "clearing", "grubbing",
            "formwork", "shoring", "scaffolding", "ladder",
            "crane", "hoist", "elevator", "conveyor",
            "concrete_placement", "pouring", "curing", "finishing",
            "welding", "bolting", "riveting", "adhesive_bonding",
            "waterproofing", "dampproofing", "sealing", "caulking",
            "roofing", "membrane", "shingle", "tile", "metal_panel",
            "cladding", "siding", "curtain_wall", "storefront",
            "paving", "asphalt_paving", "concrete_paving", "interlocking_pavers"
        ],
        "Systems": [
            "hvac", "heating", "ventilation", "air_conditioning",
            "plumbing", "water_supply", "drainage", "sanitary",
            "electrical", "power_distribution", "lighting", "controls",
            "fire_suppression", "sprinkler", "standpipe", "fire_alarm",
            "security", "access_control", "cctv", "intrusion_detection",
            "elevator", "escalator", "moving_walk",
            "communication", "data", "telephone", "audiovisual"
        ],
        "Safety": [
            "ppe", "hard_hat", "safety_vest", "gloves", "goggles",
            "fall_protection", "guardrail", "safety_net", "harness",
            "confined_space", "entry_permit", "ventilation",
            "scaffold", "ladder_safety", "trench_safety",
            "fire_safety", "extinguisher", "alarm", "evacuation",
            "first_aid", "emergency_response", "safety_plan",
            "hazard_communication", "msds", "labeling",
            "lockout_tagout", "machine_guarding", "electrical_safety"
        ],
        "Architecture": [
            "facade", "elevation", "section", "plan", "detail",
            "atrium", "lobby", "corridor", "staircase", "ramp",
            "green_building", "sustainability", "leed", "breeam",
            "bim", "3d_model", "render", "visualization",
            "specification", "schedule", "bill_of_quantities",
            "blueprint", "drawing", "sketch", "diagram"
        ],
        "Engineering": [
            "load", "dead_load", "live_load", "wind_load", "snow_load", "seismic_load",
            "stress", "compression", "tension", "shear", "bending", "torsion",
            "strain", "deformation", "deflection", "drift",
            "bearing", "capacity", "resistance", "factor_of_safety",
            "soil", "bearing_capacity", "settlement", "lateral_earth_pressure"
        ],
        "Legal": [
            "permit", "building_permit", "occupancy_permit", "sign_permit",
            "inspection", "final_inspection", "rough_in_inspection",
            "code", "building_code", "fire_code", "zoning_code",
            "zoning", "setback", "height_limit", "floor_area_ratio",
            "easement", "right_of_way", "utility_easement",
            "lien", "mechanic_lien", "materialman_lien",
            "contract", "construction_contract", "subcontractor_agreement",
            "specification", "technical_specification", "performance_spec",
            "warranty", "guarantee", "bond", "insurance",
            "liability", "negligence", "indemnity",
            "compliance", "conformance", "certification",
            "jurisdiction", "authority", "building_official"
        ]
    }
    
    # Crear diccionario
    dictionary = {
        "meta": {
            "language": "en",
            "name": "English",
            "version": "1.0.0",
            "source": "ASTM E631 - Standard Terminology for Building Constructions",
            "total_terms": 0,
            "generated_at": datetime.now().isoformat()
        },
        "categories": {}
    }
    
    total_terms = 0
    
    for category, terms in en_terms.items():
        category_dict = {}
        for term in terms:
            category_dict[term] = term  # En inglés, el término es su propia definición
            total_terms += 1
        dictionary['categories'][category] = category_dict
    
    dictionary['meta']['total_terms'] = total_terms
    
    # Guardar
    filepath = OUTPUT_DIR / "construction_terms.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dictionary, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Diccionario en inglés guardado: {filepath}")
    print(f"   Total términos: {total_terms}")
    print(f"   Categorías: {list(en_terms.keys())}")

if __name__ == "__main__":
    build_en_dictionary()
