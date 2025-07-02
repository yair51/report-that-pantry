#!/usr/bin/env python3

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Location, Report

# US State abbreviations for validation
VALID_STATE_ABBREVIATIONS = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
    'DC', 'PR', 'VI', 'AS', 'GU', 'MP'
}

def check_invalid_state_names():
    """Check for locations with full state names instead of abbreviations"""
    
    app = create_app()
    
    with app.app_context():
        # Get all locations
        all_locations = Location.query.all()
        
        print(f"Total locations in database: {len(all_locations)}")
        print()
        
        # Find locations with invalid state values (not 2-letter codes)
        invalid_locations = []
        for location in all_locations:
            if not location.state or location.state.upper() not in VALID_STATE_ABBREVIATIONS:
                invalid_locations.append(location)
        
        if invalid_locations:
            print(f"Found {len(invalid_locations)} locations with invalid state values:")
            print("-" * 80)
            
            for location in invalid_locations:
                report_count = Report.query.filter_by(location_id=location.id).count()
                print(f"ID: {location.id}")
                print(f"Name: {location.name}")
                print(f"State: '{location.state}' (should be 2-letter abbreviation)")
                print(f"Address: {location.address}")
                print(f"Reports: {report_count}")
                print("-" * 40)
            
            # Ask for confirmation to delete
            confirm = input(f"\nDo you want to DELETE these {len(invalid_locations)} locations and their reports? (yes/no): ")
            
            if confirm.lower() == 'yes':
                total_reports_deleted = 0
                for location in invalid_locations:
                    # Count reports for this location
                    reports = Report.query.filter_by(location_id=location.id).all()
                    report_count = len(reports)
                    total_reports_deleted += report_count
                    
                    # Delete reports first (due to foreign key constraints)
                    for report in reports:
                        db.session.delete(report)
                    
                    # Delete the location
                    db.session.delete(location)
                    
                    print(f"Deleted location '{location.name}' (ID: {location.id}) and {report_count} reports")
                
                # Commit all changes
                db.session.commit()
                
                print(f"\nSUCCESS: Deleted {len(invalid_locations)} locations and {total_reports_deleted} reports")
                
                # Verify cleanup
                remaining_invalid = []
                all_locations_after = Location.query.all()
                for location in all_locations_after:
                    if not location.state or location.state.upper() not in VALID_STATE_ABBREVIATIONS:
                        remaining_invalid.append(location)
                
                if remaining_invalid:
                    print(f"WARNING: Still found {len(remaining_invalid)} locations with invalid states!")
                else:
                    print("✅ All remaining locations now have valid 2-letter state codes")
            else:
                print("Operation cancelled - no changes made")
        else:
            print("✅ All locations have valid 2-letter state abbreviations")
            
        # Show current state distribution
        print(f"\nCurrent state distribution:")
        states = {}
        for location in Location.query.all():
            state = location.state or 'None'
            if state in states:
                states[state] += 1
            else:
                states[state] = 1
        
        for state, count in sorted(states.items()):
            print(f"{state}: {count} locations")

if __name__ == "__main__":
    check_invalid_state_names()
