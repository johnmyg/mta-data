from fastapi import FastAPI, HTTPException
from typing import List, Dict, Any
from mta_parser import MTAFeedParser, MTAArrivalsService
from station_lookup import station_lookup

app = FastAPI(title="MTA Train Arrivals API", version="1.0.0")

# Initialize services (you might want to make these singletons)
parser = MTAFeedParser()
arrivals_service = MTAArrivalsService(parser)

@app.get("/stations/{stop_id}/arrivals")
async def get_station_arrivals(stop_id: str, limit: int = 3) -> Dict[str, Any]:
    """Get next trains arriving at a specific station"""
    
    # Validate station exists
    station_name = station_lookup.get_station_name(stop_id)
    if not station_name:
        raise HTTPException(status_code=404, detail=f"Station with stop_id '{stop_id}' not found")
    
    # Get arrivals
    arrivals = arrivals_service.get_station_arrivals(stop_id, minutes_ahead=60)
    
    # Limit results
    limited_arrivals = arrivals[:limit]
    
    return {
        "stop_id": stop_id,
        "station_name": station_name,
        "arrivals": limited_arrivals,
        "total_arrivals": len(arrivals)
    }

@app.get("/stations/search")
async def search_stations(q: str) -> Dict[str, List[str]]:
    """Search for stations by name"""
    if len(q) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
    
    matches = station_lookup.search_stations(q)
    return matches

@app.get("/stations")
async def get_all_stations() -> List[str]:
    """Get list of all station names"""
    return station_lookup.get_all_stations()