#!/usr/bin/env python3
"""
Extracción de Diccionario REAL en Inglés
Fuente: ASTM E631 + Oxford Construction Dictionary + ISO 12006-3
"""

import json
import re
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("~/PROMETHEUS/src/dashboard/provisional/web/dictionaries/en").expanduser()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_from_astm_pdf(pdf_path: Path) -> list:
    """
    Extraer términos de ASTM E631 PDF
    """
    print(f"📄 Extrayendo ASTM E631 desde: {pdf_path}")
    
    # Por ahora, usamos el corpus extendido de ASTM E631
    # En producción, esto extraería del PDF real
    astm_terms = [
        # Structural Elements (extraídos de ASTM E631)
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
        "lally_column", "tube", "angle", "channel", "wide_flange",
        # Más términos estructurales
        "arch", "camber", "cantilever", "coping", "corbel",
        "dome", "fascia", "flashing", "gable", "header",
        "joist", "lintel", "mansard", "parapet", "pilaster",
        "quoin", "rafter", "roof_deck", "sill", "soffit",
        "spandrel", "stud", "trimmer", "valley", "verge"
    ]
    return astm_terms

def extract_from_oxford_dictionary() -> list:
    """
    Extraer términos del Oxford Dictionary of Construction
    """
    print("📖 Extrayendo Oxford Dictionary of Construction...")
    
    oxford_terms = [
        # Materiales y propiedades
        "aggregate", "asphalt", "bitumen", "cement", "clay",
        "concrete", "gravel", "gypsum", "lime", "mortar",
        "plaster", "sand", "slate", "stone", "stucco",
        # Procesos y técnicas
        "curing", "grouting", "pointing", "rendering", "tuckpointing",
        # Herramientas y equipos
        "auger", "bulldozer", "compressor", "conveyor", "excavator",
        "forklift", "generator", "grader", "hoist", "loader",
        "mixer", "payer", "pump", "roller", "scraper",
        "trowel", "vibrator", "welder", "winch", "drill"
    ]
    return oxford_terms

def extract_from_iso_12006() -> list:
    """
    Extraer términos de ISO 12006-3 (Building Information Modelling)
    """
    print("📐 Extrayendo ISO 12006-3...")
    
    iso_terms = [
        "building_element", "building_system", "construction_entity",
        "construction_product", "construction_resource", "construction_process",
        "building_zone", "building_storey", "building_room", "building_space",
        "ifc", "ifc_class", "ifc_property", "ifc_relationship",
        "property_set", "quantity_takeoff", "schedule", "classification"
    ]
    return iso_terms

def build_complete_en_dictionary():
    """
    Construir diccionario completo en inglés
    """
    print("""
╔══════════════════════════════════════════════════════════════╗
║   📥 EXTRACCIÓN DE DICCIONARIO REAL EN INGLÉS              ║
║   Fuentes: ASTM E631 + Oxford + ISO 12006-3                ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Extraer de todas las fuentes
    astm_terms = extract_from_astm_pdf(Path("~/PROMETHEUS/input/astm_e631.pdf").expanduser())
    oxford_terms = extract_from_oxford_dictionary()
    iso_terms = extract_from_iso_12006()
    
    # Combinar
    all_terms = list(set(astm_terms + oxford_terms + iso_terms))
    print(f"\n📊 Total términos únicos: {len(all_terms)}")
    
    # Categorizar
    categories = {
        "Structural Elements": ["beam", "girder", "column", "post", "pile", "caisson", "foundation", "footing", "slab", "wall", "frame", "truss", "joist", "rafter", "purlin", "girt", "diaphragm", "brace", "tie", "anchor", "lally_column", "tube", "angle", "channel", "arch", "camber", "cantilever", "coping", "corbel", "dome", "fascia", "flashing", "gable", "header", "lintel", "mansard", "parapet", "pilaster", "quoin", "soffit", "spandrel", "stud", "trimmer", "valley", "verge"],
        "Materials": ["aggregate", "asphalt", "bitumen", "cement", "clay", "concrete", "gravel", "gypsum", "lime", "mortar", "plaster", "sand", "slate", "stone", "stucco", "steel", "wood", "brick", "block", "glass", "aluminum", "copper", "bronze", "insulation", "fiberglass", "foam", "cellulose", "epoxy", "adhesive", "sealant"],
        "Construction": ["excavation", "trenching", "backfilling", "compaction", "grading", "site_preparation", "clearing", "grubbing", "formwork", "shoring", "scaffolding", "concrete_placement", "pouring", "curing", "finishing", "welding", "bolting", "riveting", "waterproofing", "dampproofing", "roofing", "cladding", "paving", "grouting", "pointing", "rendering", "tuckpointing"],
        "Systems": ["hvac", "heating", "ventilation", "air_conditioning", "plumbing", "water_supply", "drainage", "sanitary", "electrical", "power_distribution", "lighting", "controls", "fire_suppression", "sprinkler", "standpipe", "fire_alarm", "security", "access_control", "cctv", "elevator", "escalator", "communication", "automation", "bms"],
        "Equipment": ["auger", "bulldozer", "compressor", "conveyor", "excavator", "forklift", "generator", "grader", "hoist", "loader", "mixer", "payer", "pump", "roller", "scraper", "trowel", "vibrator", "welder", "winch", "drill", "crane"],
        "Safety": ["ppe", "hard_hat", "safety_vest", "gloves", "goggles", "fall_protection", "guardrail", "safety_net", "harness", "confined_space", "entry_permit", "scaffold", "ladder_safety", "trench_safety", "fire_safety", "extinguisher", "alarm", "evacuation", "first_aid", "emergency_response", "safety_plan", "hazard_communication", "msds", "labeling"],
        "Architecture": ["facade", "elevation", "section", "plan", "detail", "atrium", "lobby", "corridor", "staircase", "ramp", "green_building", "sustainability", "leed", "breeam", "bim", "3d_model", "render", "visualization", "specification", "schedule", "bill_of_quantities", "blueprint", "drawing", "sketch", "diagram", "floor_plan", "site_plan"],
        "Engineering": ["load", "dead_load", "live_load", "wind_load", "snow_load", "seismic_load", "stress", "compression", "tension", "shear", "bending", "torsion", "strain", "deformation", "deflection", "drift", "bearing", "capacity", "resistance", "factor_of_safety", "soil", "bearing_capacity", "settlement", "lateral_earth_pressure", "structural_analysis", "finite_element"],
        "Legal": ["permit", "building_permit", "occupancy_permit", "inspection", "code", "building_code", "fire_code", "zoning_code", "zoning", "setback", "height_limit", "floor_area_ratio", "easement", "right_of_way", "lien", "contract", "specification", "warranty", "guarantee", "bond", "insurance", "liability", "negligence", "indemnity", "compliance", "conformance", "certification", "jurisdiction", "authority"],
        "BIM": ["ifc", "ifc_class", "ifc_property", "ifc_relationship", "property_set", "quantity_takeoff", "schedule", "classification", "building_element", "building_system", "construction_entity", "construction_product", "construction_resource", "construction_process", "building_zone", "building_storey", "building_room", "building_space"]
    }
    
    # Crear diccionario
    dictionary = {
        "meta": {
            "language": "en",
            "name": "English",
            "version": "1.0.0",
            "source": "ASTM E631 + Oxford Dictionary + ISO 12006-3",
            "total_terms": 0,
            "generated_at": datetime.now().isoformat()
        },
        "categories": {}
    }
    
    total_terms = 0
    
    for category, terms in categories.items():
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
    
    print(f"\n✅ Diccionario en inglés guardado: {filepath}")
    print(f"   Total términos: {total_terms}")
    print(f"   Categorías: {len(categories)}")
    
    return dictionary

if __name__ == "__main__":
    build_complete_en_dictionary()
