#!/usr/bin/env python3
"""
Property Acquisition API
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn

from .search_engine import SearchEngine

app = FastAPI(title="Property Acquisition Service", version="1.0.0")

engine = SearchEngine()


class SearchRequest(BaseModel):
    query: str
    user_id: str = "anonymous"


class PropertyResponse(BaseModel):
    id: str
    address: Dict[str, Any]
    price: float
    size_sqft: float
    bedrooms: int
    bathrooms: float
    property_type: str
    source: str


@app.get("/")
async def root():
    return {"service": "Property Acquisition Service", "version": "1.0.0", "status": "operational"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/search")
async def search(request: SearchRequest):
    try:
        result = engine.search(request.query, request.user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/property/{property_id}")
async def get_property(property_id: str):
    for result in engine.search_history:
        for item in result.get("results", []):
            if item["property"].id == property_id:
                return item
    raise HTTPException(status_code=404, detail="Property not found")
@app.post("/zoning/verify")
async def verify_zoning(address: Dict[str, str], project_type: str = "general"):
    """Verify zoning for an address"""
    try:
        zoning = engine.zoning.verify_zoning(address, project_type)
        allowed, reason = engine.zoning.check_use_allowed(address, project_type)
        
        return {
            "address": address,
            "project_type": project_type,
            "zoning": zoning.__dict__,
            "allowed": allowed,
            "reason": reason
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/assistant/analyze")
async def analyze_project(
    address: Dict[str, str],
    project_type: str = "residential",
    lot_size: int = 10000,
    property_count: int = 1
):
    """Get construction options using deterministic rules"""
    try:
        from .assistant import ConstructionAssistant
        assistant = ConstructionAssistant()
        result = assistant.analyze_project(
            address=address,
            project_type=project_type,
            lot_size=lot_size,
            property_count=property_count
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)

