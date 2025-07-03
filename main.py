from mta_parser import MTAFeedParser, MTAArrivalsService
from station_lookup import station_lookup

def main():
    parser = MTAFeedParser()
    arrivals_service = MTAArrivalsService(parser)
    
   # 86th Street R train station stop IDs (you'll need to find these in your stops.txt)
    station_stop_ids = ["R44N", "R44S"]  
   
    print("Next R trains at 86th St (Brooklyn):")
   
    for stop_id in station_stop_ids:
        station_name = station_lookup.get_station_name(stop_id)
        arrivals = arrivals_service.get_station_arrivals(stop_id, minutes_ahead=60)
        
        # Filter for only R trains
        r_trains = [train for train in arrivals if train['route'] == 'R']
        
        # Determine direction
        direction = "Northbound (to Manhattan)" if stop_id.endswith('N') else "Southbound (to Bay Ridge)"
        
        print(f"\n{station_name or '86th St'} - {direction} ({stop_id}):")
        
        if r_trains:
            for train in r_trains[:3]:  # Show next 3 R trains
                print(f"  R train: {train['minutes_away']} minutes away")
        else:
            print("  No R trains found in next hour")

if __name__ == "__main__":
    main()