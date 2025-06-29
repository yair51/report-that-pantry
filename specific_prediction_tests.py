#!/usr/bin/env python3
"""
Specific Prediction Test Cases

This script tests the prediction algorithm with specific scenarios:
1. High-frequency pantries (restocked often)
2. Low-frequency pantries (restocked rarely)
3. Seasonal pantries (varying patterns)
4. Edge cases (very few reports, irregular patterns)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import Location, Report
from app.views import calculate_advanced_predictions
from datetime import datetime, timedelta
from sqlalchemy import func, desc
import json

class SpecificTestCases:
    def __init__(self, app):
        self.app = app
        
    def identify_pantry_types(self):
        """Categorize pantries by their reporting patterns"""
        with self.app.app_context():
            pantries = Location.query.all()
            categorized = {
                'high_frequency': [],
                'low_frequency': [],
                'seasonal': [],
                'edge_cases': []
            }
            
            for pantry in pantries:
                reports = Report.query.filter_by(location_id=pantry.id).order_by(Report.time).all()
                
                if len(reports) < 5:
                    categorized['edge_cases'].append((pantry, reports, "Too few reports"))
                    continue
                
                # Calculate reporting frequency
                time_span = (reports[-1].time - reports[0].time).days
                if time_span == 0:
                    categorized['edge_cases'].append((pantry, reports, "All reports same day"))
                    continue
                
                reports_per_week = len(reports) / (time_span / 7)
                
                # Categorize based on frequency
                if reports_per_week >= 2:
                    categorized['high_frequency'].append((pantry, reports, f"{reports_per_week:.1f} reports/week"))
                elif reports_per_week >= 0.5:
                    categorized['low_frequency'].append((pantry, reports, f"{reports_per_week:.1f} reports/week"))
                else:
                    categorized['edge_cases'].append((pantry, reports, f"Very low frequency: {reports_per_week:.1f} reports/week"))
                
                # Check for seasonal patterns (variation in monthly activity)
                if len(reports) >= 12:  # Need enough data
                    monthly_counts = {}
                    for report in reports:
                        month_key = f"{report.time.year}-{report.time.month:02d}"
                        monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
                    
                    if len(monthly_counts) >= 3:
                        counts = list(monthly_counts.values())
                        if max(counts) > 2 * min(counts):  # High variation
                            categorized['seasonal'].append((pantry, reports, f"Seasonal variation detected"))
            
            return categorized
    
    def test_high_frequency_pantries(self, pantries_data):
        """Test prediction accuracy on high-frequency pantries"""
        print("\n🔄 TESTING HIGH-FREQUENCY PANTRIES")
        print("=" * 40)
        
        results = []
        for pantry, reports, description in pantries_data[:3]:  # Test top 3
            print(f"\nTesting: {pantry.name} ({description})")
            
            # Use last 20 reports for prediction
            if len(reports) >= 20:
                test_reports = reports[-20:]
                analytics = self.create_analytics(test_reports)
                
                try:
                    predictions = calculate_advanced_predictions(analytics)
                    if predictions:
                        print(f"  ✅ Prediction: {predictions.get('days_until_empty', 'N/A')} days")
                        print(f"  📊 Confidence: {predictions.get('confidence', 0):.0f}%")
                        print(f"  🔧 Method: {predictions.get('prediction_explanation', 'N/A')}")
                        results.append({
                            'pantry': pantry.name,
                            'type': 'high_frequency',
                            'prediction': predictions.get('days_until_empty'),
                            'confidence': predictions.get('confidence'),
                            'method': predictions.get('prediction_explanation')
                        })
                    else:
                        print("  ❌ No prediction generated")
                except Exception as e:
                    print(f"  ❌ Error: {e}")
        
        return results
    
    def test_low_frequency_pantries(self, pantries_data):
        """Test prediction accuracy on low-frequency pantries"""
        print("\n🐌 TESTING LOW-FREQUENCY PANTRIES")
        print("=" * 40)
        
        results = []
        for pantry, reports, description in pantries_data[:3]:
            print(f"\nTesting: {pantry.name} ({description})")
            
            analytics = self.create_analytics(reports)
            
            try:
                predictions = calculate_advanced_predictions(analytics)
                if predictions:
                    print(f"  ✅ Prediction: {predictions.get('days_until_empty', 'N/A')} days")
                    print(f"  📊 Confidence: {predictions.get('confidence', 0):.0f}%")
                    print(f"  🔧 Method: {predictions.get('prediction_explanation', 'N/A')}")
                    results.append({
                        'pantry': pantry.name,
                        'type': 'low_frequency',
                        'prediction': predictions.get('days_until_empty'),
                        'confidence': predictions.get('confidence'),
                        'method': predictions.get('prediction_explanation')
                    })
                else:
                    print("  ❌ No prediction generated")
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        return results
    
    def test_edge_cases(self, pantries_data):
        """Test how the algorithm handles edge cases"""
        print("\n⚠️  TESTING EDGE CASES")
        print("=" * 40)
        
        results = []
        for pantry, reports, description in pantries_data[:5]:
            print(f"\nTesting: {pantry.name} ({description})")
            
            analytics = self.create_analytics(reports)
            
            try:
                predictions = calculate_advanced_predictions(analytics)
                if predictions:
                    print(f"  ⚠️  Prediction: {predictions.get('days_until_empty', 'N/A')} days")
                    print(f"  📊 Confidence: {predictions.get('confidence', 0):.0f}%")
                    print(f"  🔧 Method: {predictions.get('prediction_explanation', 'N/A')}")
                    results.append({
                        'pantry': pantry.name,
                        'type': 'edge_case',
                        'prediction': predictions.get('days_until_empty'),
                        'confidence': predictions.get('confidence'),
                        'method': predictions.get('prediction_explanation'),
                        'issue': description
                    })
                else:
                    print("  ✅ Correctly avoided prediction (insufficient data)")
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        return results
    
    def test_prediction_consistency(self):
        """Test if predictions are consistent when using slightly different data"""
        print("\n🔄 TESTING PREDICTION CONSISTENCY")
        print("=" * 40)
        
        with self.app.app_context():
            # Find a pantry with many reports
            pantry = Location.query.join(Report).group_by(Location.id).having(
                func.count(Report.id) >= 25
            ).first()
            
            if not pantry:
                print("  ❌ No pantry with sufficient data found")
                return []
            
            reports = Report.query.filter_by(pantry_id=pantry.id).order_by(Report.time).all()
            print(f"\nTesting consistency on: {pantry.name} ({len(reports)} reports)")
            
            # Test with different data subsets
            predictions = []
            for end_point in [-1, -2, -3, -4, -5]:  # Remove 1-5 most recent reports
                test_reports = reports[:end_point] if end_point != -1 else reports
                analytics = self.create_analytics(test_reports)
                
                try:
                    prediction = calculate_advanced_predictions(analytics)
                    if prediction:
                        days = prediction.get('days_until_empty')
                        confidence = prediction.get('confidence', 0)
                        predictions.append((len(test_reports), days, confidence))
                        print(f"  📊 With {len(test_reports)} reports: {days} days (confidence: {confidence:.0f}%)")
                except Exception as e:
                    print(f"  ❌ Error with {len(test_reports)} reports: {e}")
            
            # Analyze consistency
            if len(predictions) >= 3:
                days_predictions = [p[1] for p in predictions if p[1] is not None]
                if days_predictions:
                    avg_prediction = sum(days_predictions) / len(days_predictions)
                    max_deviation = max(abs(d - avg_prediction) for d in days_predictions)
                    print(f"\n  📈 Average prediction: {avg_prediction:.1f} days")
                    print(f"  📊 Max deviation: {max_deviation:.1f} days")
                    print(f"  ✅ Consistency: {'Good' if max_deviation <= 2 else 'Moderate' if max_deviation <= 5 else 'Poor'}")
        
        return predictions
    
    def create_analytics(self, reports):
        """Create analytics structure from reports"""
        if not reports:
            return {}
        
        fullness_values = [r.pantry_fullness for r in reports]
        
        return {
            'total_reports': len(reports),
            'fullness_stats': {
                'average': sum(fullness_values) / len(fullness_values),
                'minimum': min(fullness_values),
                'maximum': max(fullness_values)
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
    
    def run_all_specific_tests(self):
        """Run all specific test cases"""
        print("SPECIFIC PREDICTION ALGORITHM TESTS")
        print("=" * 50)
        
        # Categorize pantries
        categories = self.identify_pantry_types()
        
        print(f"\nPANTRY CATEGORIZATION:")
        print(f"  High-frequency: {len(categories['high_frequency'])} pantries")
        print(f"  Low-frequency: {len(categories['low_frequency'])} pantries")
        print(f"  Seasonal: {len(categories['seasonal'])} pantries")
        print(f"  Edge cases: {len(categories['edge_cases'])} pantries")
        
        all_results = []
        
        # Run tests
        if categories['high_frequency']:
            results = self.test_high_frequency_pantries(categories['high_frequency'])
            all_results.extend(results)
        
        if categories['low_frequency']:
            results = self.test_low_frequency_pantries(categories['low_frequency'])
            all_results.extend(results)
        
        if categories['edge_cases']:
            results = self.test_edge_cases(categories['edge_cases'])
            all_results.extend(results)
        
        # Test consistency
        consistency_results = self.test_prediction_consistency()
        
        # Save results
        test_summary = {
            'timestamp': datetime.now().isoformat(),
            'categorization': {
                'high_frequency_count': len(categories['high_frequency']),
                'low_frequency_count': len(categories['low_frequency']),
                'seasonal_count': len(categories['seasonal']),
                'edge_cases_count': len(categories['edge_cases'])
            },
            'prediction_results': all_results,
            'consistency_test': consistency_results
        }
        
        with open('specific_prediction_tests.json', 'w') as f:
            json.dump(test_summary, f, indent=2, default=str)
        
        print(f"\n" + "=" * 50)
        print("SPECIFIC TESTS COMPLETED")
        print("Results saved to 'specific_prediction_tests.json'")
        
        return test_summary

def main():
    """Main function to run specific prediction tests"""
    app = create_app()
    
    tester = SpecificTestCases(app)
    results = tester.run_all_specific_tests()
    
    # Print summary
    print(f"\nSUMMARY:")
    successful_predictions = [r for r in results['prediction_results'] if r.get('prediction') is not None]
    print(f"  Total predictions attempted: {len(results['prediction_results'])}")
    print(f"  Successful predictions: {len(successful_predictions)}")
    
    if successful_predictions:
        avg_confidence = sum(r.get('confidence', 0) for r in successful_predictions) / len(successful_predictions)
        print(f"  Average confidence: {avg_confidence:.1f}%")
        
        # Count by type
        type_counts = {}
        for r in successful_predictions:
            type_counts[r['type']] = type_counts.get(r['type'], 0) + 1
        
        for ptype, count in type_counts.items():
            print(f"  {ptype}: {count} successful predictions")

if __name__ == "__main__":
    main()
