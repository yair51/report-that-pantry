#!/usr/bin/env python3
"""
Production Data Converter

This script helps convert CSV exports from your production database
into the JSON format needed for testing.
"""

import csv
import json
from datetime import datetime
from collections import defaultdict

def convert_csv_to_json(csv_file_path: str, output_file_path: str = 'production_data.json'):
    """
    Convert CSV export to JSON format for testing
    
    Expected CSV columns:
    pantry_id, pantry_name, city, state, report_time, pantry_fullness
    """
    
    pantries_data = defaultdict(lambda: {
        'reports': []
    })
    
    try:
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                pantry_id = row['pantry_id']
                
                # Set pantry info (will overwrite with same data, which is fine)
                pantries_data[pantry_id].update({
                    'id': int(pantry_id),
                    'name': row['pantry_name'],
                    'city': row['city'],
                    'state': row['state']
                })
                
                # Add report
                pantries_data[pantry_id]['reports'].append({
                    'time': row['report_time'],
                    'pantry_fullness': int(row['pantry_fullness'])
                })
        
        # Convert to final format
        result = {
            'pantries': list(pantries_data.values())
        }
        
        # Sort reports by time for each pantry
        for pantry in result['pantries']:
            pantry['reports'].sort(key=lambda x: x['time'])
        
        # Save to JSON
        with open(output_file_path, 'w') as jsonfile:
            json.dump(result, jsonfile, indent=2)
        
        print(f"✅ Converted {csv_file_path} to {output_file_path}")
        print(f"📊 Found {len(result['pantries'])} pantries")
        
        total_reports = sum(len(p['reports']) for p in result['pantries'])
        print(f"📈 Total reports: {total_reports}")
        
        return output_file_path
        
    except FileNotFoundError:
        print(f"❌ CSV file {csv_file_path} not found")
        return None
    except Exception as e:
        print(f"❌ Error converting CSV: {e}")
        return None

def create_sample_csv():
    """Create a sample CSV file to show the expected format"""
    sample_data = [
        ['pantry_id', 'pantry_name', 'city', 'state', 'report_time', 'pantry_fullness'],
        [1, 'Downtown Community Pantry', 'San Francisco', 'CA', '2025-06-15T10:30:00Z', 75],
        [1, 'Downtown Community Pantry', 'San Francisco', 'CA', '2025-06-16T14:20:00Z', 45],
        [1, 'Downtown Community Pantry', 'San Francisco', 'CA', '2025-06-17T09:15:00Z', 20],
        [2, 'Suburban Food Hub', 'Oakland', 'CA', '2025-06-15T11:00:00Z', 90],
        [2, 'Suburban Food Hub', 'Oakland', 'CA', '2025-06-16T16:30:00Z', 60],
    ]
    
    with open('sample_production_data.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(sample_data)
    
    print("📄 Created sample_production_data.csv as an example")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert production data to testing format')
    parser.add_argument('--csv', type=str, help='Path to CSV file to convert')
    parser.add_argument('--output', type=str, default='production_data.json', 
                       help='Output JSON file path')
    parser.add_argument('--sample', action='store_true', help='Create sample CSV file')
    
    args = parser.parse_args()
    
    if args.sample:
        create_sample_csv()
    elif args.csv:
        convert_csv_to_json(args.csv, args.output)
    else:
        print("Use --csv <file> to convert a CSV file, or --sample to create an example")
        print("Use --help for more information")

if __name__ == "__main__":
    main()
