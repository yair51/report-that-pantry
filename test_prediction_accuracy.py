#!/usr/bin/env python3
"""
Prediction Algorithm Accuracy Testing Script

This script tests the accuracy of the pantry prediction algorithm by:
1. Selecting pantries with sufficient historical data
2. Using historical data to make predictions
3. Comparing predictions against actual outcomes
4. Calculating accuracy metrics and generating reports
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
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import func

@dataclass
class PredictionTest:
    """Represents a single prediction test"""
    pantry_id: int
    pantry_name: str
    prediction_date: datetime
    predicted_days_until_empty: int
    predicted_confidence: float
    actual_days_until_empty: Optional[int]
    prediction_method: str
    accuracy_error: Optional[float]  # Absolute error in days
    relative_error: Optional[float]  # Relative error as percentage

@dataclass
class TestResults:
    """Contains overall test results and metrics"""
    total_tests: int
    successful_predictions: int
    mean_absolute_error: float
    median_absolute_error: float
    mean_relative_error: float
    accuracy_within_1_day: int
    accuracy_within_3_days: int
    accuracy_within_7_days: int
    best_performing_method: str
    worst_performing_method: str

class PredictionAccuracyTester:
    def __init__(self, app):
        self.app = app
        self.test_results: List[PredictionTest] = []
        
    def select_test_pantries(self, min_reports: int = 10, min_days_history: int = 30) -> List[Location]:
        """Select pantries suitable for testing (with sufficient data)"""
        with self.app.app_context():
            # Get pantries with sufficient reports and time span
            pantries = Location.query.join(Report).group_by(Location.id).having(
                func.count(Report.id) >= min_reports
            ).all()
            
            suitable_pantries = []
            for pantry in pantries:
                reports = Report.query.filter_by(location_id=pantry.id).order_by(Report.time).all()
                if len(reports) >= min_reports:
                    time_span = (reports[-1].time - reports[0].time).days
                    if time_span >= min_days_history:
                        suitable_pantries.append(pantry)
            
            print(f"Found {len(suitable_pantries)} pantries suitable for testing")
            return suitable_pantries[:10]  # Limit to top 10 for testing
    
    def create_historical_snapshots(self, pantry: Location, test_points: int = 5) -> List[Tuple[datetime, List[Report]]]:
        """Create historical snapshots for backtesting"""
        reports = Report.query.filter_by(location_id=pantry.id).order_by(Report.time).all()
        
        if len(reports) < 10:  # Need minimum data for meaningful tests
            return []
        
        snapshots = []
        total_reports = len(reports)
        
        # Create snapshots at different points in history
        for i in range(test_points):
            # Use 70-90% of data for training, reserve rest for validation
            split_point = int(total_reports * (0.7 + i * 0.04))
            if split_point < 5 or split_point >= total_reports - 2:
                continue
                
            snapshot_date = reports[split_point].time
            historical_data = reports[:split_point]
            snapshots.append((snapshot_date, historical_data))
        
        return snapshots
    
    def find_actual_empty_date(self, pantry: Location, after_date: datetime, window_days: int = 30) -> Optional[datetime]:
        """Find the next time the pantry actually became empty after the prediction date"""
        reports = Report.query.filter(
            Report.location_id == pantry.id,
            Report.time > after_date,
            Report.time <= after_date + timedelta(days=window_days)
        ).order_by(Report.time).all()
        
        for report in reports:
            if report.pantry_fullness <= 10:  # Consider <=10% as "empty"
                return report.time
        
        return None
    
    def test_pantry_predictions(self, pantry: Location) -> List[PredictionTest]:
        """Test predictions for a single pantry"""
        tests = []
        snapshots = self.create_historical_snapshots(pantry)
        
        print(f"Testing pantry: {pantry.name} with {len(snapshots)} snapshots")
        
        for snapshot_date, historical_reports in snapshots:
            try:
                # Create a temporary analytics object with historical data
                analytics_data = self.create_analytics_from_reports(historical_reports)
                
                # Make prediction using historical data
                predictions = calculate_advanced_predictions(historical_reports, analytics_data)
                
                if not predictions or not predictions.get('days_until_empty'):
                    continue
                
                predicted_days = predictions['days_until_empty']
                confidence = predictions.get('confidence', 0)
                method = predictions.get('prediction_explanation', 'unknown')
                
                # Find actual empty date
                actual_empty_date = self.find_actual_empty_date(pantry, snapshot_date)
                
                if actual_empty_date:
                    actual_days = (actual_empty_date - snapshot_date).days
                    error = abs(predicted_days - actual_days)
                    relative_error = (error / max(actual_days, 1)) * 100
                else:
                    actual_days = None
                    error = None
                    relative_error = None
                
                test = PredictionTest(
                    pantry_id=pantry.id,
                    pantry_name=pantry.name,
                    prediction_date=snapshot_date,
                    predicted_days_until_empty=predicted_days,
                    predicted_confidence=confidence,
                    actual_days_until_empty=actual_days,
                    prediction_method=method,
                    accuracy_error=error,
                    relative_error=relative_error
                )
                
                tests.append(test)
                
            except Exception as e:
                print(f"Error testing snapshot for {pantry.name}: {e}")
                continue
        
        return tests
    
    def create_analytics_from_reports(self, reports: List[Report]) -> Dict:
        """Create analytics data structure from historical reports"""
        if not reports:
            return {}
        
        # Calculate basic stats
        fullness_values = [r.pantry_fullness for r in reports]
        
        analytics = {
            'total_reports': len(reports),
            'fullness_stats': {
                'average': np.mean(fullness_values),
                'minimum': min(fullness_values),
                'maximum': max(fullness_values),
                'current': fullness_values[-1]  # Current fullness is the latest report
            },
            'trends': {
                'recent_average': np.mean(fullness_values[-5:]) if len(fullness_values) >= 5 else np.mean(fullness_values),
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
        
        return analytics
    
    def run_all_tests(self) -> TestResults:
        """Run tests on all suitable pantries"""
        print("Starting prediction accuracy testing...")
        
        pantries = self.select_test_pantries()
        all_tests = []
        
        for pantry in pantries:
            pantry_tests = self.test_pantry_predictions(pantry)
            all_tests.extend(pantry_tests)
            self.test_results.extend(pantry_tests)
        
        return self.calculate_metrics(all_tests)
    
    def calculate_metrics(self, tests: List[PredictionTest]) -> TestResults:
        """Calculate accuracy metrics from test results"""
        successful_tests = [t for t in tests if t.accuracy_error is not None]
        
        if not successful_tests:
            print("No successful tests found!")
            return TestResults(0, 0, 0, 0, 0, 0, 0, 0, "none", "none")
        
        errors = [t.accuracy_error for t in successful_tests]
        relative_errors = [t.relative_error for t in successful_tests if t.relative_error is not None]
        
        # Count accuracy within different thresholds
        within_1_day = sum(1 for e in errors if e <= 1)
        within_3_days = sum(1 for e in errors if e <= 3)
        within_7_days = sum(1 for e in errors if e <= 7)
        
        # Find best/worst performing methods
        method_errors = {}
        for test in successful_tests:
            method = test.prediction_method
            if method not in method_errors:
                method_errors[method] = []
            method_errors[method].append(test.accuracy_error)
        
        method_avg_errors = {method: np.mean(errors) for method, errors in method_errors.items()}
        best_method = min(method_avg_errors.keys(), key=lambda k: method_avg_errors[k]) if method_avg_errors else "none"
        worst_method = max(method_avg_errors.keys(), key=lambda k: method_avg_errors[k]) if method_avg_errors else "none"
        
        return TestResults(
            total_tests=len(tests),
            successful_predictions=len(successful_tests),
            mean_absolute_error=np.mean(errors),
            median_absolute_error=np.median(errors),
            mean_relative_error=np.mean(relative_errors) if relative_errors else 0,
            accuracy_within_1_day=within_1_day,
            accuracy_within_3_days=within_3_days,
            accuracy_within_7_days=within_7_days,
            best_performing_method=best_method,
            worst_performing_method=worst_method
        )
    
    def generate_report(self, results: TestResults) -> str:
        """Generate a detailed accuracy report"""
        report = f"""
PANTRY PREDICTION ALGORITHM ACCURACY REPORT
==========================================

OVERALL METRICS:
- Total Tests Conducted: {results.total_tests}
- Successful Predictions: {results.successful_predictions}
- Success Rate: {(results.successful_predictions / max(results.total_tests, 1)) * 100:.1f}%

ACCURACY METRICS:
- Mean Absolute Error: {results.mean_absolute_error:.2f} days
- Median Absolute Error: {results.median_absolute_error:.2f} days
- Mean Relative Error: {results.mean_relative_error:.1f}%

PRECISION ANALYSIS:
- Predictions within 1 day: {results.accuracy_within_1_day} ({(results.accuracy_within_1_day / max(results.successful_predictions, 1)) * 100:.1f}%)
- Predictions within 3 days: {results.accuracy_within_3_days} ({(results.accuracy_within_3_days / max(results.successful_predictions, 1)) * 100:.1f}%)
- Predictions within 7 days: {results.accuracy_within_7_days} ({(results.accuracy_within_7_days / max(results.successful_predictions, 1)) * 100:.1f}%)

METHOD PERFORMANCE:
- Best Performing Method: {results.best_performing_method}
- Worst Performing Method: {results.worst_performing_method}

DETAILED TEST RESULTS:
"""
        
        # Add individual test results
        for i, test in enumerate(self.test_results[:20], 1):  # Show first 20 tests
            status = "✓" if test.accuracy_error is not None else "✗"
            error_str = f"{test.accuracy_error:.1f} days" if test.accuracy_error else "N/A"
            actual_str = f"{test.actual_days_until_empty}" if test.actual_days_until_empty is not None else "N/A"
            
            report += f"""
Test {i:2d} {status} | {test.pantry_name[:20]:20s} | Predicted: {test.predicted_days_until_empty:.1f} days | Actual: {actual_str:>3s} | Error: {error_str:>8s} | Confidence: {test.predicted_confidence:.0f}%"""
        
        if len(self.test_results) > 20:
            report += f"\n... and {len(self.test_results) - 20} more tests"
        
        return report
    
    def create_visualizations(self, results: TestResults):
        """Create visualization charts for the test results"""
        if not self.test_results:
            print("No test results to visualize")
            return
        
        # Filter successful tests
        successful_tests = [t for t in self.test_results if t.accuracy_error is not None]
        
        if not successful_tests:
            print("No successful tests to visualize")
            return
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Pantry Prediction Algorithm Accuracy Analysis', fontsize=16)
        
        # 1. Error Distribution
        errors = [t.accuracy_error for t in successful_tests]
        axes[0, 0].hist(errors, bins=20, edgecolor='black', alpha=0.7)
        axes[0, 0].set_title('Distribution of Prediction Errors')
        axes[0, 0].set_xlabel('Absolute Error (days)')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].axvline(np.mean(errors), color='red', linestyle='--', label=f'Mean: {np.mean(errors):.1f}')
        axes[0, 0].legend()
        
        # 2. Predicted vs Actual
        predicted = [t.predicted_days_until_empty for t in successful_tests]
        actual = [t.actual_days_until_empty for t in successful_tests]
        axes[0, 1].scatter(predicted, actual, alpha=0.6)
        max_val = max(max(predicted), max(actual))
        axes[0, 1].plot([0, max_val], [0, max_val], 'r--', label='Perfect Prediction')
        axes[0, 1].set_title('Predicted vs Actual Days Until Empty')
        axes[0, 1].set_xlabel('Predicted Days')
        axes[0, 1].set_ylabel('Actual Days')
        axes[0, 1].legend()
        
        # 3. Accuracy by Confidence Level
        confidence_bins = [(0, 50), (50, 70), (70, 85), (85, 100)]
        bin_labels = ['Low (0-50%)', 'Medium (50-70%)', 'High (70-85%)', 'Very High (85-100%)']
        accuracy_by_confidence = []
        
        for low, high in confidence_bins:
            bin_tests = [t for t in successful_tests if low <= t.predicted_confidence < high]
            if bin_tests:
                within_3_days = sum(1 for t in bin_tests if t.accuracy_error <= 3)
                accuracy = (within_3_days / len(bin_tests)) * 100
            else:
                accuracy = 0
            accuracy_by_confidence.append(accuracy)
        
        axes[1, 0].bar(bin_labels, accuracy_by_confidence)
        axes[1, 0].set_title('Accuracy (±3 days) by Confidence Level')
        axes[1, 0].set_ylabel('Accuracy (%)')
        axes[1, 0].tick_params(axis='x', rotation=45)
        
        # 4. Method Performance Comparison
        method_errors = {}
        for test in successful_tests:
            method = test.prediction_method.split('.')[0]  # Get main method name
            if method not in method_errors:
                method_errors[method] = []
            method_errors[method].append(test.accuracy_error)
        
        if method_errors:
            methods = list(method_errors.keys())
            avg_errors = [np.mean(method_errors[method]) for method in methods]
            axes[1, 1].bar(methods, avg_errors)
            axes[1, 1].set_title('Average Error by Prediction Method')
            axes[1, 1].set_ylabel('Mean Absolute Error (days)')
            axes[1, 1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.savefig('prediction_accuracy_analysis.png', dpi=300, bbox_inches='tight')
        print("Visualizations saved as 'prediction_accuracy_analysis.png'")
    
    def save_detailed_results(self):
        """Save detailed results to JSON file"""
        results_data = {
            'test_timestamp': datetime.now().isoformat(),
            'tests': [
                {
                    'pantry_id': t.pantry_id,
                    'pantry_name': t.pantry_name,
                    'prediction_date': t.prediction_date.isoformat(),
                    'predicted_days_until_empty': t.predicted_days_until_empty,
                    'predicted_confidence': t.predicted_confidence,
                    'actual_days_until_empty': t.actual_days_until_empty,
                    'prediction_method': t.prediction_method,
                    'accuracy_error': t.accuracy_error,
                    'relative_error': t.relative_error
                }
                for t in self.test_results
            ]
        }
        
        with open('prediction_test_results.json', 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print("Detailed results saved to 'prediction_test_results.json'")

def main():
    """Main function to run the prediction accuracy tests"""
    app = create_app()
    
    with app.app_context():
        tester = PredictionAccuracyTester(app)
        
        print("Starting Pantry Prediction Algorithm Accuracy Testing")
        print("=" * 60)
        
        # Run all tests
        results = tester.run_all_tests()
        
        # Generate and display report
        report = tester.generate_report(results)
        print(report)
        
        # Save detailed results
        tester.save_detailed_results()
        
        # Create visualizations
        try:
            tester.create_visualizations(results)
        except ImportError:
            print("Matplotlib not available - skipping visualizations")
        except Exception as e:
            print(f"Error creating visualizations: {e}")
        
        print("\n" + "=" * 60)
        print("Testing completed successfully!")
        print(f"Check 'prediction_test_results.json' for detailed results")
        print(f"Check 'prediction_accuracy_analysis.png' for visualizations")

if __name__ == "__main__":
    main()
