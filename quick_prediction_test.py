#!/usr/bin/env python3
"""
Quick Prediction Validation Script

This script provides a quick way to test prediction accuracy by:
1. Finding pantries with recent empty periods
2. Making predictions from earlier data points
3. Comparing against actual outcomes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import Location, Report
from app.views import calculate_advanced_predictions
from datetime import datetime, timedelta
from sqlalchemy import func

def quick_prediction_test():
    """Run a quick test of prediction accuracy"""
    app = create_app()
    
    with app.app_context():
        print("QUICK PREDICTION ACCURACY TEST")
        print("=" * 50)
        
        # Find pantries with at least 15 reports
        pantries = Location.query.join(Report).group_by(Location.id).having(
            func.count(Report.id) >= 15
        ).limit(5).all()
        
        total_tests = 0
        successful_tests = 0
        errors = []
        
        for pantry in pantries:
            print(f"\nTesting Pantry: {pantry.name}")
            print("-" * 30)
            
            # Get all reports for this pantry
            reports = Report.query.filter_by(location_id=pantry.id).order_by(Report.time).all()
            
            if len(reports) < 15:
                print("  ❌ Insufficient data")
                continue
            
            # Test multiple time points
            for test_point in [0.6, 0.7, 0.8]:  # Use 60%, 70%, 80% of data for training
                split_index = int(len(reports) * test_point)
                historical_reports = reports[:split_index]
                future_reports = reports[split_index:]
                
                if len(historical_reports) < 10 or len(future_reports) < 3:
                    continue
                
                # Create analytics from historical data
                analytics = create_test_analytics(historical_reports)
                
                # Make prediction
                try:
                    predictions = calculate_advanced_predictions(historical_reports, analytics)
                    
                    if not predictions or not predictions.get('days_until_empty'):
                        print(f"  ⚠️  No prediction at {test_point*100:.0f}% point")
                        continue
                    
                    predicted_days = predictions['days_until_empty']
                    confidence = predictions.get('confidence', 0)
                    method = predictions.get('prediction_explanation', 'unknown')
                    
                    # Find actual empty date in future reports
                    prediction_date = historical_reports[-1].time
                    actual_empty_date = None
                    
                    for report in future_reports:
                        if report.pantry_fullness <= 10:  # Consider <=10% as empty
                            actual_empty_date = report.time
                            break
                    
                    total_tests += 1
                    
                    if actual_empty_date:
                        actual_days = (actual_empty_date - prediction_date).days
                        error = abs(predicted_days - actual_days)
                        errors.append(error)
                        successful_tests += 1
                        
                        accuracy = "✅" if error <= 3 else "⚠️" if error <= 7 else "❌"
                        print(f"  {accuracy} Predicted: {predicted_days}d | Actual: {actual_days}d | Error: {error}d | Conf: {confidence:.0f}%")
                    else:
                        print(f"  ❓ Predicted: {predicted_days}d | No empty period found | Conf: {confidence:.0f}%")
                
                except Exception as e:
                    print(f"  ❌ Error making prediction: {e}")
        
        # Calculate overall metrics
        print(f"\n" + "=" * 50)
        print("RESULTS SUMMARY:")
        print(f"Total Tests: {total_tests}")
        print(f"Successful Predictions: {successful_tests}")
        
        if errors:
            import statistics
            mean_error = statistics.mean(errors)
            median_error = statistics.median(errors)
            within_3_days = sum(1 for e in errors if e <= 3)
            within_7_days = sum(1 for e in errors if e <= 7)
            
            print(f"Mean Error: {mean_error:.1f} days")
            print(f"Median Error: {median_error:.1f} days")
            print(f"Within 3 days: {within_3_days}/{successful_tests} ({within_3_days/successful_tests*100:.1f}%)")
            print(f"Within 7 days: {within_7_days}/{successful_tests} ({within_7_days/successful_tests*100:.1f}%)")
            
            print(f"\nAll Errors: {sorted(errors)}")
        else:
            print("No successful predictions to analyze")

def create_test_analytics(reports):
    """Create analytics structure from historical reports"""
    if not reports:
        return {}
    
    fullness_values = [r.pantry_fullness for r in reports]
    
    return {
        'total_reports': len(reports),
        'fullness_stats': {
            'average': sum(fullness_values) / len(fullness_values),
            'minimum': min(fullness_values),
            'maximum': max(fullness_values),
            'current': fullness_values[-1]  # Current fullness is the latest report
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

if __name__ == "__main__":
    quick_prediction_test()
