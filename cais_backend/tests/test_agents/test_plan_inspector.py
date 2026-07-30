"""
Test Plan Inspector - Tests for PlanInspector Agent

This module contains tests for the PlanInspector agent.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.agents.plan_inspector import PlanInspector


class TestPlanInspector:
    """Tests for PlanInspector agent."""

    def test_plan_inspector_initialization(self):
        """Test PlanInspector initialization."""
        inspector = PlanInspector()
        assert inspector.name == "PlanInspector"
        assert inspector.type == "visual_scanner"
        assert inspector.dpi == 200
        assert inspector.padding == 20

    @patch('app.agents.plan_inspector.pdf2image.convert_from_path')
    def test_convert_pdf_to_images(self, mock_convert, test_document):
        """Test PDF to image conversion."""
        mock_convert.return_value = [Mock(), Mock()]

        inspector = PlanInspector()
        result = inspector._convert_pdf_to_images(test_document.file_path)

        assert len(result) == 2
        mock_convert.assert_called_once_with(
            test_document.file_path,
            dpi=200,
            fmt='png',
            thread_count=4
        )

    @patch('app.agents.plan_inspector.pytesseract.image_to_string')
    def test_detect_numeric_patterns(self, mock_ocr):
        """Test numeric pattern detection."""
        import numpy as np

        mock_ocr.return_value = "Door width 30 IN"

        inspector = PlanInspector()
        image = np.zeros((100, 100, 3), dtype=np.uint8)

        violations = inspector._detect_numeric_patterns(image, 1)

        assert len(violations) > 0
        assert violations[0]["type"] == "door_width"
        assert violations[0]["severity"] == "critical"
        assert "30" in violations[0]["description"]

    @patch('app.agents.plan_inspector.pytesseract.image_to_string')
    def test_detect_keywords(self, mock_ocr):
        """Test keyword detection."""
        import numpy as np

        mock_ocr.return_value = "FIRE EXIT at north wall"

        inspector = PlanInspector()
        image = np.zeros((100, 100, 3), dtype=np.uint8)

        violations = inspector._detect_keywords(image, 1)

        assert len(violations) > 0
        assert violations[0]["type"] == "keyword"
        assert "FIRE EXIT" in violations[0]["description"]

    @patch('app.agents.plan_inspector.pytesseract.image_to_string')
    def test_extract_address(self, mock_ocr):
        """Test address extraction."""
        from PIL import Image

        mock_ocr.return_value = "123 Main Street, Los Angeles, CA"

        inspector = PlanInspector()
        image = Image.new('RGB', (100, 100))

        address = inspector._extract_address(image)

        assert address is not None
        assert "Main Street" in address

    @patch('app.agents.plan_inspector.pytesseract.image_to_string')
    def test_extract_jurisdiction(self, mock_ocr):
        """Test jurisdiction extraction."""
        from PIL import Image

        mock_ocr.return_value = "City of Miami, Florida"

        inspector = PlanInspector()
        image = Image.new('RGB', (100, 100))

        jurisdiction = inspector._extract_jurisdiction(image)

        assert jurisdiction is not None
        assert "Miami-Dade" in jurisdiction

    def test_get_code_reference(self):
        """Test code reference lookup."""
        inspector = PlanInspector()

        assert inspector._get_code_reference("FIRE EXIT") == "IBC 1007 - Means of Egress for Fire Safety"
        assert inspector._get_code_reference("DOOR") == "IBC 1005.3.1 - Door Width Requirements"
        assert inspector._get_code_reference("UNKNOWN") == "IBC General Requirements"
