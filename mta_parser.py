import requests
from google.transit import gtfs_realtime_pb2
from collections import defaultdict
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class TripUpdate:
    """Structured representation of a single trip update"""
    trip_id: str
    route_id: str
    direction_id: Optional[int]
    stop_updates: List[Dict[str, Any]]

@dataclass 
class StopTimeUpdate:
    """Structured representation of a stop time update"""
    stop_id: str
    arrival_time: Optional[int]
    departure_time: Optional[int]
    delay: Optional[int]
    stop_sequence: Optional[int]

class MTAFeedParser:
    """Handles MTA GTFS real-time feed parsing and data extraction"""
    
    # MTA Real-time feed URLs (no API key needed)
    FEED_URLS = [
        'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace',
        'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm', 
        'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g',
        'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz',
        'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l',
        'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw',
        'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si'
    ]
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    def get_mta_feed_data(self, feed_urls: Optional[List[str]] = None) -> List[TripUpdate]:
        """
        Fetch and parse all MTA GTFS real-time feeds
        
        Args:
            feed_urls: Optional list of specific feed URLs to fetch
            
        Returns:
            List of TripUpdate objects containing parsed data
        """
        if feed_urls is None:
            feed_urls = self.FEED_URLS
            
        all_trip_updates = []
        
        for feed_url in feed_urls:
            try:
                trip_updates = self._fetch_single_feed(feed_url)
                all_trip_updates.extend(trip_updates)
            except Exception as e:
                print(f"Error fetching feed {feed_url}: {e}")
                continue
                
        return all_trip_updates
    
    def _fetch_single_feed(self, feed_url: str) -> List[TripUpdate]:
        """Fetch and parse a single GTFS feed"""
        response = requests.get(feed_url, timeout=self.timeout)
        response.raise_for_status()
        
        feed = gtfs_realtime_pb2.FeedMessage() #type: ignore
        feed.ParseFromString(response.content)
        
        trip_updates = []
        
        for entity in feed.entity:
            if entity.HasField('trip_update'):
                trip_update = self._parse_trip_update(entity.trip_update)
                if trip_update:
                    trip_updates.append(trip_update)
                    
        return trip_updates
    
    def _parse_trip_update(self, trip_update) -> Optional[TripUpdate]:
        """Parse a single trip update entity"""
        try:
            stop_updates = []
            
            for stop_update in trip_update.stop_time_update:
                stop_data = {
                    'stop_id': stop_update.stop_id,
                    'arrival_time': stop_update.arrival.time if stop_update.HasField('arrival') else None,
                    'departure_time': stop_update.departure.time if stop_update.HasField('departure') else None,
                    'delay': stop_update.arrival.delay if stop_update.HasField('arrival') else None,
                    'stop_sequence': stop_update.stop_sequence if stop_update.HasField('stop_sequence') else None
                }
                stop_updates.append(stop_data)
            
            return TripUpdate(
                trip_id=trip_update.trip.trip_id,
                route_id=trip_update.trip.route_id,
                direction_id=trip_update.trip.direction_id if trip_update.trip.HasField('direction_id') else None,
                stop_updates=stop_updates
            )
            
        except Exception as e:
            print(f"Error parsing trip update: {e}")
            return None

class MTAArrivalsService:
    """Service for processing MTA data into arrival predictions"""
    
    def __init__(self, feed_parser: MTAFeedParser):
        self.feed_parser = feed_parser
    
    def get_next_trains_per_station(self, 
                                  minutes_ahead: int = 60,
                                  max_trains_per_route: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get next train arrivals for all stations
        
        Args:
            minutes_ahead: Only return trains arriving within this many minutes
            max_trains_per_route: Maximum number of trains to return per route per station
            
        Returns:
            Dict mapping station_id to list of arrival predictions
        """
        # Get raw feed data
        trip_updates = self.feed_parser.get_mta_feed_data()
        
        # Process into arrivals
        return self._process_arrivals(trip_updates, minutes_ahead, max_trains_per_route)
    
    def get_station_arrivals(self, 
                           station_id: str,
                           minutes_ahead: int = 60) -> List[Dict[str, Any]]:
        """Get arrivals for a specific station"""
        all_arrivals = self.get_next_trains_per_station(minutes_ahead)
        return all_arrivals.get(station_id, [])
    
    def get_route_arrivals(self, 
                          route_id: str,
                          minutes_ahead: int = 60) -> Dict[str, List[Dict[str, Any]]]:
        """Get arrivals for all stations on a specific route"""
        trip_updates = self.feed_parser.get_mta_feed_data()
        
        # Filter to only this route
        route_updates = [trip for trip in trip_updates if trip.route_id == route_id]
        
        return self._process_arrivals(route_updates, minutes_ahead)
    
    def _process_arrivals(self, 
                         trip_updates: List[TripUpdate],
                         minutes_ahead: int,
                         max_trains_per_route: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Process trip updates into station arrival predictions"""
        current_time = int(time.time())
        cutoff_time = current_time + (minutes_ahead * 60)
        
        # Group arrivals by station and route
        station_route_arrivals = defaultdict(lambda: defaultdict(list))
        
        for trip in trip_updates:
            for stop_update in trip.stop_updates:
                arrival_time = stop_update.get('arrival_time')
                
                if arrival_time and current_time < arrival_time <= cutoff_time:
                    minutes_away = (arrival_time - current_time) // 60
                    
                    arrival_data = {
                        'route': trip.route_id,
                        'arrival_time': arrival_time,
                        'minutes_away': minutes_away,
                        'trip_id': trip.trip_id,
                        'direction_id': trip.direction_id,
                        'delay': stop_update.get('delay', 0)
                    }
                    
                    station_route_arrivals[stop_update['stop_id']][trip.route_id].append(arrival_data)
        
        # Convert to final format and sort
        final_arrivals = {}
        
        for station_id, routes in station_route_arrivals.items():
            station_arrivals = []
            
            for route_id, arrivals in routes.items():
                # Sort by arrival time and limit
                sorted_arrivals = sorted(arrivals, key=lambda x: x['arrival_time'])
                station_arrivals.extend(sorted_arrivals[:max_trains_per_route])
            
            # Sort all arrivals by time
            final_arrivals[station_id] = sorted(station_arrivals, key=lambda x: x['arrival_time'])
        
        return final_arrivals

# # Usage example
# if __name__ == "__main__":
#     # Initialize services
#     parser = MTAFeedParser(timeout=15)
#     arrivals_service = MTAArrivalsService(parser)
    
#     # Get all station arrivals
#     all_arrivals = arrivals_service.get_next_trains_per_station(minutes_ahead=30)
    
#     # Get specific station
#     union_sq_arrivals = arrivals_service.get_station_arrivals("L08N", minutes_ahead=20)
    
#     # Get specific route
#     l_train_arrivals = arrivals_service.get_route_arrivals("L", minutes_ahead=45)
    
#     # Print sample results
#     print("Sample station arrivals:")
#     for station_id, arrivals in list(all_arrivals.items())[:3]:
#         print(f"\nStation {station_id}:")
#         for arrival in arrivals[:3]:  # Show first 3 trains
#             print(f"  {arrival['route']} train: {arrival['minutes_away']} min")