from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for, current_app, send_from_directory, abort
from flask_login import login_required, current_user
from sqlalchemy.sql.expression import true
from sqlalchemy.orm import joinedload
from .models import Location, Report, Notification, User
from app.helpers import send_email, allowed_file, upload_photo_to_s3, delete_photo_from_s3
from . import db, Message, mail
import json
from datetime import datetime, timezone
from time import mktime
from sqlalchemy import func, and_, desc
from werkzeug.utils import secure_filename
import os
import base64  # Import base64 for encoding images
from PIL import Image, ImageOps
import io
import uuid
import boto3
from boto3 import s3
# Google Vision API imports
from google.cloud import vision

views = Blueprint('views', __name__)


# Initialize Google Vision API client
def get_vision_client():
    """Initialize and return Google Vision API client"""
    try:
        # Check if credentials are available
        credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if credentials_path and not os.path.exists(credentials_path):
            print(f"Google credentials file not found at: {credentials_path}")
            return None
        
        client = vision.ImageAnnotatorClient()
        print("✓ Vision API client initialized successfully")
        return client
        
    except Exception as e:
        print(f"Error initializing Vision API client: {e}")
        print("Make sure GOOGLE_APPLICATION_CREDENTIALS is set and points to a valid service account key file")
        return None


def analyze_pantry_image(image_content):
    """
    Analyze pantry image using Google Vision API to extract useful information
    Returns a dictionary with analysis results
    """
    client = get_vision_client()
    if not client:
        return {"error": "Vision API client not available"}
    
    try:
        # Create Vision API image object
        image = vision.Image(content=image_content)
        
        # Perform different types of analysis
        analysis_results = {
            "labels": [],
            "objects": [],
            "text": [],
            "fullness_estimate": None,
            "food_items": [],
            "organization_score": None
        }
        
        # 1. Label Detection - identifies general content
        labels_response = client.label_detection(image=image)
        labels = labels_response.label_annotations
        
        food_related_labels = []
        container_labels = []
        
        for label in labels:
            label_info = {
                "description": label.description,
                "confidence": label.score,
                "topicality": label.topicality
            }
            analysis_results["labels"].append(label_info)
            
            # Categorize food-related labels - be more specific about actual food items
            actual_food_keywords = [
                # Fruits
                'apple', 'banana', 'orange', 'grape', 'berry', 'fruit', 'citrus', 'avocado',
                'lemon', 'lime', 'peach', 'pear', 'strawberry', 'blueberry', 'cherry',
                # Vegetables  
                'vegetable', 'carrot', 'potato', 'onion', 'tomato', 'lettuce', 'spinach',
                'broccoli', 'corn', 'bean', 'pea', 'pepper', 'cucumber', 'celery',
                # Grains and bread
                'bread', 'cereal', 'rice', 'pasta', 'grain', 'oats', 'wheat', 'bagel',
                'muffin', 'cracker', 'biscuit', 'roll',
                # Dairy
                'milk', 'cheese', 'yogurt', 'butter', 'cream', 'dairy',
                # Meat and protein
                'meat', 'chicken', 'beef', 'pork', 'fish', 'salmon', 'tuna', 'egg',
                'protein', 'turkey', 'ham', 'bacon', 'sausage',
                # Pantry staples
                'soup', 'sauce', 'oil', 'vinegar', 'spice', 'herb', 'salt', 'sugar',
                'honey', 'jam', 'jelly', 'nut', 'almond', 'peanut', 'snack',
                # Canned/packaged foods (but actual food, not containers)
                'canned food', 'canned goods', 'packaged food'
            ]
            
            # Items to explicitly exclude (containers, not food)
            exclude_keywords = [
                'container', 'storage', 'shelf', 'shelving', 'basket', 'bin', 'rack',
                'cabinet', 'cupboard', 'pantry', 'kitchen', 'room', 'wall', 'door',
                'bag', 'plastic', 'glass', 'metal', 'wood', 'material', 'product',
                'package', 'packaging', 'wrapper', 'label', 'brand', 'box', 'carton',
                'bottle', 'jar', 'can', 'tin', 'aluminum', 'cardboard'
            ]
            
            # Check if this is an actual food item
            description_lower = label.description.lower()
            
            # First check if it should be excluded
            is_excluded = any(exclude_word in description_lower for exclude_word in exclude_keywords)
            
            # Then check if it's actual food
            is_actual_food = any(food_word in description_lower for food_word in actual_food_keywords)
            
            # Only add to food items if it's actual food and not excluded
            if is_actual_food and not is_excluded:
                food_related_labels.append(label_info)
            elif any(keyword in description_lower for keyword in ['shelf', 'container', 'basket', 'storage']):
                container_labels.append(label_info)
                container_labels.append(label_info)
        
        analysis_results["food_items"] = food_related_labels
        
        # 2. Object Detection - locates and identifies objects
        objects_response = client.object_localization(image=image)
        objects = objects_response.localized_object_annotations
        
        for obj in objects:
            object_info = {
                "name": obj.name,
                "confidence": obj.score,
                "bounding_box": {
                    "vertices": [(vertex.x, vertex.y) for vertex in obj.bounding_poly.normalized_vertices]
                }
            }
            analysis_results["objects"].append(object_info)
        
        # 3. Text Detection - reads any text in the image (labels, signs, etc.)
        text_response = client.text_detection(image=image)
        texts = text_response.text_annotations
        
        if texts:
            # First text annotation contains the full detected text
            full_text = texts[0].description if texts else ""
            analysis_results["text"] = full_text.split('\n') if full_text else []
        
        # 4. Estimate fullness based on detected objects and labels
        analysis_results["fullness_estimate"] = estimate_pantry_fullness(analysis_results)
        
        # 5. Calculate organization score
        analysis_results["organization_score"] = calculate_organization_score(analysis_results)
        
        return analysis_results
        
    except Exception as e:
        return {"error": f"Vision API analysis failed: {str(e)}"}


def estimate_pantry_fullness(analysis_results):
    """
    Estimate pantry fullness percentage based on Vision API results
    This is a heuristic approach that can be improved with machine learning
    """
    try:
        food_items = analysis_results.get("food_items", [])
        objects = analysis_results.get("objects", [])
        labels = analysis_results.get("labels", [])
        
        # Count different types of detected items
        food_count = len(food_items)  # Only actual food items, not containers
        total_objects = len(objects)
        
        # Look for shelf/container indicators
        container_indicators = 0
        empty_indicators = 0
        full_indicators = 0
        
        for label in labels:
            desc_lower = label["description"].lower()
            confidence = label["confidence"]
            
            # Weighted scoring based on confidence
            weight = confidence
            
            if any(word in desc_lower for word in ["shelf", "shelving", "storage", "container", "cupboard"]):
                container_indicators += weight
            elif any(word in desc_lower for word in ["empty", "bare", "vacant", "sparse"]):
                empty_indicators += weight * 2  # Empty indicators more important
            elif any(word in desc_lower for word in ["full", "packed", "stocked", "abundant", "plenty"]):
                full_indicators += weight * 2
        
        # Base fullness on actual food item count (primary factor)
        # This now only counts real food, not containers or packaging
        if food_count == 0:
            base_fullness = 0
        elif food_count <= 1:
            base_fullness = 10
        elif food_count <= 3:
            base_fullness = 25
        elif food_count <= 6:
            base_fullness = 45
        elif food_count <= 10:
            base_fullness = 65
        elif food_count <= 15:
            base_fullness = 85
        else:
            base_fullness = 95
        
        # Adjust based on contextual indicators
        if empty_indicators > 0.3:  # Strong empty indicators
            base_fullness = max(0, base_fullness - 30)
        elif full_indicators > 0.3:  # Strong full indicators
            base_fullness = min(100, base_fullness + 20)
        
        # Ensure reasonable bounds
        estimated_fullness = max(0, min(100, base_fullness))
        
        return int(estimated_fullness)
            
    except Exception as e:
        print(f"Error estimating fullness: {e}")
        return None


def calculate_organization_score(analysis_results):
    """
    Calculate how well-organized the pantry appears to be
    Returns a score from 0-100 based on various visual indicators
    """
    try:
        objects = analysis_results.get("objects", [])
        labels = analysis_results.get("labels", [])
        
        organization_score = 0
        max_score = 100
        
        # Check for organization-related labels
        organization_keywords = {
            'shelf': 25, 'shelving': 25, 'container': 20, 'basket': 15, 
            'organized': 30, 'neat': 25, 'tidy': 25, 'storage': 20,
            'box': 10, 'bin': 15, 'rack': 20, 'cupboard': 15
        }
        
        disorganization_keywords = {
            'messy': -20, 'cluttered': -15, 'scattered': -10, 'chaotic': -25
        }
        
        # Analyze labels for organization indicators
        for label in labels:
            desc_lower = label["description"].lower()
            confidence = label["confidence"]
            
            for keyword, score_value in organization_keywords.items():
                if keyword in desc_lower:
                    organization_score += score_value * confidence
                    
            for keyword, score_value in disorganization_keywords.items():
                if keyword in desc_lower:
                    organization_score += score_value * confidence
        
        # Analyze object distribution (more evenly distributed = better organized)
        if len(objects) > 1:
            # Calculate if objects are well-distributed (simple heuristic)
            # More objects with similar confidence levels suggest better organization
            confidences = [obj["confidence"] for obj in objects]
            if confidences:
                confidence_variance = sum((c - sum(confidences)/len(confidences))**2 for c in confidences) / len(confidences)
                # Lower variance = more consistent detection = better organization
                if confidence_variance < 0.1:
                    organization_score += 15
        
        # Bonus for having multiple containers/storage solutions
        container_objects = [obj for obj in objects if any(word in obj["name"].lower() 
                           for word in ['container', 'box', 'basket', 'shelf'])]
        organization_score += min(20, len(container_objects) * 5)
        
        # Normalize and cap the score
        final_score = max(0, min(max_score, organization_score))
        
        return round(final_score, 1)
        
    except Exception as e:
        print(f"Error calculating organization score: {e}")
        return None


def calculate_pantry_analytics(location):
    """
    Calculate comprehensive analytics for a pantry location
    Returns analytics data for charts and insights
    """
    try:
        reports = Report.query.filter_by(location_id=location.id).order_by(Report.time.asc()).all()
        
        if len(reports) < 2:
            return None  # Need at least 2 reports for meaningful analytics
        
        analytics = {
            'total_reports': len(reports),
            'date_range': {
                'start': reports[0].time,
                'end': reports[-1].time,
                'days': (reports[-1].time - reports[0].time).days + 1
            },
            'fullness_stats': {},
            'trends': {},
            'patterns': {},
            'ai_insights': {},
            'chart_data': {}
        }
        
        # Calculate fullness statistics
        fullness_values = [r.pantry_fullness for r in reports]
        analytics['fullness_stats'] = {
            'average': round(sum(fullness_values) / len(fullness_values), 1),
            'minimum': min(fullness_values),
            'maximum': max(fullness_values),
            'current': reports[-1].pantry_fullness,
            'previous': reports[-2].pantry_fullness if len(reports) > 1 else None
        }
        
        # Calculate trends
        recent_reports = reports[-5:] if len(reports) >= 5 else reports
        recent_fullness = [r.pantry_fullness for r in recent_reports]
        
        if len(recent_fullness) >= 2:
            trend_direction = "stable"
            recent_avg = sum(recent_fullness) / len(recent_fullness)
            older_avg = sum(fullness_values[:-5]) / max(1, len(fullness_values[:-5])) if len(fullness_values) > 5 else recent_avg
            
            difference = recent_avg - older_avg
            if difference > 10:
                trend_direction = "improving"
            elif difference < -10:
                trend_direction = "declining"
        else:
            trend_direction = "insufficient_data"
        
        analytics['trends'] = {
            'direction': trend_direction,
            'recent_average': round(sum(recent_fullness) / len(recent_fullness), 1) if recent_fullness else 0,
            'change_from_previous': analytics['fullness_stats']['current'] - analytics['fullness_stats']['previous'] if analytics['fullness_stats']['previous'] else 0
        }
        
        # Calculate usage patterns
        from collections import defaultdict
        import calendar
        
        # Group by day of week
        day_counts = defaultdict(int)
        day_fullness = defaultdict(list)
        
        for report in reports:
            day_name = calendar.day_name[report.time.weekday()]
            day_counts[day_name] += 1
            day_fullness[day_name].append(report.pantry_fullness)
        
        # Find most/least active days
        most_active_day = max(day_counts, key=day_counts.get) if day_counts else None
        least_active_day = min(day_counts, key=day_counts.get) if day_counts else None
        
        # Calculate empty/critical periods
        empty_reports = [r for r in reports if r.pantry_fullness <= 33]
        critical_reports = [r for r in reports if r.pantry_fullness <= 10]
        
        analytics['patterns'] = {
            'most_active_day': most_active_day,
            'least_active_day': least_active_day,
            'empty_periods': len(empty_reports),
            'critical_periods': len(critical_reports),
            'empty_percentage': round((len(empty_reports) / len(reports)) * 100, 1),
            'day_averages': {day: round(sum(fullness) / len(fullness), 1) for day, fullness in day_fullness.items()}
        }
        
        # AI insights (if available)
        ai_reports = [r for r in reports if r.get_vision_analysis()]
        if ai_reports:
            all_detected_items = []
            ai_fullness_estimates = []
            
            for report in ai_reports:
                detected_items = report.get_detected_food_items()
                if detected_items:
                    all_detected_items.extend(detected_items)
                
                ai_fullness = report.get_ai_fullness_estimate()
                if ai_fullness is not None:
                    ai_fullness_estimates.append(ai_fullness)
            
            # Count most common food items
            from collections import Counter
            food_item_counts = Counter(all_detected_items)
            
            analytics['ai_insights'] = {
                'total_ai_reports': len(ai_reports),
                'most_common_items': food_item_counts.most_common(5),
                'average_ai_fullness': round(sum(ai_fullness_estimates) / len(ai_fullness_estimates), 1) if ai_fullness_estimates else None,
                'ai_coverage_percentage': round((len(ai_reports) / len(reports)) * 100, 1)
            }
        
        # Prepare chart data
        chart_reports = reports[-30:] if len(reports) > 30 else reports  # Last 30 reports or all
        analytics['chart_data'] = {
            'dates': [r.time.strftime('%Y-%m-%d') for r in chart_reports],
            'fullness_values': [r.pantry_fullness for r in chart_reports],
            'ai_fullness_values': [r.get_ai_fullness_estimate() or 0 for r in chart_reports if r.get_vision_analysis()],
            'report_count_by_month': {},
            'fullness_distribution': {'empty': 0, 'low': 0, 'medium': 0, 'high': 0, 'full': 0}
        }
        
        # Calculate fullness distribution
        for fullness in fullness_values:
            if fullness <= 10:
                analytics['chart_data']['fullness_distribution']['empty'] += 1
            elif fullness <= 33:
                analytics['chart_data']['fullness_distribution']['low'] += 1
            elif fullness <= 66:
                analytics['chart_data']['fullness_distribution']['medium'] += 1
            elif fullness <= 90:
                analytics['chart_data']['fullness_distribution']['high'] += 1
            else:
                analytics['chart_data']['fullness_distribution']['full'] += 1
        
        # Add advanced insights
        analytics['insights'] = generate_pantry_insights(analytics, reports)
        
        return analytics
        
    except Exception as e:
        print(f"Error calculating analytics: {e}")
        return None


def generate_pantry_insights(analytics, reports):
    """
    Generate human-readable insights and recommendations based on analytics
    """
    insights = {
        'summary': [],
        'recommendations': [],
        'alerts': []
    }
    
    try:
        # Performance insights
        avg_fullness = analytics['fullness_stats']['average']
        empty_percentage = analytics['patterns']['empty_percentage']
        
        if avg_fullness >= 70:
            insights['summary'].append("This pantry is consistently well-stocked!")
        elif avg_fullness >= 50:
            insights['summary'].append("This pantry maintains moderate stock levels.")
        elif avg_fullness >= 30:
            insights['summary'].append("This pantry often runs low on items.")
        else:
            insights['summary'].append("This pantry frequently needs restocking.")
        
        # Trend insights
        if analytics['trends']['direction'] == 'improving':
            insights['summary'].append("Recent trend shows improving stock levels.")
        elif analytics['trends']['direction'] == 'declining':
            insights['summary'].append("Recent trend shows declining stock levels.")
        
        # Activity insights
        if analytics['total_reports'] >= 20:
            insights['summary'].append("This is an actively monitored pantry.")
        elif analytics['total_reports'] >= 10:
            insights['summary'].append("This pantry has regular monitoring.")
        else:
            insights['summary'].append("This pantry could benefit from more frequent monitoring.")
        
        # Recommendations
        if empty_percentage > 40:
            insights['recommendations'].append("Consider increasing donation drives - this pantry is empty 40%+ of the time.")
        
        if analytics['trends']['direction'] == 'declining':
            insights['recommendations'].append("Recent declining trend detected - may need immediate attention.")
        
        if analytics['total_reports'] < 10:
            insights['recommendations'].append("Encourage more community members to report status for better tracking.")
        
        # AI insights recommendations
        if analytics.get('ai_insights') and analytics['ai_insights']['ai_coverage_percentage'] < 50:
            insights['recommendations'].append("Upload photos with reports to get AI-powered food item detection.")
        
        # Alerts
        if analytics['fullness_stats']['current'] <= 10:
            insights['alerts'].append("URGENT: Pantry is currently critically low!")
        elif analytics['fullness_stats']['current'] <= 33:
            insights['alerts'].append("WARNING: Pantry is currently low on items.")
        
        if analytics['patterns']['critical_periods'] > 3:
            insights['alerts'].append(f"This pantry has been critically low {analytics['patterns']['critical_periods']} times.")
        
        return insights
        
    except Exception as e:
        print(f"Error generating insights: {e}")
        return insights


# Takes a report and location as arguments and sends notification emails for that location
def send_notification_emails(location, report, image_data=None):
    recipients = [n.user.email for n in location.notifications] 
    if recipients:
        subject = f"{location.name} is Empty!"
        message = f"The Little Free Pantry located at {location.address}, {location.city}, {location.state} is currently empty.<br>"
        message += "Can you help restock it?<br>"
        if report.description:
            message += f"Description: {report.description}<br>"
        if report.photo:
            message += "New pantry photo available on website!<br>"
        message += f"View more details: <a href='{url_for('views.location', location_id=location.id, _external=True)}''>{url_for('views.location', location_id=location.id, _external=True)}</a>"


        html = f"""
            <p>{message}</p>
            """
        
        send_email(recipients, subject, html)

        # TODO - show photo in email
        # if report.photo:
        #     with Image.open(os.path.join(current_app.config['UPLOAD_FOLDER'], str(report.location_id), report.photo)) as img:
        #         # Transpose image
        #         img = ImageOps.exif_transpose(img)
        #         img.thumbnail((800, 800))  # Resize 
        #         # If image has an alpha channel, convert to RGB
        #         if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        #             img = img.convert('RGB')
        #         buffer = io.BytesIO()
        #         img.save(buffer, format="JPEG", optimize=True, quality=85)
        #         img_data = base64.b64encode(buffer.getvalue()).decode()

        #     filename = f"{uuid.uuid4().hex}.jpg"
        #     html += f'<img src="data:image/jpeg;base64,{img_data}" alt="Pantry Photo" style="max-width: 100%; height: auto; image-orientation: from-image;">'  # Force upright display
            
        # with mail.connect() as conn:
        #     for recipient in recipients:
        #         msg = Message(subject, sender='info.reportthatpantry@gmail.com', recipients=[recipient])
        #         msg.html = html
        #         conn.send(msg)



# List of US states and abbreviations
us_states = {
        "Alabama": "AL",
        "Alaska": "AK",
        "Arizona": "AZ",
        "Arkansas": "AR",
        "California": "CA",
        "Colorado": "CO",
        "Connecticut": "CT",
        "Delaware": "DE",
        "Florida": "FL",
        "Georgia": "GA",
        "Hawaii": "HI",
        "Idaho": "ID",
        "Illinois": "IL",
        "Indiana": "IN",
        "Iowa": "IA",
        "Kansas": "KS",
        "Kentucky": "KY",
        "Louisiana": "LA",
        "Maine": "ME",
        "Maryland": "MD",
        "Massachusetts": "MA",
        "Michigan": "MI",
        "Minnesota": "MN",
        "Mississippi": "MS",
        "Missouri": "MO",
        "Montana": "MT",
        "Nebraska": "NE",
        "Nevada": "NV",
        "New Hampshire": "NH",
        "New Jersey": "NJ",
        "New Mexico": "NM",
        "New York": "NY",
        "North Carolina": "NC",
        "North Dakota": "ND",
        "Ohio": "OH",
        "Oklahoma": "OK",
        "Oregon": "OR",
        "Pennsylvania": "PA",
        "Rhode Island": "RI",
        "South Carolina": "SC",
        "South Dakota": "SD",
        "Tennessee": "TN",
        "Texas": "TX",
        "Utah": "UT",
        "Vermont": "VT",
        "Virginia": "VA",
        "Washington": "WA",
        "West Virginia": "WV",
        "Wisconsin": "WI",
        "Wyoming": "WY"
    }


@views.route('/', methods=['GET', 'POST'])
@views.route('/index')
def home(id=0):
    # # queries all of the locations
    locations = Location.query.all()

    return render_template("index.html", user=current_user, title="Home")


@views.route('/location/<int:location_id>')
def location(location_id):
    # Unauthenticated user has no subscribed locations
    subscribed_locations = None
    # Eager load reports for the location
    location = Location.query.options(joinedload(Location.reports)).get_or_404(location_id)

    # Get user's subscribed locations if authenticated
    if current_user.is_authenticated:
            subscribed_locations = [notification.location_id for notification in current_user.notifications]
            print(subscribed_locations)

    # Check if user can edit this location
    can_edit = current_user.is_authenticated and location.user_id == current_user.id
    print("pantry reports: ", location.reports)
    print("pantry reports type: ", type(location.reports))
    # order the location.reports by time
    location.reports = sorted(location.reports, key=lambda report: report.id, reverse=True)  # Descending order
    # Get most recent report
    latest_report = location.reports[0] if location.reports else None
    
    # Calculate analytics for this pantry
    analytics = calculate_pantry_analytics(location)
    
    return render_template("pantry.html", 
                         user=current_user, 
                         pantry=location, 
                         latest_report=latest_report, 
                         subscribed_locations=subscribed_locations, 
                         can_edit=can_edit, 
                         current_app=current_app, 
                         analytics=analytics,
                         title="Pantry Details")


# # Determines if file submitted is allowed
# def allowed_file(filename):
#     return '.' in filename and \
#            filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}


# Route for adding a location
@views.route('/location/add', methods=['GET', 'POST'])
@views.route('/location/add/', methods=['GET', 'POST'])
@login_required
# @views.route('/add/<int:id>', methods=['GET', 'POST'])
def add_location():
    # handles form submissions
    if request.method == 'POST':
        # Get form details
        name = request.form.get('name')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        zip = request.form.get('zipCode')
        description = request.form.get('description')
        contact_info = request.form.get('contactInfo')
        photo = request.files.get('locationPhoto')  # Get the uploaded file

        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')


        # checks if the location exists
        location = Location.query.filter_by(address=address).first()
        if location:
            flash('Address already exists.', category='error')
            return render_template()
        # print(zip.isnumeric())
        # Validate and convert zip code (or set to None if invalid/empty)
        if zip.isdigit():
            zip = int(zip)
        else:
            zip = None  # Set zip to None if invalid or empty
        # Add location to database
        new_location = Location(
            address=address, 
            name=name, 
            city=city, 
            state=state, 
            zip=zip,
            user_id=current_user.id,
            description=description,
            contact_info=contact_info,
            latitude=latitude,
            longitude=longitude
        )
        db.session.add(new_location)
        db.session.commit()

        # Handle photo upload to S3
        s3_key = upload_photo_to_s3(photo, new_location.id)
        if s3_key:
            new_location.photo = s3_key
        db.session.commit()

        # # Check if photo exists and file type is allowed
        # if photo and allowed_file(photo.filename):
        #     filename = secure_filename(photo.filename)
        #     # Create or access location file directory
        #     upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(new_location.id))
        #     os.makedirs(upload_dir, exist_ok=True)
        #     save_path = os.path.join(upload_dir, filename)
        #     photo.save(save_path)
        #     # Update database value
        #     new_location.photo = filename
        #     db.session.commit()

        # Create intial report for location
        new_report = Report(
            pantry_fullness=100,
            time=datetime.now(timezone.utc),  # Use timezone-aware datetime in UTC
            location_id=new_location.id
            )
        db.session.add(new_report)
        db.session.commit()

        # Redirect user to poster page
        return redirect(url_for("views.poster", id=new_location.id, isNew1=1))

    return render_template("location.html", api_key=os.environ.get('GOOGLE_MAPS_API_KEY'), user=current_user, editing=False, title="Add Location", states=us_states)


# Edit Location
@views.route('/location/edit/<int:location_id>', methods=['GET', 'POST'])
@views.route('/location/edit/<int:location_id>/', methods=['GET', 'POST'])
@login_required  # Ensure the user is logged in
def edit_location(location_id):
    location = Location.query.get_or_404(location_id)

    # Check if the user owns this location
    if location.user_id != current_user.id:
        flash("You do not have permission to edit this location.", category='error')
        return redirect(url_for('views.map'))

    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        zip_code = request.form.get('zipCode')
        description = request.form.get('description')
        photo = request.files.get('locationPhoto')
        contact_info = request.form.get('contactInfo')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')

        # Validate and convert zip code (or set to None if invalid/empty)
        if zip_code.isdigit():
            zip_code = int(zip_code)
        else:
            zip_code = None

        # Basic input validation (add more as needed)
        if not all([name, latitude, longitude]):
            flash('All fields are required.', category='error')
        else:
            # Update location details
            location.name = name
            location.address = address
            location.city = city
            location.state = state
            location.zip = zip_code
            location.description = description
            location.contact_info = contact_info
            location.latitude = latitude
            location.longitude = longitude
            

            # Handle photo update (if a new photo is uploaded)
            if photo and allowed_file(photo.filename):
                # Delete old photo if it exists
                if location.photo:
                    s3_key = location.photo
                    delete_photo_from_s3(s3_key)
                # Upload new photo
                s3_key = upload_photo_to_s3(photo, location_id)
                if s3_key:
                    location.photo = s3_key
            # Commit changes
            db.session.commit()
            flash('Location updated successfully!', category='success')
            return redirect(url_for('views.location', location_id=location.id))

    return render_template("location.html", api_key=os.environ.get('GOOGLE_MAPS_API_KEY'), current_app=current_app, user=current_user, location=location, editing=True, title="Edit Location", states=us_states)


@views.route('/delete-location', methods=['POST'])
def delete_location():
    print("delete-location")
    location = json.loads(request.data)
    locationId = location['locationId']
    location = Location.query.get(locationId)
    if location:
        #if note.user_id == current_user.id:
        db.session.delete(location)
        db.session.commit()
        flash("Location Deleted.", category="success")

    return jsonify({})



# Report on status of given location
@views.route('/report/<int:id>', methods=['GET', 'POST'])
def report(id):
    # Get current location
    location = Location.query.get(id)
    if not location:
        flash("Location does not exist.", category='error')
        return redirect(url_for('views.map'))

    if request.method == 'POST':
        # Get fullness level from the form
        pantry_fullness = request.form.get('pantryFullness')
        # Get the description and photo
        description = request.form.get('pantryDescription')
        photo = request.files.get('pantryPhoto')
    
        # Analyze photo with Google Vision API if provided
        vision_analysis = None
        suggested_fullness = None
        
        if photo:
            # Read photo content for Vision API analysis
            photo.seek(0)  # Reset file pointer
            photo_content = photo.read()
            photo.seek(0)  # Reset again for S3 upload
            
            # Perform Vision API analysis
            vision_analysis = analyze_pantry_image(photo_content)
            
            # Get AI-suggested fullness if analysis was successful
            if vision_analysis and "fullness_estimate" in vision_analysis:
                suggested_fullness = vision_analysis["fullness_estimate"]
        
        # Create Report object
        new_report = Report(
            pantry_fullness=pantry_fullness,
            time=datetime.now(timezone.utc),  # Use timezone-aware datetime in UTC
            location_id=location.id,
            description=description,
            user_id=current_user.id if current_user.is_authenticated else None  # Associate with logged-in user if possible
        )
        
        # Upload photo to Amazon S3, if provided
        s3_key = upload_photo_to_s3(photo, location.id)
        # Store relative path in database
        if s3_key:
            new_report.photo = s3_key
        
        # Store Vision API analysis results as JSON in the new field
        if vision_analysis and "error" not in vision_analysis:
            import json
            new_report.vision_analysis = json.dumps(vision_analysis)
            
            # Also add some key findings to description for backward compatibility
            if vision_analysis.get("food_items"):
                food_items_text = ", ".join([item["description"] for item in vision_analysis["food_items"][:5]])
                if new_report.description:
                    new_report.description += f"\n\nAI detected items: {food_items_text}"
                else:
                    new_report.description = f"AI detected items: {food_items_text}"
            
            # Add suggested fullness comparison if available
            if suggested_fullness is not None:
                fullness_diff = abs(int(pantry_fullness) - suggested_fullness)
                if fullness_diff > 20:  # Significant difference
                    suggestion_text = f"\n\nAI suggested fullness: {suggested_fullness}%"
                    new_report.description = (new_report.description or "") + suggestion_text
        elif vision_analysis and "error" in vision_analysis:
            # Log the error but don't fail the report submission
            print(f"Vision API analysis error: {vision_analysis['error']}")
            new_report.vision_analysis = json.dumps({"error": vision_analysis["error"]})
        
        db.session.add(new_report)
        db.session.commit()


        # TODO - send image in email
        # if new_report.photo:
        #     with open(os.path.join(current_app.config['UPLOAD_FOLDER'], str(location.id), new_report.photo), "rb") as f:
        #         image_data = base64.b64encode(f.read()).decode()  # Encode image to base64
        # Send email notification if the pantry is empty
        if new_report.pantry_fullness <= 33:  # Check for empty status
            recipients = [n.user.email for n in location.notifications] 
            if recipients:
                subject = f"{location.name} is Empty!"
                message = f"The Little Free Pantry located at {location.address}, {location.city}, {location.state} is currently empty.<br>"
                message += "Can you help restock it?<br>"
                if new_report.description:
                    message += f"Description: {new_report.description}<br>"
                if new_report.photo:
                    message += "New pantry photo available on website!<br>"
                message += f"View more details: <a href='{url_for('views.location', location_id=location.id, _external=True)}''>{url_for('views.location', location_id=location.id, _external=True)}</a>"
                html = f"""
                    <p>{message}</p>
                    """
                send_email(recipients, subject, html)
            # send_notification_emails(location, new_report, image_data)

        flash("Thank you for your feedback!", category='success')
        return redirect(url_for('views.location', location_id=id))

    return render_template("report.html", user=current_user, title="Report", location_id=id) 



# Route to serve images from S3
@views.route('/uploads/<filename>')
def uploaded_file(filename):
    s3 = boto3.client(
        's3',
        aws_access_key_id=current_app.config['S3_KEY'],
        aws_secret_access_key=current_app.config['S3_SECRET']
    )
    url = s3.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': current_app.config['S3_BUCKET'],
            'Key': filename
        },
        ExpiresIn=3600
    )  # URL valid for 1 hour
    return redirect(url, code=302)


@views.route('/status', methods=['GET', 'POST'])
def status():
    # Get every report for every location, ordered by report time
    locations = db.session.query(Location).options(joinedload(Location.reports)).all()

    # sort reports in time ascending order
    for location in locations:
        location.reports = sorted(location.reports, key=lambda report: report.id, reverse=False)  # Ascending order

    # Calculate nationwide analytics and insights
    nationwide_analytics = calculate_nationwide_analytics()
    nationwide_insights = generate_nationwide_insights(nationwide_analytics) if nationwide_analytics else []

    # Safely access subscribed_locations only if the user is authenticated
    subscribed_locations = [notification.location_id for notification in current_user.notifications] if current_user.is_authenticated else []
    
    return render_template("status.html", 
                         user=current_user, 
                         title="Analytics Dashboard", 
                         locations=locations, 
                         subscribed_locations=subscribed_locations,
                         nationwide_analytics=nationwide_analytics,
                         nationwide_insights=nationwide_insights)


# Returns all locations in JSON format (for status page)
@views.route('/get_locations')
def get_locations():
    locations = db.session.query(Location).options(joinedload(Location.reports)).all()
    location_data = []
    for location in locations:
        # Get latest report
        latest_report = location.reports[-1] if location.reports else None
        data = {
            'id': location.id,  # Use location.id instead of location.location_id
            'location': f"{location.name}<br>{location.address}, {location.city}, {location.state}",
            'time': latest_report.time.timestamp() if latest_report else None
        }
        location_data.append(data)
    print(jsonify(location_data))
    return jsonify(location_data)


@views.route('/logs/<int:id>')
@views.route('/logs/<int:id>/')
def logs(id):
    count = 0
    # Get report logs for given location
    logs = db.session.query(Report.time, Report.id, Report.pantry_fullness).filter(Report.location_id == id).order_by(Report.time.desc())
    for log in logs:
        count += 1
    return render_template("logs.html", user=current_user, title="Logs", logs=logs, count=count)

@views.route('/poster<int:isNew1>/<int:id>')
@views.route('/poster/<int:isNew1>/<int:id>')
def poster(isNew1, id):
    location = db.session.query(Location.name.label("location_name")).filter(Location.id == id)[0][0]
    return render_template("poster.html", user=current_user, title="Poster", pantrynumber = id, isNew = isNew1, name = location)

@views.route('/setup')
@views.route('/setup/')
def setup():
    return render_template("setup.html", user=current_user, title="Setup")



# Handles changes to subscription preferences on status page
@views.route('/subscribe', methods=['POST'])
@login_required
def subscribe():
    location_id = request.form.get('location_id')

    if location_id:
        location_id = int(location_id)
        # Check if the user is already subscribed
        existing_subscription = Notification.query.filter_by(user_id=current_user.id, location_id=location_id).first()
        
        if existing_subscription:
            # Unsubscribe
            db.session.delete(existing_subscription)
            db.session.commit()
            return jsonify({'status': 'unsubscribed', 'message': 'Unsubscribed successfully'})
        else:
            # Subscribe
            new_subscription = Notification(user_id=current_user.id, location_id=location_id)
            db.session.add(new_subscription)
            db.session.commit()
            return jsonify({'status': 'subscribed', 'message': 'Subscribed successfully'})

    return jsonify({'status': 'error', 'message': 'Invalid location_id'})


# Handles changes to subscription preferances on pantry homepage
@views.route('/location/subscribe/<int:location_id>', methods=['POST'])
@login_required
def subscribe_location(location_id):
    print("page accessed")
    # Check if location exists
    location = Location.query.get(location_id)
    print(location)
    if location:
        location_id = int(location_id)
        # Check if the user is already subscribed and toggle the subscription
        existing_subscription = Notification.query.filter_by(user_id=current_user.id, location_id=location_id).first()
        print("existing_subscription", existing_subscription)
        if existing_subscription:
            # Unsubscribe
            db.session.delete(existing_subscription)
            db.session.commit()
            flash('You have successfully unsubscribed from this pantry.', 'success')
        else:
            # Subscribe
            new_subscription = Notification(user_id=current_user.id, location_id=location_id)
            db.session.add(new_subscription)
            db.session.commit()
            flash('You have successfully subscribed to this pantry.', 'success')
    else:
        flash("Location does not exist", category='error')
        return redirect(url_for('views.location', location_id=location_id))

    return redirect(url_for('views.location', location_id=location_id))  # Redirect back to the location page


from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="report_that_pantry") 

# Route to get pantry data for the map
@views.route('/get_pantry_data')
def get_pantry_data():
    locations = Location.query.all()
    pantry_data = []
    for location in locations:
        # Geocode the address if coordinates are missing (you might have already done this)
        if not location.latitude or not location.longitude:
            address = f"{location.address}, {location.city}, {location.state} {location.zip}"
            try:
                geocode_result = geolocator.geocode(address)
                print("geocode_result", geocode_result)
                if geocode_result:
                    location.latitude = geocode_result.latitude
                    location.longitude = geocode_result.longitude
                    db.session.commit() 
            except Exception as e:
                print(f"Error geocoding address {address}: {e}")
                continue 
            
        # Get the most recent status update for this location
        latest_report = Report.query.filter_by(location_id=location.id)\
                                    .order_by(desc(Report.time)).first()
        
        # Determine status and marker color based on fullness
        fullness = latest_report.pantry_fullness if latest_report else None
        
        if fullness is not None:
            if fullness >= 75:
                status = 'full'
                marker_color = 'green'
            elif fullness >= 25:
                status = 'low'
                marker_color = 'yellow'
            else:
                status = 'empty'
                marker_color = 'red'
        else:
            status = 'unknown'
            marker_color = 'gray'

        pantry_data.append({
            'id': location.id,
            'name': location.name,
            'latitude': location.latitude,
            'longitude': location.longitude,
            'address': f"{location.address}, {location.city}, {location.state} {location.zip}",
            'description': location.description, 
            'contact_info': location.contact_info, 
            'fullness': fullness,
            'status': status,
            'marker_color': marker_color,
            'lastUpdated': latest_report.time.isoformat() if latest_report else None,
            # ... other relevant data
        })

    return jsonify(pantry_data)


@views.route('/map')
def map():
    locations = Location.query.all()
    pantry_data = []

    for location in locations:
        # Geocode if coordinates are missing
        if not location.latitude or not location.longitude:
            address = f"{location.address}, {location.city}, {location.state} {location.zip}"
            try:
                geocode_result = geolocator.geocode(address)
                if geocode_result:
                    location.latitude = geocode_result.latitude
                    location.longitude = geocode_result.longitude
                    db.session.commit()
            except Exception as e:
                print(f"Error geocoding address {address}: {e}")
                continue

        pantry_data.append({
            'id': location.id,
            'name': location.name,
            'latitude': location.latitude,
            'longitude': location.longitude,
            'address': location.address,
            'description': location.description, 
            'contact_info': location.contact_info, 
            # ... other relevant data
        })

    return render_template('map.html', 
                           pantries=pantry_data,
                           map_center=[44.0521, 123.0868],  # Adjust as needed
                           zoom_start=10,
                           api_key=os.environ.get('GOOGLE_MAPS_API_KEY'),
                           title='Status', user=current_user)


@views.route('/vision-demo', methods=['GET', 'POST'])
def vision_demo():
    """
    Demonstration route for testing Google Vision API capabilities
    Upload an image and see detailed analysis results
    """
    analysis_results = None
    error_message = None
    
    if request.method == 'POST':
        photo = request.files.get('demoPhoto')
        
        if photo and allowed_file(photo.filename):
            try:
                # Read photo content
                photo_content = photo.read()
                photo.seek(0)  # Reset file pointer
                
                # Perform comprehensive Vision API analysis
                analysis_results = analyze_pantry_image(photo_content)
                
                if "error" in analysis_results:
                    error_message = analysis_results["error"]
                    analysis_results = None
                    
            except Exception as e:
                error_message = f"Error processing image: {str(e)}"
        else:
            error_message = "Please upload a valid image file (PNG, JPG, JPEG, GIF)"
    
    return render_template("vision_demo.html", 
                         user=current_user, 
                         title="Vision API Demo",
                         analysis_results=analysis_results,
                         error_message=error_message)


@views.route('/api/analyze-image', methods=['POST'])
def api_analyze_image():
    """
    API endpoint for analyzing images with Vision API
    Returns JSON response with analysis results
    """
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    photo = request.files['image']
    
    if photo.filename == '':
        return jsonify({'error': 'No image file selected'}), 400
    
    if not allowed_file(photo.filename):
        return jsonify({'error': 'Invalid file type. Please upload PNG, JPG, JPEG, or GIF'}), 400
    
    try:
        # Read photo content
        photo_content = photo.read()
        
        # Perform Vision API analysis
        analysis_results = analyze_pantry_image(photo_content)
        
        return jsonify(analysis_results)
        
    except Exception as e:
        return jsonify({'error': f'Error processing image: {str(e)}'}), 500


@views.route('/api/analytics/<int:location_id>')
def api_analytics(location_id):
    """
    API endpoint to get analytics data for a location in JSON format
    """
    location = Location.query.get_or_404(location_id)
    analytics = calculate_pantry_analytics(location)
    
    if analytics:
        # Convert datetime objects to strings for JSON serialization
        analytics['date_range']['start'] = analytics['date_range']['start'].isoformat()
        analytics['date_range']['end'] = analytics['date_range']['end'].isoformat()
        
        return jsonify({
            'success': True,
            'location_id': location_id,
            'location_name': location.name,
            'analytics': analytics
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Insufficient data for analytics (need at least 2 reports)',
            'location_id': location_id,
            'location_name': location.name
        })


def calculate_nationwide_analytics():
    """
    Calculate analytics and trends across all pantries in the network
    """
    from datetime import datetime, timedelta
    from collections import defaultdict
    import statistics
    
    # Get all locations with their reports
    locations = db.session.query(Location).options(joinedload(Location.reports)).all()
    
    if not locations:
        return None
    
    # Filter out locations without reports
    active_locations = [loc for loc in locations if loc.reports]
    
    if len(active_locations) < 1:
        return None
    
    # Collect all reports for analysis
    all_reports = []
    for location in active_locations:
        all_reports.extend(location.reports)
    
    if len(all_reports) < 2:
        return None
    
    # Sort reports by time
    all_reports.sort(key=lambda r: r.time)
    
    # Time range analysis - with safe datetime handling
    try:
        start_date = normalize_datetime(all_reports[0].time)
        end_date = normalize_datetime(all_reports[-1].time)
        days_active = (end_date - start_date).days + 1
    except Exception as e:
        print(f"Error calculating date range: {e}")
        start_date = normalize_datetime(datetime.now(timezone.utc))
        end_date = start_date
        days_active = 1
    
    # Current status across all pantries
    current_reports = []
    for location in active_locations:
        if location.reports:
            current_reports.append(location.reports[-1])
    
    # Calculate current metrics
    current_fullness_values = [r.pantry_fullness for r in current_reports if r.pantry_fullness is not None]
    avg_current_fullness = statistics.mean(current_fullness_values) if current_fullness_values else 0
    
    # Count pantries by status
    empty_pantries = sum(1 for r in current_reports if r.pantry_fullness is not None and r.pantry_fullness <= 33)
    low_pantries = sum(1 for r in current_reports if r.pantry_fullness is not None and 33 < r.pantry_fullness <= 66)
    full_pantries = sum(1 for r in current_reports if r.pantry_fullness is not None and r.pantry_fullness > 66)
    
    # Historical trends - use timezone-aware datetime
    from datetime import timezone
    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(days=30)
    last_week_cutoff = now - timedelta(days=7)
    
    recent_reports = safe_datetime_filter(all_reports, recent_cutoff)
    last_week_reports = safe_datetime_filter(all_reports, last_week_cutoff)
    
    # Activity metrics
    total_reports = len(all_reports)
    reports_last_30_days = len(recent_reports)
    reports_last_7_days = len(last_week_reports)
    
    # Average reports per location
    avg_reports_per_location = total_reports / len(active_locations) if active_locations else 0
    
    # Time series data for charts (last 30 days) - safe datetime handling
    daily_data = defaultdict(list)
    for report in recent_reports:
        try:
            # Normalize the report time to handle timezone issues
            normalized_time = normalize_datetime(report.time)
            day_key = normalized_time.strftime('%Y-%m-%d')
            if report.pantry_fullness is not None:
                daily_data[day_key].append(report.pantry_fullness)
        except Exception as e:
            print(f"Error processing report {report.id} for chart data: {e}")
            continue
    
    # Calculate daily averages
    chart_data = []
    for day in sorted(daily_data.keys()):
        avg_fullness = statistics.mean(daily_data[day])
        chart_data.append({
            'date': day,
            'avg_fullness': round(avg_fullness, 1),
            'report_count': len(daily_data[day])
        })
    
    # State/regional breakdown
    state_stats = defaultdict(lambda: {'locations': 0, 'reports': 0, 'avg_fullness': 0, 'fullness_values': []})
    for location in active_locations:
        state = location.state
        state_stats[state]['locations'] += 1
        state_stats[state]['reports'] += len(location.reports)
        
        if location.reports:
            latest_fullness = location.reports[-1].pantry_fullness
            if latest_fullness is not None:
                state_stats[state]['fullness_values'].append(latest_fullness)
    
    # Calculate state averages
    for state_data in state_stats.values():
        if state_data['fullness_values']:
            state_data['avg_fullness'] = round(statistics.mean(state_data['fullness_values']), 1)
        del state_data['fullness_values']  # Remove raw data
    
    # Vision API analytics (if available)
    vision_reports = [r for r in all_reports if r.vision_analysis]
    food_items_detected = []
    ai_fullness_scores = []
    
    for report in vision_reports:
        try:
            analysis = report.get_vision_analysis()
            if analysis:
                if 'food_items' in analysis and analysis['food_items']:
                    # Extract food item descriptions from the dictionary objects
                    for food_item in analysis['food_items']:
                        if isinstance(food_item, dict) and 'description' in food_item:
                            food_items_detected.append(food_item['description'])
                        elif isinstance(food_item, str):
                            food_items_detected.append(food_item)
                if 'fullness_estimate' in analysis:
                    ai_fullness_scores.append(analysis['fullness_estimate'])
        except Exception as e:
            print(f"Error processing vision analysis for report: {e}")
            continue
    
    # Most common food items
    from collections import Counter
    common_foods = Counter(food_items_detected).most_common(10) if food_items_detected else []
    
    # Calculate trends (compare periods for more meaningful insights)
    two_weeks_ago = now - timedelta(days=14)
    one_week_ago = now - timedelta(days=7)
    
    # Get reports from different time periods
    last_week_reports = safe_datetime_filter(all_reports, one_week_ago)
    previous_week_reports = []
    last_month_reports = safe_datetime_filter(all_reports, recent_cutoff)
    
    # Get reports from week before last (for week-over-week comparison)
    for report in all_reports:
        try:
            normalized_time = normalize_datetime(report.time)
            normalized_two_weeks = normalize_datetime(two_weeks_ago)
            normalized_one_week = normalize_datetime(one_week_ago)
            
            if normalized_two_weeks <= normalized_time < normalized_one_week:
                previous_week_reports.append(report)
        except Exception as e:
            print(f"Error processing report {report.id} for weekly comparison: {e}")
            continue
    
    # Calculate empty vs full trends
    def count_empty_full(reports):
        empty = sum(1 for r in reports if r.pantry_fullness is not None and r.pantry_fullness <= 33)
        full = sum(1 for r in reports if r.pantry_fullness is not None and r.pantry_fullness > 66)
        return empty, full
    
    last_week_empty, last_week_full = count_empty_full(last_week_reports)
    prev_week_empty, prev_week_full = count_empty_full(previous_week_reports)
    
    # Calculate trends
    empty_trend = "stable"
    full_trend = "stable"
    
    if prev_week_empty > 0:
        empty_change = ((last_week_empty - prev_week_empty) / prev_week_empty) * 100
        if empty_change > 10:
            empty_trend = "increasing"
        elif empty_change < -10:
            empty_trend = "decreasing"
    
    if prev_week_full > 0:
        full_change = ((last_week_full - prev_week_full) / prev_week_full) * 100
        if full_change > 10:
            full_trend = "increasing"
        elif full_change < -10:
            full_trend = "decreasing"
    
    # Overall fullness trend
    old_fullness = [r.pantry_fullness for r in previous_week_reports if r.pantry_fullness is not None]
    new_fullness = [r.pantry_fullness for r in last_week_reports if r.pantry_fullness is not None]
    
    fullness_trend = None
    if old_fullness and new_fullness:
        old_avg = statistics.mean(old_fullness)
        new_avg = statistics.mean(new_fullness)
        fullness_trend = new_avg - old_avg
    
    return {
        'network_overview': {
            'total_locations': len(locations),
            'active_locations': len(active_locations),
            'total_reports': total_reports,
            'avg_reports_per_location': round(avg_reports_per_location, 1),
            'days_active': days_active,
            'reports_last_30_days': reports_last_30_days,
            'reports_last_7_days': reports_last_7_days
        },
        'current_status': {
            'avg_fullness': round(avg_current_fullness, 1),
            'empty_pantries': empty_pantries,
            'low_pantries': low_pantries,
            'full_pantries': full_pantries,
            'total_reporting': len(current_reports)
        },
        'trends': {
            'fullness_trend_weekly': round(fullness_trend, 1) if fullness_trend is not None else None,
            'empty_trend': empty_trend,
            'full_trend': full_trend,
            'last_week_empty': last_week_empty,
            'last_week_full': last_week_full,
            'prev_week_empty': prev_week_empty,
            'prev_week_full': prev_week_full,
            'community_engagement': 'high' if reports_last_7_days > reports_last_30_days / 3 else 'moderate' if reports_last_7_days > reports_last_30_days / 6 else 'low'
        },
        'chart_data': chart_data,
        'state_breakdown': dict(state_stats),
        'ai_insights': {
            'reports_with_ai': len(vision_reports),
            'common_foods': common_foods,
            'avg_ai_fullness': round(statistics.mean(ai_fullness_scores), 1) if ai_fullness_scores else None
        },
        'date_range': {
            'start': normalize_datetime(start_date),
            'end': normalize_datetime(end_date)
        }
    }


def generate_nationwide_insights(analytics):
    """
    Generate insights and recommendations based on nationwide analytics
    """
    if not analytics:
        return []
    
    insights = []
    
    # Network size insights
    network = analytics['network_overview']
    status = analytics['current_status']
    
    if network['total_locations'] >= 10:
        insights.append({
            'type': 'success',
            'title': 'Growing Network',
            'message': f"Your network has grown to {network['total_locations']} pantry locations!"
        })
    
    # Activity insights
    if network['reports_last_7_days'] > network['reports_last_30_days'] / 3:
        insights.append({
            'type': 'info',
            'title': 'High Activity',
            'message': f"Strong engagement with {network['reports_last_7_days']} reports in the last week."
        })
    elif network['reports_last_7_days'] < network['reports_last_30_days'] / 6:
        insights.append({
            'type': 'warning',
            'title': 'Low Activity',
            'message': "Consider engaging with your community to encourage more frequent reporting."
        })
    
    # Fullness insights
    empty_rate = (status['empty_pantries'] / status['total_reporting']) * 100 if status['total_reporting'] > 0 else 0
    
    if empty_rate > 50:
        insights.append({
            'type': 'danger',
            'title': 'High Empty Rate',
            'message': f"{empty_rate:.0f}% of pantries are running low. Consider organizing a restocking drive."
        })
    elif empty_rate < 20:
        insights.append({
            'type': 'success',
            'title': 'Well Stocked Network',
            'message': f"Great job! Only {empty_rate:.0f}% of pantries are running low."
        })
    
    # Trend insights
    trends = analytics['trends']
    if trends.get('fullness_trend_weekly') is not None:
        if trends['fullness_trend_weekly'] > 5:
            insights.append({
                'type': 'success',
                'title': 'Improving Trend',
                'message': f"Pantry fullness has improved by {trends['fullness_trend_weekly']:.1f}% over the last week."
            })
        elif trends['fullness_trend_weekly'] < -5:
            insights.append({
                'type': 'warning',
                'title': 'Declining Trend',
                'message': f"Pantry fullness has decreased by {abs(trends['fullness_trend_weekly']):.1f}% over the last week."
            })
    
    # AI insights
    ai = analytics['ai_insights']
    if ai['reports_with_ai'] > 0:
        coverage = (ai['reports_with_ai'] / network['total_reports']) * 100
        insights.append({
            'type': 'info',
            'title': 'AI Analysis Coverage',
            'message': f"AI analysis available for {coverage:.0f}% of reports, providing enhanced insights."
        })
    
    # Regional insights
    states = analytics['state_breakdown']
    if len(states) > 1:
        best_state = max(states.items(), key=lambda x: x[1]['avg_fullness']) if states else None
        if best_state and best_state[1]['avg_fullness'] > 0:
            insights.append({
                'type': 'info',
                'title': 'Regional Leader',
                'message': f"{best_state[0]} leads with {best_state[1]['avg_fullness']:.0f}% average fullness across {best_state[1]['locations']} locations."
            })
    
    return insights


@views.route('/api/nationwide-analytics')
def api_nationwide_analytics():
    """
    API endpoint to get nationwide analytics data in JSON format
    """
    analytics = calculate_nationwide_analytics()
    
    if analytics:
        # Convert datetime objects to strings for JSON serialization
        analytics['date_range']['start'] = analytics['date_range']['start'].isoformat()
        analytics['date_range']['end'] = analytics['date_range']['end'].isoformat()
        
        insights = generate_nationwide_insights(analytics)
        
        return jsonify({
            'success': True,
            'analytics': analytics,
            'insights': insights
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Insufficient data for nationwide analytics'
        })


def normalize_datetime(dt):
    """
    Normalize datetime to UTC timezone-aware datetime
    Handles both timezone-aware and timezone-naive datetime objects
    """
    from datetime import timezone
    
    if dt is None:
        return None
    
    # If datetime is timezone-naive, assume it's UTC
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    
    # If datetime is timezone-aware, convert to UTC
    return dt.astimezone(timezone.utc)


def safe_datetime_filter(reports, cutoff_datetime):
    """
    Safely filter reports by datetime, handling timezone issues
    """
    filtered_reports = []
    for report in reports:
        try:
            normalized_report_time = normalize_datetime(report.time)
            normalized_cutoff = normalize_datetime(cutoff_datetime)
            
            if normalized_report_time >= normalized_cutoff:
                filtered_reports.append(report)
        except Exception as e:
            # If there's an error with timezone conversion, skip this report
            print(f"Error comparing datetime for report {report.id}: {e}")
            continue
    
    return filtered_reports