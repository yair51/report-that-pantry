#!/usr/bin/env python3
"""
Little Free Pantry Analytics Dashboard
Interactive Dash app for visualizing pantry data and analytics
"""

import dash
from dash import dcc, html, Input, Output, callback, dash_table
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import sys
import calendar
from collections import Counter, defaultdict

# Add the project root to Python path to import our Flask app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our Flask app models and database
try:
    from app import create_app, db
    from app.models import Location, Report, User
    # Initialize Flask app to access database
    flask_app = create_app()
    print("✅ Flask app imports successful")
except Exception as e:
    print(f"❌ Error importing Flask app: {e}")
    print("🔧 Make sure you're running from the correct directory")
    sys.exit(1)

# Initialize Dash app with modern styling
app = dash.Dash(__name__, 
                external_stylesheets=[
                    'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
                    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'
                ])

app.title = "Little Free Pantry Analytics Dashboard"

# Custom CSS styling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                margin: 0;
                padding: 0;
            }
            .main-container {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                margin: 20px;
                padding: 30px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            }
            .header-section {
                background: linear-gradient(135deg, #2E8B57 0%, #3CB371 100%);
                color: white;
                padding: 30px;
                border-radius: 15px;
                margin-bottom: 30px;
                text-align: center;
            }
            .control-panel {
                background: #f8f9fa;
                padding: 25px;
                border-radius: 15px;
                margin-bottom: 30px;
                border: 1px solid #e9ecef;
            }
            .summary-card {
                background: white;
                border-radius: 15px;
                padding: 25px;
                margin: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                border-left: 5px solid;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            .summary-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2);
            }
            .chart-container {
                background: white;
                border-radius: 15px;
                padding: 20px;
                margin: 15px 0;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .table-container {
                background: white;
                border-radius: 15px;
                padding: 25px;
                margin-top: 30px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .metric-value {
                font-size: 2.5em;
                font-weight: bold;
                margin: 10px 0;
            }
            .metric-label {
                font-size: 1.1em;
                color: #6c757d;
                margin: 0;
            }
            .tab-content {
                background: white;
                border-radius: 15px;
                padding: 20px;
                margin-top: 20px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .refresh-button {
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                border: none;
                color: white;
                padding: 10px 20px;
                border-radius: 25px;
                font-weight: bold;
                transition: all 0.3s ease;
            }
            .refresh-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(40, 167, 69, 0.4);
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

def fetch_pantry_data():
    """Fetch all pantry locations and their reports from the database"""
    with flask_app.app_context():
        locations = Location.query.all()
        pantry_data = []
        
        for location in locations:
            reports = Report.query.filter_by(location_id=location.id).order_by(Report.time.asc()).all()
            
            if reports:  # Only include pantries with reports
                # Convert reports to DataFrame-friendly format
                location_reports = []
                for report in reports:
                    location_reports.append({
                        'location_id': location.id,
                        'location_name': location.name,
                        'address': location.address,
                        'city': location.city,
                        'state': location.state,
                        'report_id': report.id,
                        'timestamp': report.time,
                        'date': report.time.date(),
                        'time_str': report.time.strftime('%Y-%m-%d %H:%M'),
                        'pantry_fullness': report.pantry_fullness,
                        'status': report.get_status(),
                        'ai_fullness': report.get_ai_fullness_estimate(),
                        'detected_items': ', '.join(report.get_detected_food_items()) if report.get_detected_food_items() else 'No AI data',
                        'has_ai_data': bool(report.get_vision_analysis()),
                        'photo_available': bool(report.photo),
                        'description': report.description or 'No description'
                    })
                
                pantry_data.extend(location_reports)
        
        return pd.DataFrame(pantry_data) if pantry_data else pd.DataFrame()

def calculate_summary_stats(df):
    """Calculate summary statistics for all pantries"""
    if df.empty:
        return {}
    
    # Group by location for location-level stats
    location_stats = df.groupby(['location_id', 'location_name']).agg({
        'pantry_fullness': ['count', 'mean', 'min', 'max', 'std'],
        'has_ai_data': 'sum',
        'photo_available': 'sum'
    }).round(1)
    
    # Flatten column names
    location_stats.columns = ['_'.join(col).strip() if col[1] else col[0] for col in location_stats.columns]
    location_stats = location_stats.reset_index()
    
    # Overall stats
    total_reports = len(df)
    total_locations = df['location_id'].nunique()
    avg_fullness = df['pantry_fullness'].mean()
    
    # AI coverage
    ai_reports = df[df['has_ai_data']].shape[0]
    ai_coverage = (ai_reports / total_reports * 100) if total_reports > 0 else 0
    
    # Status distribution
    status_counts = df['status'].value_counts()
    
    return {
        'total_reports': total_reports,
        'total_locations': total_locations,
        'avg_fullness': round(avg_fullness, 1),
        'ai_coverage': round(ai_coverage, 1),
        'status_distribution': status_counts.to_dict(),
        'location_stats': location_stats
    }

def create_charts(df, selected_location=None):
    """Create interactive charts for the dashboard"""
    charts = {}
    
    if df.empty:
        # Return empty charts if no data
        empty_fig = go.Figure()
        empty_fig.add_annotation(text="No data available", xref="paper", yref="paper", 
                               x=0.5, y=0.5, showarrow=False, font_size=16)
        empty_fig.update_layout(
            template="plotly_white",
            height=400,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        return {'empty': empty_fig}
    
    # Filter data if location is selected
    if selected_location and selected_location != 'all':
        df_filtered = df[df['location_id'] == int(selected_location)]
        chart_title_suffix = f" - {df_filtered['location_name'].iloc[0]}"
    else:
        df_filtered = df
        chart_title_suffix = " - All Pantries"
    
    # Color scheme
    color_palette = ['#2E8B57', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
    
    # 1. Enhanced Fullness Over Time with better styling
    fig_fullness = go.Figure()
    
    if selected_location == 'all' or selected_location is None:
        # Multiple locations - show separate lines
        for i, (location_id, location_data) in enumerate(df_filtered.groupby('location_id')):
            location_name = location_data['location_name'].iloc[0]
            color = color_palette[i % len(color_palette)]
            
            # Add line
            fig_fullness.add_trace(go.Scatter(
                x=location_data['timestamp'], 
                y=location_data['pantry_fullness'],
                mode='lines+markers',
                name=location_name,
                line=dict(color=color, width=3),
                marker=dict(size=8, line=dict(width=2, color='white')),
                hovertemplate=f'<b>{location_name}</b><br>Date: %{{x}}<br>Fullness: %{{y}}%<extra></extra>'
            ))
    else:
        # Single location - show detailed view with color coding
        colors = df_filtered['pantry_fullness'].apply(lambda x: '#dc3545' if x <= 33 else ('#ffc107' if x <= 66 else '#28a745'))
        
        fig_fullness.add_trace(go.Scatter(
            x=df_filtered['timestamp'], 
            y=df_filtered['pantry_fullness'],
            mode='lines+markers',
            name='Fullness Level',
            line=dict(color='#2E8B57', width=3),
            marker=dict(
                size=10, 
                color=colors,
                line=dict(width=2, color='white'),
                opacity=0.8
            ),
            hovertemplate='<b>Pantry Fullness</b><br>Date: %{x}<br>Fullness: %{y}%<extra></extra>'
        ))
    
    fig_fullness.update_layout(
        title=dict(
            text=f'<b>Pantry Fullness Over Time{chart_title_suffix}</b>',
            x=0.5,
            font=dict(size=18, color='#2c3e50')
        ),
        template="plotly_white",
        height=450,
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis=dict(title="Date", gridcolor='#f0f0f0'),
        yaxis=dict(title="Fullness (%)", gridcolor='#f0f0f0', range=[0, 100]),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode='x unified'
    )
    charts['fullness_over_time'] = fig_fullness
    
    # 2. Enhanced Status Distribution with better colors
    status_counts = df_filtered['status'].value_counts()
    colors_pie = {'Empty': '#dc3545', 'Half Full': '#ffc107', 'Full': '#28a745'}
    
    fig_status = go.Figure(data=[go.Pie(
        labels=status_counts.index, 
        values=status_counts.values,
        hole=0.4,
        marker=dict(colors=[colors_pie.get(status, '#6c757d') for status in status_counts.index]),
        textinfo='label+percent+value',
        textfont=dict(size=12),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
    )])
    
    fig_status.update_layout(
        title=dict(
            text=f'<b>Pantry Status Distribution{chart_title_suffix}</b>',
            x=0.5,
            font=dict(size=18, color='#2c3e50')
        ),
        template="plotly_white",
        height=450,
        margin=dict(l=20, r=20, t=60, b=20),
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.05
        )
    )
    charts['status_distribution'] = fig_status
    
    # 3. Enhanced Activity Heatmap
    df_filtered['weekday'] = df_filtered['timestamp'].dt.day_name()
    df_filtered['hour'] = df_filtered['timestamp'].dt.hour
    
    activity_matrix = df_filtered.groupby(['weekday', 'hour']).size().unstack(fill_value=0)
    # Reorder weekdays
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    activity_matrix = activity_matrix.reindex(weekday_order, fill_value=0)
    
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=activity_matrix.values,
        x=activity_matrix.columns,
        y=activity_matrix.index,
        colorscale='Viridis',
        hoverongaps=False,
        hovertemplate='<b>Activity Heatmap</b><br>Day: %{y}<br>Hour: %{x}<br>Reports: %{z}<extra></extra>'
    ))
    
    fig_heatmap.update_layout(
        title=dict(
            text=f'<b>Activity Heatmap - Reports by Day & Hour{chart_title_suffix}</b>',
            x=0.5,
            font=dict(size=18, color='#2c3e50')
        ),
        template="plotly_white",
        height=450,
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis=dict(title="Hour of Day"),
        yaxis=dict(title="Day of Week")
    )
    charts['activity_heatmap'] = fig_heatmap
    
    # 4. Enhanced AI vs Manual Comparison
    df_ai = df_filtered[df_filtered['has_ai_data'] & df_filtered['ai_fullness'].notna()]
    if not df_ai.empty:
        fig_ai_comparison = go.Figure()
        
        # Add scatter points
        fig_ai_comparison.add_trace(go.Scatter(
            x=df_ai['pantry_fullness'], 
            y=df_ai['ai_fullness'],
            mode='markers',
            name='AI vs Manual',
            marker=dict(
                size=12,
                color=df_ai['pantry_fullness'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Manual Assessment"),
                line=dict(width=2, color='white'),
                opacity=0.8
            ),
            hovertemplate='<b>Assessment Comparison</b><br>Manual: %{x}%<br>AI: %{y}%<extra></extra>'
        ))
        
        # Add diagonal line for perfect correlation
        min_val = 0
        max_val = 100
        fig_ai_comparison.add_trace(go.Scatter(
            x=[min_val, max_val], 
            y=[min_val, max_val],
            mode='lines', 
            name='Perfect Agreement',
            line=dict(dash='dash', color='#dc3545', width=3),
            hovertemplate='Perfect Agreement Line<extra></extra>'
        ))
        
        fig_ai_comparison.update_layout(
            title=dict(
                text=f'<b>AI vs Manual Fullness Assessment{chart_title_suffix}</b>',
                x=0.5,
                font=dict(size=18, color='#2c3e50')
            ),
            template="plotly_white",
            height=450,
            margin=dict(l=20, r=20, t=60, b=20),
            xaxis=dict(title="Manual Assessment (%)", range=[0, 100], gridcolor='#f0f0f0'),
            yaxis=dict(title="AI Assessment (%)", range=[0, 100], gridcolor='#f0f0f0'),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        charts['ai_comparison'] = fig_ai_comparison
    
    # 5. Enhanced Monthly Trends
    df_filtered['month'] = df_filtered['timestamp'].dt.to_period('M')
    monthly_stats = df_filtered.groupby('month').agg({
        'pantry_fullness': ['mean', 'count'],
        'has_ai_data': 'sum'
    }).round(1)
    monthly_stats.columns = ['avg_fullness', 'report_count', 'ai_reports']
    monthly_stats = monthly_stats.reset_index()
    monthly_stats['month_str'] = monthly_stats['month'].astype(str)
    
    fig_monthly = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add bar chart for report count
    fig_monthly.add_trace(go.Bar(
        x=monthly_stats['month_str'], 
        y=monthly_stats['report_count'],
        name='Number of Reports',
        marker_color='#4ECDC4',
        opacity=0.8,
        hovertemplate='<b>Reports</b><br>Month: %{x}<br>Count: %{y}<extra></extra>'
    ), secondary_y=False)
    
    # Add line for average fullness
    fig_monthly.add_trace(go.Scatter(
        x=monthly_stats['month_str'], 
        y=monthly_stats['avg_fullness'],
        mode='lines+markers', 
        name='Average Fullness',
        line=dict(color='#dc3545', width=4),
        marker=dict(size=10, line=dict(width=2, color='white')),
        hovertemplate='<b>Average Fullness</b><br>Month: %{x}<br>Fullness: %{y}%<extra></extra>'
    ), secondary_y=True)
    
    fig_monthly.update_yaxes(title_text="<b>Number of Reports</b>", secondary_y=False, gridcolor='#f0f0f0')
    fig_monthly.update_yaxes(title_text="<b>Average Fullness (%)</b>", secondary_y=True, gridcolor='#f0f0f0')
    fig_monthly.update_layout(
        title=dict(
            text=f'<b>Monthly Activity & Fullness Trends{chart_title_suffix}</b>',
            x=0.5,
            font=dict(size=18, color='#2c3e50')
        ),
        template="plotly_white",
        height=450,
        margin=dict(l=20, r=20, t=60, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode='x unified'
    )
    charts['monthly_trends'] = fig_monthly
    
    return charts

# Layout of the dashboard
app.layout = html.Div([
    html.Div([
        # Header Section
        html.Div([
            html.Div([
                html.I(className="fas fa-chart-line fa-3x", style={'marginRight': '20px', 'opacity': '0.8'}),
                html.Div([
                    html.H1("Little Free Pantry Analytics", 
                            style={'margin': '0', 'fontSize': '2.5em', 'fontWeight': 'bold'}),
                    html.P("Real-time insights and AI-powered analytics for community pantries", 
                           style={'margin': '5px 0 0 0', 'fontSize': '1.2em', 'opacity': '0.9'})
                ], style={'display': 'flex', 'flexDirection': 'column', 'justifyContent': 'center'})
            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'})
        ], className='header-section'),
        
        # Control Panel
        html.Div([
            html.H4([
                html.I(className="fas fa-sliders-h", style={'marginRight': '10px'}),
                "Dashboard Controls"
            ], style={'color': '#2c3e50', 'marginBottom': '20px'}),
            
            html.Div([
                html.Div([
                    html.Label([
                        html.I(className="fas fa-map-marker-alt", style={'marginRight': '8px'}),
                        "Select Pantry Location:"
                    ], style={'fontWeight': 'bold', 'color': '#495057', 'marginBottom': '8px'}),
                    dcc.Dropdown(
                        id='location-dropdown',
                        options=[],  # Will be populated by callback
                        value='all',
                        style={'marginBottom': '20px'},
                        placeholder="Choose a pantry location...",
                        className='form-select'
                    )
                ], className='col-lg-4 col-md-6'),
                
                html.Div([
                    html.Label([
                        html.I(className="fas fa-calendar-alt", style={'marginRight': '8px'}),
                        "Date Range:"
                    ], style={'fontWeight': 'bold', 'color': '#495057', 'marginBottom': '8px'}),
                    dcc.DatePickerRange(
                        id='date-range-picker',
                        start_date=datetime.now() - timedelta(days=30),
                        end_date=datetime.now(),
                        display_format='YYYY-MM-DD',
                        style={'width': '100%'}
                    )
                ], className='col-lg-4 col-md-6'),
                
                html.Div([
                    html.Label("Quick Actions:", 
                               style={'fontWeight': 'bold', 'color': '#495057', 'marginBottom': '8px'}),
                    html.Div([
                        html.Button([
                            html.I(className="fas fa-sync-alt", style={'marginRight': '8px'}),
                            "Refresh Data"
                        ], id='refresh-button', className='btn refresh-button me-2'),
                        html.Button([
                            html.I(className="fas fa-download", style={'marginRight': '8px'}),
                            "Export"
                        ], id='export-button', className='btn btn-outline-secondary')
                    ])
                ], className='col-lg-4 col-md-12', style={'display': 'flex', 'flexDirection': 'column', 'justifyContent': 'end'})
            ], className='row')
        ], className='control-panel'),
        
        # Summary Cards
        html.Div(id='summary-cards', className='row', style={'marginBottom': '30px'}),
        
        # Navigation Tabs
        html.Div([
            dcc.Tabs(id='main-tabs', value='overview', children=[
                dcc.Tab(label='📊 Overview', value='overview', className='custom-tab'),
                dcc.Tab(label='📈 Trends', value='trends', className='custom-tab'),
                dcc.Tab(label='🤖 AI Analysis', value='ai-analysis', className='custom-tab'),
                dcc.Tab(label='📋 Data Table', value='data-table', className='custom-tab')
            ], className='nav nav-tabs')
        ]),
        
        # Tab Content
        html.Div(id='tab-content', className='tab-content')
        
    ], className='main-container')
], style={'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 'minHeight': '100vh', 'padding': '0'})

# Define tab content layouts
def get_overview_layout():
    return html.Div([
        html.Div([
            html.Div([
                dcc.Graph(id='fullness-chart')
            ], className='col-lg-6'),
            
            html.Div([
                dcc.Graph(id='status-chart')
            ], className='col-lg-6')
        ], className='row'),
        
        html.Div([
            html.Div([
                dcc.Graph(id='activity-heatmap')
            ], className='col-12')
        ], className='row')
    ], className='chart-container')

def get_trends_layout():
    return html.Div([
        html.Div([
            dcc.Graph(id='monthly-trends-chart')
        ], className='row')
    ], className='chart-container')

def get_ai_analysis_layout():
    return html.Div([
        html.Div([
            html.Div([
                dcc.Graph(id='ai-comparison-chart')
            ], className='col-12')
        ], className='row'),
        
        html.Div([
            html.Div([
                html.H5([
                    html.I(className="fas fa-robot", style={'marginRight': '10px'}),
                    "AI Analysis Insights"
                ], style={'color': '#2c3e50', 'marginBottom': '20px'}),
                html.Div(id='ai-insights-content')
            ], className='col-12')
        ], className='row', style={'marginTop': '20px'})
    ], className='chart-container')

def get_data_table_layout():
    return html.Div([
        html.Div([
            html.H4([
                html.I(className="fas fa-table", style={'marginRight': '10px'}),
                "Recent Reports"
            ], style={'color': '#2c3e50', 'marginBottom': '20px'}),
            dash_table.DataTable(
                id='reports-table',
                columns=[],  # Will be populated by callback
                data=[],
                page_size=15,
                sort_action='native',
                filter_action='native',
                style_table={'overflowX': 'auto'},
                style_cell={
                    'textAlign': 'left', 
                    'padding': '12px',
                    'fontFamily': 'Segoe UI, sans-serif',
                    'fontSize': '14px'
                },
                style_header={
                    'backgroundColor': '#2E8B57', 
                    'color': 'white', 
                    'fontWeight': 'bold',
                    'textAlign': 'center'
                },
                style_data_conditional=[
                    {
                        'if': {'filter_query': '{status} = "Empty"'},
                        'backgroundColor': '#ffebee',
                        'color': 'black',
                    },
                    {
                        'if': {'filter_query': '{status} = "Full"'},
                        'backgroundColor': '#e8f5e8',
                        'color': 'black',
                    },
                    {
                        'if': {'filter_query': '{status} = "Half Full"'},
                        'backgroundColor': '#fff8e1',
                        'color': 'black',
                    }
                ],
                export_format='xlsx',
                export_headers='display'
            )
        ], className='col-12')
    ], className='table-container')

# Callbacks for interactivity
@app.callback(
    [Output('location-dropdown', 'options'),
     Output('summary-cards', 'children')],
    [Input('location-dropdown', 'value'),
     Input('date-range-picker', 'start_date'),
     Input('date-range-picker', 'end_date')]
)
def update_summary_data(selected_location, start_date, end_date):
    # Fetch data
    df = fetch_pantry_data()
    
    if df.empty:
        return ([], [html.Div([
            html.Div([
                html.I(className="fas fa-exclamation-circle fa-3x", style={'color': '#ffc107'}),
                html.H4("No Data Available", style={'marginTop': '15px', 'color': '#6c757d'}),
                html.P("No pantry reports found in the database.", style={'color': '#6c757d'})
            ], style={'textAlign': 'center', 'padding': '40px'})
        ], className='col-12 alert alert-warning')])
    
    # Filter by date range
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()
    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    
    # Dropdown options
    location_options = [{'label': 'All Pantries', 'value': 'all'}]
    for location_id, location_name in df[['location_id', 'location_name']].drop_duplicates().values:
        location_options.append({'label': location_name, 'value': location_id})
    
    # Summary statistics
    summary_stats = calculate_summary_stats(df)
    
    # Enhanced summary cards with icons and animations
    summary_cards = [
        html.Div([
            html.Div([
                html.Div([
                    html.I(className="fas fa-clipboard-list fa-2x", 
                           style={'color': '#2E8B57', 'marginBottom': '10px'}),
                    html.Div(f"{summary_stats.get('total_reports', 0)}", className='metric-value', 
                             style={'color': '#2E8B57'}),
                    html.P("Total Reports", className='metric-label')
                ], style={'textAlign': 'center'})
            ], className='summary-card', style={'borderLeftColor': '#2E8B57'})
        ], className='col-lg-3 col-md-6 col-sm-12'),
        
        html.Div([
            html.Div([
                html.Div([
                    html.I(className="fas fa-map-marker-alt fa-2x", 
                           style={'color': '#FF6B6B', 'marginBottom': '10px'}),
                    html.Div(f"{summary_stats.get('total_locations', 0)}", className='metric-value',
                             style={'color': '#FF6B6B'}),
                    html.P("Active Pantries", className='metric-label')
                ], style={'textAlign': 'center'})
            ], className='summary-card', style={'borderLeftColor': '#FF6B6B'})
        ], className='col-lg-3 col-md-6 col-sm-12'),
        
        html.Div([
            html.Div([
                html.Div([
                    html.I(className="fas fa-chart-pie fa-2x", 
                           style={'color': '#4ECDC4', 'marginBottom': '10px'}),
                    html.Div(f"{summary_stats.get('avg_fullness', 0)}%", className='metric-value',
                             style={'color': '#4ECDC4'}),
                    html.P("Average Fullness", className='metric-label')
                ], style={'textAlign': 'center'})
            ], className='summary-card', style={'borderLeftColor': '#4ECDC4'})
        ], className='col-lg-3 col-md-6 col-sm-12'),
        
        html.Div([
            html.Div([
                html.Div([
                    html.I(className="fas fa-robot fa-2x", 
                           style={'color': '#45B7D1', 'marginBottom': '10px'}),
                    html.Div(f"{summary_stats.get('ai_coverage', 0)}%", className='metric-value',
                             style={'color': '#45B7D1'}),
                    html.P("AI Analysis Coverage", className='metric-label')
                ], style={'textAlign': 'center'})
            ], className='summary-card', style={'borderLeftColor': '#45B7D1'})
        ], className='col-lg-3 col-md-6 col-sm-12')
    ]
    
    return location_options, summary_cards

@app.callback(
    Output('tab-content', 'children'),
    [Input('main-tabs', 'value')]
)
def update_tab_content(active_tab):
    if active_tab == 'overview':
        return get_overview_layout()
    elif active_tab == 'trends':
        return get_trends_layout()
    elif active_tab == 'ai-analysis':
        return get_ai_analysis_layout()
    elif active_tab == 'data-table':
        return get_data_table_layout()
    else:
        return get_overview_layout()

@app.callback(
    [Output('fullness-chart', 'figure'),
     Output('status-chart', 'figure'),
     Output('activity-heatmap', 'figure')],
    [Input('location-dropdown', 'value'),
     Input('date-range-picker', 'start_date'),
     Input('date-range-picker', 'end_date')]
)
def update_overview_charts(selected_location, start_date, end_date):
    df = fetch_pantry_data()
    
    if df.empty:
        empty_fig = go.Figure()
        empty_fig.add_annotation(text="No data available", xref="paper", yref="paper", 
                               x=0.5, y=0.5, showarrow=False, font_size=16)
        empty_fig.update_layout(template="plotly_white", height=400)
        return empty_fig, empty_fig, empty_fig
    
    # Filter by date range
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()
    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    
    charts = create_charts(df, selected_location)
    
    return (charts.get('fullness_over_time', go.Figure()),
            charts.get('status_distribution', go.Figure()),
            charts.get('activity_heatmap', go.Figure()))

@app.callback(
    Output('monthly-trends-chart', 'figure'),
    [Input('location-dropdown', 'value'),
     Input('date-range-picker', 'start_date'),
     Input('date-range-picker', 'end_date')]
)
def update_trends_chart(selected_location, start_date, end_date):
    df = fetch_pantry_data()
    
    if df.empty:
        empty_fig = go.Figure()
        empty_fig.add_annotation(text="No data available", xref="paper", yref="paper", 
                               x=0.5, y=0.5, showarrow=False, font_size=16)
        empty_fig.update_layout(template="plotly_white", height=400)
        return empty_fig
    
    # Filter by date range
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()
    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    
    charts = create_charts(df, selected_location)
    return charts.get('monthly_trends', go.Figure())

@app.callback(
    [Output('ai-comparison-chart', 'figure'),
     Output('ai-insights-content', 'children')],
    [Input('location-dropdown', 'value'),
     Input('date-range-picker', 'start_date'),
     Input('date-range-picker', 'end_date')]
)
def update_ai_analysis(selected_location, start_date, end_date):
    df = fetch_pantry_data()
    
    if df.empty:
        empty_fig = go.Figure()
        empty_fig.add_annotation(text="No data available", xref="paper", yref="paper", 
                               x=0.5, y=0.5, showarrow=False, font_size=16)
        empty_fig.update_layout(template="plotly_white", height=400)
        return empty_fig, html.Div("No AI data available", className='alert alert-info')
    
    # Filter by date range
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()
    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    
    charts = create_charts(df, selected_location)
    
    # AI insights
    df_ai = df[df['has_ai_data'] & df['ai_fullness'].notna()]
    if not df_ai.empty:
        # Calculate AI accuracy metrics
        manual_avg = df_ai['pantry_fullness'].mean()
        ai_avg = df_ai['ai_fullness'].mean()
        correlation = df_ai['pantry_fullness'].corr(df_ai['ai_fullness'])
        mae = np.mean(np.abs(df_ai['pantry_fullness'] - df_ai['ai_fullness']))
        
        insights_content = html.Div([
            html.Div([
                html.Div([
                    html.H6("AI Accuracy", style={'color': '#2c3e50'}),
                    html.H4(f"{correlation:.2f}", style={'color': '#28a745', 'margin': '0'}),
                    html.Small("Correlation Score", style={'color': '#6c757d'})
                ], className='text-center p-3 bg-light rounded me-3'),
                
                html.Div([
                    html.H6("Average Error", style={'color': '#2c3e50'}),
                    html.H4(f"{mae:.1f}%", style={'color': '#dc3545', 'margin': '0'}),
                    html.Small("Mean Absolute Error", style={'color': '#6c757d'})
                ], className='text-center p-3 bg-light rounded me-3'),
                
                html.Div([
                    html.H6("AI Coverage", style={'color': '#2c3e50'}),
                    html.H4(f"{len(df_ai)}/{len(df)}", style={'color': '#007bff', 'margin': '0'}),
                    html.Small("Reports with AI", style={'color': '#6c757d'})
                ], className='text-center p-3 bg-light rounded')
            ], style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '20px'}),
            
            html.Div([
                html.H6("AI Performance Summary:", style={'marginBottom': '15px'}),
                html.Ul([
                    html.Li(f"Manual assessment average: {manual_avg:.1f}%"),
                    html.Li(f"AI assessment average: {ai_avg:.1f}%"),
                    html.Li(f"Correlation strength: {'Strong' if correlation > 0.7 else 'Moderate' if correlation > 0.4 else 'Weak'}"),
                    html.Li(f"Average prediction error: {mae:.1f} percentage points")
                ])
            ], className='alert alert-info')
        ])
    else:
        insights_content = html.Div([
            html.H6("No AI Analysis Data Available"),
            html.P("Upload images with pantry reports to see AI analysis insights.")
        ], className='alert alert-warning')
    
    return charts.get('ai_comparison', go.Figure()), insights_content

@app.callback(
    [Output('reports-table', 'columns'),
     Output('reports-table', 'data')],
    [Input('location-dropdown', 'value'),
     Input('date-range-picker', 'start_date'),
     Input('date-range-picker', 'end_date')]
)
def update_data_table(selected_location, start_date, end_date):
    df = fetch_pantry_data()
    
    if df.empty:
        return [], []
    
    # Filter by date range
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()
    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    
    # Table columns
    table_columns = [
        {'name': '📅 Date', 'id': 'time_str'},
        {'name': '📍 Location', 'id': 'location_name'},
        {'name': '📊 Fullness (%)', 'id': 'pantry_fullness', 'type': 'numeric'},
        {'name': '🚦 Status', 'id': 'status'},
        {'name': '🤖 AI Data', 'id': 'has_ai_data', 'type': 'text'},
        {'name': '📝 Description', 'id': 'description'}
    ]
    
    # Filter for table
    if selected_location and selected_location != 'all':
        table_data = df[df['location_id'] == int(selected_location)]
    else:
        table_data = df
    
    table_data = table_data.sort_values('timestamp', ascending=False).head(100)
    table_data['has_ai_data'] = table_data['has_ai_data'].map({True: '✅ Yes', False: '❌ No'})
    table_records = table_data[['time_str', 'location_name', 'pantry_fullness', 'status', 'has_ai_data', 'description']].to_dict('records')
    
    return table_columns, table_records

if __name__ == '__main__':
    print("🚀 Starting Little Free Pantry Analytics Dashboard...")
    print("📊 Dashboard will be available at: http://127.0.0.1:8051")
    print("🔍 Loading pantry data from database...")
    
    # Test database connection
    try:
        with flask_app.app_context():
            location_count = Location.query.count()
            report_count = Report.query.count()
            print(f"✅ Database connected successfully!")
            print(f"📍 Found {location_count} pantry locations")
            print(f"📋 Found {report_count} reports")
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        print("🔧 Please check your database configuration")
    
    app.run_server(debug=True, host='127.0.0.1', port=8051)
