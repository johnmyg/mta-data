import csv
from typing import Dict, Optional
from pathlib import Path

class StationLookup:
    """Handles mapping between MTA stop IDs and human-readable station names"""
    
    def __init__(self, stops_file_path: str = "data/stops.txt"):
        self.stops_file_path = stops_file_path
        self._stop_id_to_name: Dict[str, str] = {}
        self._name_to_stop_ids: Dict[str, list] = {}
        self._load_stops()
    
    def _load_stops(self):
        """Load stop data from CSV file"""
        try:
            with open(self.stops_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    stop_id = row['stop_id'].strip()
                    stop_name = row['stop_name'].strip()
                    
                    # Map stop_id -> stop_name
                    self._stop_id_to_name[stop_id] = stop_name
                    
                    # Map stop_name -> list of stop_ids (for search)
                    if stop_name not in self._name_to_stop_ids:
                        self._name_to_stop_ids[stop_name] = []
                    self._name_to_stop_ids[stop_name].append(stop_id)
                    
        except FileNotFoundError:
            print(f"Warning: Stops file not found at {self.stops_file_path}")
        except Exception as e:
            print(f"Error loading stops file: {e}")
    
    def get_station_name(self, stop_id: str) -> Optional[str]:
        """Get station name from stop ID"""
        return self._stop_id_to_name.get(stop_id)
    
    def get_stop_ids(self, station_name: str) -> list:
        """Get all stop IDs for a station name (handles multiple platforms)"""
        return self._name_to_stop_ids.get(station_name, [])
    
    def search_stations(self, query: str) -> Dict[str, list]:
        """Search for stations by partial name match"""
        query_lower = query.lower()
        matches = {}
        
        for station_name, stop_ids in self._name_to_stop_ids.items():
            if query_lower in station_name.lower():
                matches[station_name] = stop_ids
                
        return matches
    
    def get_all_stations(self) -> list:
        """Get list of all unique station names"""
        return list(self._name_to_stop_ids.keys())
    
    def get_station_info(self, stop_id: str) -> Optional[Dict[str, any]]: #type: ignore
        """Get detailed info about a station"""
        station_name = self.get_station_name(stop_id)
        if not station_name:
            return None
            
        # Determine direction from stop_id (common MTA pattern)
        direction = None
        if stop_id.endswith('N'):
            direction = 'Northbound'
        elif stop_id.endswith('S'):
            direction = 'Southbound'
        
        return {
            'stop_id': stop_id,
            'station_name': station_name,
            'direction': direction,
            'all_platforms': self.get_stop_ids(station_name)
        }

# Global instance for easy importing
station_lookup = StationLookup()