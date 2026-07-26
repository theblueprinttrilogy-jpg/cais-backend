import pytest
import importlib.util
import sys
from pathlib import Path
from src.generators.code_generator import CodeGenerator

@pytest.fixture
def generator(tmp_path):
    return CodeGenerator(output_dir=str(tmp_path))

def test_generate_and_load_api(generator):
    # 1. Probar que el generador funciona
    api_path = generator._generate_api()
    assert api_path.exists()
    assert api_path.name == 'api.py'

    # 2. Carga dinámica del archivo generado
    spec = importlib.util.spec_from_file_location("generated_api", api_path)
    generated_module = importlib.util.module_from_spec(spec)
    sys.modules["generated_api"] = generated_module
    spec.loader.exec_module(generated_module)

    # 3. Validar instancia de FastAPI
    assert hasattr(generated_module, "app")
    from fastapi import FastAPI
    assert isinstance(generated_module.app, FastAPI)
