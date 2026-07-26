#!/usr/bin/env python3
"""
Test Suite for Designer Agent
"""

import unittest
import json
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.designer.DesignerAgent import DesignerAgent

class TestDesignerAgent(unittest.TestCase):
    """Test cases for Designer Agent"""
    
    def setUp(self):
        """Set up test environment"""
        self.agent = DesignerAgent(output_dir=Path("/tmp/test_dashboard"))
        
    def test_initialization(self):
        """Test agent initialization"""
        self.assertIsNotNone(self.agent)
        self.assertTrue(self.agent.output_dir.exists())
        
    def test_research_dashboards(self):
        """Test dashboard research"""
        inspirations = self.agent.research_top_dashboards()
        self.assertGreater(len(inspirations), 0)
        self.assertIsInstance(inspirations[0].name, str)
        
    def test_color_scheme_generation(self):
        """Test color scheme generation"""
        colors = self.agent.generate_color_scheme()
        self.assertIn("bg_primary", colors)
        self.assertIn("accent_gold", colors)
        self.assertTrue(colors["bg_primary"].startswith("#"))
        
    def test_typography_generation(self):
        """Test typography generation"""
        typography = self.agent.generate_typography()
        self.assertIn("font_family", typography)
        self.assertIn("sizes", typography)
        self.assertIn("weights", typography)
        
    def test_dashboard_creation(self):
        """Test full dashboard creation"""
        design = self.agent.create_dashboard()
        self.assertIsNotNone(design)
        self.assertEqual(design.name, "CAIS Sovereign Dashboard")
        
        # Check files were created
        html_path = self.agent.output_dir / "index.html"
        css_path = self.agent.output_dir / "dashboard.css"
        js_path = self.agent.output_dir / "dashboard.js"
        
        self.assertTrue(html_path.exists())
        self.assertTrue(css_path.exists())
        self.assertTrue(js_path.exists())
        
        # Check content
        html_content = html_path.read_text()
        self.assertIn("CAIS Sovereign Dashboard", html_content)
        self.assertIn("WORM Chain Integrity", html_content)
        self.assertIn("Agent Performance", html_content)
        
        css_content = css_path.read_text()
        self.assertIn("--bg-primary", css_content)
        self.assertIn("--accent-gold", css_content)
        
        js_content = js_path.read_text()
        self.assertIn("CAIS SOVEREIGN DASHBOARD", js_content)
        self.assertIn("updateMetrics", js_content)
        
    def test_design_summary(self):
        """Test design summary generation"""
        self.agent.create_dashboard()
        summary = self.agent.get_design_summary()
        
        self.assertEqual(summary["status"], "✅ DESIGN COMPLETE")
        self.assertIn("inspirations", summary)
        self.assertIn("components", summary)
        self.assertIn("design_principles", summary)


if __name__ == "__main__":
    unittest.main()
