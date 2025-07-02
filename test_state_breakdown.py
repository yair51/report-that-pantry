#!/usr/bin/env python3

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Location, Report
from app.views import calculate_nationwide_analytics

def test_state_breakdown():
    """Test the state breakdown functionality"""
    
    app = create_app()
    
    with app.app_context():
        print("Testing state breakdown analytics...")
        
        # Get analytics data
        analytics = calculate_nationwide_analytics()
        
        if analytics and 'state_breakdown' in analytics:
            print(f"\nState breakdown found with {len(analytics['state_breakdown'])} states:")
            print("-" * 60)
            
            for state_name, data in analytics['state_breakdown'].items():
                print(f"State: {state_name}")
                print(f"  Locations: {data['locations']}")
                print(f"  Reports: {data['reports']}")
                print(f"  Avg Fullness: {data['avg_fullness']}%")
                print("-" * 30)
        else:
            print("No state breakdown data found")
        
        # Also check if we have any locations
        total_locations = Location.query.count()
        total_reports = Report.query.count()
        print(f"\nDatabase summary:")
        print(f"Total locations: {total_locations}")
        print(f"Total reports: {total_reports}")

if __name__ == "__main__":
    test_state_breakdown()
