#!/usr/bin/env python3
"""
Test Data Generation Script

Creates realistic pantry locations and report data for testing the prediction algorithm.
Simulates three different traffic patterns:
1. High traffic: 1 beneficiary per hour (8am-8pm)
2. Medium traffic: 1 beneficiary per 2 hours (8am-8pm)  
3. Low traffic: 1 beneficiary per 5 hours (8am-8pm)

Restocking: Normal distribution, average 5% increase every 2 hours during day
Reports: 1-4 reports per day at random times
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Location, Report, User
import numpy as np
from datetime import datetime, timedelta
import random
import json

class PantryDataGenerator:
    def __init__(self, app):
        self.app = app
        self.start_date = datetime.now() - timedelta(days=14)  # 14 days of history
        self.end_date = datetime.now()
        
    def create_test_user(self):
        """Create a test user for pantry ownership"""
        with self.app.app_context():
            # Check if test user already exists
            test_user = User.query.filter_by(email='test@reportthatpantry.com').first()
            if not test_user:
                test_user = User(
                    email='test@reportthatpantry.com',
                    password='test_password',
                    first_name='Test',
                    last_name='User',
                    user_type='individual'
                )
                db.session.add(test_user)
                db.session.commit()
            return test_user
    
    def create_test_pantries(self):
        """Create three test pantries with different traffic patterns"""
        with self.app.app_context():
            test_user = self.create_test_user()
            test_user_id = test_user.id  # Store the ID to avoid session issues
            
            pantries_data = [
                {
                    'name': 'High Traffic Community Pantry',
                    'address': '123 Main Street',
                    'city': 'Downtown',
                    'state': 'CA',
                    'zip': 90210,
                    'description': 'Busy downtown location with high foot traffic',
                    'traffic_pattern': 'high',  # 1 beneficiary per hour
                    'latitude': 34.0522,
                    'longitude': -118.2437
                },
                {
                    'name': 'Medium Traffic Neighborhood Pantry',
                    'address': '456 Oak Avenue',
                    'city': 'Suburbia',
                    'state': 'CA', 
                    'zip': 90211,
                    'description': 'Suburban neighborhood with moderate usage',
                    'traffic_pattern': 'medium',  # 1 beneficiary per 2 hours
                    'latitude': 34.0622,
                    'longitude': -118.2537
                },
                {
                    'name': 'Low Traffic Rural Pantry',
                    'address': '789 Country Road',
                    'city': 'Countryside',
                    'state': 'CA',
                    'zip': 90212,
                    'description': 'Quiet rural area with occasional visitors',
                    'traffic_pattern': 'low',  # 1 beneficiary per 5 hours
                    'latitude': 34.0722,
                    'longitude': -118.2637
                }
            ]
            
            created_pantries = []
            for pantry_data in pantries_data:
                # Check if pantry already exists
                existing = Location.query.filter_by(name=pantry_data['name']).first()
                if existing:
                    print(f"Pantry '{pantry_data['name']}' already exists, using existing one")
                    created_pantries.append((existing, pantry_data['traffic_pattern']))
                    continue
                
                pantry = Location(
                    name=pantry_data['name'],
                    address=pantry_data['address'],
                    city=pantry_data['city'],
                    state=pantry_data['state'],
                    zip=pantry_data['zip'],
                    description=pantry_data['description'],
                    user_id=test_user_id,  # Use the ID instead of the object
                    latitude=pantry_data['latitude'],
                    longitude=pantry_data['longitude']
                )
                
                db.session.add(pantry)
                db.session.commit()
                
                created_pantries.append((pantry, pantry_data['traffic_pattern']))
                print(f"Created pantry: {pantry.name} (ID: {pantry.id})")
            
            return created_pantries
    
    def simulate_pantry_usage(self, traffic_pattern: str, current_time: datetime) -> float:
        """Simulate pantry usage based on traffic pattern and time of day"""
        hour = current_time.hour
        
        # No activity overnight (10pm - 6am)
        if hour < 6 or hour >= 22:
            return 0
        
        # Peak hours: 7-9am, 12-1pm, 5-7pm
        peak_multiplier = 1.0
        if hour in [7, 8, 12, 17, 18]:
            peak_multiplier = 1.5
        elif hour in [9, 13, 19]:
            peak_multiplier = 1.2
        
        # Base usage rates per hour
        if traffic_pattern == 'high':
            base_usage = 1.0 * peak_multiplier  # 1 person per hour
        elif traffic_pattern == 'medium':
            base_usage = 0.5 * peak_multiplier  # 1 person per 2 hours
        else:  # low traffic
            base_usage = 0.2 * peak_multiplier  # 1 person per 5 hours
        
        # Add some randomness
        usage = np.random.poisson(base_usage)
        
        # Each person takes 5-15% of remaining food
        food_taken_per_person = np.random.uniform(5, 15)
        return min(usage * food_taken_per_person, 30)  # Cap at 30% per hour
    
    def simulate_restocking(self, current_time: datetime, current_fullness: float) -> float:
        """Simulate restocking events"""
        hour = current_time.hour
        
        # Restocking happens roughly every 2 hours during day (8am-6pm)
        # Higher probability if pantry is very low
        if 8 <= hour <= 18 and current_time.minute == 0:
            
            # Probability increases if pantry is low
            if current_fullness < 20:
                restock_prob = 0.8  # 80% chance if very low
            elif current_fullness < 40:
                restock_prob = 0.4  # 40% chance if low
            else:
                restock_prob = 0.1  # 10% chance if not low
            
            if np.random.random() < restock_prob:
                # Normal distribution: average 5% increase, std dev 2%
                restock_amount = max(0, np.random.normal(5, 2))
                return min(restock_amount, 100 - current_fullness)  # Can't exceed 100%
        
        return 0
    
    def generate_reports_for_pantry(self, pantry: Location, traffic_pattern: str):
        """Generate realistic report data for a pantry over 14 days"""
        print(f"Generating 14 days of data for {pantry.name} ({traffic_pattern} traffic)...")
        
        current_time = self.start_date
        current_fullness = 75.0  # Start at 75% full
        
        all_reports = []
        
        # Simulate hour by hour for the entire 14-day period
        while current_time < self.end_date:
            # Apply usage (people taking food)
            usage = self.simulate_pantry_usage(traffic_pattern, current_time)
            current_fullness = max(0, current_fullness - usage)
            
            # Apply restocking
            restock = self.simulate_restocking(current_time, current_fullness)
            current_fullness = min(100, current_fullness + restock)
            
            # Add some natural fluctuation
            current_fullness += np.random.normal(0, 0.5)
            current_fullness = max(0, min(100, current_fullness))
            
            # Generate reports randomly throughout the day (1-4 per day)
            # Check if this is a new day and if we should generate reports
            if current_time.hour in [8, 12, 17, 20]:  # Common reporting times
                if np.random.random() < 0.3:  # 30% chance of report at these times
                    # Add some measurement error to reports (±5%)
                    reported_fullness = current_fullness + np.random.normal(0, 5)
                    reported_fullness = max(0, min(100, round(reported_fullness)))
                    
                    all_reports.append({
                        'time': current_time,
                        'fullness': reported_fullness
                    })
            
            # Move to next hour
            current_time += timedelta(hours=1)
        
        # Ensure we have at least 1-2 reports per day by adding some if needed
        daily_report_counts = {}
        for report in all_reports:
            day_key = report['time'].date()
            daily_report_counts[day_key] = daily_report_counts.get(day_key, 0) + 1
        
        # Add additional reports for days with too few reports
        current_time = self.start_date
        while current_time < self.end_date:
            day_key = current_time.date()
            if daily_report_counts.get(day_key, 0) < 1:
                # Add at least one report for this day
                report_hour = np.random.randint(6, 23)
                report_minute = np.random.randint(0, 60)
                report_time = current_time.replace(hour=report_hour, minute=report_minute)
                
                if report_time < self.end_date:
                    # Estimate fullness at this time (rough approximation)
                    estimated_fullness = 50 + np.random.normal(0, 20)
                    estimated_fullness = max(0, min(100, round(estimated_fullness)))
                    
                    all_reports.append({
                        'time': report_time,
                        'fullness': estimated_fullness
                    })
            
            current_time += timedelta(days=1)
        
        # Sort reports by time and save to database
        all_reports.sort(key=lambda x: x['time'])
        
        with self.app.app_context():
            # Get the pantry and user IDs to avoid session issues
            pantry_id = pantry.id
            user_id = pantry.user_id
            
            for report_data in all_reports:
                report = Report(
                    pantry_fullness=int(report_data['fullness']),
                    time=report_data['time'],
                    location_id=pantry_id,
                    user_id=user_id,
                    description=f"Simulated report - {traffic_pattern} traffic area"
                )
                db.session.add(report)
            
            db.session.commit()
            print(f"Created {len(all_reports)} reports for {pantry.name} over 14 days")
    
    def generate_all_data(self):
        """Generate all test data"""
        print("Starting test data generation...")
        print("=" * 50)
        
        # Create pantries
        pantries = self.create_test_pantries()
        
        # Store pantry IDs to avoid session issues
        pantry_info = []
        for pantry, traffic_pattern in pantries:
            pantry_info.append((pantry.id, pantry.name, traffic_pattern))
        
        # Generate reports for each pantry
        for pantry_id, pantry_name, traffic_pattern in pantry_info:
            with self.app.app_context():
                # Get fresh pantry object in this context
                pantry = Location.query.get(pantry_id)
                
                # Clear existing reports for clean testing
                existing_reports = Report.query.filter_by(location_id=pantry.id).all()
                for report in existing_reports:
                    db.session.delete(report)
                db.session.commit()
            
            # Generate reports
            with self.app.app_context():
                pantry = Location.query.get(pantry_id)
                self.generate_reports_for_pantry(pantry, traffic_pattern)
        
        print("\n" + "=" * 50)
        print("Test data generation completed!")
        
        # Print summary
        with self.app.app_context():
            for pantry_id, pantry_name, traffic_pattern in pantry_info:
                report_count = Report.query.filter_by(location_id=pantry_id).count()
                latest_report = Report.query.filter_by(location_id=pantry_id).order_by(Report.time.desc()).first()
                latest_fullness = latest_report.pantry_fullness if latest_report else "N/A"
                print(f"{pantry_name}: {report_count} reports, latest: {latest_fullness}% full")
    
    def create_summary_report(self):
        """Create a summary report of generated data"""
        with self.app.app_context():
            pantries = Location.query.filter(Location.name.like('%Traffic%')).all()
            
            summary = {
                'generation_date': datetime.now().isoformat(),
                'date_range': {
                    'start': self.start_date.isoformat(),
                    'end': self.end_date.isoformat(),
                    'days': (self.end_date - self.start_date).days
                },
                'pantries': []
            }
            
            for pantry in pantries:
                reports = Report.query.filter_by(location_id=pantry.id).order_by(Report.time).all()
                
                if reports:
                    fullness_values = [r.pantry_fullness for r in reports]
                    
                    pantry_data = {
                        'id': pantry.id,
                        'name': pantry.name,
                        'total_reports': len(reports),
                        'avg_fullness': np.mean(fullness_values),
                        'min_fullness': min(fullness_values),
                        'max_fullness': max(fullness_values),
                        'empty_periods': sum(1 for f in fullness_values if f <= 10),
                        'full_periods': sum(1 for f in fullness_values if f >= 90),
                        'reports_per_day': len(reports) / (self.end_date - self.start_date).days
                    }
                    
                    summary['pantries'].append(pantry_data)
            
            # Save summary
            with open('test_data_summary.json', 'w') as f:
                json.dump(summary, f, indent=2)
            
            print("Test data summary saved to 'test_data_summary.json'")
            return summary

def main():
    """Main function to generate test data"""
    app = create_app()
    
    generator = PantryDataGenerator(app)
    
    # Generate all test data
    generator.generate_all_data()
    
    # Create summary report
    summary = generator.create_summary_report()
    
    print("\nGenerated Test Data Summary:")
    print("=" * 40)
    for pantry_data in summary['pantries']:
        print(f"\n{pantry_data['name']}:")
        print(f"  - Reports: {pantry_data['total_reports']}")
        print(f"  - Avg Fullness: {pantry_data['avg_fullness']:.1f}%")
        print(f"  - Empty Periods: {pantry_data['empty_periods']}")
        print(f"  - Reports/Day: {pantry_data['reports_per_day']:.1f}")

if __name__ == "__main__":
    main()
