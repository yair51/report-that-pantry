import os
import google.generativeai as genai
from google.cloud import vision
from PIL import Image
from dotenv import load_dotenv
import tempfile
import re
import json

load_dotenv()

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

def get_vision_client():
    """Initialize Google Vision API client"""
    try:
        return vision.ImageAnnotatorClient()
    except Exception as e:
        print(f"Error initializing Vision API client: {e}")
        return None

def analyze_pantry_image_hybrid(image_content):
    """
    Analyze pantry image using Gemini AI (primary) with Vision API as fallback
    """
    try:
        # Use Gemini as primary analysis method
        gemini_results = analyze_pantry_with_gemini(image_content)
        
        # If Gemini succeeds, use it as the primary result
        if not gemini_results.get("error"):
            # Enhance Gemini results with confidence scoring
            enhanced_results = enhance_gemini_results(gemini_results)
            return enhanced_results
        
        # Fallback to Vision API if Gemini fails
        print("Gemini analysis failed, falling back to Vision API...")
        vision_results = analyze_pantry_with_vision_api(image_content)
        
        if not vision_results.get("error"):
            return vision_results
        
        # Both failed
        return {
            "error": f"Both AI systems failed. Gemini: {gemini_results.get('error', 'Unknown error')}, Vision: {vision_results.get('error', 'Unknown error')}"
        }
        
    except Exception as e:
        print(f"Hybrid analysis failed: {str(e)}")
        return {"error": f"Analysis failed: {str(e)}"}

def enhance_gemini_results(gemini_results):
    """
    Enhance Gemini results with confidence scoring and standardized format
    """
    try:
        enhanced = {
            "food_items": gemini_results.get("food_items", []),
            "fullness_estimate": gemini_results.get("fullness_estimate"),
            "confidence_score": calculate_gemini_confidence(gemini_results),
            "method_agreement": True,  # Single method, so always true
            "analysis_method": "gemini_primary",
            "empty_areas": gemini_results.get("empty_areas", ""),
            "non_food_items": gemini_results.get("non_food_items", [])
        }
        
        return enhanced
        
    except Exception as e:
        print(f"Error enhancing Gemini results: {e}")
        return gemini_results

def calculate_gemini_confidence(gemini_results):
    """
    Calculate confidence score for Gemini analysis based on completeness and quality
    Updated for concise response format
    """
    try:
        confidence = 60  # Higher base confidence for focused responses
        
        # Bonus for detecting food items
        food_items = gemini_results.get("food_items", [])
        if food_items:
            confidence += min(25, len(food_items) * 6)  # Up to 25 points for food items
            
            # Bonus for concise but specific food descriptions
            specific_items = [item for item in food_items if len(item.split()) <= 3 and len(item) > 3]
            confidence += min(10, len(specific_items) * 2)
        
        # Bonus for having fullness estimate
        if gemini_results.get("fullness_estimate") is not None:
            confidence += 15
            
            # Consistency check: reasonable fullness for detected items
            fullness = gemini_results.get("fullness_estimate", 0)
            if len(food_items) > 0:
                # Should have reasonable fullness if food detected
                if 20 <= fullness <= 95:  # Reasonable range
                    confidence += 5
                elif fullness > 95 or (fullness < 20 and len(food_items) > 3):
                    confidence -= 10  # Inconsistent
        
        # Small penalty if no food detected but high fullness (inconsistency)
        fullness = gemini_results.get("fullness_estimate", 0)
        if len(food_items) == 0 and fullness > 30:
            confidence -= 15
        
        # Bonus for identifying empty areas when appropriate
        empty_areas = gemini_results.get("empty_areas", "")
        if empty_areas and empty_areas.strip():
            confidence += 5
        
        return min(100, max(40, confidence))  # Keep between 40-100
        
    except Exception as e:
        print(f"Error calculating Gemini confidence: {e}")
        return 75  # Default reasonable confidence

def analyze_pantry_with_vision_api(image_content):
    """
    Enhanced pantry image analysis using Google Vision API
    """
    client = get_vision_client()
    if not client:
        return {"error": "Vision API client not available"}
    
    try:
        image = vision.Image(content=image_content)
        
        analysis_results = {
            "labels": [],
            "objects": [],
            "food_items": [],
            "fullness_estimate": None,
            "confidence_score": 0,
            "spatial_analysis": {}
        }
        
        # Enhanced Label Detection with better food categorization
        labels_response = client.label_detection(image=image, max_results=50)
        labels = labels_response.label_annotations
        
        # Comprehensive food categories
        food_categories = {
            'canned_goods': [
                'canned food', 'canned goods', 'tin can', 'soup', 'beans', 'tomatoes',
                'corn', 'peas', 'fruit cocktail', 'tuna', 'salmon', 'sardines', 'sauce'
            ],
            'packaged_foods': [
                'cereal', 'pasta', 'rice', 'bread', 'crackers', 'chips', 'snacks',
                'cookies', 'granola', 'oatmeal', 'flour', 'sugar', 'salt', 'box'
            ],
            'fresh_produce': [
                'apple', 'banana', 'orange', 'potato', 'onion', 'carrot', 'tomato',
                'lettuce', 'fruit', 'vegetable', 'produce'
            ],
            'beverages': [
                'bottle', 'drink', 'juice', 'water', 'soda', 'beverage'
            ],
            'condiments_pantry': [
                'jar', 'oil', 'vinegar', 'dressing', 'jam', 'jelly', 'honey', 'syrup'
            ]
        }
        
        # Items to exclude (containers, not food)
        exclude_keywords = [
            'container', 'storage', 'shelf', 'shelving', 'basket', 'bin', 'rack',
            'cabinet', 'cupboard', 'pantry', 'kitchen', 'room', 'wall', 'door',
            'plastic', 'glass', 'metal', 'wood', 'material', 'packaging',
            'wrapper', 'label', 'brand', 'cardboard', 'paper'
        ]
        
        detected_food_items = []
        
        for label in labels:
            label_info = {
                "description": label.description,
                "confidence": label.score,
                "topicality": label.topicality
            }
            analysis_results["labels"].append(label_info)
            
            description_lower = label.description.lower()
            
            # Skip if it's explicitly excluded
            if any(exclude_word in description_lower for exclude_word in exclude_keywords):
                continue
            
            # Categorize food items
            for category, keywords in food_categories.items():
                if any(keyword in description_lower for keyword in keywords):
                    food_item = label_info.copy()
                    food_item['category'] = category
                    detected_food_items.append(food_item)
                    break
        
        analysis_results["food_items"] = detected_food_items
        
        # Object Detection with spatial analysis
        objects_response = client.object_localization(image=image, max_results=20)
        objects = objects_response.localized_object_annotations
        
        food_objects = []
        
        for obj in objects:
            # Calculate object area from bounding box
            vertices = obj.bounding_poly.normalized_vertices
            if len(vertices) >= 4:
                width = abs(vertices[1].x - vertices[0].x)
                height = abs(vertices[2].y - vertices[0].y)
                area = width * height
            else:
                area = 0
            
            object_info = {
                "name": obj.name,
                "confidence": obj.score,
                "area": area,
                "bounding_box": {
                    "vertices": [(vertex.x, vertex.y) for vertex in vertices]
                }
            }
            analysis_results["objects"].append(object_info)
            
            # Look for food-related objects
            obj_name_lower = obj.name.lower()
            if any(food_word in obj_name_lower for food_word in 
                   ['food', 'fruit', 'vegetable', 'bottle', 'jar', 'package', 'box']):
                food_objects.append(object_info)
        
        # Spatial analysis
        spatial_data = analyze_spatial_distribution(food_objects)
        analysis_results["spatial_analysis"] = spatial_data
        
        # Enhanced fullness estimation
        analysis_results["fullness_estimate"] = estimate_fullness_vision(
            detected_food_items, food_objects, spatial_data
        )
        
        # Calculate confidence score
        analysis_results["confidence_score"] = calculate_vision_confidence(
            detected_food_items, food_objects
        )
        
        return analysis_results
        
    except Exception as e:
        print(f"Vision API analysis failed: {str(e)}")
        return {"error": f"Vision API analysis failed: {str(e)}"}

def analyze_spatial_distribution(food_objects):
    """
    Analyze the spatial distribution of food items
    """
    try:
        total_food_area = sum(obj.get('area', 0) for obj in food_objects)
        
        # Calculate coverage metrics
        estimated_pantry_coverage = min(1.0, total_food_area * 3)  # Heuristic multiplier
        
        # Analyze distribution if multiple objects
        distribution_score = 0
        if len(food_objects) > 1:
            x_positions = []
            y_positions = []
            
            for obj in food_objects:
                if obj.get('bounding_box', {}).get('vertices'):
                    vertices = obj['bounding_box']['vertices']
                    center_x = sum(v[0] for v in vertices) / len(vertices)
                    center_y = sum(v[1] for v in vertices) / len(vertices)
                    x_positions.append(center_x)
                    y_positions.append(center_y)
            
            if x_positions and y_positions:
                x_spread = max(x_positions) - min(x_positions)
                y_spread = max(y_positions) - min(y_positions)
                distribution_score = (x_spread + y_spread) / 2
        
        return {
            "total_food_area": total_food_area,
            "estimated_coverage": estimated_pantry_coverage,
            "distribution_score": distribution_score,
            "food_object_count": len(food_objects)
        }
        
    except Exception as e:
        print(f"Error in spatial analysis: {e}")
        return {}

def estimate_fullness_vision(food_items, food_objects, spatial_data):
    """
    Enhanced fullness estimation using Vision API data
    """
    try:
        food_label_count = len(food_items)
        food_object_count = spatial_data.get('food_object_count', 0)
        estimated_coverage = spatial_data.get('estimated_coverage', 0)
        distribution_score = spatial_data.get('distribution_score', 0)
        
        # Weight different detection methods
        label_weight = 0.4
        object_weight = 0.3
        spatial_weight = 0.3
        
        # Calculate component scores
        label_score = min(100, food_label_count * 12)  # ~12% per detected food label
        object_score = min(100, food_object_count * 18)  # ~18% per detected food object
        spatial_score = min(100, estimated_coverage * 100)  # Based on estimated coverage
        
        # Combine scores with weights
        base_fullness = (
            label_score * label_weight +
            object_score * object_weight +
            spatial_score * spatial_weight
        )
        
        # Apply distribution bonus (better distributed = likely fuller)
        if distribution_score > 0.3:
            base_fullness *= 1.1
        
        # Final bounds and rounding
        final_fullness = max(0, min(100, round(base_fullness)))
        
        return final_fullness
        
    except Exception as e:
        print(f"Error in Vision fullness estimation: {e}")
        return None

def calculate_vision_confidence(food_items, food_objects):
    """
    Calculate confidence score for Vision API analysis
    """
    try:
        confidence = 0
        
        # Base confidence from detection counts
        confidence += min(40, len(food_items) * 8)  # Up to 40 points for food labels
        confidence += min(30, len(food_objects) * 10)  # Up to 30 points for food objects
        
        # Bonus for multiple detection methods
        if len(food_items) > 0 and len(food_objects) > 0:
            confidence += 15  # Bonus for multiple detection methods
        
        # Bonus for high-confidence detections
        high_confidence_items = [item for item in food_items if item.get('confidence', 0) > 0.8]
        confidence += min(15, len(high_confidence_items) * 3)
        
        return min(100, confidence)
        
    except Exception as e:
        print(f"Error calculating Vision confidence: {e}")
        return 0

def analyze_pantry_with_gemini(image_content):
    """
    Use Gemini to analyze pantry image with specific prompts
    """
    try:
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        
        # Save image content to temporary file for Gemini
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_file.write(image_content)
            temp_path = temp_file.name
        
        try:
            # Upload to Gemini
            uploaded_file = genai.upload_file(temp_path)
            
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            # Concise prompt focused specifically on food and fullness
            prompt = """
            Analyze this pantry image. Identify ONLY edible food items and estimate fullness.

            IGNORE: posters, flyers, papers, signs, logos, website materials, non-edible items.

            Provide a brief response in this exact format:
            FOOD ITEMS: [list only actual food/beverages, be concise]
            FULLNESS: [0-100]%
            EMPTY: [brief description if significantly empty areas exist]

            Be concise. Focus only on consumable food items and space utilization.
            """
            
            result = model.generate_content([uploaded_file, prompt])
            
            # Parse Gemini response
            parsed_results = parse_gemini_response(result.text)
            
            return parsed_results
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
    except Exception as e:
        print(f"Gemini analysis error: {e}")
        return {"error": str(e)}

def parse_gemini_response(response_text):
    """
    Parse Gemini's structured response into usable data with filtering
    """
    try:
        results = {
            "food_items": [],
            "fullness_estimate": None,
            "empty_areas": "",
            "non_food_items": []
        }
        
        # Define items to filter out (non-food items that shouldn't be in results)
        non_food_filter = [
            'poster', 'flyer', 'paper', 'sign', 'logo', 'website', 'printout',
            'notice', 'advertisement', 'label', 'sticker', 'card', 'sheet',
            'document', 'text', 'writing', 'information', 'instruction',
            'shelf', 'container', 'basket', 'bin', 'rack', 'storage',
            'cabinet', 'wall', 'door', 'wood', 'plastic', 'metal'
        ]
        
        lines = response_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith("FOOD ITEMS:"):
                items_text = line.replace("FOOD ITEMS:", "").strip()
                if items_text and items_text.lower() not in ['none', 'no items', 'empty']:
                    raw_items = [item.strip() for item in items_text.split(',') if item.strip()]
                    # Filter out non-food items
                    filtered_items = []
                    for item in raw_items:
                        item_lower = item.lower()
                        # Only keep items that don't contain filtered keywords
                        if not any(filter_word in item_lower for filter_word in non_food_filter):
                            filtered_items.append(item)
                    results["food_items"] = filtered_items
            
            elif line.startswith("FULLNESS:"):
                fullness_text = line.replace("FULLNESS:", "").strip()
                # Extract percentage
                match = re.search(r'(\d+)%?', fullness_text)
                if match:
                    results["fullness_estimate"] = int(match.group(1))
            
            elif line.startswith("EMPTY:"):
                empty_text = line.replace("EMPTY:", "").strip()
                if empty_text and empty_text.lower() not in ['none', 'no', 'n/a']:
                    results["empty_areas"] = empty_text
        
        return results
        
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        return {"error": str(e)}

def combine_ai_analyses(vision_results, gemini_results):
    """
    Combine and cross-validate results from both AI systems
    """
    try:
        combined = {
            "food_items": [],
            "fullness_estimate": None,
            "confidence_score": 0,
            "method_agreement": False,
            "analysis_details": {
                "vision_analysis": vision_results,
                "gemini_analysis": gemini_results
            }
        }
        
        # Handle errors from either system
        vision_error = vision_results.get("error")
        gemini_error = gemini_results.get("error")
        
        if vision_error and gemini_error:
            return {"error": f"Both AI systems failed. Vision: {vision_error}, Gemini: {gemini_error}"}
        
        # Combine food items from both sources
        vision_foods = []
        if not vision_error:
            vision_foods = [item.get("description", "") for item in vision_results.get("food_items", [])]
        
        gemini_foods = []
        if not gemini_error:
            gemini_foods = gemini_results.get("food_items", [])
        
        # Merge and deduplicate food items
        all_foods = vision_foods + gemini_foods
        unique_foods = []
        for item in all_foods:
            if item and item.strip() and item.strip().lower() not in [f.lower() for f in unique_foods]:
                unique_foods.append(item.strip())
        
        combined["food_items"] = unique_foods
        
        # Combine fullness estimates with agreement checking
        vision_fullness = vision_results.get("fullness_estimate") if not vision_error else None
        gemini_fullness = gemini_results.get("fullness_estimate") if not gemini_error else None
        
        if vision_fullness is not None and gemini_fullness is not None:
            # Check agreement level
            difference = abs(vision_fullness - gemini_fullness)
            
            if difference <= 20:  # Good agreement (within 20%)
                combined["method_agreement"] = True
                combined["fullness_estimate"] = round((vision_fullness + gemini_fullness) / 2)
                combined["confidence_score"] = min(100, 85 + (20 - difference))
            else:  # Poor agreement - use weighted average
                combined["method_agreement"] = False
                # Weight Gemini slightly higher as it has semantic understanding
                weighted_fullness = (vision_fullness * 0.4 + gemini_fullness * 0.6)
                combined["fullness_estimate"] = round(weighted_fullness)
                combined["confidence_score"] = max(40, 75 - difference)
        
        elif vision_fullness is not None:
            combined["fullness_estimate"] = vision_fullness
            combined["confidence_score"] = vision_results.get("confidence_score", 60)
        
        elif gemini_fullness is not None:
            combined["fullness_estimate"] = gemini_fullness
            combined["confidence_score"] = 65  # Slightly higher base confidence for Gemini
        
        else:
            combined["confidence_score"] = 20  # Low confidence if no estimates
        
        # Add food count bonus to confidence
        food_count_bonus = min(15, len(unique_foods) * 3)
        combined["confidence_score"] = min(100, combined["confidence_score"] + food_count_bonus)
        
        return combined
        
    except Exception as e:
        print(f"Error combining analyses: {e}")
        # Fallback to vision results if combination fails
        if not vision_results.get("error"):
            return vision_results
        elif not gemini_results.get("error"):
            return gemini_results
        else:
            return {"error": f"Analysis combination failed: {str(e)}"}

# Legacy function for backward compatibility
def analyze_pantry_image_with_gemini(image_path):
    """
    Legacy function - analyze image file with Gemini only
    """
    try:
        with open(image_path, 'rb') as f:
            image_content = f.read()
        
        return analyze_pantry_with_gemini(image_content)
        
    except Exception as e:
        print(f"Error in legacy Gemini analysis: {e}")
        return {"error": str(e)}

# Test the implementation if run directly
if __name__ == "__main__":
    test_image_path = './app/static/pantry-photo-2.jpg'
    print(f"Looking for test image at: {test_image_path}")
    
    if os.path.exists(test_image_path):
        print("Test image found! Starting hybrid analysis...")
        try:
            with open(test_image_path, 'rb') as f:
                test_content = f.read()
            
            print("Testing hybrid analysis...")
            result = analyze_pantry_image_hybrid(test_content)
            
            print("\n=== HYBRID ANALYSIS RESULTS ===")
            print(json.dumps(result, indent=2))
            
        except Exception as e:
            print(f"Error during test: {e}")
    else:
        print(f"Test image not found at {test_image_path}")
        print("Available files:")
        for root, dirs, files in os.walk('.'):
            for file in files:
                if file.endswith(('.jpg', '.jpeg', '.png')):
                    print(f"  {os.path.join(root, file)}")