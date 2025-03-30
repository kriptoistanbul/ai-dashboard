from flask import Flask, request, jsonify, send_file
import pandas as pd
from urllib.parse import urlparse
import json
import plotly.express as px
import plotly.io
import io
import os

app = Flask(__name__)

# HTML template (shortened for brevity)
INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SEO Position Tracking Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        .chart-container {min-height: 400px; margin-bottom: 20px;}
        .dashboard-section {display: none;}
        #file-upload-section {display: block;}
        .loading {display: flex; justify-content: center; align-items: center; height: 100px;}
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="#">SEO Position Tracker</a>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="#" id="nav-upload">Upload Data</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#" id="nav-dashboard">Dashboard</a>
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

        <!-- Dashboard Section -->
        <div id="dashboard-section" class="dashboard-section">
            <h2 class="mb-4">SEO Position Tracking Dashboard</h2>
            <div id="summary-cards" class="row mb-4"></div>
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header"><h5>Position Distribution</h5></div>
                        <div class="card-body">
                            <div id="position-chart" class="chart-container"></div>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header"><h5>Domain Distribution</h5></div>
                        <div class="card-body">
                            <div id="domain-chart" class="chart-container"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Navigation
            document.getElementById('nav-upload').addEventListener('click', function(e) {
                e.preventDefault();
                showSection('file-upload-section');
            });
            
            document.getElementById('nav-dashboard').addEventListener('click', function(e) {
                e.preventDefault();
                showSection('dashboard-section');
                loadDashboard();
            });
            
            // File Upload
            document.getElementById('upload-form').addEventListener('submit', function(e) {
                e.preventDefault();
                uploadFile();
            });
        });
        
        function showSection(sectionId) {
            const sections = document.querySelectorAll('.dashboard-section');
            sections.forEach(section => section.style.display = 'none');
            document.getElementById(sectionId).style.display = 'block';
        }
        
        function uploadFile() {
            const fileInput = document.getElementById('file');
            const file = fileInput.files[0];
            
            if (!file) {
                showStatus('Please select a file', 'danger');
                return;
            }
            
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
                    showStatus(data.error, 'danger');
                    return;
                }
                
                showStatus('File uploaded successfully!', 'success');
                setTimeout(() => {
                    showSection('dashboard-section');
                    loadDashboard();
                }, 1000);
            })
            .catch(error => {
                document.getElementById('upload-loading').classList.add('d-none');
                showStatus('Error: ' + error, 'danger');
            });
        }
        
        function showStatus(message, type) {
            document.getElementById('upload-status').innerHTML = 
                `<div class="alert alert-${type}">${message}</div>`;
        }
        
        function loadDashboard() {
            fetch('/dashboard')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Display summary cards
                    createSummaryCards(data.summary);
                    
                    // Display charts
                    Plotly.newPlot('position-chart', data.charts.position.data, data.charts.position.layout);
                    Plotly.newPlot('domain-chart', data.charts.domain.data, data.charts.domain.layout);
                }
            })
            .catch(error => console.error('Error:', error));
        }
        
        function createSummaryCards(summary) {
            const container = document.getElementById('summary-cards');
            container.innerHTML = '';
            
            const cards = [
                { title: 'Total Keywords', value: summary.keywords, color: 'primary' },
                { title: 'Total Domains', value: summary.domains, color: 'success' },
                { title: 'Total URLs', value: summary.urls, color: 'info' }
            ];
            
            cards.forEach(card => {
                const col = document.createElement('div');
                col.className = 'col-md-4';
                col.innerHTML = `
                    <div class="card bg-${card.color} text-white">
                        <div class="card-body">
                            <h5 class="card-title">${card.title}</h5>
                            <h2>${card.value}</h2>
                        </div>
                    </div>
                `;
                container.appendChild(col);
            });
        }
    </script>
</body>
</html>"""

def get_domain(url):
    """Extract domain from URL"""
    try:
        return urlparse(url).netloc
    except:
        return None

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
        
        # Load data safely with error handling
        try:
            df = pd.read_excel(temp_path, engine='openpyxl')
        except Exception as e:
            return jsonify({'error': f'Error reading Excel file: {str(e)}'})
        
        # Process data
        if 'Keyword' in df.columns:
            df['Keyword'].fillna(method='ffill', inplace=True)
        
        # Extract domains
        if 'Results' in df.columns:
            df['domain'] = df['Results'].apply(get_domain)
        
        # Save processed data
        df.to_excel(temp_path, index=False, engine='openpyxl')
        
        return jsonify({
            'success': True,
            'message': 'File uploaded and processed successfully'
        })
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'})

@app.route('/dashboard')
def dashboard():
    try:
        # Load processed data
        df = pd.read_excel('temp_upload.xlsx', engine='openpyxl')
        
        # Calculate summary statistics
        summary = {
            'keywords': df['Keyword'].nunique() if 'Keyword' in df.columns else 0,
            'domains': df['domain'].nunique() if 'domain' in df.columns else 0,
            'urls': df['Results'].nunique() if 'Results' in df.columns else 0,
        }
        
        # Create position distribution chart
        if 'Position' in df.columns:
            position_chart = px.histogram(
                df, 
                x='Position',
                title='Position Distribution',
                color_discrete_sequence=['#3366CC']
            )
        else:
            position_chart = px.histogram(
                pd.DataFrame({'Position': [1, 2, 3]}),
                x='Position',
                title='No Position Data'
            )
        
        # Create domain distribution chart
        if 'domain' in df.columns:
            domain_counts = df['domain'].value_counts().reset_index()
            domain_counts.columns = ['domain', 'count']
            
            domain_chart = px.bar(
                domain_counts.head(10),
                x='domain',
                y='count',
                title='Top 10 Domains',
                color_discrete_sequence=['#33CC66']
            )
        else:
            domain_chart = px.bar(
                pd.DataFrame({'domain': ['example.com'], 'count': [1]}),
                x='domain',
                y='count',
                title='No Domain Data'
            )
        
        # Convert charts to JSON
        charts = {
            'position': json.loads(plotly.io.to_json(position_chart)),
            'domain': json.loads(plotly.io.to_json(domain_chart))
        }
        
        return jsonify({
            'success': True,
            'summary': summary,
            'charts': charts
        })
    except Exception as e:
        return jsonify({'error': f'Error generating dashboard: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True, port=8080)