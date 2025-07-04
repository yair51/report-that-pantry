from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for, current_app, send_from_directory, abort
from flask_login import login_required, current_user
from sqlalchemy.sql.expression import true
from sqlalchemy.orm import joinedload
from .models import Location, Report, Notification, User
from app.helpers import send_email, allowed_file, upload_photo_to_s3, delete_photo_from_s3, generate_qr_poster_pdf, get_state_full_name, convert_heic_to_jpeg, is_heic_file
from . import db, Message, mail
import json
from datetime import datetime, timezone, timedelta
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
import calendar
import numpy as np
from collections import defaultdict, Counter
import statistics
# Google Vision API imports
from google.cloud import vision
# Import our enhanced vision analysis
from .vision import analyze_pantry_image_hybrid

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
    Analyze pantry image using hybrid AI approach (Google Vision API + Gemini)
    Returns a dictionary with enhanced analysis results
    """
    return analyze_pantry_image_hybrid(image_content)


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
            'chart_data': {},
            'engagement': {},
            'restocking': {}
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
            food_item_counts = Counter(all_detected_items)
            
            analytics['ai_insights'] = {
                'total_ai_reports': len(ai_reports),
                'most_common_items': food_item_counts.most_common(5),
                'average_ai_fullness': round(sum(ai_fullness_estimates) / len(ai_fullness_estimates), 1) if ai_fullness_estimates else None,
                'ai_coverage_percentage': round((len(ai_reports) / len(reports)) * 100, 1)
            }
        
        # Prepare chart data - FIX: Use actual timestamps for proper time-based x-axis
        chart_reports = reports[-30:] if len(reports) > 30 else reports  # Last 30 reports or all
        
        # Generate proper time-based chart data
        chart_data_points = []
        for report in chart_reports:
            chart_data_points.append({
                'timestamp': report.time.isoformat(),
                'date': report.time.strftime('%Y-%m-%d'),
                'datetime': report.time.strftime('%Y-%m-%d %H:%M'),
                'fullness': report.pantry_fullness,
                'ai_fullness': report.get_ai_fullness_estimate()
            })
        
        analytics['chart_data'] = {
            'data_points': chart_data_points,
            'dates': [r.time.strftime('%Y-%m-%d') for r in chart_reports],
            'timestamps': [r.time.isoformat() for r in chart_reports],
            'fullness_values': [r.pantry_fullness for r in chart_reports],
            'ai_fullness_values': [r.get_ai_fullness_estimate() or 0 for r in chart_reports if r.get_vision_analysis()],
            'report_count_by_month': {},
            'fullness_distribution': {'empty': 0, 'low': 0, 'medium': 0, 'high': 0, 'full': 0}
        }
        
        # ENHANCED ANALYTICS - Time Period Trends
        from datetime import timedelta
        
        # Calculate weekly, monthly, and yearly trends
        weekly_trends = []
        monthly_trends = []
        yearly_trends = []
        
        # Group reports by time periods
        report_groups = {
            'weekly': defaultdict(list),
            'monthly': defaultdict(list),
            'yearly': defaultdict(list)
        }
        
        for report in reports:
            # Weekly grouping (Monday as start of week)
            week_start = report.time - timedelta(days=report.time.weekday())
            week_key = week_start.strftime('%Y-%m-%d')
            report_groups['weekly'][week_key].append(report)
            
            # Monthly grouping
            month_key = report.time.strftime('%Y-%m')
            report_groups['monthly'][month_key].append(report)
            
            # Yearly grouping
            year_key = report.time.strftime('%Y')
            report_groups['yearly'][year_key].append(report)
        print("report_groups", report_groups)
        # Calculate averages for each period
        for week_key, week_reports in report_groups['weekly'].items():
            if len(week_reports) >= 2:  # Need at least 2 reports for meaningful average
                avg_fullness = sum(r.pantry_fullness for r in week_reports) / len(week_reports)
                weekly_trends.append({
                    'period': week_key,
                    'label': f"Week of {week_key}",
                    'average_fullness': round(avg_fullness, 1),
                    'report_count': len(week_reports),
                    'min_fullness': min(r.pantry_fullness for r in week_reports),
                    'max_fullness': max(r.pantry_fullness for r in week_reports)
                })
        
        for month_key, month_reports in report_groups['monthly'].items():
            if len(month_reports) >= 2:
                avg_fullness = sum(r.pantry_fullness for r in month_reports) / len(month_reports)
                monthly_trends.append({
                    'period': month_key,
                    'label': datetime.strptime(month_key, '%Y-%m').strftime('%B %Y'),
                    'average_fullness': round(avg_fullness, 1),
                    'report_count': len(month_reports),
                    'min_fullness': min(r.pantry_fullness for r in month_reports),
                    'max_fullness': max(r.pantry_fullness for r in month_reports)
                })
        
        for year_key, year_reports in report_groups['yearly'].items():
            if len(year_reports) >= 5:  # Need more reports for yearly average
                avg_fullness = sum(r.pantry_fullness for r in year_reports) / len(year_reports)
                yearly_trends.append({
                    'period': year_key,
                    'label': year_key,
                    'average_fullness': round(avg_fullness, 1),
                    'report_count': len(year_reports),
                    'min_fullness': min(r.pantry_fullness for r in year_reports),
                    'max_fullness': max(r.pantry_fullness for r in year_reports)
                })
        
        # Sort trends chronologically
        weekly_trends.sort(key=lambda x: x['period'])
        monthly_trends.sort(key=lambda x: x['period'])
        yearly_trends.sort(key=lambda x: x['period'])
        
        # Add to analytics
        analytics['time_trends'] = {
            'weekly': weekly_trends,
            'monthly': monthly_trends,
            'yearly': yearly_trends,
            'has_weekly_data': len(weekly_trends) >= 2,
            'has_monthly_data': len(monthly_trends) >= 2,
            'has_yearly_data': len(yearly_trends) >= 2
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
        
        # ENHANCED ANALYTICS - Community Engagement
        unique_users = set()
        user_report_counts = {}
        for report in reports:
            if report.user_id:
                unique_users.add(report.user_id)
                user_report_counts[report.user_id] = user_report_counts.get(report.user_id, 0) + 1
        
        analytics['engagement'] = {
            'unique_reporters': len(unique_users),
            'anonymous_reports': sum(1 for r in reports if not r.user_id),
            'average_reports_per_user': round(len(reports) / max(1, len(unique_users)), 1),
            'most_active_reporter': max(user_report_counts.values()) if user_report_counts else 0,
            'engagement_rate': round((len(unique_users) / max(1, analytics['date_range']['days'])) * 7, 2)  # reporters per week
        }
        
        # ENHANCED ANALYTICS - Restocking Patterns
        restocking_events = []
        depletion_events = []
        
        for i in range(1, len(reports)):
            prev_report = reports[i-1]
            curr_report = reports[i]
            
            # Detect restocking (significant increase in fullness)
            if curr_report.pantry_fullness > prev_report.pantry_fullness + 30:
                time_diff = (curr_report.time - prev_report.time).total_seconds() / 3600  # hours
                restocking_events.append({
                    'time': curr_report.time,
                    'from_fullness': prev_report.pantry_fullness,
                    'to_fullness': curr_report.pantry_fullness,
                    'time_since_last': time_diff
                })
            
            # Detect depletion (significant decrease)
            elif prev_report.pantry_fullness > curr_report.pantry_fullness + 20:
                time_diff = (curr_report.time - prev_report.time).total_seconds() / 3600  # hours
                depletion_events.append({
                    'time': curr_report.time,
                    'from_fullness': prev_report.pantry_fullness,
                    'to_fullness': curr_report.pantry_fullness,
                    'depletion_rate': time_diff
                })
        
        # Calculate restocking analytics
        restock_times = [event['time_since_last'] for event in restocking_events if event['time_since_last'] < 24*7]  # within a week
        depletion_rates = [event['depletion_rate'] for event in depletion_events if event['depletion_rate'] < 24*3]  # within 3 days
        
        analytics['restocking'] = {
            'total_restocking_events': len(restocking_events),
            'total_depletion_events': len(depletion_events),
            'average_restock_time_hours': round(sum(restock_times) / len(restock_times), 1) if restock_times else None,
            'average_depletion_time_hours': round(sum(depletion_rates) / len(depletion_rates), 1) if depletion_rates else None,
            'recent_restocking_events': restocking_events[-3:],  # Last 3
            'restocking_frequency_per_week': round(len(restocking_events) / max(1, analytics['date_range']['days'] / 7), 1)
        }
        
        # ENHANCED ANALYTICS - Peak Usage Patterns  
        hour_patterns = defaultdict(list)
        month_patterns = defaultdict(list)
        
        for report in reports:
            hour_patterns[report.time.hour].append(report.pantry_fullness)
            month_patterns[report.time.strftime('%B')].append(report.pantry_fullness)
        
        # Find peak depletion hours (hours with lowest average fullness)
        hour_averages = {hour: sum(fullness_list) / len(fullness_list) 
                        for hour, fullness_list in hour_patterns.items()}
        
        sorted_hours = sorted(hour_averages.items(), key=lambda x: x[1])
        peak_depletion_hours = sorted_hours[:3] if len(sorted_hours) >= 3 else sorted_hours
        
        analytics['patterns'].update({
            'peak_depletion_hours': [f"{hour:02d}:00 ({avg:.1f}% avg)" for hour, avg in peak_depletion_hours],
            'month_averages': {month: round(sum(fullness_list) / len(fullness_list), 1) 
                             for month, fullness_list in month_patterns.items()},
            'busiest_months': sorted(month_patterns.items(), key=lambda x: len(x[1]), reverse=True)[:3]
        })
        
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
    notifications = location.notifications
    if notifications:
        subject = f"{location.name} is Empty!"
        location_url = url_for('views.location', location_id=location.id, _external=True)
        
        # Send individual emails to each subscriber with their unique unsubscribe link
        for notification in notifications:
            if notification.user and notification.user.email:
                # Generate token if it doesn't exist (for existing subscriptions)
                if not notification.unsubscribe_token:
                    import secrets
                    notification.unsubscribe_token = secrets.token_urlsafe(32)
                    notification.created_at = datetime.now(timezone.utc)
                    db.session.commit()
                
                unsubscribe_url = url_for('views.unsubscribe_from_email', token=notification.unsubscribe_token, _external=True)
                
                html = f"""
                <h3>🚨 {location.name} Needs Restocking!</h3>
                
                <p>The Little Free Pantry located at <strong>{location.address}, {location.city}, {location.state}</strong> is currently running low on supplies.</p>
                
                <p><strong>Can you help restock it?</strong></p>
                
                {f'<p><strong>Recent Update:</strong> {report.description}</p>' if report.description else ''}
                
                {f'<p>📸 A new photo has been uploaded - check it out on the website!</p>' if report.photo else ''}
                
                <p><a href="{location_url}" style="background-color: #4a90e2; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">View Pantry Details</a></p>
                
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 20px;">
                    <p style="font-size: 12px; color: #666; margin: 0 0 10px 0;">
                        You're receiving this email because you're subscribed to updates for this pantry.
                    </p>
                    <a href="{unsubscribe_url}" style="background-color: #dc3545; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; font-size: 12px; display: inline-block;">Unsubscribe from this pantry</a>
                </div>
                
                <p>Thank you for being part of our community!</p>
                <p><strong>Report That Pantry Team</strong></p>
                """
                
                send_email([notification.user.email], subject, html)


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
    """New improved homepage with focus on pantry visibility"""
    # Get some basic stats for the homepage
    total_pantries = Location.query.count()
    total_reports = Report.query.count()
    
    # Count unique states
    states = db.session.query(Location.state).distinct().count()
    
    # Count empty alerts (reports with fullness <= 33%)
    empty_alerts = Report.query.filter(Report.pantry_fullness <= 33).count()
    
    stats = {
        'total_pantries': total_pantries,
        'total_reports': total_reports,
        'states_covered': states,
        'empty_alerts': empty_alerts
    }
    
    return render_template("index-new.html", 
                         user=current_user, 
                         title="Home", 
                         stats=stats)


@views.route('/home')
def home_redirect():
    """Redirect to main home page for compatibility"""
    return redirect(url_for('views.home'))


@views.route('/home-old')
def home_old():
    """Original homepage kept as backup"""
    locations = Location.query.all()
    return render_template("index.html", user=current_user, title="Home - Original")


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
# @login_required  # Temporarily removed - allowing anonymous submissions
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
            return render_template("location.html", api_key=os.environ.get('GOOGLE_MAPS_API_KEY'), user=current_user, editing=False, title="Add Location", states=us_states)
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
            user_id=current_user.id if current_user.is_authenticated else None,  # Allow anonymous submissions
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
# @login_required  # Temporarily removed - will need to handle ownership differently
def edit_location(location_id):
    location = Location.query.get_or_404(location_id)

    # Check if the user owns this location (only if authenticated)
    if current_user.is_authenticated and location.user_id and location.user_id != current_user.id:
        flash("You do not have permission to edit this location.", category='error')
        return redirect(url_for('views.map'))
    elif not current_user.is_authenticated and location.user_id:
        # Location has an owner but user is not authenticated
        flash("You must be logged in to edit this location.", category='error')
        return redirect(url_for('auth.login'))

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
        # Get fullness level from the form and convert to integer
        pantry_fullness = request.form.get('pantryFullness')
        try:
            pantry_fullness = int(pantry_fullness) if pantry_fullness else 0
        except (ValueError, TypeError):
            pantry_fullness = 0
        
        # Get the description and photo
        description = request.form.get('pantryDescription')
        photo = request.files.get('pantryPhoto')
    
        # Analyze photo with Google Vision API if provided
        vision_analysis = None
        suggested_fullness = None
        
        if photo:
            # Handle HEIC conversion for vision analysis if needed
            if is_heic_file(photo.filename):
                print(f"Converting HEIC file for analysis: {photo.filename}")
                converted_data = convert_heic_to_jpeg(photo)
                if converted_data is not None:
                    # Use converted data for Vision API analysis
                    photo_content = converted_data.read()
                    # Reset file pointer for S3 upload (original photo will be converted in upload_photo_to_s3)
                    photo.seek(0)
                else:
                    print("Failed to convert HEIC for vision analysis, skipping AI analysis")
                    photo_content = None
            else:
                # Reset file pointer
                photo.seek(0)
                # Read photo content for Vision API analysis
                photo_content = photo.read()
                photo.seek(0)  # Reset again for S3 upload
            
            # Perform Vision API analysis if we have photo content
            if photo_content:
                vision_analysis = analyze_pantry_image(photo_content)
                
                # Get AI-suggested fullness if analysis was successful
                if vision_analysis and "fullness_estimate" in vision_analysis:
                    suggested_fullness = vision_analysis["fullness_estimate"]
        
        # Create Report object
        new_report = Report(
            pantry_fullness=pantry_fullness,
            time=datetime.now(timezone.utc),
            location_id=location.id,
            description=description,
            user_id=current_user.id if current_user.is_authenticated else None,
            submitted_by_email=request.form.get('submitterEmail', '').strip() if not current_user.is_authenticated else None
        )
        
        # Upload photo to Amazon S3, if provided
        s3_key = upload_photo_to_s3(photo, location.id)
        # Store relative path in database
        if s3_key:
            new_report.photo = s3_key
        
        # Store Vision API analysis results as JSON in the new field
        if vision_analysis and "error" not in vision_analysis:
            new_report.vision_analysis = json.dumps(vision_analysis)
        elif vision_analysis and "error" in vision_analysis:
            # Log the error but don't fail the report submission
            print(f"Vision API analysis error: {vision_analysis['error']}")
            new_report.vision_analysis = json.dumps({"error": vision_analysis["error"]})
        
        db.session.add(new_report)
        db.session.commit()

        # Send email notification if the pantry is empty
        if new_report.pantry_fullness <= 33:  # Check for empty status
            send_notification_emails(location, new_report)

        # Return JSON response for AJAX (modern interface)
        return jsonify({
            'success': True, 
            'message': 'Thank you for your report!',
            'location_id': location.id,
            'redirect_url': url_for('views.location', location_id=id)
        })

    # Use the modern demo template for GET requests
    return render_template("report-demo.html", user=current_user, title="Report Pantry Status", location_id=id) 


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
                         title="Dashboard", 
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
# @login_required  # Temporarily removed - will handle subscriptions differently
def subscribe():
    # Check if user is authenticated
    if not current_user.is_authenticated:
        return jsonify({'status': 'error', 'message': 'Please log in to subscribe to notifications'})
    
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
            import secrets
            unsubscribe_token = secrets.token_urlsafe(32)
            new_subscription = Notification(
                user_id=current_user.id, 
                location_id=location_id,
                unsubscribe_token=unsubscribe_token,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(new_subscription)
            db.session.commit()
            return jsonify({'status': 'subscribed', 'message': 'Subscribed successfully'})

    return jsonify({'status': 'error', 'message': 'Invalid location_id'})


# Handles changes to subscription preferences on pantry homepage
@views.route('/location/subscribe/<int:location_id>', methods=['POST'])
def subscribe_location(location_id):
    print("Subscription endpoint accessed")
    
    # Check if location exists
    location = Location.query.get(location_id)
    if not location:
        return jsonify({'success': False, 'message': 'Location does not exist'}), 404
    
    # Handle JSON requests (for email subscription form)
    if request.is_json:
        data = request.get_json()
        email = data.get('email', '').strip()
        
        if not email:
            return jsonify({'success': False, 'message': 'Email address is required'}), 400
        
        # Check if user with this email already exists
        existing_user = User.query.filter_by(email=email).first()
        
        if existing_user:
            # Check if already subscribed
            existing_subscription = Notification.query.filter_by(user_id=existing_user.id, location_id=location_id).first()
            if existing_subscription:
                return jsonify({'success': False, 'message': 'This email is already subscribed to this pantry'})
            else:
                # Subscribe existing user
                import secrets
                unsubscribe_token = secrets.token_urlsafe(32)
                new_subscription = Notification(
                    user_id=existing_user.id, 
                    location_id=location_id,
                    unsubscribe_token=unsubscribe_token,
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(new_subscription)
                db.session.commit()
                return jsonify({'success': True, 'message': 'Successfully subscribed to pantry updates!'})
        else:
            # Create new user account and subscribe
            new_user = User(email=email, first_name="", last_name="")
            db.session.add(new_user)
            db.session.flush()  # Get the user ID
            
            import secrets
            unsubscribe_token = secrets.token_urlsafe(32)
            new_subscription = Notification(
                user_id=new_user.id, 
                location_id=location_id,
                unsubscribe_token=unsubscribe_token,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(new_subscription)
            db.session.commit()

            return jsonify({'success': True, 'message': 'Subscribed to this pantry\'s updates!'})

    # Handle form-based requests (for authenticated users)
    if not current_user.is_authenticated:
        flash('Please log in to subscribe to notifications for this pantry.', 'info')
        return redirect(url_for('auth.login'))
    
    location_id = int(location_id)
    # Check if the user is already subscribed and toggle the subscription
    existing_subscription = Notification.query.filter_by(user_id=current_user.id, location_id=location_id).first()
    
    if existing_subscription:
        # Unsubscribe
        db.session.delete(existing_subscription)
        db.session.commit()
        flash('You have successfully unsubscribed from this pantry.', 'success')
    else:
        # Subscribe
        import secrets
        unsubscribe_token = secrets.token_urlsafe(32)
        new_subscription = Notification(
            user_id=current_user.id, 
            location_id=location_id,
            unsubscribe_token=unsubscribe_token,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(new_subscription)
        db.session.commit()
        flash('You have successfully subscribed to this pantry.', 'success')

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
    return render_template('map-new.html', 
                         title='Map', 
                         api_key=os.environ.get('GOOGLE_MAPS_API_KEY'),
                         user=current_user)

@views.route('/demo-new-design')
def demo_new_design():
    return render_template('demo-new-design.html', title='New Design Demo')

@views.route('/how-it-works')
def how_it_works():
    return render_template('background-info.html', title='How It Works', user=current_user)

@views.route('/unsubscribe/<token>')
def unsubscribe_from_email(token):
    """
    Unsubscribe a user from a specific pantry via email link
    Uses a secure token to prevent unauthorized unsubscriptions
    """
    # Find the notification by token
    notification = Notification.query.filter_by(unsubscribe_token=token).first()
    
    if not notification:
        flash('Invalid unsubscribe link. Please contact support if you need help.', 'error')
        return redirect(url_for('views.home'))
    
    # Get the location name before deleting
    location = Location.query.get(notification.location_id)
    location_name = location.name if location else "this pantry"
    
    # Remove the notification subscription
    db.session.delete(notification)
    db.session.commit()
    
    flash(f'You have been successfully unsubscribed from notifications for {location_name}.', 'success')
    return redirect(url_for('views.home'))

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
                # Handle HEIC conversion if needed
                if is_heic_file(photo.filename):
                    print(f"Converting HEIC file for demo: {photo.filename}")
                    converted_data = convert_heic_to_jpeg(photo)
                    if converted_data is not None:
                        photo_content = converted_data.read()
                    else:
                        error_message = "Failed to convert HEIC image. Please try a different format."
                        photo_content = None
                else:
                    # Read photo content
                    photo_content = photo.read()
                    photo.seek(0)  # Reset file pointer
                
                # Perform comprehensive Vision API analysis if we have photo content
                if photo_content:
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
        return jsonify({'error': 'Invalid file type. Please upload PNG, JPG, JPEG, GIF, HEIC, or HEIF'}), 400
    
    try:
        # Handle HEIC conversion if needed
        if is_heic_file(photo.filename):
            print(f"Converting HEIC file for analysis: {photo.filename}")
            converted_data = convert_heic_to_jpeg(photo)
            if converted_data is None:
                return jsonify({'error': 'Failed to convert HEIC image. Please try a different format.'}), 400
            photo_content = converted_data.read()
        else:
            # Read photo content for non-HEIC files
            photo_content = photo.read()
        
        # Perform Vision API analysis
        analysis_results = analyze_pantry_image(photo_content)
        
        if "error" in analysis_results:
            return jsonify({'error': analysis_results['error']}), 500
        
        # Format response for frontend
        response = {
            'success': True,
            'fullness_estimate': analysis_results.get('fullness_estimate'),
            'food_items': analysis_results.get('food_items', []),
            'organization_score': analysis_results.get('organization_score'),
            'confidence_score': analysis_results.get('confidence_score'),
            'analysis_details': analysis_results.get('analysis_summary', '')
        }
        
        return jsonify(response)
        
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
    def new_state_stats():
        return {'locations': 0, 'reports': 0, 'avg_fullness': 0.0, 'fullness_values': []}
    state_stats = defaultdict(new_state_stats)
    for location in active_locations:
        state = location.state
        state_stats[state]['locations'] += 1
        state_stats[state]['reports'] += len(location.reports)
        
        if location.reports:
            latest_fullness = location.reports[-1].pantry_fullness
            if latest_fullness is not None:
                state_stats[state]['fullness_values'].append(latest_fullness)
    
    # Calculate state averages and convert to full state names
    state_breakdown_with_full_names = {}
    for state_abbrev, state_data in state_stats.items():
        if state_data['fullness_values']:
            state_data['avg_fullness'] = round(statistics.mean(state_data['fullness_values']), 1)
        del state_data['fullness_values']  # Remove raw data
        
        # Use full state name as the key
        full_state_name = get_state_full_name(state_abbrev)
        state_breakdown_with_full_names[full_state_name] = state_data
    
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
            normalized_one_week = normalize_datetime(one_week_ago);
            
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
        'state_breakdown': state_breakdown_with_full_names,
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


@views.route('/analyze_image', methods=['POST'])
# @login_required  # Temporarily removed - allowing anonymous AI analysis
def analyze_image():
    """
    Real-time AI analysis endpoint for uploaded images
    Returns JSON with analysis results
    """
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No image file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type. Please upload a valid image (PNG, JPG, JPEG, GIF, HEIC, HEIF)."}), 400
        
        # Handle HEIC conversion if needed
        if is_heic_file(file.filename):
            print(f"Converting HEIC file for analysis: {file.filename}")
            converted_data = convert_heic_to_jpeg(file)
            if converted_data is not None:
                photo_content = converted_data.read()
            else:
                return jsonify({"error": "Failed to convert HEIC image. Please try a different format."}), 400
        else:
            # Read image content
            file.seek(0)
            photo_content = file.read()
        
        # Run hybrid AI analysis
        analysis_results = analyze_pantry_image(photo_content)
        
        if "error" in analysis_results:
            return jsonify({
                "error": analysis_results["error"],
                "fallback_message": "AI analysis failed, but you can still submit manually."
            }), 500
        
        # Extract key information for frontend
        response_data = {
            "success": True,
            "fullness_estimate": analysis_results.get("fullness_estimate"),
            "confidence_score": analysis_results.get("confidence_score", 0),
            "method_agreement": analysis_results.get("method_agreement", False),
            "food_items": analysis_results.get("food_items", [])[:8],  # Limit to 8 items for display
            "food_count": len(analysis_results.get("food_items", []))
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in real-time AI analysis: {e}")
        return jsonify({
            "error": "Analysis failed due to technical error",
            "fallback_message": "Please continue with manual entry."
        }), 500


# AJAX endpoint for real-time AI image analysis
@views.route('/analyze-image', methods=['POST'])
def analyze_image_ajax():
    """
    AJAX endpoint to analyze uploaded image in real-time and return AI suggestions
    """
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        photo = request.files['image']
        if photo.filename == '':
            return jsonify({'error': 'No image selected'}), 400
        
        # Handle HEIC conversion if needed
        if is_heic_file(photo.filename):
            print(f"Converting HEIC file for AJAX analysis: {photo.filename}")
            converted_data = convert_heic_to_jpeg(photo)
            if converted_data is not None:
                photo_content = converted_data.read()
            else:
                return jsonify({'error': 'Failed to convert HEIC image. Please try a different format.'}), 400
        else:
            # Read photo content for AI analysis
            photo_content = photo.read()
        
        # Perform AI analysis
        analysis_result = analyze_pantry_image(photo_content)
        
        if 'error' in analysis_result:
            return jsonify({'error': analysis_result['error']}), 500
        
        # Format response for frontend
        response = {
            'success': True,
            'fullness_estimate': analysis_result.get('fullness_estimate'),
            'food_items': analysis_result.get('food_items', []),
            'empty_areas': analysis_result.get('empty_areas', ''),
            'analysis_method': analysis_result.get('analysis_method', 'ai')
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"AJAX image analysis error: {e}")
        return jsonify({'error': 'Analysis failed. Please try again.'}), 500


# Email-only location submission route (no login required)
@views.route('/location/submit', methods=['GET', 'POST'])
@views.route('/location/submit/', methods=['GET', 'POST'])
def submit_location():
    """
    Email-only location submission - no account required
    Users submit with just email, get verification email with QR code
    """
    if request.method == 'GET':
        return render_template('add_location.html', api_key=current_app.config.get('GOOGLE_MAPS_API_KEY'))
    
    if request.method == 'POST':
        try:
            # Get form data
            address = request.form.get('address', '').strip()
            city = request.form.get('city', '').strip()
            state = request.form.get('state', '').strip()
            zip_code = request.form.get('zipCode', '').strip()
            latitude = request.form.get('latitude', '').strip()
            longitude = request.form.get('longitude', '').strip()
            description = request.form.get('description', '').strip()
            email = request.form.get('email', '').strip()
            submitter_name = request.form.get('submitterName', '').strip()
            pantry_name = request.form.get('pantryName', '').strip()
            photo = request.files.get('pantryPhoto')
            
            # Basic validation
            if not address:
                return jsonify({'error': 'Address is required'}), 400
            if not email:
                return jsonify({'error': 'Email is required'}), 400
            if not latitude or not longitude:
                return jsonify({'error': 'Please select a valid address from the suggestions'}), 400
                
            # Validate email format
            import re
            email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
            if not re.match(email_pattern, email):
                return jsonify({'error': 'Invalid email format'}), 400
            
            # Check if location already exists
            existing_location = Location.query.filter_by(address=address).first()
            if existing_location:
                return jsonify({'error': 'A location with this address already exists'}), 400
            
            # Generate verification token
            verification_token = str(uuid.uuid4())
            
            # Create new location (initially unverified)
            new_location = Location(
                address=address,
                city=city,
                state=state,
                zip=int(zip_code) if zip_code and zip_code.isdigit() else None,
                latitude=float(latitude) if latitude else None,
                longitude=float(longitude) if longitude else None,
                name=pantry_name if pantry_name else f"Pantry at {address}",
                description=description,
                user_id=None,  # No user account required
                submitter_email=email,
                submitter_name=submitter_name,
                verification_token=verification_token,
                verified=False,
                created_at=datetime.now(timezone.utc)
            )
            
            db.session.add(new_location)
            db.session.commit()
            
            # Upload photo to S3 (if provided)
            if photo:
                s3_key = upload_photo_to_s3(photo, new_location.id)
                if s3_key:
                    new_location.photo = s3_key
                    db.session.commit()
            
            # Create initial report (set to unknown status)
            new_report = Report(
                pantry_fullness=50,  # Default to 50% until first real report
                time=datetime.now(timezone.utc),
                               location_id=new_location.id,
                submitted_by_email=email
            )
            db.session.add(new_report)
            db.session.commit()
            
            # Send verification email
            verification_url = url_for('views.verify_location', 
                                     token=verification_token, 
                                     _external=True)
            
            email_subject = "Verify your pantry location submission"
            email_body = f"""
            <p>Hello{' ' + submitter_name if submitter_name else ''}!</p>
            
            <p>Thank you for adding a new pantry location to our community map!</p>
            
            <p>📍 <strong>Location:</strong> {pantry_name if pantry_name else address}</p>
            <p>🏠 <strong>Address:</strong> {address}</p>
            
            <p>To complete your submission and receive your QR code, please verify your email by clicking the link below:</p>
            
            <p><a href="{verification_url}" style="background-color: #4a90e2; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">Verify Email Address</a></p>
            
            <p>Once verified, your location will appear on our map and you'll receive:</p>
            <ul>
                <li>✅ A QR code to attach to your pantry</li>
                <li>📧 Email notifications when your pantry needs attention</li>
                <li>🔗 A direct link to share with your community</li>
            </ul>
            
            <p>If you didn't submit this location, you can safely ignore this email.</p>
            
            <p>Thanks for building our community!<br>
            <strong>Report That Pantry Team</strong></p>
            """
            
            try:
                send_email(email, email_subject, email_body)
                print(f"Verification email sent to {email}")
            except Exception as e:
                print(f"Failed to send verification email: {e}")
                # Continue anyway - admin can manually verify
            
            return jsonify({
                'success': True, 
                'message': 'Location submitted successfully! Check your email for verification instructions.',
                'location_id': new_location.id
            })
            
        except Exception as e:
            print(f"Error submitting location: {e}")
            db.session.rollback()
            return jsonify({'error': 'Failed to submit location. Please try again.'}), 500


@views.route('/location/verify/<token>')
def verify_location(token):
    """
    Verify a location submission via email token
    """
    try:
        location = Location.query.filter_by(verification_token=token).first()
        
        if not location:
            flash('Invalid or expired verification link.', 'error')
            return redirect(url_for('views.index'))
        
        if location.verified:
            flash('This location has already been verified.', 'info')
            return redirect(url_for('views.location', location_id=location.id))
        
        # Mark as verified
        location.verified = True
        location.verified_at = datetime.now(timezone.utc)
        db.session.commit()
        
        # Generate QR code URL
        qr_url = url_for('views.report', id=location.id, _external=True)
        
        # Generate PDF poster
        pdf_content = generate_qr_poster_pdf(location.name, location.id, qr_url)
        
        # Send QR code email with PDF attachment
        email_subject = "🎉 Your pantry location is verified! Here's your QR code poster"
        email_body = f"""
        <h2>🎉 Great news! Your pantry location is verified!</h2>
        
        <p>Your pantry location has been verified and is now live on our community map.</p>
        
        <p><strong>📍 Location:</strong> {location.address}</p>
        
        <p><strong>🔗 View on map:</strong> <a href="{url_for('views.location', location_id=location.id, _external=True)}" style="color: #4a90e2;">Click here to view your location</a></p>
        
        <h3>🎯 Your QR Code Poster</h3>
        
        <p>We've attached a professionally designed QR code poster to this email. Here's what to do:</p>
        
        <ol>
            <li><strong>Download and print</strong> the attached PDF poster</li>
            <li><strong>Laminate it</strong> (recommended for weather protection)</li>
            <li><strong>Attach it to your pantry</strong> where people can easily see it</li>
        </ol>
        
        <p>The QR code on the poster will direct people to: <a href="{qr_url}" style="color: #4a90e2;">{qr_url}</a></p>
        
        <h3>💡 What's next?</h3>
        
        <ul>
            <li>✅ Your location is now visible on our community map</li>
            <li>📱 People can scan the QR code to report pantry status</li>
            <li>📧 You'll get email notifications when your pantry needs attention</li>
            <li>🌍 You're helping build a stronger community!</li>
        </ul>
        
        <h3>📧 Need help?</h3>
        
        <p>If you need to make changes or have questions, contact us with your verification code: <strong>{token[:8]}</strong></p>
        
        <p>Thank you for serving your community! ❤️</p>
        
        <p><strong>The Report That Pantry Team</strong></p>
        """
        
        # Prepare attachment
        attachments = []
        if pdf_content:
            attachments.append({
                'filename': f'pantry_qr_poster_{location.id}.pdf',
                'content': pdf_content,
                'content_type': 'application/pdf'
            })
        
        try:
            send_email(location.submitter_email, email_subject, email_body, attachments)
            print(f"QR code poster email sent to {location.submitter_email}")
        except Exception as e:
            print(f"Failed to send QR code email: {e}")
        
        flash('Location verified successfully! Check your email for your QR code poster PDF.', 'success')
        return redirect(url_for('views.location', location_id=location.id))
        
    except Exception as e:
        print(f"Error verifying location: {e}")
        flash('An error occurred during verification. Please try again.', 'error')
        return redirect(url_for('views.index'))


