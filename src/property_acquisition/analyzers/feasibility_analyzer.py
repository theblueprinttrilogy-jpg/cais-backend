#!/usr/bin/env python3
"""
Feasibility Analyzer - Analyze project feasibility
"""

from typing import Dict, List
from ..models import Property, ZoningInfo, FeasibilityAnalysis


class FeasibilityAnalyzer:
    """Analyze project feasibility"""

    def __init__(self):
        self.construction_costs = {
            "house": 200.0,
            "church": 250.0,
            "warehouse": 150.0,
            "office": 220.0,
            "restaurant": 280.0,
            "general": 200.0
        }

        self.value_multipliers = {
            "house": 1.2,
            "church": 1.1,
            "warehouse": 1.3,
            "office": 1.25,
            "restaurant": 1.3,
            "general": 1.2
        }

    def analyze(self, property: Property, zoning: ZoningInfo, project_type: str) -> FeasibilityAnalysis:
        """Analyze feasibility"""
        property_cost = property.price
        construction_cost = property.size_sqft * self.construction_costs.get(project_type, 200.0)
        total_cost = property_cost + construction_cost

        estimated_value = (property_cost + construction_cost) * self.value_multipliers.get(project_type, 1.2)
        roi = ((estimated_value - total_cost) / total_cost) * 100

        zoning_approved = project_type in zoning.allowed_uses
        zoning_issues = []
        if not zoning_approved:
            zoning_issues.append(f"'{project_type}' not in allowed uses: {zoning.allowed_uses}")

        score = self._calculate_score(roi, zoning_approved, len(zoning_issues))
        risk_level = self._calculate_risk(roi, zoning_approved, len(zoning_issues))

        return FeasibilityAnalysis(
            property_id=property.id,
            project_type=project_type,
            property_cost=property_cost,
            construction_cost=construction_cost,
            total_cost=total_cost,
            estimated_value=estimated_value,
            roi=roi,
            zoning_approved=zoning_approved,
            zoning_issues=zoning_issues,
            recommendations=self._generate_recommendations(roi, zoning_approved),
            timeline_months=12,
            risk_level=risk_level,
            score=score
        )

    def _calculate_score(self, roi: float, zoning_approved: bool, issues: int) -> float:
        score = 50.0
        if roi > 30:
            score += 25
        elif roi > 20:
            score += 15
        elif roi > 10:
            score += 5
        else:
            score -= 10

        if zoning_approved:
            score += 15
        else:
            score -= 20

        score -= issues * 5
        return max(0, min(100, score))

    def _calculate_risk(self, roi: float, zoning_approved: bool, issues: int) -> str:
        if roi > 25 and zoning_approved and issues < 2:
            return "low"
        elif roi > 15 and zoning_approved and issues < 4:
            return "medium"
        return "high"

    def _generate_recommendations(self, roi: float, zoning_approved: bool) -> List[str]:
        recommendations = []
        if roi > 25:
            recommendations.append("Excellent ROI - proceed with due diligence")
        elif roi > 15:
            recommendations.append("Good ROI - consider moving forward")
        else:
            recommendations.append("Low ROI - reconsider or negotiate price")

        if not zoning_approved:
            recommendations.append("Address zoning issues - consider variance application")

        recommendations.append("Conduct thorough property inspection")
        return recommendations
