#!/usr/bin/env python3
"""
Test Data Prediction Accuracy Script

This script tests the prediction algorithm specifically on the generated test data
with known traffic patterns and realistic behavior.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import Location, Report
from app.views import calculate_advanced_predictions
import numpy as np
from datetime import datetime, timedelta
import json
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

@dataclass
class TestResult:
    pantry_name: str
    traffic_pattern: str
    prediction_date: datetime
    predicted_days: int
    actual_days: Optional[int]
    confidence: float
    error: Optional[float]
    success: bool

class TestDataPredictionTester:
    def __init__(self, app):
        self.app = app
        self.results: List[TestResult] = []
    
    def get_test_pantries(self) -> List[Tuple[Location, str]]:
        """Get the test pantries we created"""
        with self.app.app_context():
            pantries = []
            
            # High traffic pantry
            high_traffic = Location.query.filter_by(name='High Traffic Community Pantry').first()
            if high_traffic:
                pantries.append((high_traffic, 'high'))
            
            # Medium traffic pantry  
            medium_traffic = Location.query.filter_by(name='Medium Traffic Neighborhood Pantry').first()
            if medium_traffic:
                pantries.append((medium_traffic, 'medium'))
            
            # Low traffic pantry
            low_traffic = Location.query.filter_by(name='Low Traffic Rural Pantry').first()
            if low_traffic:
                pantries.append((low_traffic, 'low'))
            
            return pantries
    
    def create_analytics_from_reports(self, reports: List[Report]) -> Dict:
        """Create analytics data structure from reports for prediction algorithm"""
        if not reports:
            return {}
        
        fullness_values = [r.pantry_fullness for r in reports]
        
        analytics = {
            'total_reports': len(reports),
            'fullness_stats': {
                'average': np.mean(fullness_values),
                'minimum': min(fullness_values),
                'maximum': max(fullness_values)
            },
            'trends': {
                'recent_average': np.mean(fullness_values[-5:]) if len(fullness_values) >= 5 else np.mean(fullness_values),
                'direction': 'stable',
                'change_from_previous': 0
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
        
        return analytics
    
    def find_next_empty_period(self, pantry_id: int, after_date: datetime, max_days: int = 14) -> Optional[datetime]:
        """Find when the pantry next becomes empty (≤10%) after the given date"""
        with self.app.app_context():
            reports = Report.query.filter(
                Report.location_id == pantry_id,
                Report.time > after_date,
                Report.time <= after_date + timedelta(days=max_days)
            ).order_by(Report.time).all()
            
            for report in reports:
                if report.pantry_fullness <= 10:
                    return report.time
            
            return None
    
    def test_pantry_predictions(self, pantry: Location, traffic_pattern: str) -> List[TestResult]:
        """Test predictions for a specific pantry"""
        with self.app.app_context():
            print(f"\nTesting {pantry.name} ({traffic_pattern} traffic)")
            print("-" * 50)
            
            # Get all reports for this pantry
            reports = Report.query.filter_by(location_id=pantry.id).order_by(Report.time).all()
            
            if len(reports) < 20:
                print(f"Insufficient data: only {len(reports)} reports")
                return []
            
            results = []
            total_reports = len(reports)
            
            # Test predictions at different points in time
            # Use 70%, 80%, 90% of data for training
            test_points = [0.7, 0.8, 0.9]
            
            for test_point in test_points:
                split_index = int(total_reports * test_point)
                
                if split_index < 10 or split_index >= total_reports - 5:
                    continue
                
                # Use data up to split point for prediction
                training_reports = reports[:split_index]
                prediction_date = training_reports[-1].time
                
                # Create analytics data
                analytics = self.create_analytics_from_reports(training_reports)
                
                try:
                    # Make prediction
                    prediction = calculate_advanced_predictions(analytics)
                    
                    if not prediction or not prediction.get('days_until_empty'):
                        print(f"  No prediction available for {prediction_date.date()}")
                        continue
                    
                    predicted_days = prediction['days_until_empty']
                    confidence = prediction.get('confidence', 0)
                    
                    # Find actual empty date
                    actual_empty_date = self.find_next_empty_period(pantry.id, prediction_date)
                    
                    if actual_empty_date:
                        actual_days = (actual_empty_date - prediction_date).days
                        error = abs(predicted_days - actual_days)
                        success = error <= 3  # Consider success if within 3 days
                        
                        print(f"  {prediction_date.date()}: Predicted {predicted_days} days, Actual {actual_days} days, Error: {error:.1f} days, Confidence: {confidence:.0f}%")
                    else:
                        actual_days = None
                        error = None
                        success = False
                        print(f"  {prediction_date.date()}: Predicted {predicted_days} days, No empty period found, Confidence: {confidence:.0f}%")
                    
                    result = TestResult(
                        pantry_name=pantry.name,
                        traffic_pattern=traffic_pattern,
                        prediction_date=prediction_date,
                        predicted_days=predicted_days,
                        actual_days=actual_days,
                        confidence=confidence,
                        error=error,
                        success=success
                    )
                    
                    results.append(result)
                    
                except Exception as e:
                    print(f"  Error making prediction for {prediction_date.date()}: {e}")
                    continue
            
            return results
    
    def run_all_tests(self):
        """Run tests on all test pantries"""
        print("Testing Prediction Algorithm on Generated Test Data")
        print("=" * 60)
        
        pantries = self.get_test_pantries()
        
        if not pantries:
            print("No test pantries found! Please run generate_test_data.py first.")
            return
        
        all_results = []
        
        for pantry, traffic_pattern in pantries:
            pantry_results = self.test_pantry_predictions(pantry, traffic_pattern)
            all_results.extend(pantry_results)
            self.results.extend(pantry_results)
        
        self.analyze_results()
        self.save_results()
    
    def analyze_results(self):
        """Analyze and display results"""
        if not self.results:
            print("No results to analyze")
            return
        
        print(f"\n{'='*60}")
        print("PREDICTION ACCURACY ANALYSIS")
        print("=" * 60)
        
        # Overall statistics
        successful_tests = [r for r in self.results if r.error is not None]
        
        if successful_tests:
            errors = [r.error for r in successful_tests]
            successes = [r for r in successful_tests if r.success]
            
            print(f"\nOVERALL STATISTICS:")
            print(f"Total Tests: {len(self.results)}")
            print(f"Tests with Results: {len(successful_tests)}")
            print(f"Success Rate (±3 days): {len(successes)}/{len(successful_tests)} ({len(successes)/len(successful_tests)*100:.1f}%)")
            print(f"Mean Absolute Error: {np.mean(errors):.2f} days")
            print(f"Median Absolute Error: {np.median(errors):.2f} days")
            print(f"Min Error: {min(errors):.1f} days")
            print(f"Max Error: {max(errors):.1f} days")
        
        # Results by traffic pattern
        traffic_patterns = ['high', 'medium', 'low']
        
        print(f"\nRESULTS BY TRAFFIC PATTERN:")
        for pattern in traffic_patterns:
            pattern_results = [r for r in successful_tests if r.traffic_pattern == pattern]
            if pattern_results:
                pattern_errors = [r.error for r in pattern_results]
                pattern_successes = [r for r in pattern_results if r.success]
                
                print(f"\n{pattern.upper()} TRAFFIC:")
                print(f"  Tests: {len(pattern_results)}")
                print(f"  Success Rate: {len(pattern_successes)}/{len(pattern_results)} ({len(pattern_successes)/len(pattern_results)*100:.1f}%)")
                print(f"  Mean Error: {np.mean(pattern_errors):.2f} days")
                print(f"  Avg Confidence: {np.mean([r.confidence for r in pattern_results]):.1f}%")
        
        # Confidence analysis
        print(f"\nCONFIDENCE ANALYSIS:")
        confidence_ranges = [(0, 50), (50, 70), (70, 85), (85, 100)]
        
        for low, high in confidence_ranges:
            range_results = [r for r in successful_tests if low <= r.confidence < high]
            if range_results:
                range_successes = [r for r in range_results if r.success]
                range_errors = [r.error for r in range_results]
                
                print(f"  {low}-{high}% Confidence: {len(range_results)} tests, "
                      f"{len(range_successes)}/{len(range_results)} success "
                      f"({len(range_successes)/len(range_results)*100:.1f}%), "
                      f"Avg Error: {np.mean(range_errors):.2f} days")
    
    def save_results(self):
        """Save results to JSON file"""
        results_data = {
            'test_timestamp': datetime.now().isoformat(),
            'test_type': 'generated_test_data',
            'summary': {
                'total_tests': len(self.results),
                'successful_tests': len([r for r in self.results if r.error is not None]),
                'overall_success_rate': len([r for r in self.results if r.success]) / max(len(self.results), 1) * 100
            },
            'detailed_results': [
                {
                    'pantry_name': r.pantry_name,
                    'traffic_pattern': r.traffic_pattern,
                    'prediction_date': r.prediction_date.isoformat(),
                    'predicted_days': r.predicted_days,
                    'actual_days': r.actual_days,
                    'confidence': r.confidence,
                    'error': r.error,
                    'success': r.success
                }
                for r in self.results
            ]
        }
        
        with open('test_data_prediction_results.json', 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\nResults saved to 'test_data_prediction_results.json'")

def main():
    """Main function"""
    app = create_app()
    
    tester = TestDataPredictionTester(app)
    tester.run_all_tests()

if __name__ == "__main__":
    main()
