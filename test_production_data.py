#!/usr/bin/env python3
"""
Production Data Prediction Testing Script

This script tests the prediction algorithm on real data from your production website.
It can work with data exported from your live database or API.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import Location, Report
from app.views import calculate_advanced_predictions
from datetime import datetime, timedelta
import numpy as np
import json
from typing import List, Dict, Optional

def create_analytics_from_reports(reports):
    """Create analytics data structure from reports"""
    if not reports:
        return {}
    
    fullness_values = [r.pantry_fullness for r in reports]
    
    return {
        'total_reports': len(reports),
        'fullness_stats': {
            'average': sum(fullness_values) / len(fullness_values),
            'minimum': min(fullness_values),
            'maximum': max(fullness_values),
            'current': fullness_values[-1]
        },
        'trends': {
            'recent_average': sum(fullness_values[-5:]) / min(5, len(fullness_values)),
            'direction': 'stable'
        },
        'date_range': {
            'start': reports[0].time,
            'end': reports[-1].time,
            'days': (reports[-1].time - reports[0].time).days
        },
        'chart_data': {
            'data_points': [
                {
                    'timestamp': r.time.isoformat(),
                    'fullness': r.pantry_fullness
                } for r in reports
            ]
        }
    }

def test_production_pantries_from_db():
    """Test prediction algorithm on production data from your database"""
    app = create_app()
    
    with app.app_context():
        print("PRODUCTION DATA PREDICTION ACCURACY TEST")
        print("="*60)
        print("Testing on pantries with the most reports from your live database")
        print("="*60)
        
        # Get top 10 pantries with most reports
        from sqlalchemy import func
        
        top_pantries = Location.query.join(Report)\
            .group_by(Location.id)\
            .order_by(func.count(Report.id).desc())\
            .limit(10)\
            .all()
        
        if not top_pantries:
            print("❌ No pantries found in database")
            return
        
        print(f"Found {len(top_pantries)} pantries to test")
        
        all_results = []
        
        for i, pantry in enumerate(top_pantries, 1):
            reports = Report.query.filter_by(location_id=pantry.id)\
                .order_by(Report.time).all()
            
            print(f"\n{i:2d}. 🏪 {pantry.name}")
            print(f"     📍 {pantry.city}, {pantry.state}")
            print(f"     📊 {len(reports)} reports")
            
            if len(reports) < 15:
                print("     ⚠️  Insufficient data for testing (need 15+ reports)")
                continue
            
            # Calculate time span
            time_span = (reports[-1].time - reports[0].time).days
            print(f"     📅 {time_span} days of data")
            
            if time_span < 7:
                print("     ⚠️  Insufficient time span for testing (need 7+ days)")
                continue
            
            # Test at different historical points
            test_points = [0.6, 0.7, 0.8]  # Use 60%, 70%, 80% of data
            pantry_results = []
            
            for j, test_point in enumerate(test_points):
                split_index = int(len(reports) * test_point)
                if split_index < 10 or split_index >= len(reports) - 2:
                    continue
                
                historical_reports = reports[:split_index]
                future_reports = reports[split_index:]
                
                # Create analytics
                analytics = create_analytics_from_reports(historical_reports)
                
                try:
                    # Make prediction
                    predictions = calculate_advanced_predictions(historical_reports, analytics)
                    
                    if not predictions or not predictions.get('days_until_empty'):
                        continue
                    
                    predicted_days = predictions['days_until_empty']
                    confidence = predictions.get('confidence', 0)
                    
                    # Find actual empty date in future reports
                    prediction_date = historical_reports[-1].time
                    actual_empty_date = None
                    
                    for report in future_reports:
                        if report.pantry_fullness <= 10:  # Consider <=10% as empty
                            actual_empty_date = report.time
                            break
                    
                    if actual_empty_date:
                        actual_days = (actual_empty_date - prediction_date).days
                        error = abs(predicted_days - actual_days)
                        
                        accuracy = "✅" if error <= 2 else "⚠️" if error <= 5 else "❌"
                        print(f"     {accuracy} Test {j+1}: Pred {predicted_days:.1f}d | Act {actual_days}d | Err {error:.1f}d | Conf {confidence:.0f}%")
                        
                        pantry_results.append({
                            'pantry_name': pantry.name,
                            'predicted': predicted_days,
                            'actual': actual_days,
                            'error': error,
                            'confidence': confidence
                        })
                    else:
                        print(f"     ❓ Test {j+1}: Pred {predicted_days:.1f}d | No empty period found")
                        
                except Exception as e:
                    print(f"     ❌ Test {j+1}: Error - {str(e)[:50]}...")
            
            if pantry_results:
                avg_error = np.mean([r['error'] for r in pantry_results])
                within_2_days = sum(1 for r in pantry_results if r['error'] <= 2)
                print(f"     📊 Summary: {len(pantry_results)} tests | Avg Error: {avg_error:.1f}d | Within 2d: {within_2_days}/{len(pantry_results)}")
                all_results.extend(pantry_results)
            else:
                print("     ❌ No successful predictions")
        
        # Overall summary
        if all_results:
            print(f"\n{'='*60}")
            print("PRODUCTION DATA RESULTS:")
            total_tests = len(all_results)
            mean_error = np.mean([r['error'] for r in all_results])
            median_error = np.median([r['error'] for r in all_results])
            
            within_1_day = sum(1 for r in all_results if r['error'] <= 1)
            within_2_days = sum(1 for r in all_results if r['error'] <= 2)
            within_5_days = sum(1 for r in all_results if r['error'] <= 5)
            
            print(f"Total Tests: {total_tests}")
            print(f"Mean Error: {mean_error:.2f} days")
            print(f"Median Error: {median_error:.2f} days")
            print(f"Within 1 day: {within_1_day}/{total_tests} ({within_1_day/total_tests*100:.1f}%)")
            print(f"Within 2 days: {within_2_days}/{total_tests} ({within_2_days/total_tests*100:.1f}%)")
            print(f"Within 5 days: {within_5_days}/{total_tests} ({within_5_days/total_tests*100:.1f}%)")
            
            # Save results
            with open('production_test_results.json', 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'total_tests': total_tests,
                    'mean_error': mean_error,
                    'median_error': median_error,
                    'accuracy_metrics': {
                        'within_1_day': within_1_day,
                        'within_2_days': within_2_days,
                        'within_5_days': within_5_days
                    },
                    'results': all_results
                }, f, indent=2)
            
            print(f"\n💾 Results saved to 'production_test_results.json'")
            
            # Performance assessment
            if mean_error <= 1.5:
                print("🟢 EXCELLENT: Algorithm performs excellently on production data!")
            elif mean_error <= 3.0:
                print("🟡 GOOD: Algorithm shows good accuracy on production data")
            elif mean_error <= 5.0:
                print("🟠 FAIR: Algorithm shows fair accuracy, could use improvement")
            else:
                print("🔴 POOR: Algorithm needs significant improvement for production data")
                
        else:
            print("\n❌ No successful tests completed on production data")

def import_production_data_from_json(json_file_path: str):
    """Import and test production data from a JSON export"""
    print("TESTING PRODUCTION DATA FROM JSON EXPORT")
    print("="*60)
    
    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        print(f"📁 Loaded data from {json_file_path}")
        
        # Expected JSON format:
        # {
        #   "pantries": [
        #     {
        #       "id": 1,
        #       "name": "Pantry Name",
        #       "city": "City",
        #       "state": "State",
        #       "reports": [
        #         {
        #           "time": "2025-06-15T10:30:00Z",
        #           "pantry_fullness": 75
        #         }
        #       ]
        #     }
        #   ]
        # }
        
        pantries = data.get('pantries', [])
        
        # Handle your specific production data format
        if not pantries and 'values' in data and 'fields' in data:
            print("🔄 Converting from ReportThatPantry.org export format...")
            
            fields = data['fields']
            values = data['values']
            
            # Group data by pantry
            pantries_dict = {}
            
            for record in values:
                if len(record) != len(fields):
                    continue
                    
                row_data = dict(zip(fields, record))
                
                pantry_id = row_data.get('pantry_id')
                pantry_name = row_data.get('pantry_name')
                city = row_data.get('city', '')
                state = row_data.get('state', '')
                report_time_str = row_data.get('report_time')
                pantry_fullness = row_data.get('pantry_fullness')
                
                if not all([pantry_id, pantry_name, report_time_str, pantry_fullness is not None]):
                    continue
                
                # Parse timestamp
                try:
                    report_time = datetime.fromisoformat(report_time_str.replace('+00', '+00:00'))
                except:
                    continue
                
                # Group by pantry
                pantry_key = f"{pantry_id}_{pantry_name}"
                if pantry_key not in pantries_dict:
                    pantries_dict[pantry_key] = {
                        'id': pantry_id,
                        'name': pantry_name,
                        'city': city,
                        'state': state,
                        'reports': []
                    }
                
                pantries_dict[pantry_key]['reports'].append({
                    'time': report_time.isoformat(),
                    'pantry_fullness': int(pantry_fullness)
                })
            
            # Convert to list format and sort reports
            pantries = []
            for pantry_data in pantries_dict.values():
                pantry_data['reports'].sort(key=lambda x: x['time'])
                pantries.append(pantry_data)
        
        print(f"Found {len(pantries)} pantries in export")
        
        all_results = []
        
        # Test each pantry
        for pantry_data in pantries:
            name = pantry_data.get('name', 'Unknown')
            reports_data = pantry_data.get('reports', [])
            
            print(f"\n🏪 {name}")
            print(f"   📊 {len(reports_data)} reports")
            
            if len(reports_data) < 15:
                print("   ⚠️  Insufficient data for testing")
                continue
            
            # Convert to report-like objects
            class MockReport:
                def __init__(self, time_str, fullness):
                    self.time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                    self.pantry_fullness = fullness
            
            reports = [MockReport(r['time'], r['pantry_fullness']) for r in reports_data]
            reports.sort(key=lambda x: x.time)
            
            # Calculate time span
            time_span = (reports[-1].time - reports[0].time).days
            print(f"   📅 {time_span} days of data")
            
            if time_span < 7:
                print("   ⚠️  Insufficient time span for testing (need 7+ days)")
                continue
            
            # Test at different historical points
            test_points = [0.6, 0.7, 0.8]  # Use 60%, 70%, 80% of data
            pantry_results = []
            
            for j, test_point in enumerate(test_points):
                split_index = int(len(reports) * test_point)
                if split_index < 10 or split_index >= len(reports) - 2:
                    continue
                
                historical_reports = reports[:split_index]
                future_reports = reports[split_index:]
                
                # Create analytics
                analytics = create_analytics_from_reports(historical_reports)
                
                try:
                    # Make prediction
                    predictions = calculate_advanced_predictions(historical_reports, analytics)
                    
                    if not predictions or not predictions.get('days_until_empty'):
                        continue
                    
                    predicted_days = predictions['days_until_empty']
                    confidence = predictions.get('confidence', 0)
                    
                    # Find actual empty date in future reports
                    prediction_date = historical_reports[-1].time
                    actual_empty_date = None
                    
                    for report in future_reports:
                        if report.pantry_fullness <= 10:  # Consider <=10% as empty
                            actual_empty_date = report.time
                            break
                    
                    if actual_empty_date:
                        actual_days = (actual_empty_date - prediction_date).days
                        error = abs(predicted_days - actual_days)
                        
                        accuracy = "✅" if error <= 2 else "⚠️" if error <= 5 else "❌"
                        print(f"   {accuracy} Test {j+1}: Pred {predicted_days:.1f}d | Act {actual_days}d | Err {error:.1f}d | Conf {confidence:.0f}%")
                        
                        pantry_results.append({
                            'pantry_name': name,
                            'predicted': predicted_days,
                            'actual': actual_days,
                            'error': error,
                            'confidence': confidence
                        })
                    else:
                        print(f"   ❓ Test {j+1}: Pred {predicted_days:.1f}d | No empty period found")
                        
                except Exception as e:
                    print(f"   ❌ Test {j+1}: Error - {str(e)[:50]}...")
            
            if pantry_results:
                avg_error = np.mean([r['error'] for r in pantry_results])
                within_2_days = sum(1 for r in pantry_results if r['error'] <= 2)
                print(f"   📊 Summary: {len(pantry_results)} tests | Avg Error: {avg_error:.1f}d | Within 2d: {within_2_days}/{len(pantry_results)}")
                all_results.extend(pantry_results)
            else:
                print("   ❌ No successful predictions")
        
        # Overall summary for JSON data testing
        if all_results:
            print(f"\n{'='*60}")
            print("PRODUCTION JSON DATA RESULTS:")
            total_tests = len(all_results)
            mean_error = np.mean([r['error'] for r in all_results])
            median_error = np.median([r['error'] for r in all_results])
            
            within_1_day = sum(1 for r in all_results if r['error'] <= 1)
            within_2_days = sum(1 for r in all_results if r['error'] <= 2)
            within_5_days = sum(1 for r in all_results if r['error'] <= 5)
            
            print(f"Total Tests: {total_tests}")
            print(f"Mean Error: {mean_error:.2f} days")
            print(f"Median Error: {median_error:.2f} days")
            print(f"Within 1 day: {within_1_day}/{total_tests} ({within_1_day/total_tests*100:.1f}%)")
            print(f"Within 2 days: {within_2_days}/{total_tests} ({within_2_days/total_tests*100:.1f}%)")
            print(f"Within 5 days: {within_5_days}/{total_tests} ({within_5_days/total_tests*100:.1f}%)")
            
            # Save results
            with open('production_test_results.json', 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'source': 'json_export',
                    'total_tests': total_tests,
                    'mean_error': mean_error,
                    'median_error': median_error,
                    'accuracy_metrics': {
                        'within_1_day': within_1_day,
                        'within_2_days': within_2_days,
                        'within_5_days': within_5_days
                    },
                    'results': all_results
                }, f, indent=2)
            
            print(f"\n💾 Results saved to 'production_test_results.json'")
            
            # Performance assessment
            if mean_error <= 1.5:
                print("🟢 EXCELLENT: Algorithm performs excellently on your production data!")
            elif mean_error <= 3.0:
                print("🟡 GOOD: Algorithm shows good accuracy on your production data")
            elif mean_error <= 5.0:
                print("🟠 FAIR: Algorithm shows fair accuracy, could use improvement")
            else:
                print("🔴 POOR: Algorithm needs significant improvement for your production data")
        else:
            print(f"\n{'='*60}")
            print("PRODUCTION JSON DATA TESTING COMPLETED")
            print("❌ No successful prediction tests completed")
            print("This could be due to:")
            print("  - Insufficient data per pantry (need 15+ reports)")
            print("  - Insufficient time span (need 7+ days)")
            print("  - No empty periods in the test data")
            print("  - Algorithm unable to generate predictions")
            
    except FileNotFoundError:
        print(f"❌ File {json_file_path} not found")
        print("Please export your production data to JSON format")
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON format in {json_file_path}")

def generate_production_data_export_instructions():
    """Generate instructions for exporting production data"""
    instructions = """
    INSTRUCTIONS FOR TESTING WITH PRODUCTION DATA
    =============================================
    
    Option 1: Test with Current Database
    -----------------------------------
    If this script is running against your production database:
    
    python test_production_data.py --database
    
    Option 2: Export Data from Production and Import
    -----------------------------------------------
    1. Export data from your production database using this SQL:
    
    SELECT 
        l.id as pantry_id,
        l.name as pantry_name,
        l.city,
        l.state,
        r.time as report_time,
        r.pantry_fullness
    FROM locations l
    INNER JOIN reports r ON l.id = r.location_id
    WHERE l.id IN (
        SELECT location_id 
        FROM reports 
        GROUP BY location_id 
        ORDER BY COUNT(*) DESC 
        LIMIT 10
    )
    ORDER BY l.id, r.time;
    
    2. Convert to JSON format and save as 'production_data.json'
    
    3. Run: python test_production_data.py --json production_data.json
    
    Option 3: API Export (if you have an API endpoint)
    -------------------------------------------------
    Create an API endpoint that returns pantry data in JSON format
    and modify this script to fetch from your API.
    
    JSON Format Expected:
    {
      "pantries": [
        {
          "id": 1,
          "name": "Pantry Name",
          "city": "City Name",
          "state": "State",
          "reports": [
            {
              "time": "2025-06-15T10:30:00Z",
              "pantry_fullness": 75
            }
          ]
        }
      ]
    }
    """
    print(instructions)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test prediction algorithm on production data')
    parser.add_argument('--database', action='store_true', help='Test using current database')
    parser.add_argument('--json', type=str, help='Test using JSON export file')
    parser.add_argument('--instructions', action='store_true', help='Show export instructions')
    
    args = parser.parse_args()
    
    if args.instructions:
        generate_production_data_export_instructions()
    elif args.database:
        test_production_pantries_from_db()
    elif args.json:
        import_production_data_from_json(args.json)
    else:
        print("Please specify --database, --json <file>, or --instructions")
        print("Use --help for more information")
