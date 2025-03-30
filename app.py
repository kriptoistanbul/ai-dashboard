from flask import Flask, render_template, request, jsonify, send_from_directory
import pandas as pd
import json
from urllib.parse import urlparse
import plotly
import plotly.express as px
import plotly.graph_objects as go
import os
import datetime

# Create Flask app with explicit template folder
app = Flask(__name__, 
            template_folder=os.path.abspath('templates'),
            static_folder=os.path.abspath('static'))

def load_data(file_path):
    """Load data from Excel file and perform initial processing"""
    df = pd.read_excel(file_path)
    # Fill NA values in keyword column with the value from previous row
    if 'Keyword' in df.columns:
        df['Keyword'].fillna(method='ffill', inplace=True)
    return df

def get_domain(url):
    """Extract domain from URL"""
    try:
        return urlparse(url).netloc
    except (TypeError, ValueError):
        return None

def prepare_data(df):
    """Prepare data for analysis"""
    # Add domain column
    if 'Results' in df.columns:
        df['domain'] = df['Results'].apply(get_domain)
    else:
        df['domain'] = None
    
    # Convert date columns to datetime - handle errors
    date_columns = ['Time', 'date/time']
    for col in date_columns:
        if col in df.columns:
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except:
                pass
    
    # Add date column (without time) - safely
    if 'Time' in df.columns:
        # Make sure to handle NaT values
        df['date'] = pd.NaT  # Initialize with NaT
        mask = df['Time'].notna()
        if mask.any():
            df.loc[mask, 'date'] = df.loc[mask, 'Time'].dt.date
    
    return df

def get_date_range(df):
    """Safely get date range from dataframe"""
    if 'date' not in df.columns or df['date'].isna().all():
        return ["N/A", "N/A"]
    
    # Remove NaT values before finding min/max
    valid_dates = df['date'].dropna()
    if len(valid_dates) == 0:
        return ["N/A", "N/A"]
    
    try:
        min_date = valid_dates.min()
        max_date = valid_dates.max()
        
        # Format dates
        if isinstance(min_date, datetime.date):
            min_date_str = min_date.strftime('%Y-%m-%d')
        else:
            min_date_str = str(min_date).split(' ')[0]
            
        if isinstance(max_date, datetime.date):
            max_date_str = max_date.strftime('%Y-%m-%d')
        else:
            max_date_str = str(max_date).split(' ')[0]
            
        return [min_date_str, max_date_str]
    except:
        return ["N/A", "N/A"]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    
    # Save file to temporary location
    temp_path = 'temp_upload.xlsx'
    file.save(temp_path)
    
    # Load and process data
    try:
        df = load_data(temp_path)
        df = prepare_data(df)
        
        # Get summary statistics
        summary = {
            'total_keywords': df['Keyword'].nunique() if 'Keyword' in df.columns else 0,
            'total_domains': df['domain'].nunique() if 'domain' in df.columns else 0,
            'total_urls': df['Results'].nunique() if 'Results' in df.columns else 0,
            'date_range': get_date_range(df)
        }
        
        # Get list of keywords for dropdown
        keywords = df['Keyword'].unique().tolist() if 'Keyword' in df.columns else []
        
        return jsonify({
            'success': True,
            'summary': summary,
            'keywords': keywords
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/keyword_analytics', methods=['POST'])
def keyword_analytics():
    try:
        data = request.json
        keyword = data.get('keyword')
        
        # Load data
        df = load_data('temp_upload.xlsx')
        df = prepare_data(df)
        
        # Filter by keyword
        if 'Keyword' in df.columns and keyword:
            keyword_df = df[df['Keyword'] == keyword]
        else:
            return jsonify({'error': 'Keyword not found in data'})
        
        # Get domain positions
        if 'domain' in df.columns and 'Position' in df.columns:
            domain_positions = keyword_df.groupby('domain')['Position'].agg(['mean', 'min', 'max', 'count']).reset_index()
            domain_positions = domain_positions.sort_values('mean')
        else:
            return jsonify({'error': 'Required columns missing in data'})
        
        # Create position distribution chart
        pos_dist = px.histogram(
            keyword_df, 
            x='Position',
            title=f'Position Distribution for "{keyword}"',
            labels={'Position': 'Position', 'count': 'Count'},
            nbins=20
        )
        
        # Create domain performance chart
        domain_perf = px.bar(
            domain_positions.head(10), 
            x='domain', 
            y='mean',
            error_y='count',
            title=f'Top 10 Domains for "{keyword}" (by Average Position)',
            labels={'domain': 'Domain', 'mean': 'Average Position'},
            color='mean',
            color_continuous_scale='RdYlGn_r'  # Red for high positions (worse), green for low (better)
        )
        
        # Convert to JSON
        charts = {
            'position_distribution': json.loads(plotly.io.to_json(pos_dist)),
            'domain_performance': json.loads(plotly.io.to_json(domain_perf))
        }
        
        return jsonify({
            'success': True,
            'charts': charts,
            'domain_data': domain_positions.head(20).to_dict('records')
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/domain_analytics', methods=['POST'])
def domain_analytics():
    try:
        data = request.json
        domain = data.get('domain')
        
        # Load data
        df = load_data('temp_upload.xlsx')
        df = prepare_data(df)
        
        # Filter by domain
        if 'domain' in df.columns and domain:
            domain_df = df[df['domain'] == domain]
        else:
            return jsonify({'error': 'Domain not found in data'})
        
        # Get keyword performance for this domain
        if 'Keyword' in df.columns and 'Position' in df.columns:
            keyword_perf = domain_df.groupby('Keyword')['Position'].agg(['mean', 'min', 'max', 'count']).reset_index()
            keyword_perf = keyword_perf.sort_values('mean')
        else:
            return jsonify({'error': 'Required columns missing in data'})
        
        # Create keyword performance chart
        keyword_chart = px.bar(
            keyword_perf.head(10), 
            x='Keyword', 
            y='mean',
            title=f'Top 10 Keywords for "{domain}" (by Average Position)',
            labels={'Keyword': 'Keyword', 'mean': 'Average Position'},
            color='mean',
            color_continuous_scale='RdYlGn_r'
        )
        
        charts = {
            'keyword_performance': json.loads(plotly.io.to_json(keyword_chart))
        }
        
        return jsonify({
            'success': True,
            'charts': charts,
            'keyword_data': keyword_perf.to_dict('records')
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/overall_stats')
def overall_stats():
    try:
        # Load data
        df = load_data('temp_upload.xlsx')
        df = prepare_data(df)
        
        # Top keywords by volume (number of URLs)
        if 'Keyword' in df.columns and 'Results' in df.columns:
            keyword_volume = df.groupby('Keyword')['Results'].nunique().reset_index()
            keyword_volume = keyword_volume.sort_values('Results', ascending=False)
        else:
            keyword_volume = pd.DataFrame(columns=['Keyword', 'Results'])
        
        # Top domains by frequency
        if 'domain' in df.columns:
            domain_freq = df['domain'].value_counts().reset_index()
            domain_freq.columns = ['domain', 'count']
        else:
            domain_freq = pd.DataFrame(columns=['domain', 'count'])
        
        # Position distribution overall
        if 'Position' in df.columns:
            pos_dist = px.histogram(
                df, 
                x='Position',
                title='Overall Position Distribution',
                labels={'Position': 'Position', 'count': 'Count'},
                nbins=20
            )
        else:
            # Create an empty figure
            pos_dist = px.histogram(
                pd.DataFrame({'Position': []}),
                x='Position',
                title='No Position Data Available',
                labels={'Position': 'Position', 'count': 'Count'}
            )
        
        # Domain distribution by position
        if 'domain' in df.columns and 'Position' in df.columns:
            domain_positions = df.groupby('domain')['Position'].mean().reset_index()
            domain_positions = domain_positions.sort_values('Position')
            
            top_domains_chart = px.bar(
                domain_positions.head(15), 
                x='domain', 
                y='Position',
                title='Top 15 Domains by Average Position',
                labels={'domain': 'Domain', 'Position': 'Average Position'},
                color='Position',
                color_continuous_scale='RdYlGn_r'
            )
        else:
            # Create an empty figure
            top_domains_chart = px.bar(
                pd.DataFrame({'domain': [], 'Position': []}),
                x='domain',
                y='Position',
                title='No Domain Position Data Available'
            )
        
        charts = {
            'position_distribution': json.loads(plotly.io.to_json(pos_dist)),
            'top_domains': json.loads(plotly.io.to_json(top_domains_chart))
        }
        
        # Get summary data
        summary = {
            'total_keywords': df['Keyword'].nunique() if 'Keyword' in df.columns else 0,
            'total_domains': df['domain'].nunique() if 'domain' in df.columns else 0,
            'total_urls': df['Results'].nunique() if 'Results' in df.columns else 0,
            'date_range': get_date_range(df)
        }
        
        return jsonify({
            'success': True,
            'charts': charts,
            'keyword_data': keyword_volume.head(20).to_dict('records'),
            'domain_data': domain_freq.head(20).to_dict('records'),
            'summary': summary
        })
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=8080)