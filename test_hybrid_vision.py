#!/usr/bin/env python3
"""
Test script for the hybrid vision analysis
"""

import os
import sys
import json

# Add the app directory to the path
sys.path.append('/Users/yairgritzman/Downloads/web-projects/pantry-website/pantry-website')

from app.vision import analyze_pantry_image_hybrid

def test_hybrid_analysis():
    """Test the hybrid analysis with a sample image"""
    test_image_path = './app/static/pantry-photo-2.jpg'
    
    if not os.path.exists(test_image_path):
        print(f"Test image not found at {test_image_path}")
        print("Available images in static folder:")
        static_dir = './app/static'
        if os.path.exists(static_dir):
            for file in os.listdir(static_dir):
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    print(f"  - {file}")
        return
    
    try:
        # Read the test image
        with open(test_image_path, 'rb') as f:
            image_content = f.read()
        
        print("Testing hybrid vision analysis...")
        print("=" * 50)
        
        # Run the hybrid analysis
        result = analyze_pantry_image_hybrid(image_content)
        
        # Print results in a nice format
        print("ANALYSIS RESULTS:")
        print("-" * 30)
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return
        
        print(f"📊 Fullness Estimate: {result.get('fullness_estimate', 'N/A')}%")
        print(f"🔍 Confidence Score: {result.get('confidence_score', 'N/A')}%")
        print(f"🤝 Method Agreement: {result.get('method_agreement', 'N/A')}")
        
        food_items = result.get('food_items', [])
        print(f"\n🍎 Food Items Detected ({len(food_items)}):")
        for i, item in enumerate(food_items[:10], 1):  # Show first 10 items
            print(f"  {i}. {item}")
        
        if len(food_items) > 10:
            print(f"  ... and {len(food_items) - 10} more items")
        
        # Show analysis details if available
        analysis_details = result.get('analysis_details', {})
        if analysis_details:
            print(f"\n📋 Analysis Details:")
            vision_analysis = analysis_details.get('vision_analysis', {})
            gemini_analysis = analysis_details.get('gemini_analysis', {})
            
            if not vision_analysis.get('error'):
                vision_fullness = vision_analysis.get('fullness_estimate')
                print(f"  Vision API Fullness: {vision_fullness}%")
                vision_items = len(vision_analysis.get('food_items', []))
                print(f"  Vision API Items: {vision_items}")
            
            if not gemini_analysis.get('error'):
                gemini_fullness = gemini_analysis.get('fullness_estimate')
                print(f"  Gemini Fullness: {gemini_fullness}%")
                gemini_items = len(gemini_analysis.get('food_items', []))
                print(f"  Gemini Items: {gemini_items}")
        
        print("\n" + "=" * 50)
        print("✅ Test completed successfully!")
        
        # Save detailed results to file for inspection
        with open('hybrid_analysis_results.json', 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print("📁 Detailed results saved to 'hybrid_analysis_results.json'")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_hybrid_analysis()
