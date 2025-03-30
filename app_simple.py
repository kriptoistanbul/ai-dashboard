from flask import Flask, request, jsonify
import pandas as pd
from urllib.parse import urlparse
import json
import datetime
import plotly.express as px
import plotly.io

app = Flask(__name__)

# Define the HTML content directly in the Python file
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SEO Position Tracking Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        .chart-container {min-height: 400px; margin-bottom: 20px;}
        .dashboard-section {display: none;}
        #file-upload-section {display: block;}
        .loading {display: flex; justify-content: center; align-items: center; height: 100px;}
        .data-table {max-height: 500px; overflow-y: auto;}
        .summary-card:hover {transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.1);}
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="#">SEO Position Tracker</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="#" id="nav-upload">Upload Data</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#" id="nav-dashboard">Dashboard</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#" id="nav-keyword">Keyword Analysis</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#" id="nav-domain">Domain Analysis</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <!-- File Upload Section -->
        <div id="file-upload-section" class="dashboard-section">
            <div class="row justify-content-center">
                <div class="col-md-8">
                    <div class="card">
                        <div class="card-header bg-primary text-white">
                            <h5 class="mb-0">Upload Excel Data</h5>
                        </div>
                        <div class="card-body">
                            <form id="upload-form" enctype="multipart/form-data">
                                <div class="mb-3">
                                    <label for="file" class="form-label">Select Excel File</label>
                                    <input type="file" class="form-control" id="file" name="file" accept=".xlsx, .xls">
                                    <div class="form-text">Your Excel file should contain columns for Keyword, Results, Position, and Time.</div>
                                </div>
                                <button type="submit" class="btn btn-primary">Upload and Analyze</button>
                            </form>
                            <div id="upload-status" class="mt-3"></div>
                            <div id="upload-loading" class="loading d-none">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Other sections (dashboard, keyword, domain) omitted for brevity -->
        <div id="dashboard-section" class="dashboard-section">
            <h2 class="mb-4">SEO Position Tracking Dashboard</h2>
            <div class="row mb-4" id="summary-cards"></div>
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header"><h5>Position Distribution</h5></div>
                        <div class="card-body">
                            <div id="position-distribution-chart" class="chart-container"></div>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header"><h5>Top Domains by Average Position</h5></div>
                        <div class="card-body">
                            <div id="top-domains-chart" class="chart-container"></div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="row mt-4">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header"><h5>Top Keywords by Volume</h5></div>
                        <div class="card-body data-table">
                            <table class="table table-striped table-hover">
                                <thead><tr><th>Keyword</th><th>Number of URLs</th></tr></thead>
                                <tbody id="keyword-volume-table"></tbody>
                            </table>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header"><h5>Top Domains by Frequency</h5></div>
                        <div class="card-body data-table">
                            <table class="table table-striped table-hover">
                                <thead><tr><th>Domain</th><th>Frequency</th></tr></thead>
                                <tbody id="domain-frequency-table"></tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div id="keyword-section" class="dashboard-section">
            <h2 class="mb-4">Keyword Analysis</h2>
            <div class="row mb-4">
                <div class="col-md-6">
                    <div class="form-group">
                        <label for="keyword-select">Select Keyword:</label>
                        <select class="form-control" id="keyword-select">
                            <option value="">-- Select a keyword --</option>
                        </select>
                    </div>
                </div>
                <div class="col-md-6">
                    <div id="keyword-loading" class="loading d-none">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                </div>
            </div>
            <div id="keyword-content" class="d-none">
                <!-- Keyword analysis content will be loaded here -->
            </div>
        </div>

        <div id="domain-section" class="dashboard-section">
            <h2 class="mb-4">Domain Analysis</h2>
            <div class="row mb-4">
                <div class="col-md-6">
                    <div class="form-group">
                        <label for="domain-input">Enter Domain:</label>
                        <input type="text" class="form-control" id="domain-input" placeholder="e.g., example.com">
                    </div>
                </div>
                <div class="col-md-6">
                    <button class="btn btn-primary mt-4" id="analyze-domain-btn">Analyze Domain</button>
                    <div id="domain-loading" class="loading d-none">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                </div>
            </div>
            <div id="domain-content" class="d-none">
                <!-- Domain analysis content will be loaded here -->
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Navigation handlers
            document.getElementById('nav-upload').addEventListener('click', function(e) {
                e.preventDefault();
                showSection('file-upload-section');
            });
            
            document.getElementById('nav-dashboard').addEventListener('click', function(e) {
                e.preventDefault();
                showSection('dashboard-section');
                loadOverallStats();
            });
            
            document.getElementById('nav-keyword').addEventListener('click', function(e) {
                e.preventDefault();
                showSection('keyword-section');
            });
            
            document.getElementById('nav-domain').addEventListener('click', function(e) {
                e.preventDefault();
                showSection('domain-section');
            });
            
            // File Upload Form Submission
            document.getElementById('upload-form').addEventListener('submit', function(e) {
                e.preventDefault();
                uploadFile();
            });
            
            // Keyword Select Change Event
            document.getElementById('keyword-select').addEventListener('change', function() {
                const keyword = this.value;
                if (keyword) {
                    analyzeKeyword(keyword);
                } else {
                    document.getElementById('keyword-content').classList.add('d-none');
                }
            });
            
            // Domain Analysis Button
            document.getElementById('analyze-domain-btn').addEventListener('click', function() {
                const domain = document.getElementById('domain-input').value.trim();
                if (domain) {
                    analyzeDomain(domain);
                } else {
                    alert('Please enter a domain name');
                }
            });
        });

        // Helper Functions
        function showSection(sectionId) {
            const sections = document.querySelectorAll('.dashboard-section');
            sections.forEach(section => section.style.display = 'none');
            document.getElementById(sectionId).style.display = 'block';
        }

        function uploadFile() {
            const fileInput = document.getElementById('file');
            const file = fileInput.files[0];
            
            if (!file) {
                showUploadStatus('Please select a file', 'danger');
                return;
            }
            
            // Show loading indicator
            document.getElementById('upload-loading').classList.remove('d-none');
            
            const formData = new FormData();
            formData.append('file', file);
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('upload-loading').classList.add('d-none');
                
                if (data.error) {
                    showUploadStatus(data.error, 'danger');
                    return;
                }
                
                showUploadStatus('File uploaded successfully! Data is ready for analysis.', 'success');
                
                // Populate the keyword dropdown
                populateKeywordDropdown(data.keywords);
                
                // Show the dashboard after a short delay
                setTimeout(() => {
                    showSection('dashboard-section');
                    loadOverallStats();
                }, 1000);
            })
            .catch(error => {
                document.getElementById('upload-loading').classList.add('d-none');
                showUploadStatus('Error uploading file: ' + error, 'danger');
            });
        }

        function showUploadStatus(message, type) {
            document.getElementById('upload-status').innerHTML = 
                `<div class="alert alert-${type}">${message}</div>`;
        }

        function populateKeywordDropdown(keywords) {
            const select = document.getElementById('keyword-select');
            while (select.options.length > 1) select.options.remove(1);
            keywords.forEach(keyword => {
                const option = document.createElement('option');
                option.value = keyword;
                option.textContent = keyword;
                select.appendChild(option);
            });
        }

        function loadOverallStats() {
            fetch('/overall_stats')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        createSummaryCards(data.summary);
                        Plotly.newPlot('position-distribution-chart', data.charts.position_distribution.data, data.charts.position_distribution.layout);
                        Plotly.newPlot('top-domains-chart', data.charts.top_domains.data, data.charts.top_domains.layout);
                        populateKeywordVolumeTable(data.keyword_data);
                        populateDomainFrequencyTable(data.domain_data);
                    } else if (data.error) {
                        alert("Error: " + data.error);
                    }
                })
                .catch(error => console.error('Error:', error));
        }

        function createSummaryCards(summary) {
            const summaryCards = document.getElementById('summary-cards');
            summaryCards.innerHTML = '';
            
            const summaryData = [
                { title: 'Total Keywords', value: summary.total_keywords, icon: 'bi-search', color: 'primary' },
                { title: 'Total Domains', value: summary.total_domains, icon: 'bi-globe', color: 'success' },
                { title: 'Total URLs', value: summary.total_urls, icon: 'bi-link', color: 'info' },
                { title: 'Date Range', value: `${summary.date_range[0]} to ${summary.date_range[1]}`, icon: 'bi-calendar', color: 'warning' }
            ];
            
            summaryData.forEach(item => {
                const card = document.createElement('div');
                card.className = 'col-md-3 col-sm-6 mb-3';
                card.innerHTML = `
                    <div class="card summary-card bg-light">
                        <div class="card-body">
                            <div class="d-flex justify-content-between">
                                <div>
                                    <h5 class="card-title">${item.title}</h5>
                                    <h2 class="text-${item.color}">${item.value}</h2>
                                </div>
                                <div class="align-self-center">
                                    <i class="bi ${item.icon} fs-1 text-${item.color}"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                summaryCards.appendChild(card);
            });
        }

        function populateKeywordVolumeTable(data) {
            const table = document.getElementById('keyword-volume-table');
            table.innerHTML = '';
            
            if (!data || data.length === 0) {
                table.innerHTML = '<tr><td colspan="2" class="text-center">No data available</td></tr>';
                return;
            }
            
            data.forEach(item => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${item.Keyword}</td>
                    <td>${item.Results}</td>
                `;
                table.appendChild(row);
            });
        }

        function populateDomainFrequencyTable(data) {
            const table = document.getElementById('domain-frequency-table');
            table.innerHTML = '';
            
            if (!data || data.length === 0) {
                table.innerHTML = '<tr><td colspan="2" class="text-center">No data available</td></tr>';
                return;
            }
            
            data.forEach(item => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${item.domain}</td>
                    <td>${item.count}</td>
                `;
                table.appendChild(row);
            });
        }

        function analyzeKeyword(keyword) {
            document.getElementById('keyword-loading').classList.remove('d-none');
            document.getElementById('keyword-content').classList.add('d-none');
            
            fetch('/keyword_analytics', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ keyword: keyword })
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('keyword-loading').classList.add('d-none');
                const contentDiv = document.getElementById('keyword-content');
                
                if (data.success) {
                    // Display keyword analysis results
                    contentDiv.classList.remove('d-none');
                    contentDiv.innerHTML = `
                        <div class="row">
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-header"><h5>Position Distribution</h5></div>
                                    <div class="card-body">
                                        <div id="keyword-position-chart" class="chart-container"></div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-header"><h5>Domain Performance</h5></div>
                                    <div class="card-body">
                                        <div id="keyword-domain-chart" class="chart-container"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header"><h5>Domain Rankings</h5></div>
                                    <div class="card-body data-table">
                                        <table class="table table-striped table-hover">
                                            <thead>
                                                <tr>
                                                    <th>Domain</th>
                                                    <th>Average Position</th>
                                                    <th>Best Position</th>
                                                    <th>Worst Position</th>
                                                    <th>Count</th>
                                                </tr>
                                            </thead>
                                            <tbody id="domain-ranking-table"></tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    // Render charts and tables
                    Plotly.newPlot('keyword-position-chart', data.charts.position_distribution.data, data.charts.position_distribution.layout);
                    Plotly.newPlot('keyword-domain-chart', data.charts.domain_performance.data, data.charts.domain_performance.layout);
                    
                    // Populate domain ranking table
                    const table = document.getElementById('domain-ranking-table');
                    table.innerHTML = '';
                    data.domain_data.forEach(item => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${item.domain}</td>
                            <td>${item.mean.toFixed(2)}</td>
                            <td>${item.min}</td>
                            <td>${item.max}</td>
                            <td>${item.count}</td>
                        `;
                        table.appendChild(row);
                    });
                } else if (data.error) {
                    contentDiv.classList.remove('d-none');
                    contentDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                }
            })
            .catch(error => {
                document.getElementById('keyword-loading').classList.add('d-none');
                document.getElementById('keyword-content').classList.remove('d-none');
                document.getElementById('keyword-content').innerHTML = `
                    <div class="alert alert-danger">Error analyzing keyword: ${error}</div>
                `;
            });
        }

        function analyzeDomain(domain) {
            document.getElementById('domain-loading').classList.remove('d-none');
            document.getElementById('domain-content').classList.add('d-none');
            
            fetch('/domain_analytics', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ domain: domain })
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('domain-loading').classList.add('d-none');
                const contentDiv = document.getElementById('domain-content');
                
                if (data.success) {
                    // Display domain analysis results
                    contentDiv.classList.remove('d-none');
                    contentDiv.innerHTML = `
                        <div class="row">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header"><h5>Keyword Performance</h5></div>
                                    <div class="card-body">
                                        <div id="domain-keyword-chart" class="chart-container"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header"><h5>Keyword Rankings</h5></div>
                                    <div class="card-body data-table">
                                        <table class="table table-striped table-hover">
                                            <thead>
                                                <tr>
                                                    <th>Keyword</th>
                                                    <th>Average Position</th>
                                                    <th>Best Position</th>
                                                    <th>Worst Position</th>
                                                    <th>Count</th>
                                                </tr>
                                            </thead>
                                            <tbody id="keyword-ranking-table"></tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    // Render chart
                    Plotly.newPlot('domain-keyword-chart', data.charts.keyword_performance.data, data.charts.keyword_performance.layout);
                    
                    // Populate keyword ranking table
                    const table = document.getElementById('keyword-ranking-table');
                    table.innerHTML = '';
                    data.keyword_data.forEach(item => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${item.Keyword}</td>
                            <td>${item.mean.toFixed(2)}</td>
                            <td>${item.min}</td>
                            <td>${item.max}</td>
                            <td>${item.count}</td>
                        `;
                        table.appendChild(row);
                    });
                } else if (data.error) {
                    contentDiv.classList.remove('d-none');
                    contentDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                }
            })
            .catch(error => {
                document.getElementById('domain-loading').classList.add('d-none');
                document.getElementById('domain-content').classList.remove('d-none');
                document.getElementById('domain-content').innerHTML = `
                    <div class="alert alert-danger">Error analyzing domain: ${error}</div>
                `;
            });
        }
    </script>
</body>
</html>
"""

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
    
    # Convert date columns to datetime
    date_columns = ['Time', 'date/time']
    for col in date_columns:
        if col in df.columns:
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except:
                pass
    
    # Add date column (without time)
    if 'Time' in df.columns:
        df['date'] = pd.NaT
        mask = df['Time'].notna()
        if mask.any():
            df.loc[mask, 'date'] = df.loc[mask, 'Time'].dt.date
    
    return df

def get_date_range(df):
    """Safely get date range from dataframe"""
    if 'date' not in df.columns or df['date'].isna().all():
        return ["N/A", "N/A"]
    
    try:
        valid_dates = df['date'].dropna()
        if len(valid_dates) == 0:
            return ["N/A", "N/A"]
        
        min_date = valid_dates.min()
        max_date = valid_dates.max()
        
        # Format dates safely
        min_date_str = min_date.strftime('%Y-%m-%d') if isinstance(min_date, datetime.date) else str(min_date).split(' ')[0]
        max_date_str = max_date.strftime('%Y-%m-%d') if isinstance(max_date, datetime.date) else str(max_date).split(' ')[0]
        
        return [min_date_str, max_date_str]
    except:
        return ["N/A", "N/A"]

@app.route('/')
def index():
    return INDEX_HTML

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    
    try:
        # Save file to temporary location
        temp_path = 'temp_upload.xlsx'
        file.save(temp_path)
        
        # Load and process data
        df = pd.read_excel(temp_path)
        if 'Keyword' in df.columns:
            df['Keyword'].fillna(method='ffill', inplace=True)
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
        df = pd.read_excel('temp_upload.xlsx')
        if 'Keyword' in df.columns:
            df['Keyword'].fillna(method='ffill', inplace=True)
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
        
        # Create charts
        pos_dist = px.histogram(
            keyword_df, 
            x='Position',
            title=f'Position Distribution for "{keyword}"',
            labels={'Position': 'Position', 'count': 'Count'},
            nbins=20
        )
        
        domain_perf = px.bar(
            domain_positions.head(10), 
            x='domain', 
            y='mean',
            error_y='count',
            title=f'Top 10 Domains for "{keyword}"',
            labels={'domain': 'Domain', 'mean': 'Average Position'},
            color='mean',
            color_continuous_scale='RdYlGn_r'
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
        df = pd.read_excel('temp_upload.xlsx')
        if 'Keyword' in df.columns:
            df['Keyword'].fillna(method='ffill', inplace=True)
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
        
        # Create chart
        keyword_chart = px.bar(
            keyword_perf.head(10), 
            x='Keyword', 
            y='mean',
            title=f'Top 10 Keywords for "{domain}"',
            labels={'Keyword': 'Keyword', 'mean': 'Average Position'},
            color='mean',
            color_continuous_scale='RdYlGn_r'
        )
        
        # Convert to JSON
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
        df = pd.read_excel('temp_upload.xlsx')
        if 'Keyword' in df.columns:
            df['Keyword'].fillna(method='ffill', inplace=True)
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
            top_domains_chart = px.bar(
                pd.DataFrame({'domain': [], 'Position': []}),
                x='domain',
                y='Position',
                title='No Domain Position Data Available'
            )
        
        # Convert to JSON
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