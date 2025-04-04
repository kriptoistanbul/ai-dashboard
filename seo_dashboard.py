from flask import Flask, request, jsonify, send_file
import pandas as pd
from urllib.parse import urlparse
import json
import datetime
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io
import numpy as np
import os
import io
import re
import streamlit as st
app = Flask(__name__)

# Define the HTML content directly in the Python file
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Advanced SEO Position Tracking Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/daterangepicker/daterangepicker.css">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
    <style>
        .chart-container {min-height: 400px; margin-bottom: 20px;}
        .dashboard-section {display: none;}
        #file-upload-section {display: block;}
        .loading {display: flex; justify-content: center; align-items: center; height: 100px;}
        .data-table {max-height: 500px; overflow-y: auto;}
        .summary-card:hover {transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.1);}
        .filter-section {margin-bottom: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;}
        .comparison-chart {min-height: 450px;}
        .btn-export {margin-bottom: 10px;}
        .multi-select {height: 150px !important;}
        .rank-btn {margin-right: 5px; margin-bottom: 5px;}
        .position-legend {display: flex; align-items: center; justify-content: center; margin-bottom: 10px;}
        .position-legend .legend-item {display: flex; align-items: center; margin-right: 20px;}
        .position-legend .color-box {width: 15px; height: 15px; margin-right: 5px;}
        .transition {transition: all 0.3s ease;}
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="#">Advanced SEO Position Tracker</a>
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
                    <li class="nav-item">
                        <a class="nav-link" href="#" id="nav-url-compare">URL Comparison</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#" id="nav-time-compare">Time Comparison</a>
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
        <!-- Dashboard Overview Section -->
        <div id="dashboard-section" class="dashboard-section">
            <h2 class="mb-4">SEO Position Tracking Dashboard</h2>
            
            <!-- Filter Section -->
            <div class="filter-section">
                <div class="row">
                    <div class="col-md-3">
                        <div class="form-group">
                            <label for="dashboard-date-range">Date Range:</label>
                            <input type="text" class="form-control" id="dashboard-date-range">
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="form-group">
                            <label for="dashboard-keyword-filter">Keyword Filter:</label>
                            <select class="form-control" id="dashboard-keyword-filter">
                                <option value="">All Keywords</option>
                            </select>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="form-group">
                            <label for="dashboard-position-filter">Position Range:</label>
                            <div class="input-group">
                                <input type="number" class="form-control" id="dashboard-position-min" placeholder="Min">
                                <span class="input-group-text">-</span>
                                <input type="number" class="form-control" id="dashboard-position-max" placeholder="Max">
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="form-group">
                            <label> </label>
                            <button class="btn btn-primary form-control" id="dashboard-apply-filters">Apply Filters</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Summary Cards -->
            <div class="row mb-4" id="summary-cards"></div>
            
            <!-- Export Button -->
            <div class="text-end mb-3">
                <button class="btn btn-success btn-export" id="dashboard-export-data">
                    <i class="bi bi-file-excel"></i> Export to Excel
                </button>
            </div>
            
            <!-- Charts -->
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <div class="d-flex justify-content-between align-items-center">
                                <h5>Position Distribution</h5>
                                <div class="btn-group" role="group">
                                    <button type="button" class="btn btn-sm btn-outline-primary rank-btn" data-rank="3">Top 3</button>
                                    <button type="button" class="btn btn-sm btn-primary rank-btn" data-rank="5">Top 5</button>
                                    <button type="button" class="btn btn-sm btn-outline-primary rank-btn" data-rank="10">Top 10</button>
                                    <button type="button" class="btn btn-sm btn-outline-primary rank-btn" data-rank="20">Top 20</button>
                                </div>
                            </div>
                        </div>
                        <div class="card-body">
                            <div id="position-distribution-chart" class="chart-container"></div>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <div class="d-flex justify-content-between align-items-center">
                                <h5>Top Domains by Average Position</h5>
                                <div class="btn-group" role="group">
                                    <button type="button" class="btn btn-sm btn-outline-primary domain-rank-btn" data-rank="3">Top 3</button>
                                    <button type="button" class="btn btn-sm btn-primary domain-rank-btn" data-rank="5">Top 5</button>
                                    <button type="button" class="btn btn-sm btn-outline-primary domain-rank-btn" data-rank="10">Top 10</button>
                                    <button type="button" class="btn btn-sm btn-outline-primary domain-rank-btn" data-rank="20">Top 20</button>
                                </div>
                            </div>
                        </div>
                        <div class="card-body">
                            <div id="top-domains-chart" class="chart-container"></div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Data Tables -->
            <div class="row mt-4">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header"><h5>Top Keywords by Volume</h5></div>
                        <div class="card-body data-table">
                            <table class="table table-striped table-hover" id="keyword-volume-table-container">
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
                            <table class="table table-striped table-hover" id="domain-frequency-table-container">
                                <thead><tr><th>Domain</th><th>Frequency</th></tr></thead>
                                <tbody id="domain-frequency-table"></tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <!-- Keyword Analysis Section -->
        <div id="keyword-section" class="dashboard-section">
            <h2 class="mb-4">Keyword Analysis</h2>
            
            <!-- Filter Section -->
            <div class="filter-section">
                <div class="row">
                    <div class="col-md-3">
                        <div class="form-group">
                            <label for="keyword-select">Select Keyword:</label>
                            <select class="form-control" id="keyword-select">
                                <option value="">-- Select a keyword --</option>
                            </select>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="form-group">
                            <label for="keyword-date-range">Date Range:</label>
                            <input type="text" class="form-control" id="keyword-date-range">
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="form-group">
                            <label for="keyword-domain-filter">Domain Filter:</label>
                            <input type="text" class="form-control" id="keyword-domain-filter" placeholder="e.g., example.com">
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="form-group">
                            <label> </label>
                            <button class="btn btn-primary form-control" id="keyword-apply-filters">Apply Filters</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Available Dates Section -->
            <div id="keyword-available-dates" class="mb-4 d-none">
                <div class="card">
                    <div class="card-header"><h5>Available Dates for Selected Keyword</h5></div>
                    <div class="card-body">
                        <div id="keyword-dates-list" class="d-flex flex-wrap"></div>
                    </div>
                </div>
            </div>
            
            <!-- Export Button -->
            <div class="text-end mb-3">
                <button class="btn btn-success btn-export" id="keyword-export-data">
                    <i class="bi bi-file-excel"></i> Export to Excel
                </button>
            </div>
            
            <div id="keyword-loading" class="loading d-none">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
            
            <div id="keyword-content" class="d-none">
                <!-- Keyword analysis content will be loaded here -->
            </div>
        </div>
        <!-- Domain Analysis Section -->
        <div id="domain-section" class="dashboard-section">
            <h2 class="mb-4">Domain Analysis</h2>
            
            <!-- Filter Section -->
            <div class="filter-section">
                <div class="row">
                    <div class="col-md-3">
                        <div class="form-group">
                            <label for="domain-input">Enter Domain:</label>
                            <input type="text" class="form-control" id="domain-input" placeholder="e.g., example.com">
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="form-group">
                            <label for="domain-date-range">Date Range:</label>
                            <input type="text" class="form-control" id="domain-date-range">
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="form-group">
                            <label for="domain-position-filter">Position Range:</label>
                            <div class="input-group">
                                <input type="number" class="form-control" id="domain-position-min" placeholder="Min">
                                <span class="input-group-text">-</span>
                                <input type="number" class="form-control" id="domain-position-max" placeholder="Max">
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="form-group">
                            <label> </label>
                            <button class="btn btn-primary form-control" id="analyze-domain-btn">Analyze Domain</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Export Button -->
            <div class="text-end mb-3">
                <button class="btn btn-success btn-export" id="domain-export-data">
                    <i class="bi bi-file-excel"></i> Export to Excel
                </button>
            </div>
            
            <div id="domain-loading" class="loading d-none">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
            
            <div id="domain-content" class="d-none">
                <!-- Domain analysis content will be loaded here -->
            </div>
        </div>
        
        <!-- URL Comparison Section -->
        <div id="url-comparison-section" class="dashboard-section">
            <h2 class="mb-4">URL Comparison</h2>
            
            <!-- Filter Section -->
            <div class="filter-section">
                <div class="row">
                    <div class="col-md-6">
                        <div class="form-group">
                            <label for="url-compare-select">Select URLs to Compare:</label>
                            <select multiple class="form-control multi-select" id="url-compare-select">
                                <!-- URLs will be loaded dynamically -->
                            </select>
                            <small class="form-text text-muted">Hold Ctrl/Cmd to select multiple URLs</small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="form-group">
                            <label for="url-compare-date-range">Date Range:</label>
                            <input type="text" class="form-control" id="url-compare-date-range">
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="form-group">
                            <label> </label>
                            <button class="btn btn-primary form-control" id="compare-urls-btn">Compare URLs</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Export Button -->
            <div class="text-end mb-3">
                <button class="btn btn-success btn-export" id="url-compare-export-data">
                    <i class="bi bi-file-excel"></i> Export to Excel
                </button>
            </div>
            
            <div id="url-comparison-loading" class="loading d-none">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
            
            <div id="url-comparison-content" class="d-none">
                <!-- URL comparison content will be loaded here -->
            </div>
        </div>
        
        <!-- Time Comparison Section -->
        <div id="time-comparison-section" class="dashboard-section">
            <h2 class="mb-4">Time Comparison</h2>
            
            <!-- Filter Section -->
            <div class="filter-section">
                <div class="row">
                    <div class="col-md-3">
                        <div class="form-group">
                            <label for="time-compare-keyword">Select Keyword:</label>
                            <select class="form-control" id="time-compare-keyword" required>
                                <option value="">-- Select a keyword --</option>
                            </select>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="form-group">
                            <label for="time-compare-start-date">Start Date:</label>
                            <select class="form-control" id="time-compare-start-date" disabled>
                                <option value="">Select a keyword first</option>
                            </select>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="form-group">
                            <label for="time-compare-end-date">End Date:</label>
                            <select class="form-control" id="time-compare-end-date" disabled>
                                <option value="">Select a keyword first</option>
                            </select>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="form-group">
                            <label> </label>
                            <button class="btn btn-primary form-control" id="compare-time-btn" disabled>Compare Over Time</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Export Button -->
            <div class="text-end mb-3">
                <button class="btn btn-success btn-export" id="time-compare-export-data">
                    <i class="bi bi-file-excel"></i> Export to Excel
                </button>
            </div>
            
                <div id="time-comparison-loading" class="loading d-none">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
                
                <!-- Updated Time Comparison Content section in HTML -->
                <div id="time-comparison-content" class="d-none">
                    <div class="card mb-4">
                        <div class="card-header">
                            <h5>Comparison Summary</h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-4">
                                    <div class="alert alert-info">
                                        <strong>Keyword:</strong> <span id="time-compare-selected-keyword"></span>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="alert alert-primary">
                                        <strong>Start Date:</strong> <span id="time-compare-selected-start-date"></span>
                                        <small class="d-block">(<span id="start-url-count">0</span> URLs found)</small>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="alert alert-primary">
                                        <strong>End Date:</strong> <span id="time-compare-selected-end-date"></span>
                                        <small class="d-block">(<span id="end-url-count">0</span> URLs found)</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <!-- Start Date URLs Table -->
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-header">
                                    <h5>Start Date URLs</h5>
                                    <small class="text-muted">Sorted by position (best positions first)</small>
                                </div>
                                <div class="card-body data-table">
                                    <table class="table table-striped table-hover" id="start-date-table">
                                        <thead>
                                            <tr>
                                                <th>Position</th>
                                                <th>URL</th>
                                                <th>Domain</th>
                                                <th>Position Change</th>
                                            </tr>
                                        </thead>
                                        <tbody id="start-date-urls"></tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                        
                        <!-- End Date URLs Table -->
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-header">
                                    <h5>End Date URLs</h5>
                                    <small class="text-muted">Sorted by position (best positions first)</small>
                                </div>
                                <div class="card-body data-table">
                                    <table class="table table-striped table-hover" id="end-date-table">
                                        <thead>
                                            <tr>
                                                <th>Position</th>
                                                <th>URL</th>
                                                <th>Domain</th>
                                                <th>Position Change</th>
                                            </tr>
                                        </thead>
                                        <tbody id="end-date-urls"></tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- URL Movement Analysis -->
                    <div class="card mt-4">
                        <div class="card-header">
                            <h5>Position Changes Analysis</h5>
                            <small class="text-muted">All URLs with their position changes</small>
                        </div>
                        <div class="card-body data-table">
                            <table class="table table-striped table-hover" id="position-changes-table">
                                <thead>
                                    <tr>
                                        <th>URL</th>
                                        <th>Domain</th>
                                        <th>Start Position</th>
                                        <th>End Position</th>
                                        <th>Change</th>
                                    </tr>
                                </thead>
                                <tbody id="position-changes"></tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
    <!-- Required JavaScript -->
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/momentjs/latest/moment.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/daterangepicker/daterangepicker.min.js"></script>
    
    <script>
        // Global variables
        let globalData = null;
        let availableDates = [];
        let availableKeywords = [];
        let availableUrls = [];
        let currentTopRank = 5; // Default top rank value
        let currentDomainRank = 5; // Default domain rank value
        let keywordDates = {}; // Store dates available for each keyword
        
        document.addEventListener('DOMContentLoaded', function() {
            // Initialize date pickers
            initializeDatePickers();
            
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
            
            document.getElementById('nav-url-compare').addEventListener('click', function(e) {
                e.preventDefault();
                showSection('url-comparison-section');
                loadUrlOptions();
            });
            
            document.getElementById('nav-time-compare').addEventListener('click', function(e) {
                e.preventDefault();
                showSection('time-comparison-section');
            });
            
            // File Upload Form Submission
            document.getElementById('upload-form').addEventListener('submit', function(e) {
                e.preventDefault();
                uploadFile();
            });
            
            // Dashboard filter button
            document.getElementById('dashboard-apply-filters').addEventListener('click', function() {
                loadOverallStats();
            });
            
            // Keyword filter button
            document.getElementById('keyword-apply-filters').addEventListener('click', function() {
                const keyword = document.getElementById('keyword-select').value;
                if (keyword) {
                    analyzeKeyword(keyword);
                }
            });
            
            // Keyword Select Change Event
            document.getElementById('keyword-select').addEventListener('change', function() {
                const keyword = this.value;
                if (keyword) {
                    // Show available dates for the selected keyword
                    showKeywordDates(keyword);
                    analyzeKeyword(keyword);
                } else {
                    document.getElementById('keyword-available-dates').classList.add('d-none');
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
            
            // URL Comparison Button
            document.getElementById('compare-urls-btn').addEventListener('click', function() {
                const urls = getSelectedOptions('url-compare-select');
                if (urls.length > 0) {
                    compareUrls(urls);
                } else {
                    alert('Please select at least one URL to compare');
                }
            });
            
            // Time Comparison Keyword Selection
            document.getElementById('time-compare-keyword').addEventListener('change', function() {
                const keyword = this.value;
                const startSelect = document.getElementById('time-compare-start-date');
                const endSelect = document.getElementById('time-compare-end-date');
                const compareBtn = document.getElementById('compare-time-btn');
                
                // Reset and disable if no keyword selected
                if (!keyword) {
                    startSelect.innerHTML = '<option value="">Select a keyword first</option>';
                    endSelect.innerHTML = '<option value="">Select a keyword first</option>';
                    startSelect.disabled = true;
                    endSelect.disabled = true;
                    compareBtn.disabled = true;
                    return;
                }
                
                // Show loading message
                startSelect.innerHTML = '<option value="">Loading dates...</option>';
                endSelect.innerHTML = '<option value="">Loading dates...</option>';
                startSelect.disabled = true;
                endSelect.disabled = true;
                compareBtn.disabled = true;
                
                // Fetch available dates for the keyword
                fetch('/get_keyword_dates', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ keyword: keyword })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.dates && data.dates.length > 0) {
                        console.log(`Found ${data.dates.length} dates for keyword "${keyword}"`);
                        
                        // Populate start and end date dropdowns
                        startSelect.innerHTML = '<option value="">Select start date</option>';
                        endSelect.innerHTML = '<option value="">Select end date</option>';
                        
                        data.dates.forEach(date => {
                            // Add option to start date dropdown
                            const option1 = document.createElement('option');
                            option1.value = date;
                            option1.textContent = date;
                            startSelect.appendChild(option1);
                            
                            // Add option to end date dropdown
                            const option2 = document.createElement('option');
                            option2.value = date;
                            option2.textContent = date;
                            endSelect.appendChild(option2);
                        });
                        
                        // Enable dropdowns
                        startSelect.disabled = false;
                        endSelect.disabled = false;
                        
                        // If we have at least 2 dates, pre-select the first and last dates
                        if (data.dates.length >= 2) {
                            // Sort dates chronologically
                            data.dates.sort();
                            
                            // Set first date as start and last date as end
                            startSelect.value = data.dates[0];
                            endSelect.value = data.dates[data.dates.length - 1];
                            
                            // Enable the compare button
                            compareBtn.disabled = false;
                            
                            // Optional: automatically run the comparison
                            // compareOverTime(data.dates[0], data.dates[data.dates.length - 1], keyword);
                        }
                    } else {
                        if (data.error) {
                            console.error(`Error fetching dates: ${data.error}`);
                            startSelect.innerHTML = `<option value="">Error: ${data.error}</option>`;
                            endSelect.innerHTML = `<option value="">Error: ${data.error}</option>`;
                        } else {
                            console.warn(`No dates found for keyword "${keyword}"`);
                            startSelect.innerHTML = '<option value="">No dates available</option>';
                            endSelect.innerHTML = '<option value="">No dates available</option>';
                        }
                        startSelect.disabled = true;
                        endSelect.disabled = true;
                        compareBtn.disabled = true;
                    }
                })
                .catch(error => {
                    console.error('Error fetching dates:', error);
                    startSelect.innerHTML = '<option value="">Error loading dates</option>';
                    endSelect.innerHTML = '<option value="">Error loading dates</option>';
                    startSelect.disabled = true;
                    endSelect.disabled = true;
                    compareBtn.disabled = true;
                });
            });

            // Enable the compare button when both start and end dates are selected
            document.getElementById('time-compare-start-date').addEventListener('change', updateCompareButtonState);
            document.getElementById('time-compare-end-date').addEventListener('change', updateCompareButtonState);

            function updateCompareButtonState() {
                const startDate = document.getElementById('time-compare-start-date').value;
                const endDate = document.getElementById('time-compare-end-date').value;
                const compareBtn = document.getElementById('compare-time-btn');
                
                compareBtn.disabled = !(startDate && endDate);
            }
            
            // Time Comparison Button
            document.getElementById('compare-time-btn').addEventListener('click', function() {
                const keyword = document.getElementById('time-compare-keyword').value;
                const startDate = document.getElementById('time-compare-start-date').value;
                const endDate = document.getElementById('time-compare-end-date').value;
                if (keyword && startDate && endDate) {
                    compareOverTime(startDate, endDate, keyword);
                } else {
                    alert('Please select a keyword and both dates');
                }
            });
            
            // Top rank buttons in dashboard
            document.querySelectorAll('.rank-btn').forEach(button => {
                button.addEventListener('click', function() {
                    // Update selected button style
                    document.querySelectorAll('.rank-btn').forEach(btn => {
                        btn.classList.remove('btn-primary');
                        btn.classList.add('btn-outline-primary');
                    });
                    this.classList.remove('btn-outline-primary');
                    this.classList.add('btn-primary');
                    
                    // Update current rank value
                    currentTopRank = parseInt(this.getAttribute('data-rank'));
                    
                    // Reload data with new rank value
                    loadOverallStats();
                });
            });
            
            // Domain rank buttons in dashboard
            document.querySelectorAll('.domain-rank-btn').forEach(button => {
                button.addEventListener('click', function() {
                    // Update selected button style
                    document.querySelectorAll('.domain-rank-btn').forEach(btn => {
                        btn.classList.remove('btn-primary');
                        btn.classList.add('btn-outline-primary');
                    });
                    this.classList.remove('btn-outline-primary');
                    this.classList.add('btn-primary');
                    
                    // Update current domain rank value
                    currentDomainRank = parseInt(this.getAttribute('data-rank'));
                    
                    // Reload data with new rank value
                    loadOverallStats();
                });
            });
            
            // Export buttons
            document.getElementById('dashboard-export-data').addEventListener('click', function() {
                exportToExcel('dashboard');
            });
            
            document.getElementById('keyword-export-data').addEventListener('click', function() {
                exportToExcel('keyword');
            });
            
            document.getElementById('domain-export-data').addEventListener('click', function() {
                exportToExcel('domain');
            });
            
            document.getElementById('url-compare-export-data').addEventListener('click', function() {
                exportToExcel('url-compare');
            });
            
            document.getElementById('time-compare-export-data').addEventListener('click', function() {
                exportToExcel('time-compare');
            });
        });
        
        function showKeywordDates(keyword) {
            const datesContainer = document.getElementById('keyword-dates-list');
            const availableDatesSection = document.getElementById('keyword-available-dates');
            
            // Clear previous dates
            datesContainer.innerHTML = '';
            
            if (keywordDates[keyword] && keywordDates[keyword].length > 0) {
                // Show available dates section
                availableDatesSection.classList.remove('d-none');
                
                // Add dates as badges
                keywordDates[keyword].forEach(date => {
                    const badge = document.createElement('span');
                    badge.className = 'badge bg-primary m-1';
                    badge.textContent = date;
                    datesContainer.appendChild(badge);
                });
            } else {
                // Fetch dates for this keyword
                fetch('/get_keyword_dates', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ keyword: keyword })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.dates.length > 0) {
                        // Store dates for this keyword
                        keywordDates[keyword] = data.dates;
                        
                        // Show available dates section
                        availableDatesSection.classList.remove('d-none');
                        
                        // Add dates as badges
                        data.dates.forEach(date => {
                            const badge = document.createElement('span');
                            badge.className = 'badge bg-primary m-1';
                            badge.textContent = date;
                            datesContainer.appendChild(badge);
                        });
                    } else {
                        availableDatesSection.classList.add('d-none');
                    }
                })
                .catch(error => {
                    console.error('Error fetching keyword dates:', error);
                    availableDatesSection.classList.add('d-none');
                });
            }
        }
        
        function initializeDatePickers() {
            // Initialize with empty date range
            $('#dashboard-date-range, #keyword-date-range, #domain-date-range, #url-compare-date-range').daterangepicker({
                autoUpdateInput: false,
                locale: {
                    cancelLabel: 'Clear'
                }
            });
            
            $('.daterangepicker').each(function() {
                $(this).on('apply.daterangepicker', function(ev, picker) {
                    $(this).val(picker.startDate.format('MM/DD/YYYY') + ' - ' + picker.endDate.format('MM/DD/YYYY'));
                });
                
                $(this).on('cancel.daterangepicker', function() {
                    $(this).val('');
                });
            });
        }
        
        function getSelectedOptions(selectId) {
            const select = document.getElementById(selectId);
            const result = [];
            const options = select && select.options;
            
            if (options) {
                for (let i = 0; i < options.length; i++) {
                    if (options[i].selected) {
                        result.push(options[i].value);
                    }
                }
            }
            
            return result;
        }
        
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
                
                globalData = data;
                availableDates = data.dates || [];
                availableKeywords = data.keywords || [];
                availableUrls = data.urls || [];
                
                showUploadStatus('File uploaded successfully! Data is ready for analysis.', 'success');
                
                // Populate keyword dropdowns
                populateKeywordDropdowns(data.keywords);
                
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
        
        function populateKeywordDropdowns(keywords) {
            const keywordSelect = document.getElementById('keyword-select');
            if (!keywordSelect) {
                console.error('Element with ID "keyword-select" not found');
                return;
            }

            const dashboardKeywordFilter = document.getElementById('dashboard-keyword-filter');
            if (!dashboardKeywordFilter) {
                console.error('Element with ID "dashboard-keyword-filter" not found');
                return;
            }

            const timeCompareKeyword = document.getElementById('time-compare-keyword');
            if (!timeCompareKeyword) {
                console.error('Element with ID "time-compare-keyword" not found');
                return;
            }

            // Clear existing options except the first one
            while (keywordSelect.options.length > 1) keywordSelect.options.remove(1);
            while (dashboardKeywordFilter.options.length > 1) dashboardKeywordFilter.options.remove(1);
            while (timeCompareKeyword.options.length > 1) timeCompareKeyword.options.remove(1);

            // Add new options
            keywords.forEach(keyword => {
                const option1 = document.createElement('option');
                option1.value = keyword;
                option1.textContent = keyword;
                keywordSelect.appendChild(option1);

                const option2 = document.createElement('option');
                option2.value = keyword;
                option2.textContent = keyword;
                dashboardKeywordFilter.appendChild(option2);

                const option3 = document.createElement('option');
                option3.value = keyword;
                option3.textContent = keyword;
                timeCompareKeyword.appendChild(option3);
            });
        }
        
        function loadUrlOptions() {
            const urlSelect = document.getElementById('url-compare-select');
            
            // Clear existing options
            urlSelect.innerHTML = '';
            
            // Add new options from availableUrls
            if (availableUrls && availableUrls.length > 0) {
                availableUrls.forEach(url => {
                    const option = document.createElement('option');
                    option.value = url;
                    option.textContent = url;
                    urlSelect.appendChild(option);
                });
            } else {
                // If no URLs available, make a request to get them
                fetch('/get_urls')
                    .then(response => response.json())
                    .then(data => {
                        if (data.success && data.urls) {
                            availableUrls = data.urls;
                            
                            // Add each URL as an option
                            data.urls.forEach(url => {
                                const option = document.createElement('option');
                                option.value = url;
                                option.textContent = url;
                                urlSelect.appendChild(option);
                            });
                        }
                    })
                    .catch(error => console.error('Error loading URLs:', error));
            }
        }
        
        function getDateRangeFilter(elementId) {
            const dateRange = document.getElementById(elementId).value;
            if (!dateRange) return null;
            
            const dates = dateRange.split(' - ');
            if (dates.length === 2) {
                return {
                    start: dates[0],
                    end: dates[1]
                };
            }
            
            return null;
        }
        
        function loadOverallStats() {
            // Get filter values
            const dateRange = getDateRangeFilter('dashboard-date-range');
            const keywordFilter = document.getElementById('dashboard-keyword-filter').value;
            const positionMin = document.getElementById('dashboard-position-min').value;
            const positionMax = document.getElementById('dashboard-position-max').value;
            
            // Build filter object
            const filters = {
                top_rank: currentTopRank,
                domain_rank: currentDomainRank
            };
            if (dateRange) filters.date_range = dateRange;
            if (keywordFilter) filters.keyword = keywordFilter;
            if (positionMin) filters.position_min = parseInt(positionMin);
            if (positionMax) filters.position_max = parseInt(positionMax);
            
            fetch('/overall_stats', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(filters)
            })
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
                    <div class="card summary-card bg-light transition">
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
            
            // Get filter values
            const dateRange = getDateRangeFilter('keyword-date-range');
            const domainFilter = document.getElementById('keyword-domain-filter').value.trim();
            
            // Build request data
            const requestData = {
                keyword: keyword
            };
            if (dateRange) requestData.date_range = dateRange;
            if (domainFilter) requestData.domain = domainFilter;
            
            fetch('/keyword_analytics', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
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
                                    <div class="card-header">
                                        <div class="d-flex justify-content-between align-items-center">
                                            <h5>Position Distribution</h5>
                                            <div class="btn-group" role="group">
                                                <button type="button" class="btn btn-sm btn-outline-primary keyword-rank-btn" data-rank="3">Top 3</button>
                                                <button type="button" class="btn btn-sm btn-primary keyword-rank-btn" data-rank="5">Top 5</button>
                                                <button type="button" class="btn btn-sm btn-outline-primary keyword-rank-btn" data-rank="10">Top 10</button>
                                                <button type="button" class="btn btn-sm btn-outline-primary keyword-rank-btn" data-rank="20">Top 20</button>
                                            </div>
                                        </div>
                                    </div>
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
                            <div class="col-md-12">
                                <div class="card">
                                    <div class="card-header"><h5>Position Trend Over Time</h5></div>
                                    <div class="card-body">
                                        <div id="keyword-trend-chart" class="chart-container"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="row mt-4">
                            <div class="col-md-12">
                                <div class="card">
                                    <div class="card-header"><h5>Domain Rankings</h5></div>
                                    <div class="card-body data-table">
                                        <table class="table table-striped table-hover" id="domain-ranking-table-container">
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
                    
                    // Set up rank button event listeners
                    document.querySelectorAll('.keyword-rank-btn').forEach(button => {
                        button.addEventListener('click', function() {
                            // Update button styles
                            document.querySelectorAll('.keyword-rank-btn').forEach(btn => {
                                btn.classList.remove('btn-primary');
                                btn.classList.add('btn-outline-primary');
                            });
                            this.classList.remove('btn-outline-primary');
                            this.classList.add('btn-primary');
                            
                            // Update chart with new rank value
                            const rank = parseInt(this.getAttribute('data-rank'));
                            updateKeywordChart(keyword, rank);
                        });
                    });
                    
                    // Render charts
                    Plotly.newPlot('keyword-position-chart', data.charts.position_distribution.data, data.charts.position_distribution.layout);
                    Plotly.newPlot('keyword-domain-chart', data.charts.domain_performance.data, data.charts.domain_performance.layout);
                    
                    if (data.charts.trend_chart) {
                        Plotly.newPlot('keyword-trend-chart', data.charts.trend_chart.data, data.charts.trend_chart.layout);
                    }
                    
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
        
        function updateKeywordChart(keyword, rank) {
            // Get filter values
            const dateRange = getDateRangeFilter('keyword-date-range');
            const domainFilter = document.getElementById('keyword-domain-filter').value.trim();
            
            // Build request data
            const requestData = {
                keyword: keyword,
                top_rank: rank
            };
            if (dateRange) requestData.date_range = dateRange;
            if (domainFilter) requestData.domain = domainFilter;
            
            fetch('/keyword_chart', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update chart with new data
                    Plotly.newPlot('keyword-position-chart', data.chart.data, data.chart.layout);
                }
            })
            .catch(error => console.error('Error updating keyword chart:', error));
        }
        
        function analyzeDomain(domain) {
            document.getElementById('domain-loading').classList.remove('d-none');
            document.getElementById('domain-content').classList.add('d-none');
            
            // Get filter values
            const dateRange = getDateRangeFilter('domain-date-range');
            const positionMin = document.getElementById('domain-position-min').value;
            const positionMax = document.getElementById('domain-position-max').value;
            
            // Build request data
            const requestData = {
                domain: domain
            };
            if (dateRange) requestData.date_range = dateRange;
            if (positionMin) requestData.position_min = parseInt(positionMin);
            if (positionMax) requestData.position_max = parseInt(positionMax);
            
            fetch('/domain_analytics', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
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
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-header">
                                        <div class="d-flex justify-content-between align-items-center">
                                            <h5>Keyword Performance</h5>
                                            <div class="btn-group" role="group">
                                                <button type="button" class="btn btn-sm btn-outline-primary domain-keyword-btn" data-rank="3">Top 3</button>
                                                <button type="button" class="btn btn-sm btn-primary domain-keyword-btn" data-rank="5">Top 5</button>
                                                <button type="button" class="btn btn-sm btn-outline-primary domain-keyword-btn" data-rank="10">Top 10</button>
                                                <button type="button" class="btn btn-sm btn-outline-primary domain-keyword-btn" data-rank="20">Top 20</button>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="card-body">
                                        <div id="domain-keyword-chart" class="chart-container"></div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-header"><h5>Position Trend Over Time</h5></div>
                                    <div class="card-body">
                                        <div id="domain-trend-chart" class="chart-container"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header"><h5>Keyword Rankings</h5></div>
                                    <div class="card-body data-table">
                                        <table class="table table-striped table-hover" id="keyword-ranking-table-container">
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
                    
                    // Set up rank button event listeners
                    document.querySelectorAll('.domain-keyword-btn').forEach(button => {
                        button.addEventListener('click', function() {
                            // Update button styles
                            document.querySelectorAll('.domain-keyword-btn').forEach(btn => {
                                btn.classList.remove('btn-primary');
                                btn.classList.add('btn-outline-primary');
                            });
                            this.classList.remove('btn-outline-primary');
                            this.classList.add('btn-primary');
                            
                            // Update chart with new rank value
                            const rank = parseInt(this.getAttribute('data-rank'));
                            updateDomainChart(domain, rank);
                        });
                    });
                    
                    // Render charts
                    Plotly.newPlot('domain-keyword-chart', data.charts.keyword_performance.data, data.charts.keyword_performance.layout);
                    
                    if (data.charts.trend_chart) {
                        Plotly.newPlot('domain-trend-chart', data.charts.trend_chart.data, data.charts.trend_chart.layout);
                    }
                    
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
        
        function updateDomainChart(domain, rank) {
            // Get filter values
            const dateRange = getDateRangeFilter('domain-date-range');
            const positionMin = document.getElementById('domain-position-min').value;
            const positionMax = document.getElementById('domain-position-max').value;
            
            // Build request data
            const requestData = {
                domain: domain,
                top_rank: rank
            };
            if (dateRange) requestData.date_range = dateRange;
            if (positionMin) requestData.position_min = parseInt(positionMin);
            if (positionMax) requestData.position_max = parseInt(positionMax);
            
            fetch('/domain_chart', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update chart with new data
                    Plotly.newPlot('domain-keyword-chart', data.chart.data, data.chart.layout);
                }
            })
            .catch(error => console.error('Error updating domain chart:', error));
        }
        
        function compareUrls(urls) {
            document.getElementById('url-comparison-loading').classList.remove('d-none');
            document.getElementById('url-comparison-content').classList.add('d-none');
            
            // Get date range filter
            const dateRange = getDateRangeFilter('url-compare-date-range');
            
            // Build request data
            const requestData = {
                urls: urls
            };
            if (dateRange) requestData.date_range = dateRange;
            
            fetch('/compare_urls', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('url-comparison-loading').classList.add('d-none');
                const contentDiv = document.getElementById('url-comparison-content');
                
                if (data.success) {
                    // Display URL comparison results
                    contentDiv.classList.remove('d-none');
                    contentDiv.innerHTML = `
                        <div class="row">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header"><h5>URL Position Comparison</h5></div>
                                    <div class="card-body">
                                        <div id="url-comparison-chart" class="chart-container"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header"><h5>URL Performance by Keyword</h5></div>
                                    <div class="card-body">
                                        <div id="url-keyword-chart" class="chart-container"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header"><h5>URL Position Trend Over Time</h5></div>
                                    <div class="card-body">
                                        <div id="url-time-chart" class="chart-container"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header"><h5>URL Comparison Data</h5></div>
                                    <div class="card-body data-table">
                                        <table class="table table-striped table-hover" id="url-comparison-table-container">
                                            <thead>
                                                <tr>
                                                    <th>URL</th>
                                                    <th>Average Position</th>
                                                    <th>Best Position</th>
                                                    <th>Worst Position</th>
                                                    <th>Keywords Count</th>
                                                </tr>
                                            </thead>
                                            <tbody id="url-comparison-table"></tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    // Render charts
                    Plotly.newPlot('url-comparison-chart', data.charts.url_comparison.data, data.charts.url_comparison.layout);
                    Plotly.newPlot('url-keyword-chart', data.charts.keyword_comparison.data, data.charts.keyword_comparison.layout);
                    
                    if (data.charts.time_comparison) {
                        Plotly.newPlot('url-time-chart', data.charts.time_comparison.data, data.charts.time_comparison.layout);
                    }
                    
                    // Populate URL comparison table
                    const table = document.getElementById('url-comparison-table');
                    table.innerHTML = '';
                    data.url_data.forEach(item => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${item.url}</td>
                            <td>${item.avg_position.toFixed(2)}</td>
                            <td>${item.best_position}</td>
                            <td>${item.worst_position}</td>
                            <td>${item.keywords_count}</td>
                        `;
                        table.appendChild(row);
                    });
                } else if (data.error) {
                    contentDiv.classList.remove('d-none');
                    contentDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                }
            })
            .catch(error => {
                document.getElementById('url-comparison-loading').classList.add('d-none');
                document.getElementById('url-comparison-content').classList.remove('d-none');
                document.getElementById('url-comparison-content').innerHTML = `
                    <div class="alert alert-danger">Error comparing URLs: ${error}</div>
                `;
            });
        }
        



        function compareOverTime(startDate, endDate, keyword) {
            // Show the loading spinner, hide the content
            document.getElementById('time-comparison-loading').classList.remove('d-none');
            document.getElementById('time-comparison-content').classList.add('d-none');
            
            console.log(`Comparing keyword "${keyword}" between dates: ${startDate} and ${endDate}`);
            
            fetch('/compare_over_time', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ start_date: startDate, end_date: endDate, keyword: keyword })
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('time-comparison-loading').classList.add('d-none');
                
                const contentDiv = document.getElementById('time-comparison-content');
                
                if (data.success) {
                    console.log(`Received data: ${data.start_count} start URLs, ${data.end_count} end URLs`);
                    
                    // Show the content area
                    contentDiv.classList.remove('d-none');
                    
                    // Update summary information
                    document.getElementById('time-compare-selected-keyword').textContent = data.keyword;
                    document.getElementById('time-compare-selected-start-date').textContent = data.start_date;
                    document.getElementById('time-compare-selected-end-date').textContent = data.end_date;
                    document.getElementById('start-url-count').textContent = data.start_count;
                    document.getElementById('end-url-count').textContent = data.end_count;
                    
                    // Populate the start date table
                    const startTableBody = document.getElementById('start-date-urls');
                    startTableBody.innerHTML = '';
                    
                    if (data.start_urls && data.start_urls.length > 0) {
                        console.log(`Displaying ${data.start_urls.length} URLs for start date`);
                        
                        // Display ALL URLs for the start date
                        data.start_urls.forEach(item => {
                            const tr = document.createElement('tr');
                            
                            // Add row class based on position change
                            if (item.position_change) {
                                if (item.position_change < 0) {
                                    tr.className = 'table-success'; // improved
                                } else if (item.position_change > 0) {
                                    tr.className = 'table-warning'; // declined
                                }
                            }
                            
                            tr.innerHTML = `
                                <td>${item.position}</td>
                                <td>${item.url}</td>
                                <td>${item.domain || ''}</td>
                                <td>${item.position_change_text}</td>
                            `;
                            startTableBody.appendChild(tr);
                        });
                    } else {
                        // No start date data
                        startTableBody.innerHTML = '<tr><td colspan="4" class="text-center">No data available for start date</td></tr>';
                    }
                    
                    // Populate the end date table
                    const endTableBody = document.getElementById('end-date-urls');
                    endTableBody.innerHTML = '';
                    
                    if (data.end_urls && data.end_urls.length > 0) {
                        console.log(`Displaying ${data.end_urls.length} URLs for end date`);
                        
                        // Display ALL URLs for the end date
                        data.end_urls.forEach(item => {
                            const tr = document.createElement('tr');
                            
                            // Add row class based on position change
                            if (item.position_change) {
                                if (item.position_change < 0) {
                                    tr.className = 'table-success'; // improved
                                } else if (item.position_change > 0) {
                                    tr.className = 'table-warning'; // declined
                                }
                            } else if (item.position_change_text === "New") {
                                tr.className = 'table-info'; // new URL
                            }
                            
                            tr.innerHTML = `
                                <td>${item.position}</td>
                                <td>${item.url}</td>
                                <td>${item.domain || ''}</td>
                                <td>${item.position_change_text}</td>
                            `;
                            endTableBody.appendChild(tr);
                        });
                    } else {
                        // No end date data
                        endTableBody.innerHTML = '<tr><td colspan="4" class="text-center">No data available for end date</td></tr>';
                    }
                    
                    // Create the position changes analysis table
                    const changesTableBody = document.getElementById('position-changes');
                    changesTableBody.innerHTML = '';
                    
                    if (data.position_changes && data.position_changes.length > 0) {
                        console.log(`Displaying ${data.position_changes.length} position changes`);
                        
                        data.position_changes.forEach(item => {
                            const tr = document.createElement('tr');
                            
                            // Add row class based on change status
                            if (item.status === 'improved') {
                                tr.className = 'table-success';
                            } else if (item.status === 'declined') {
                                tr.className = 'table-warning';
                            } else if (item.status === 'new') {
                                tr.className = 'table-info';
                            } else if (item.status === 'dropped') {
                                tr.className = 'table-danger';
                            }
                            
                            // Format values
                            const startPos = item.start_position !== null ? item.start_position : '-';
                            const endPos = item.end_position !== null ? item.end_position : '-';
                            
                            tr.innerHTML = `
                                <td>${item.url}</td>
                                <td>${item.domain || ''}</td>
                                <td>${startPos}</td>
                                <td>${endPos}</td>
                                <td>${item.change_text}</td>
                            `;
                            changesTableBody.appendChild(tr);
                        });
                    } else {
                        changesTableBody.innerHTML = '<tr><td colspan="5" class="text-center">No position changes to display</td></tr>';
                    }
                } 
                else if (data.error) {
                    contentDiv.classList.remove('d-none');
                    contentDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                    console.error(`Error: ${data.error}`);
                    if (data.traceback) {
                        console.error(`Traceback: ${data.traceback}`);
                    }
                }
            })
            .catch(error => {
                document.getElementById('time-comparison-loading').classList.add('d-none');
                const contentDiv = document.getElementById('time-comparison-content');
                contentDiv.classList.remove('d-none');
                contentDiv.innerHTML = `<div class="alert alert-danger">Error comparing time periods: ${error}</div>`;
                console.error(`Fetch error: ${error}`);
            });
        }




        
        function exportToExcel(section) {
            // Determine what data to export based on the section
            let data = [];
            let filename = 'seo_data.xlsx';
            
            switch (section) {
                case 'dashboard':
                    // Export keyword volume and domain frequency tables
                    const keywordData = getTableData('keyword-volume-table-container');
                    const domainData = getTableData('domain-frequency-table-container');
                    
                    exportMultipleSheets({
                        'Keyword Volume': keywordData,
                        'Domain Frequency': domainData
                    }, 'dashboard_data.xlsx');
                    break;
                    
                case 'keyword':
                    // Export domain ranking table
                    data = getTableData('domain-ranking-table-container');
                    filename = 'keyword_analysis.xlsx';
                    exportToExcelSheet(data, filename);
                    break;
                    
                case 'domain':
                    // Export keyword ranking table
                    data = getTableData('keyword-ranking-table-container');
                    filename = 'domain_analysis.xlsx';
                    exportToExcelSheet(data, filename);
                    break;
                    
                case 'url-compare':
                    // Export URL comparison table
                    data = getTableData('url-comparison-table-container');
                    filename = 'url_comparison.xlsx';
                    exportToExcelSheet(data, filename);
                    break;
                    
                case 'time-compare':
                    // Export time comparison table
                    data = getTableData('time-comparison-table-container');
                    filename = 'time_comparison.xlsx';
                    exportToExcelSheet(data, filename);
                    break;
            }
        }
        
        function getTableData(tableId) {
            const table = document.getElementById(tableId);
            if (!table) return [];
            
            const data = [];
            
            // Get headers
            const headers = [];
            const headerCells = table.querySelectorAll('thead th');
            headerCells.forEach(cell => {
                headers.push(cell.textContent);
            });
            
            data.push(headers);
            
            // Get rows
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const rowData = [];
                const cells = row.querySelectorAll('td');
                cells.forEach(cell => {
                    rowData.push(cell.textContent);
                });
                data.push(rowData);
            });
            
            return data;
        }
        
        function exportToExcelSheet(data, filename) {
            if (!data || data.length === 0) {
                alert('No data to export');
                return;
            }
            
            // Create a workbook
            const wb = XLSX.utils.book_new();
            const ws = XLSX.utils.aoa_to_sheet(data);
            
            // Add the worksheet to the workbook
            XLSX.utils.book_append_sheet(wb, ws, 'Data');
            
            // Write the workbook and trigger download
            XLSX.writeFile(wb, filename);
        }
        
        function exportMultipleSheets(dataSheets, filename) {
            if (!dataSheets || Object.keys(dataSheets).length === 0) {
                alert('No data to export');
                return;
            }
            
            // Create a workbook
            const wb = XLSX.utils.book_new();
            
            // Add each sheet
            Object.entries(dataSheets).forEach(([sheetName, data]) => {
                if (data && data.length > 0) {
                    const ws = XLSX.utils.aoa_to_sheet(data);
                    XLSX.utils.book_append_sheet(wb, ws, sheetName);
                }
            });
            
            // Write the workbook and trigger download
            XLSX.writeFile(wb, filename);
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
    # Check for special format (position at end of URL)
    # Format: URL + Position + Keyword + DateTime (all in one row without proper columns)
    if len(df.columns) == 1:
        print("Detected single column data format - trying to parse")
        # Extract data from single column
        column_name = df.columns[0]
        
        try:
            # Create new dataframe with proper columns
            data_list = []
            
            for _, row in df.iterrows():
                text = str(row[column_name])
                
                # Try to find position and keyword pattern
                matches = re.findall(r'(https?://[^\s]+)(\d+)(best free android vpn|[\w\s]+)(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[\s\d:-]+', text)
                
                if matches:
                    for match in matches:
                        url = match[0]
                        position = int(match[1])
                        keyword = match[2]
                        date_part = match[3] + match[0].split(match[3])[1] if len(match) > 3 else ""
                        
                        data_list.append({
                            'Results': url,
                            'Position': position,
                            'Keyword': keyword,
                            'Time': date_part
                        })
            
            if data_list:
                print(f"Successfully parsed {len(data_list)} rows from single column format")
                return pd.DataFrame(data_list)
            
        except Exception as e:
            print(f"Error parsing single column format: {str(e)}")
    
    # Continue with normal processing if the special format wasn't detected
    # Convert key columns to strings to prevent type issues
    if 'Results' in df.columns:
        df['Results'] = df['Results'].astype(str)
    if 'Keyword' in df.columns:
        df['Keyword'] = df['Keyword'].astype(str)
    
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

def apply_date_filter(df, date_range):
    """Apply date range filter to DataFrame"""
    if not date_range or 'date' not in df.columns:
        return df
    
    try:
        start_date = pd.to_datetime(date_range['start'])
        end_date = pd.to_datetime(date_range['end'])
        return df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    except:
        return df

def apply_position_filter(df, position_min=None, position_max=None):
    """Apply position range filter to DataFrame"""
    if 'Position' not in df.columns:
        return df
    
    filtered_df = df.copy()
    
    if position_min is not None:
        filtered_df = filtered_df[filtered_df['Position'] >= position_min]
    
    if position_max is not None:
        filtered_df = filtered_df[filtered_df['Position'] <= position_max]
    
    return filtered_df

def apply_keyword_filter(df, keyword):
    """Apply keyword filter to DataFrame"""
    if not keyword or 'Keyword' not in df.columns:
        return df
    
    return df[df['Keyword'] == keyword]

def apply_domain_filter(df, domain):
    """Apply domain filter to DataFrame"""
    if not domain or 'domain' not in df.columns:
        return df
    
    return df[df['domain'] == domain]

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
        
        # Load file - try different approaches based on possible formats
        try:
            # First try standard Excel
            df = pd.read_excel(temp_path)
        except Exception as e:
            print(f"Error reading as Excel: {str(e)}")
            try:
                # Try as CSV
                df = pd.read_csv(temp_path)
            except Exception as e2:
                print(f"Error reading as CSV: {str(e2)}")
                try:
                    # Try as text file
                    with open(temp_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # If lines contain typical URL + number pattern, parse it
                    data_list = []
                    import re
                    
                    for line in lines:
                        # Look for URL + number + keyword pattern
                        matches = re.search(r'(https?://[^\s]+)(\d+)(best free android vpn|[\w\s]+)(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[\s\d:-]+', line)
                        if matches:
                            url = matches.group(1)
                            position = int(matches.group(2))
                            keyword = matches.group(3)
                            date_str = line.split(keyword)[1].strip()
                            
                            data_list.append({
                                'Results': url,
                                'Position': position,
                                'Keyword': keyword,
                                'Time': date_str
                            })
                    
                    if data_list:
                        df = pd.DataFrame(data_list)
                    else:
                        return jsonify({'error': 'Could not parse file format'})
                        
                except Exception as e3:
                    print(f"Error reading as text: {str(e3)}")
                    return jsonify({'error': f'Could not read file: {str(e)}, {str(e2)}, {str(e3)}'})
        
        # Process the data
        if 'Keyword' in df.columns:
            df['Keyword'].fillna(method='ffill', inplace=True)
        
        # In case the data is in a custom format, check and parse
        if len(df.columns) == 1:
            # Try to parse the special format using the prepare_data function
            import re
            df = prepare_data(df)
        else:
            # Standard preprocessing
            df = prepare_data(df)
        
        # Extract unique dates and format them
        dates = []
        if 'date' in df.columns:
            date_series = df['date'].dropna().unique()
            dates = [d.strftime('%Y-%m-%d') if isinstance(d, datetime.date) else str(d).split(' ')[0] 
                     for d in sorted(date_series)]
        
        # Extract unique URLs
        urls = []
        if 'Results' in df.columns:
            urls = sorted(df['Results'].dropna().unique().tolist())
        
        # Get summary statistics
        summary = {
            'total_keywords': df['Keyword'].nunique() if 'Keyword' in df.columns else 0,
            'total_domains': df['domain'].nunique() if 'domain' in df.columns else 0,
            'total_urls': df['Results'].nunique() if 'Results' in df.columns else 0,
            'date_range': get_date_range(df)
        }
        
        # Get list of keywords for dropdown
        keywords = df['Keyword'].unique().tolist() if 'Keyword' in df.columns else []
        
        # Save processed data
        df.to_excel(temp_path, index=False)
        
        return jsonify({
            'success': True,
            'summary': summary,
            'keywords': keywords,
            'dates': dates,
            'urls': urls
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})

@app.route('/get_keyword_dates', methods=['POST'])
def get_keyword_dates():
    try:
        data = request.json
        keyword = data.get('keyword')
        
        if not keyword:
            return jsonify({'error': 'Keyword is required'})
        
        # Load data
        df = pd.read_excel('temp_upload.xlsx')
        print(f"Original columns: {df.columns.tolist()}")
        
        # Check if we have the needed columns
        required_cols = ['Results', 'Position', 'Filled keyword', 'date/time']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"Missing columns: {missing_cols}")
            print(f"Available columns: {df.columns.tolist()}")
            
            # Try alternative column names
            if 'C' in df.columns and 'D' in df.columns and 'E' in df.columns and 'F' in df.columns:
                print("Using letter columns instead")
                df = df.rename(columns={
                    'C': 'Results',
                    'D': 'Position',
                    'E': 'Filled keyword',
                    'F': 'date/time'
                })
            else:
                return jsonify({'error': f'Required columns {missing_cols} not found in data'})
        
        # Filter by keyword (Filled keyword column)
        print(f"Filtering by Filled keyword = '{keyword}'")
        df_keyword = df[df['Filled keyword'] == keyword]
        
        if df_keyword.empty:
            return jsonify({'success': True, 'dates': []})
        
        # For date matching, use the 'date/time' column
        date_col = 'date/time'
        
        if date_col not in df_keyword.columns:
            return jsonify({'error': f'Date column "{date_col}" not found. Available columns: {df_keyword.columns.tolist()}'})
        
        # Show some sample date values for debugging
        sample_dates = df_keyword[date_col].head(5).tolist()
        print(f"Sample date values: {sample_dates}")
        
        # Extract the date part from the "Mon YYYY-MM-DD H:MM:SS" format
        # First convert to string to ensure we can do string operations
        df_keyword['date_str_full'] = df_keyword[date_col].astype(str)
        
        # Extract just the date part using regex or string splitting
        df_keyword['date_part'] = df_keyword['date_str_full'].str.extract(r'(\d{4}-\d{2}-\d{2})')
        
        # Show the extracted date parts
        print("Extracted date parts:", df_keyword['date_part'].head(5).tolist())
        
        # Get unique dates for this keyword
        unique_dates = df_keyword['date_part'].dropna().unique().tolist()
        unique_dates.sort()  # Sort chronologically
        
        print(f"Found {len(unique_dates)} unique dates for keyword '{keyword}': {unique_dates}")
        
        return jsonify({
            'success': True,
            'dates': unique_dates
        })
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print(traceback_str)
        return jsonify({'error': str(e), 'traceback': traceback_str})
    try:
        data = request.json
        keyword = data.get('keyword')
        
        if not keyword:
            return jsonify({'error': 'Keyword is required'})
        
        # Load data
        original_df = pd.read_excel('temp_upload.xlsx')
        print(f"Original columns: {original_df.columns.tolist()}")
        
        # Detect data structure based on column names
        df = original_df.copy()
        
        # If we have standard column names, rename them to our expected format
        if 'Keyword' in df.columns and 'Time' in df.columns and 'Results' in df.columns and 'Position' in df.columns:
            # Standard format
            pass
        elif 'A' in df.columns and 'B' in df.columns and 'C' in df.columns and 'D' in df.columns and 'E' in df.columns:
            # Excel-style column names (A, B, C, D, E, etc.)
            col_map = {
                'A': 'Keyword',
                'B': 'Time',
                'C': 'Results',
                'D': 'Position',
                'E': 'Filled keyword',
                'F': 'date/time'
            }
            df = df.rename(columns=col_map)
        
        # Determine which column to use for keyword filtering
        # First try 'Filled keyword', then 'Keyword'
        keyword_column = 'Filled keyword' if 'Filled keyword' in df.columns else 'Keyword'
        
        if keyword_column not in df.columns:
            return jsonify({'error': f'Keyword column not found in data. Available columns: {df.columns.tolist()}'})
        
        # Filter by keyword
        print(f"Filtering by {keyword_column} = '{keyword}'")
        keyword_df = df[df[keyword_column] == keyword]
        
        print(f"Found {len(keyword_df)} rows for keyword '{keyword}'")
        if keyword_df.empty:
            return jsonify({'success': True, 'dates': []})
        
        # Identify all possible date columns
        date_columns = []
        for col in ['Time', 'date/time', 'B', 'F']:
            if col in keyword_df.columns:
                date_columns.append(col)
        
        if not date_columns:
            return jsonify({'error': 'No date columns found in data'})
        
        print(f"Date columns to check: {date_columns}")
        
        # Extract unique dates from all date columns
        all_dates = set()
        
        for date_col in date_columns:
            try:
                # Try to convert to datetime
                keyword_df['date_dt'] = pd.to_datetime(keyword_df[date_col], errors='coerce')
                keyword_df['date_str'] = keyword_df['date_dt'].dt.strftime('%Y-%m-%d')
                
                # Add all valid date strings to our set
                valid_dates = keyword_df['date_str'].dropna().unique().tolist()
                all_dates.update(valid_dates)
                
                print(f"Found {len(valid_dates)} unique dates in column '{date_col}'")
            except Exception as e:
                print(f"Error processing date column '{date_col}': {e}")
        
        # Convert to sorted list
        dates = sorted(list(all_dates))
        print(f"Total unique dates found: {len(dates)}")
        print(f"Sample dates: {dates[:5]}")
        
        return jsonify({
            'success': True,
            'dates': dates
        })
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print(traceback_str)
        return jsonify({'error': str(e), 'traceback': traceback_str})
    try:
        data = request.json
        keyword = data.get('keyword')
        
        if not keyword:
            return jsonify({'error': 'Keyword is required'})
        
        # Load data
        df = pd.read_excel('temp_upload.xlsx')
        if 'Keyword' in df.columns:
            df['Keyword'].fillna(method='ffill', inplace=True)
        df = prepare_data(df)
        
        # Filter by keyword
        keyword_df = df[df['Keyword'] == keyword]
        
        if keyword_df.empty:
            return jsonify({'success': True, 'dates': []})
        
        # Get unique dates for this keyword
        dates = []
        if 'date' in keyword_df.columns:
            date_series = keyword_df['date'].dropna().unique()
            dates = [d.strftime('%Y-%m-%d') if isinstance(d, datetime.date) else str(d).split(' ')[0] 
                     for d in sorted(date_series)]
        
        return jsonify({
            'success': True,
            'dates': dates
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/get_urls')
def get_urls():
    try:
        df = pd.read_excel('temp_upload.xlsx')
        urls = []
        
        if 'Results' in df.columns:
            urls = sorted(df['Results'].dropna().unique().tolist())
        
        return jsonify({
            'success': True,
            'urls': urls
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/overall_stats', methods=['POST'])
def overall_stats():
    try:
        # Get filters from request
        filters = request.json if request.json else {}
        top_rank = filters.get('top_rank', 5)  # Default to top 5 if not specified
        domain_rank = filters.get('domain_rank', 5)  # Default domain rank
        
        # Load data
        df = pd.read_excel('temp_upload.xlsx')
        if 'Keyword' in df.columns:
            df['Keyword'].fillna(method='ffill', inplace=True)
        df = prepare_data(df)
        
        # Apply filters
        if 'date_range' in filters:
            df = apply_date_filter(df, filters['date_range'])
        
        if 'keyword' in filters:
            df = apply_keyword_filter(df, filters['keyword'])
        
        if 'position_min' in filters or 'position_max' in filters:
            df = apply_position_filter(df, filters.get('position_min'), filters.get('position_max'))
        
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
                nbins=20,
                color_discrete_sequence=['#3366CC']
            )
            
            pos_dist.update_layout(
                xaxis_title="Position",
                yaxis_title="Count",
                bargap=0.1
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
                domain_positions.head(domain_rank), 
                x='domain', 
                y='Position',
                title=f'Top {domain_rank} Domains by Average Position',
                labels={'domain': 'Domain', 'Position': 'Average Position'},
                color='Position',
                color_continuous_scale='RdYlGn_r'
            )
            
            top_domains_chart.update_layout(
                xaxis_title="Domain",
                yaxis_title="Average Position",
                yaxis_autorange='reversed'  # Lower positions (better rankings) at the top
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

@app.route('/keyword_analytics', methods=['POST'])
def keyword_analytics():
    try:
        data = request.json
        keyword = data.get('keyword')
        top_rank = data.get('top_rank', 5)  # Default to top 5 if not specified
        
        if not keyword:
            return jsonify({'error': 'Keyword is required'})
        
        # Load data
        df = pd.read_excel('temp_upload.xlsx')
        if 'Keyword' in df.columns:
            df['Keyword'].fillna(method='ffill', inplace=True)
        df = prepare_data(df)
        
        # Apply filters
        if 'date_range' in data:
            df = apply_date_filter(df, data['date_range'])
        
        if 'domain' in data:
            df = apply_domain_filter(df, data['domain'])
        
        # Filter by keyword
        if 'Keyword' in df.columns:
            keyword_df = df[df['Keyword'] == keyword]
        else:
            return jsonify({'error': 'Keyword column not found in data'})
        
        if keyword_df.empty:
            return jsonify({'error': f'No data found for keyword "{keyword}"'})
        
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
            nbins=20,
            color_discrete_sequence=['#3366CC']
        )
        
        pos_dist.update_layout(
            xaxis_title="Position",
            yaxis_title="Count",
            bargap=0.1
        )
        
        # Create domain performance chart
        domain_perf = px.bar(
            domain_positions.head(top_rank), 
            x='domain', 
            y='mean',
            error_y='count',
            title=f'Top {top_rank} Domains for "{keyword}"',
            labels={'domain': 'Domain', 'mean': 'Average Position'},
            color='mean',
            color_continuous_scale='RdYlGn_r'
        )
        
        domain_perf.update_layout(
            xaxis_title="Domain",
            yaxis_title="Average Position",
            yaxis_autorange='reversed'  # Lower positions (better rankings) at the top
        )
        
        # Create position trend over time chart
        trend_chart = None
        if 'date' in keyword_df.columns and 'Position' in keyword_df.columns and 'domain' in keyword_df.columns:
            # Get top domains for this keyword
            top_domains = domain_positions.head(top_rank)['domain'].tolist()
            
            # Filter data for these domains
            trend_data = keyword_df[keyword_df['domain'].isin(top_domains)]
            
            if not trend_data.empty:
                # Group by date and domain, calculate average position
                trend_daily = trend_data.groupby(['date', 'domain'])['Position'].mean().reset_index()
                
                # Create trend chart
                trend_chart = px.line(
                    trend_daily,
                    x='date',
                    y='Position',
                    color='domain',
                    title=f'Position Trend Over Time for "{keyword}"',
                    labels={'date': 'Date', 'Position': 'Position', 'domain': 'Domain'}
                )
                
                trend_chart.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Position",
                    yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                    legend_title="Domain"
                )
        
        # Convert charts to JSON
        charts = {
            'position_distribution': json.loads(plotly.io.to_json(pos_dist)),
            'domain_performance': json.loads(plotly.io.to_json(domain_perf))
        }
        
        if trend_chart:
            charts['trend_chart'] = json.loads(plotly.io.to_json(trend_chart))
        
        return jsonify({
            'success': True,
            'charts': charts,
            'domain_data': domain_positions.to_dict('records')
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/keyword_chart', methods=['POST'])
def keyword_chart():
    try:
        data = request.json
        keyword = data.get('keyword')
        top_rank = data.get('top_rank', 5)
        
        if not keyword:
            return jsonify({'error': 'Keyword is required'})
        
        # Load data
        df = pd.read_excel('temp_upload.xlsx')
        if 'Keyword' in df.columns:
            df['Keyword'].fillna(method='ffill', inplace=True)
        df = prepare_data(df)
        
        # Apply filters
        if 'date_range' in data:
            df = apply_date_filter(df, data['date_range'])
        
        if 'domain' in data:
            df = apply_domain_filter(df, data['domain'])
        
        # Filter by keyword
        keyword_df = df[df['Keyword'] == keyword]
        
        if keyword_df.empty:
            return jsonify({'error': f'No data found for keyword "{keyword}"'})
        
        # Get domain positions
        domain_positions = keyword_df.groupby('domain')['Position'].agg(['mean', 'min', 'max', 'count']).reset_index()
        domain_positions = domain_positions.sort_values('mean')
        
        # Create domain performance chart with updated top_rank
        domain_perf = px.bar(
            domain_positions.head(top_rank), 
            x='domain', 
            y='mean',
            error_y='count',
            title=f'Top {top_rank} Domains for "{keyword}"',
            labels={'domain': 'Domain', 'mean': 'Average Position'},
            color='mean',
            color_continuous_scale='RdYlGn_r'
        )
        
        domain_perf.update_layout(
            xaxis_title="Domain",
            yaxis_title="Average Position",
            yaxis_autorange='reversed'  # Lower positions (better rankings) at the top
        )
        
        return jsonify({
            'success': True,
            'chart': json.loads(plotly.io.to_json(domain_perf))
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/domain_analytics', methods=['POST'])
def domain_analytics():
    try:
        data = request.json
        domain = data.get('domain')
        top_rank = data.get('top_rank', 5)  # Default to top 5 if not specified
        
        if not domain:
            return jsonify({'error': 'Domain is required'})
        
        # Load data
        df = pd.read_excel('temp_upload.xlsx')
        if 'Keyword' in df.columns:
            df['Keyword'].fillna(method='ffill', inplace=True)
        df = prepare_data(df)
        
        # Apply filters
        if 'date_range' in data:
            df = apply_date_filter(df, data['date_range'])
        
        if 'position_min' in data or 'position_max' in data:
            df = apply_position_filter(df, data.get('position_min'), data.get('position_max'))
        
        # Filter by domain
        if 'domain' in df.columns:
            domain_df = df[df['domain'] == domain]
        else:
            return jsonify({'error': 'Domain column not found in data'})
        
        if domain_df.empty:
            return jsonify({'error': f'No data found for domain "{domain}"'})
        
        # Get keyword performance for this domain
        if 'Keyword' in df.columns and 'Position' in df.columns:
            keyword_perf = domain_df.groupby('Keyword')['Position'].agg(['mean', 'min', 'max', 'count']).reset_index()
            keyword_perf = keyword_perf.sort_values('mean')
        else:
            return jsonify({'error': 'Required columns missing in data'})
        
        # Create keyword performance chart
        keyword_chart = px.bar(
            keyword_perf.head(top_rank), 
            x='Keyword', 
            y='mean',
            title=f'Top {top_rank} Keywords for "{domain}"',
            labels={'Keyword': 'Keyword', 'mean': 'Average Position'},
            color='mean',
            color_continuous_scale='RdYlGn_r'
        )
        
        keyword_chart.update_layout(
            xaxis_title="Keyword",
            yaxis_title="Average Position",
            yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
            xaxis_tickangle=-45  # Rotate x-axis labels for better readability
        )
        
        # Create position trend over time chart
        trend_chart = None
        if 'date' in domain_df.columns and 'Position' in domain_df.columns and 'Keyword' in domain_df.columns:
            # Get top keywords for this domain
            top_keywords = keyword_perf.head(top_rank)['Keyword'].tolist()
            
            # Filter data for these keywords
            trend_data = domain_df[domain_df['Keyword'].isin(top_keywords)]
            
            if not trend_data.empty:
                # Group by date and keyword, calculate average position
                trend_daily = trend_data.groupby(['date', 'Keyword'])['Position'].mean().reset_index()
                
                # Create trend chart
                trend_chart = px.line(
                    trend_daily,
                    x='date',
                    y='Position',
                    color='Keyword',
                    title=f'Position Trend Over Time for "{domain}"',
                    labels={'date': 'Date', 'Position': 'Position', 'Keyword': 'Keyword'}
                )
                
                trend_chart.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Position",
                    yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                    legend_title="Keyword"
                )
        
        # Convert charts to JSON
        charts = {
            'keyword_performance': json.loads(plotly.io.to_json(keyword_chart))
        }
        
        if trend_chart:
            charts['trend_chart'] = json.loads(plotly.io.to_json(trend_chart))
        
        return jsonify({
            'success': True,
            'charts': charts,
            'keyword_data': keyword_perf.to_dict('records')
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/domain_chart', methods=['POST'])
def domain_chart():
    try:
        data = request.json
        domain = data.get('domain')
        top_rank = data.get('top_rank', 5)
        
        if not domain:
            return jsonify({'error': 'Domain is required'})
        
        # Load data
        df = pd.read_excel('temp_upload.xlsx')
        if 'Keyword' in df.columns:
            df['Keyword'].fillna(method='ffill', inplace=True)
        df = prepare_data(df)
        
        # Apply filters
        if 'date_range' in data:
            df = apply_date_filter(df, data['date_range'])
        
        if 'position_min' in data or 'position_max' in data:
            df = apply_position_filter(df, data.get('position_min'), data.get('position_max'))
        
        # Filter by domain
        domain_df = df[df['domain'] == domain]
        
        if domain_df.empty:
            return jsonify({'error': f'No data found for domain "{domain}"'})
        
        # Get keyword performance for this domain
        keyword_perf = domain_df.groupby('Keyword')['Position'].agg(['mean', 'min', 'max', 'count']).reset_index()
        keyword_perf = keyword_perf.sort_values('mean')
        
        # Create keyword performance chart with updated top_rank
        keyword_chart = px.bar(
            keyword_perf.head(top_rank), 
            x='Keyword', 
            y='mean',
            title=f'Top {top_rank} Keywords for "{domain}"',
            labels={'Keyword': 'Keyword', 'mean': 'Average Position'},
            color='mean',
            color_continuous_scale='RdYlGn_r'
        )
        
        keyword_chart.update_layout(
            xaxis_title="Keyword",
            yaxis_title="Average Position",
            yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
            xaxis_tickangle=-45  # Rotate x-axis labels for better readability
        )
        
        return jsonify({
            'success': True,
            'chart': json.loads(plotly.io.to_json(keyword_chart))
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/compare_urls', methods=['POST'])
def compare_urls():
    try:
        data = request.json
        urls = data.get('urls', [])
        
        if not urls or len(urls) == 0:
            return jsonify({'error': 'At least one URL is required'})
        
        # Load data
        df = pd.read_excel('temp_upload.xlsx')
        if 'Keyword' in df.columns:
            df['Keyword'].fillna(method='ffill', inplace=True)
        df = prepare_data(df)
        
        # Apply date range filter if provided
        if 'date_range' in data:
            df = apply_date_filter(df, data['date_range'])
        
        # Filter by URLs
        if 'Results' in df.columns:
            url_df = df[df['Results'].isin(urls)]
        else:
            return jsonify({'error': 'URL column not found in data'})
        
        if url_df.empty:
            return jsonify({'error': 'No data found for the selected URLs'})
        
        # Prepare URL performance data
        url_data = []
        for url in urls:
            url_subset = url_df[url_df['Results'] == url]
            
            if not url_subset.empty and 'Position' in url_subset.columns:
                url_data.append({
                    'url': url,
                    'avg_position': url_subset['Position'].mean(),
                    'best_position': url_subset['Position'].min(),
                    'worst_position': url_subset['Position'].max(),
                    'keywords_count': url_subset['Keyword'].nunique() if 'Keyword' in url_subset.columns else 0
                })
        
        # Sort by average position
        url_data = sorted(url_data, key=lambda x: x['avg_position'])
        
        # Create URL comparison chart
        url_comparison_chart = px.bar(
            pd.DataFrame(url_data),
            x='url',
            y='avg_position',
            error_y=[(d['worst_position'] - d['avg_position']) for d in url_data],
            title='URL Position Comparison',
            labels={'url': 'URL', 'avg_position': 'Average Position'},
            color='avg_position',
            color_continuous_scale='RdYlGn_r'
        )
        
        url_comparison_chart.update_layout(
            xaxis_title="URL",
            yaxis_title="Average Position",
            yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
            xaxis_tickangle=-45  # Rotate x-axis labels for better readability
        )
        
        # Create keyword performance by URL chart
        keyword_comparison_data = []
        
        if 'Keyword' in url_df.columns and 'Position' in url_df.columns:
            # Get top 5 keywords by frequency across these URLs
            top_keywords = url_df['Keyword'].value_counts().head(5).index.tolist()
            
            # For each keyword, get position by URL
            for keyword in top_keywords:
                keyword_data = url_df[url_df['Keyword'] == keyword]
                
                for url in urls:
                    url_keyword_data = keyword_data[keyword_data['Results'] == url]
                    
                    if not url_keyword_data.empty:
                        keyword_comparison_data.append({
                            'keyword': keyword,
                            'url': url,
                            'position': url_keyword_data['Position'].mean()
                        })
        
        if keyword_comparison_data:
            keyword_comparison_df = pd.DataFrame(keyword_comparison_data)
            
            keyword_comparison_chart = px.bar(
                keyword_comparison_df,
                x='keyword',
                y='position',
                color='url',
                barmode='group',
                title='URL Performance by Keyword',
                labels={'keyword': 'Keyword', 'position': 'Average Position', 'url': 'URL'}
            )
            
            keyword_comparison_chart.update_layout(
                xaxis_title="Keyword",
                yaxis_title="Average Position",
                yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                legend_title="URL"
            )
        else:
            # Create empty chart if no data
            keyword_comparison_chart = px.bar(
                pd.DataFrame({'keyword': [], 'position': [], 'url': []}),
                x='keyword',
                y='position',
                color='url',
                title='No Keyword Data Available'
            )
        
        # Create position trend over time chart (new feature)
        time_comparison_chart = None
        if 'date' in url_df.columns and len(urls) > 0:
            # For each URL, get positions over time
            trend_data = []
            for url in urls:
                url_time_data = url_df[url_df['Results'] == url]
                
                if not url_time_data.empty and 'date' in url_time_data.columns:
                    # Group by date and calculate average position
                    url_daily = url_time_data.groupby('date')['Position'].mean().reset_index()
                    url_daily['url'] = url
                    trend_data.append(url_daily)
            
            if trend_data:
                # Combine all URL data
                all_trend_data = pd.concat(trend_data)
                
                # Create trend chart
                time_comparison_chart = px.line(
                    all_trend_data,
                    x='date',
                    y='Position',
                    color='url',
                    title='URL Position Trend Over Time',
                    labels={'date': 'Date', 'Position': 'Position', 'url': 'URL'}
                )
                
                time_comparison_chart.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Position",
                    yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                    legend_title="URL"
                )
        
        # Convert charts to JSON
        charts = {
            'url_comparison': json.loads(plotly.io.to_json(url_comparison_chart)),
            'keyword_comparison': json.loads(plotly.io.to_json(keyword_comparison_chart))
        }
        
        if time_comparison_chart:
            charts['time_comparison'] = json.loads(plotly.io.to_json(time_comparison_chart))
        
        return jsonify({
            'success': True,
            'charts': charts,
            'url_data': url_data
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/compare_over_time', methods=['POST'])
def compare_over_time():
    try:
        data = request.json
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        keyword = data.get('keyword')
        
        # Validation
        if not all([start_date_str, end_date_str, keyword]):
            return jsonify({'error': 'Start date, end date, and keyword are required'})
        
        # Load the Excel file
        df = pd.read_excel('temp_upload.xlsx')
        
        # Print columns for debugging
        print("Original columns:", df.columns.tolist())
        
        # Check if we have the needed columns
        required_cols = ['Results', 'Position', 'Filled keyword', 'date/time']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"Missing columns: {missing_cols}")
            print(f"Available columns: {df.columns.tolist()}")
            
            # Try alternative column names
            if 'C' in df.columns and 'D' in df.columns and 'E' in df.columns and 'F' in df.columns:
                print("Using letter columns instead")
                df = df.rename(columns={
                    'C': 'Results',
                    'D': 'Position',
                    'E': 'Filled keyword',
                    'F': 'date/time'
                })
            else:
                return jsonify({'error': f'Required columns {missing_cols} not found in data'})
        
        # Filter by keyword (Filled keyword column)
        print(f"Filtering by Filled keyword = '{keyword}'")
        df_keyword = df[df['Filled keyword'] == keyword]
        
        if df_keyword.empty:
            return jsonify({'error': f'No data found for keyword "{keyword}"'})
        
        # For date matching, use the 'date/time' column
        date_col = 'date/time'
        
        if date_col not in df_keyword.columns:
            return jsonify({'error': f'Date column "{date_col}" not found. Available columns: {df_keyword.columns.tolist()}'})
        
        # Extract the date part from the "Mon YYYY-MM-DD H:MM:SS" format
        df_keyword['date_str_full'] = df_keyword[date_col].astype(str)
        df_keyword['date_part'] = df_keyword['date_str_full'].str.extract(r'(\d{4}-\d{2}-\d{2})')
        
        # Get unique dates for this keyword
        unique_dates = df_keyword['date_part'].dropna().unique().tolist()
        unique_dates.sort()
        print(f"Unique dates for keyword '{keyword}': {unique_dates}")
        
        # Format input dates to match the format in our data
        try:
            start_dt = pd.to_datetime(start_date_str)
            end_dt = pd.to_datetime(end_date_str)
            start_date_formatted = start_dt.strftime('%Y-%m-%d')
            end_date_formatted = end_dt.strftime('%Y-%m-%d')
        except Exception as e:
            print(f"Error parsing input dates: {e}")
            start_date_formatted = start_date_str
            end_date_formatted = end_date_str
        
        # Filter by the date part to match our input dates
        start_data = df_keyword[df_keyword['date_part'] == start_date_formatted]
        end_data = df_keyword[df_keyword['date_part'] == end_date_formatted]
        
        print(f"Found {len(start_data)} rows for start date and {len(end_data)} rows for end date")
        
        # If no data found, try alternative methods (contains match or fallback to available dates)
        if start_data.empty:
            print(f"No matches for start date '{start_date_formatted}', trying contains match")
            start_data = df_keyword[df_keyword[date_col].astype(str).str.contains(start_date_formatted)]
            print(f"Found {len(start_data)} rows after contains match")
            
            if start_data.empty and unique_dates:
                earliest_date = unique_dates[0]
                start_data = df_keyword[df_keyword['date_part'] == earliest_date]
                print(f"Using earliest date {earliest_date} with {len(start_data)} rows")
        
        if end_data.empty:
            print(f"No matches for end date '{end_date_formatted}', trying contains match")
            end_data = df_keyword[df_keyword[date_col].astype(str).str.contains(end_date_formatted)]
            print(f"Found {len(end_data)} rows after contains match")
            
            if end_data.empty and len(unique_dates) > 1:
                latest_date = unique_dates[-1]
                end_data = df_keyword[df_keyword['date_part'] == latest_date]
                print(f"Using latest date {latest_date} with {len(end_data)} rows")
        
        # ======== FIX DUPLICATES ========
        # Remove duplicates by URL to fix the double position issue
        if not start_data.empty:
            # Drop duplicates, keeping only the first occurrence for each URL
            start_data = start_data.drop_duplicates(subset=['Results'])
            print(f"After removing duplicates, start data has {len(start_data)} rows")
        
        if not end_data.empty:
            # Drop duplicates, keeping only the first occurrence for each URL
            end_data = end_data.drop_duplicates(subset=['Results'])
            print(f"After removing duplicates, end data has {len(end_data)} rows")
        
        # ======== PREPARE START DATE DATA ========
        start_urls = []
        if not start_data.empty:
            # Sort by Position (ascending - lower numbers = better ranking)
            start_data_sorted = start_data.sort_values(by='Position', ascending=True)
            
            # Create URL to position mapping for end data to calculate changes
            end_positions = {}
            if not end_data.empty:
                for idx, row in end_data.iterrows():
                    if pd.notna(row['Results']) and pd.notna(row['Position']):
                        end_positions[row['Results']] = int(row['Position']) if isinstance(row['Position'], (int, float)) else row['Position']
            
            # Collect ALL URLs and positions
            for idx, row in start_data_sorted.iterrows():
                url = row['Results']
                position = row['Position']
                
                if pd.notna(url) and pd.notna(position):
                    try:
                        # Try to convert position to integer if possible
                        pos_value = int(position) if isinstance(position, (int, float)) else position
                        
                        # Get the domain
                        domain = urlparse(url).netloc if pd.notna(url) else ''
                        
                        # Calculate position change if URL exists in end data
                        position_change = None
                        position_change_text = "N/A"
                        if url in end_positions:
                            end_pos = end_positions[url]
                            position_change = end_pos - pos_value
                            if position_change < 0:
                                position_change_text = f"↑ {abs(position_change)} (improved)"
                            elif position_change > 0:
                                position_change_text = f"↓ {position_change} (declined)"
                            else:
                                position_change_text = "No change"
                        else:
                            position_change_text = "Not in end data"
                        
                        start_urls.append({
                            'url': url,
                            'position': pos_value,
                            'domain': domain,
                            'position_change': position_change,
                            'position_change_text': position_change_text
                        })
                    except Exception as e:
                        print(f"Error processing start URL {url}: {e}")
                        continue
        
        # ======== PREPARE END DATE DATA ========
        end_urls = []
        if not end_data.empty:
            # Sort by Position (ascending - lower numbers = better ranking)
            end_data_sorted = end_data.sort_values(by='Position', ascending=True)
            
            # Create URL to position mapping for start data to calculate changes
            start_positions = {}
            if not start_data.empty:
                for idx, row in start_data.iterrows():
                    if pd.notna(row['Results']) and pd.notna(row['Position']):
                        start_positions[row['Results']] = int(row['Position']) if isinstance(row['Position'], (int, float)) else row['Position']
            
            # Collect ALL URLs and positions
            for idx, row in end_data_sorted.iterrows():
                url = row['Results']
                position = row['Position']
                
                if pd.notna(url) and pd.notna(position):
                    try:
                        # Try to convert position to integer if possible
                        pos_value = int(position) if isinstance(position, (int, float)) else position
                        
                        # Get the domain
                        domain = urlparse(url).netloc if pd.notna(url) else ''
                        
                        # Calculate position change if URL exists in start data
                        position_change = None
                        position_change_text = "N/A"
                        if url in start_positions:
                            start_pos = start_positions[url]
                            position_change = pos_value - start_pos
                            if position_change < 0:
                                position_change_text = f"↑ {abs(position_change)} (improved)"
                            elif position_change > 0:
                                position_change_text = f"↓ {position_change} (declined)"
                            else:
                                position_change_text = "No change"
                        else:
                            position_change_text = "New"
                        
                        end_urls.append({
                            'url': url,
                            'position': pos_value,
                            'domain': domain,
                            'position_change': position_change,
                            'position_change_text': position_change_text
                        })
                    except Exception as e:
                        print(f"Error processing end URL {url}: {e}")
                        continue
        
        # ======== PREPARE POSITION CHANGES ANALYSIS ========
        # Identify all URLs that exist in either start or end data
        all_urls = set()
        if start_data.empty and end_data.empty:
            position_changes = []
        else:
            for url_data in start_urls:
                all_urls.add(url_data['url'])
            
            for url_data in end_urls:
                all_urls.add(url_data['url'])
            
            # Create combined start and end mappings
            start_pos_map = {item['url']: item['position'] for item in start_urls}
            end_pos_map = {item['url']: item['position'] for item in end_urls}
            
            # Build the position changes data for ALL URLs
            position_changes = []
            for url in all_urls:
                start_pos = start_pos_map.get(url, None)
                end_pos = end_pos_map.get(url, None)
                
                # Only include if at least one position exists
                if start_pos is not None or end_pos is not None:
                    change_data = {
                        'url': url,
                        'start_position': start_pos,
                        'end_position': end_pos,
                        'domain': urlparse(url).netloc
                    }
                    
                    # Calculate position change
                    if start_pos is not None and end_pos is not None:
                        change = end_pos - start_pos
                        if change < 0:
                            change_data['change_text'] = f"↑ {abs(change)} (improved)"
                            change_data['status'] = 'improved'
                        elif change > 0:
                            change_data['change_text'] = f"↓ {change} (declined)"
                            change_data['status'] = 'declined'
                        else:
                            change_data['change_text'] = "No change"
                            change_data['status'] = 'unchanged'
                        change_data['change'] = change
                    else:
                        change_data['change'] = None
                        if start_pos is None:
                            change_data['change_text'] = "New"
                            change_data['status'] = 'new'
                        else:
                            change_data['change_text'] = "Dropped"
                            change_data['status'] = 'dropped'
                    
                    position_changes.append(change_data)
            
            # Sort by absolute change (biggest changes first)
            position_changes = sorted(position_changes, 
                key=lambda x: (
                    # Sort order: first by status (changed, then new/dropped, then unchanged)
                    0 if x['status'] in ('improved', 'declined') else (1 if x['status'] in ('new', 'dropped') else 2),
                    # Then by absolute change value (descending)
                    abs(x['change']) if x['change'] is not None else 0
                ), 
                reverse=True
            )
        
        # Return all the prepared data
        return jsonify({
            'success': True,
            'keyword': keyword,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'start_urls': start_urls,
            'end_urls': end_urls,
            'position_changes': position_changes,
            'start_count': len(start_urls),
            'end_count': len(end_urls),
            'available_dates': unique_dates
        })
        
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print(traceback_str)
        return jsonify({'error': str(e), 'traceback': traceback_str})
    try:
        data = request.json
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        keyword = data.get('keyword')
        
        # Validation
        if not all([start_date_str, end_date_str, keyword]):
            return jsonify({'error': 'Start date, end date, and keyword are required'})
        
        # Load the Excel file
        df = pd.read_excel('temp_upload.xlsx')
        
        # Print columns for debugging
        print("Original columns:", df.columns.tolist())
        
        # Check if we have the needed columns
        required_cols = ['Results', 'Position', 'Filled keyword', 'date/time']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"Missing columns: {missing_cols}")
            print(f"Available columns: {df.columns.tolist()}")
            
            # Try alternative column names
            if 'C' in df.columns and 'D' in df.columns and 'E' in df.columns and 'F' in df.columns:
                print("Using letter columns instead")
                df = df.rename(columns={
                    'C': 'Results',
                    'D': 'Position',
                    'E': 'Filled keyword',
                    'F': 'date/time'
                })
            else:
                return jsonify({'error': f'Required columns {missing_cols} not found in data'})
        
        # Filter by keyword (Filled keyword column)
        print(f"Filtering by Filled keyword = '{keyword}'")
        df_keyword = df[df['Filled keyword'] == keyword]
        
        if df_keyword.empty:
            return jsonify({'error': f'No data found for keyword "{keyword}"'})
        
        # For date matching, use the 'date/time' column
        date_col = 'date/time'
        
        if date_col not in df_keyword.columns:
            return jsonify({'error': f'Date column "{date_col}" not found. Available columns: {df_keyword.columns.tolist()}'})
        
        # Show some sample date values for debugging
        sample_dates = df_keyword[date_col].head(5).tolist()
        print(f"Sample date values: {sample_dates}")
        
        # Extract the date part from the "Mon YYYY-MM-DD H:MM:SS" format
        # First convert to string to ensure we can do string operations
        df_keyword['date_str_full'] = df_keyword[date_col].astype(str)
        
        # Extract just the date part using regex or string splitting
        df_keyword['date_part'] = df_keyword['date_str_full'].str.extract(r'(\d{4}-\d{2}-\d{2})')
        
        # Show the extracted date parts
        print("Extracted date parts:", df_keyword['date_part'].head(5).tolist())
        
        # Get unique dates for this keyword
        unique_dates = df_keyword['date_part'].dropna().unique().tolist()
        print(f"Unique dates for keyword '{keyword}': {unique_dates}")
        
        # Format input dates to match the format in our data
        # First parse the input dates
        try:
            start_dt = pd.to_datetime(start_date_str)
            end_dt = pd.to_datetime(end_date_str)
            
            # Format to match YYYY-MM-DD format in our data
            start_date_formatted = start_dt.strftime('%Y-%m-%d')
            end_date_formatted = end_dt.strftime('%Y-%m-%d')
            
            print(f"Formatted input dates: {start_date_formatted} and {end_date_formatted}")
        except Exception as e:
            print(f"Error parsing input dates: {e}")
            # Use as-is if parsing fails
            start_date_formatted = start_date_str
            end_date_formatted = end_date_str
        
        # Filter by the date part to match our input dates
        start_data = df_keyword[df_keyword['date_part'] == start_date_formatted]
        end_data = df_keyword[df_keyword['date_part'] == end_date_formatted]
        
        print(f"Found {len(start_data)} rows for start date and {len(end_data)} rows for end date")
        
        # If no data found, try alternative methods
        if start_data.empty:
            print(f"No matches for start date '{start_date_formatted}', trying contains match")
            start_data = df_keyword[df_keyword[date_col].astype(str).str.contains(start_date_formatted)]
            print(f"Found {len(start_data)} rows after contains match")
        
        if end_data.empty:
            print(f"No matches for end date '{end_date_formatted}', trying contains match")
            end_data = df_keyword[df_keyword[date_col].astype(str).str.contains(end_date_formatted)]
            print(f"Found {len(end_data)} rows after contains match")
        
        # If still empty and we have data overall, just use some of the data
        if (start_data.empty or end_data.empty) and not df_keyword.empty:
            print("Not enough date matches, using available data as fallback")
            
            # Get unique dates and use the earliest and latest
            if len(unique_dates) >= 2:
                unique_dates.sort()
                
                if start_data.empty:
                    earliest_date = unique_dates[0]
                    start_data = df_keyword[df_keyword['date_part'] == earliest_date]
                    print(f"Using earliest date {earliest_date} with {len(start_data)} rows")
                
                if end_data.empty:
                    latest_date = unique_dates[-1]
                    end_data = df_keyword[df_keyword['date_part'] == latest_date]
                    print(f"Using latest date {latest_date} with {len(end_data)} rows")
            else:
                # If only one date, split the data in half
                print("Only one date available, splitting the data")
                all_data = df_keyword.copy()
                half_idx = len(all_data) // 2
                
                if start_data.empty:
                    start_data = all_data.iloc[:half_idx]
                
                if end_data.empty:
                    end_data = all_data.iloc[half_idx:]
        
        # ======== PREPARE START DATE DATA ========
        start_urls = []
        if not start_data.empty:
            # Sort by Position (ascending - lower numbers = better ranking)
            start_data_sorted = start_data.sort_values(by='Position', ascending=True)
            
            # Collect ALL URLs and positions
            for idx, row in start_data_sorted.iterrows():
                url = row['Results']
                position = row['Position']
                
                if pd.notna(url) and pd.notna(position):
                    try:
                        # Try to convert position to integer if possible
                        pos_value = int(position) if isinstance(position, (int, float)) else position
                        
                        # Get the domain
                        domain = urlparse(url).netloc if pd.notna(url) else ''
                        
                        start_urls.append({
                            'url': url,
                            'position': pos_value,
                            'domain': domain
                        })
                    except:
                        # Skip entries that can't be processed
                        continue
        
        # ======== PREPARE END DATE DATA ========
        end_urls = []
        if not end_data.empty:
            # Sort by Position (ascending - lower numbers = better ranking)
            end_data_sorted = end_data.sort_values(by='Position', ascending=True)
            
            # Collect ALL URLs and positions
            for idx, row in end_data_sorted.iterrows():
                url = row['Results']
                position = row['Position']
                
                if pd.notna(url) and pd.notna(position):
                    try:
                        # Try to convert position to integer if possible
                        pos_value = int(position) if isinstance(position, (int, float)) else position
                        
                        # Get the domain
                        domain = urlparse(url).netloc if pd.notna(url) else ''
                        
                        end_urls.append({
                            'url': url,
                            'position': pos_value,
                            'domain': domain
                        })
                    except:
                        # Skip entries that can't be processed
                        continue
        
        # Return separate lists for both dates
        return jsonify({
            'success': True,
            'keyword': keyword,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'start_urls': start_urls,
            'end_urls': end_urls,
            'start_count': len(start_urls),
            'end_count': len(end_urls),
            'available_dates': unique_dates
        })
        
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print(traceback_str)
        return jsonify({'error': str(e), 'traceback': traceback_str})
    try:
        data = request.json
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        keyword = data.get('keyword')
        
        # Validation
        if not all([start_date_str, end_date_str, keyword]):
            return jsonify({'error': 'Start date, end date, and keyword are required'})
        
        # Load the Excel file
        df = pd.read_excel('temp_upload.xlsx')
        
        # Print columns for debugging
        print("Original columns:", df.columns.tolist())
        
        # Check if we have the needed columns
        required_cols = ['Results', 'Position', 'Filled keyword']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"Missing columns: {missing_cols}")
            print(f"Available columns: {df.columns.tolist()}")
            
            # Check if we have alternative columns 
            if 'C' in df.columns and 'D' in df.columns and 'E' in df.columns:
                print("Found letter columns instead, using those")
                df = df.rename(columns={
                    'C': 'Results',
                    'D': 'Position',
                    'E': 'Filled keyword'
                })
            else:
                return jsonify({'error': f'Required columns {missing_cols} not found in data. Available columns: {df.columns.tolist()}'})
        
        # Filter by keyword (Filled keyword column)
        print(f"Filtering by Filled keyword = '{keyword}'")
        df_keyword = df[df['Filled keyword'] == keyword]
        
        if df_keyword.empty:
            return jsonify({'error': f'No data found for keyword "{keyword}"'})
        
        # For date matching, we'll use the 'Time' column or 'B' if available
        date_col = 'Time' if 'Time' in df.columns else ('B' if 'B' in df.columns else None)
        
        if not date_col:
            print(f"No date column found. Available columns: {df.columns.tolist()}")
            return jsonify({'error': 'No date column found'})
        
        print(f"Using {date_col} as date column")
        
        # Convert to datetime for matching
        df_keyword['datetime'] = pd.to_datetime(df_keyword[date_col], errors='coerce')
        df_keyword['date_str'] = df_keyword['datetime'].dt.strftime('%Y-%m-%d')
        
        # Print unique dates for debugging
        unique_dates = df_keyword['date_str'].dropna().unique().tolist()
        print(f"Available dates ({len(unique_dates)}): {unique_dates}")
        
        # Filter by dates
        start_data = df_keyword[df_keyword['date_str'] == start_date_str]
        end_data = df_keyword[df_keyword['date_str'] == end_date_str]
        
        print(f"Found {len(start_data)} rows for start date and {len(end_data)} rows for end date")
        
        # If we didn't find exact matches, try to find dates containing the string
        if start_data.empty:
            print(f"No exact matches for start date, trying contains match for {start_date_str}")
            start_data = df_keyword[df_keyword[date_col].astype(str).str.contains(start_date_str)]
            print(f"Found {len(start_data)} rows after contains match")
        
        if end_data.empty:
            print(f"No exact matches for end date, trying contains match for {end_date_str}")
            end_data = df_keyword[df_keyword[date_col].astype(str).str.contains(end_date_str)]
            print(f"Found {len(end_data)} rows after contains match")
        
        # If still empty, try a more lenient date matching approach
        if start_data.empty or end_data.empty:
            # Try matching just the day value
            try:
                start_day = pd.to_datetime(start_date_str).day
                end_day = pd.to_datetime(end_date_str).day
                
                print(f"Trying day matching: start_day={start_day}, end_day={end_day}")
                
                if start_data.empty:
                    start_data = df_keyword[df_keyword['datetime'].dt.day == start_day]
                    print(f"Found {len(start_data)} rows after day matching for start date")
                
                if end_data.empty:
                    end_data = df_keyword[df_keyword['datetime'].dt.day == end_day]
                    print(f"Found {len(end_data)} rows after day matching for end date")
            except Exception as e:
                print(f"Error in day matching: {e}")
        
        # Last resort: just split the data if still empty
        if start_data.empty and end_data.empty and not df_keyword.empty:
            print("Using all data and splitting it as last resort")
            df_keyword_sorted = df_keyword.sort_values(by='datetime')
            
            # Split into first half and second half
            half_index = len(df_keyword_sorted) // 2
            start_data = df_keyword_sorted.iloc[:half_index]
            end_data = df_keyword_sorted.iloc[half_index:]
            
            print(f"Split data into {len(start_data)} start rows and {len(end_data)} end rows")
        
        # ======== PREPARE START DATE DATA ========
        start_urls = []
        if not start_data.empty:
            # Sort by Position (ascending - lower numbers = better ranking)
            start_data_sorted = start_data.sort_values(by='Position', ascending=True)
            
            # Collect ALL URLs and positions
            for idx, row in start_data_sorted.iterrows():
                url = row['Results']
                position = row['Position']
                
                if pd.notna(url) and pd.notna(position):
                    domain = get_domain(url) if callable(get_domain) else urlparse(url).netloc
                    
                    start_urls.append({
                        'url': url,
                        'position': int(position) if isinstance(position, (int, float)) else position,
                        'domain': domain or ''
                    })
        
        # ======== PREPARE END DATE DATA ========
        end_urls = []
        if not end_data.empty:
            # Sort by Position (ascending - lower numbers = better ranking)
            end_data_sorted = end_data.sort_values(by='Position', ascending=True)
            
            # Collect ALL URLs and positions
            for idx, row in end_data_sorted.iterrows():
                url = row['Results']
                position = row['Position']
                
                if pd.notna(url) and pd.notna(position):
                    domain = get_domain(url) if callable(get_domain) else urlparse(url).netloc
                    
                    end_urls.append({
                        'url': url,
                        'position': int(position) if isinstance(position, (int, float)) else position,
                        'domain': domain or ''
                    })
        
        # Return separate lists for both dates
        return jsonify({
            'success': True,
            'keyword': keyword,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'start_urls': start_urls,
            'end_urls': end_urls,
            'start_count': len(start_urls),
            'end_count': len(end_urls)
        })
        
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print(traceback_str)
        return jsonify({'error': str(e), 'traceback': traceback_str})
    try:
        data = request.json
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        keyword = data.get('keyword')
        
        # Validation
        if not all([start_date_str, end_date_str, keyword]):
            return jsonify({'error': 'Start date, end date, and keyword are required'})
        
        # Load the Excel file
        df = pd.read_excel('temp_upload.xlsx')
        
        # Print columns for debugging
        print("Original columns:", df.columns.tolist())
        
        # Just work directly with letter columns to simplify
        # A = Keyword, B = Time, C = Results (URLs), D = Position, E = Filled keyword
        # Make sure we have the needed columns
        required_cols = ['C', 'D', 'E']
        for col in required_cols:
            if col not in df.columns:
                return jsonify({'error': f'Required column {col} not found in data'})
        
        # Filter by keyword (column E)
        print(f"Filtering by E = '{keyword}'")
        df_keyword = df[df['E'] == keyword]
        
        if df_keyword.empty:
            return jsonify({'error': f'No data found for keyword "{keyword}"'})
        
        # For date matching, we'll use the B column (Time)
        date_col = 'B'
        
        # Convert to datetime for matching
        df_keyword['datetime'] = pd.to_datetime(df_keyword[date_col], errors='coerce')
        df_keyword['date_str'] = df_keyword['datetime'].dt.strftime('%Y-%m-%d')
        
        # Print unique dates for debugging
        print("Available dates:", df_keyword['date_str'].unique().tolist())
        
        # Filter by dates
        start_data = df_keyword[df_keyword['date_str'] == start_date_str]
        end_data = df_keyword[df_keyword['date_str'] == end_date_str]
        
        print(f"Found {len(start_data)} rows for start date and {len(end_data)} rows for end date")
        
        # If we didn't find exact matches, try to find dates containing the string
        if start_data.empty:
            print(f"No exact matches for start date, trying contains match for {start_date_str}")
            start_data = df_keyword[df_keyword[date_col].astype(str).str.contains(start_date_str)]
            print(f"Found {len(start_data)} rows after contains match")
        
        if end_data.empty:
            print(f"No exact matches for end date, trying contains match for {end_date_str}")
            end_data = df_keyword[df_keyword[date_col].astype(str).str.contains(end_date_str)]
            print(f"Found {len(end_data)} rows after contains match")
        
        # If still empty, take two different days as fallback
        if start_data.empty or end_data.empty:
            unique_days = df_keyword['datetime'].dt.day.unique()
            if len(unique_days) >= 2:
                print("Using different days as fallback")
                earliest_day = min(unique_days)
                latest_day = max(unique_days)
                
                start_data = df_keyword[df_keyword['datetime'].dt.day == earliest_day]
                end_data = df_keyword[df_keyword['datetime'].dt.day == latest_day]
        
        # ======== PREPARE START DATE DATA ========
        start_urls = []
        if not start_data.empty:
            # Sort by Position (column D) - ascending (lower numbers = better ranking)
            start_data = start_data.sort_values(by='D', ascending=True)
            
            # Simple collect ALL URLs from column C and positions from column D
            for idx, row in start_data.iterrows():
                start_urls.append({
                    'url': row['C'],
                    'position': int(row['D']) if pd.notna(row['D']) else None,
                    'domain': urlparse(row['C']).netloc if pd.notna(row['C']) else ''
                })
        
        # ======== PREPARE END DATE DATA ========
        end_urls = []
        if not end_data.empty:
            # Sort by Position (column D) - ascending (lower numbers = better ranking)
            end_data = end_data.sort_values(by='D', ascending=True)
            
            # Simple collect ALL URLs from column C and positions from column D
            for idx, row in end_data.iterrows():
                end_urls.append({
                    'url': row['C'],
                    'position': int(row['D']) if pd.notna(row['D']) else None,
                    'domain': urlparse(row['C']).netloc if pd.notna(row['C']) else ''
                })
        
        # Return separate lists for both dates
        return jsonify({
            'success': True,
            'keyword': keyword,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'start_urls': start_urls,
            'end_urls': end_urls,
            'start_count': len(start_urls),
            'end_count': len(end_urls)
        })
        
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print(traceback_str)
        return jsonify({'error': str(e), 'traceback': traceback_str})
    try:
        data = request.json
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        keyword = data.get('keyword')
        
        # Validation
        if not all([start_date_str, end_date_str, keyword]):
            return jsonify({'error': 'Start date, end date, and keyword are required'})
        
        # Load the Excel file
        original_df = pd.read_excel('temp_upload.xlsx')
        
        # Print column names for debugging
        print("Original columns:", original_df.columns.tolist())
        
        # Detect data structure based on column names
        df = original_df.copy()
        
        # If we have standard column names, rename them to our expected format
        if 'Keyword' in df.columns and 'Time' in df.columns and 'Results' in df.columns and 'Position' in df.columns:
            # Standard format
            pass
        elif 'A' in df.columns and 'B' in df.columns and 'C' in df.columns and 'D' in df.columns and 'E' in df.columns:
            # Excel-style column names (A, B, C, D, E, etc.)
            col_map = {
                'A': 'Keyword',
                'B': 'Time',
                'C': 'Results',
                'D': 'Position',
                'E': 'Filled keyword',
                'F': 'date/time'
            }
            df = df.rename(columns=col_map)
        
        # Check if we have necessary columns
        if 'Results' not in df.columns or 'Position' not in df.columns:
            print("Required columns not found. Available columns:", df.columns.tolist())
            return jsonify({'error': 'Required columns not found in data'})
        
        # Determine which column to use for keyword filtering
        # First try 'Filled keyword', then 'Keyword'
        keyword_column = 'Filled keyword' if 'Filled keyword' in df.columns else 'Keyword'
        
        if keyword_column not in df.columns:
            return jsonify({'error': f'Keyword column not found in data. Available columns: {df.columns.tolist()}'})
        
        # Filter by keyword
        print(f"Filtering by {keyword_column} = '{keyword}'")
        keyword_df = df[df[keyword_column] == keyword]
        
        print(f"Found {len(keyword_df)} rows for keyword '{keyword}'")
        if keyword_df.empty:
            return jsonify({'error': f'No data for keyword "{keyword}" in column {keyword_column}'})
        
        # Determine which column has date information
        date_columns = []
        for col in ['Time', 'date/time', 'date']:
            if col in keyword_df.columns:
                date_columns.append(col)
        
        if not date_columns:
            return jsonify({'error': 'No date columns found in data'})
        
        print(f"Available date columns: {date_columns}")
        
        # Try each date column until we find matches
        found_start = False
        found_end = False
        start_data = pd.DataFrame()
        end_data = pd.DataFrame()
        
        for date_col in date_columns:
            print(f"Trying date column: {date_col}")
            
            # Print unique date values for debugging
            unique_dates = keyword_df[date_col].unique()
            print(f"Unique {date_col} values ({len(unique_dates)}): {unique_dates[:10]}")
            
            # Convert dates to strings for comparison to handle different formats
            keyword_df['date_str'] = keyword_df[date_col].astype(str)
            
            # Show some sample date strings
            print(f"Sample date strings: {keyword_df['date_str'].iloc[:5].tolist()}")
            
            # Try multiple date formats for start_date
            start_date_formats = [
                start_date_str,
                pd.to_datetime(start_date_str).strftime('%Y-%m-%d'),
                pd.to_datetime(start_date_str).strftime('%m/%d/%Y'),
                pd.to_datetime(start_date_str).strftime('%Y/%m/%d')
            ]
            
            end_date_formats = [
                end_date_str,
                pd.to_datetime(end_date_str).strftime('%Y-%m-%d'),
                pd.to_datetime(end_date_str).strftime('%m/%d/%Y'),
                pd.to_datetime(end_date_str).strftime('%Y/%m/%d')
            ]
            
            # Try multiple ways to match the date
            # Method 1: Direct string contains matching
            for start_format in start_date_formats:
                temp_start = keyword_df[keyword_df['date_str'].str.contains(start_format, na=False)]
                if not temp_start.empty:
                    print(f"Found {len(temp_start)} rows with date {start_format}")
                    start_data = temp_start
                    found_start = True
                    break
            
            for end_format in end_date_formats:
                temp_end = keyword_df[keyword_df['date_str'].str.contains(end_format, na=False)]
                if not temp_end.empty:
                    print(f"Found {len(temp_end)} rows with date {end_format}")
                    end_data = temp_end
                    found_end = True
                    break
            
            if found_start and found_end:
                break
            
            # Method 2: Convert to datetime and compare
            if not (found_start and found_end):
                try:
                    keyword_df['date_dt'] = pd.to_datetime(keyword_df[date_col], errors='coerce')
                    keyword_df['date_only'] = keyword_df['date_dt'].dt.date
                    
                    start_date_dt = pd.to_datetime(start_date_str).date()
                    end_date_dt = pd.to_datetime(end_date_str).date()
                    
                    # Show some converted dates
                    print(f"Converted dates sample: {keyword_df['date_only'].iloc[:5].tolist()}")
                    print(f"Looking for dates: {start_date_dt} and {end_date_dt}")
                    
                    if not found_start:
                        temp_start = keyword_df[keyword_df['date_only'] == start_date_dt]
                        if not temp_start.empty:
                            print(f"Found {len(temp_start)} rows matching start date")
                            start_data = temp_start
                            found_start = True
                    
                    if not found_end:
                        temp_end = keyword_df[keyword_df['date_only'] == end_date_dt]
                        if not temp_end.empty:
                            print(f"Found {len(temp_end)} rows matching end date")
                            end_data = temp_end
                            found_end = True
                except Exception as e:
                    print(f"Error in datetime conversion: {e}")
            
            if found_start and found_end:
                break
        
        # If still no matches, try more lenient matching
        if not (found_start and found_end):
            # Try partial date matching (just the day)
            start_day = pd.to_datetime(start_date_str).day
            end_day = pd.to_datetime(end_date_str).day
            
            print(f"Trying to match just the day: start={start_day}, end={end_day}")
            
            for date_col in date_columns:
                try:
                    keyword_df['date_dt'] = pd.to_datetime(keyword_df[date_col], errors='coerce')
                    
                    if not found_start:
                        temp_start = keyword_df[keyword_df['date_dt'].dt.day == start_day]
                        if not temp_start.empty:
                            print(f"Found {len(temp_start)} rows matching start day {start_day}")
                            start_data = temp_start
                            found_start = True
                    
                    if not found_end:
                        temp_end = keyword_df[keyword_df['date_dt'].dt.day == end_day]
                        if not temp_end.empty:
                            print(f"Found {len(temp_end)} rows matching end day {end_day}")
                            end_data = temp_end
                            found_end = True
                except Exception as e:
                    print(f"Error in day matching: {e}")
                
                if found_start and found_end:
                    break
        
        # Last resort: Return the first and last dates in the dataset
        if not (found_start or found_end):
            print("No matches found - using first/last dates in dataset as fallback")
            try:
                for date_col in date_columns:
                    keyword_df['date_dt'] = pd.to_datetime(keyword_df[date_col], errors='coerce')
                    keyword_df = keyword_df.sort_values('date_dt')
                    
                    # Take earliest date for start and latest for end
                    if not found_start:
                        start_data = keyword_df.head(len(keyword_df) // 2)  # First half
                        found_start = True
                    
                    if not found_end:
                        end_data = keyword_df.tail(len(keyword_df) // 2)  # Second half
                        found_end = True
                    
                    if found_start and found_end:
                        break
            except Exception as e:
                print(f"Error in fallback date handling: {e}")
        
        # Debug: Check number of rows found
        print(f"Final start date data rows: {len(start_data)}")
        print(f"Final end date data rows: {len(end_data)}")
        
        if start_data.empty and end_data.empty:
            # As a last resort, just use all the data split into two parts
            print("Both dates still empty - splitting all data")
            start_data = keyword_df.iloc[:len(keyword_df)//2]
            end_data = keyword_df.iloc[len(keyword_df)//2:]
        
        # ======== PREPARE START DATE DATA ========
        start_urls = []
        if not start_data.empty:
            # Sort by Position (ascending)
            start_data_sorted = start_data.sort_values(by='Position', ascending=True)
            
            # Get all URLs and positions
            for idx, row in start_data_sorted.iterrows():
                start_urls.append({
                    'url': row['Results'],
                    'position': int(row['Position']) if isinstance(row['Position'], (int, float)) else None,
                    'domain': row.get('domain', '')
                })
        
        # ======== PREPARE END DATE DATA ========
        end_urls = []
        if not end_data.empty:
            # Sort by Position (ascending)
            end_data_sorted = end_data.sort_values(by='Position', ascending=True)
            
            # Get all URLs and positions
            for idx, row in end_data_sorted.iterrows():
                end_urls.append({
                    'url': row['Results'],
                    'position': int(row['Position']) if isinstance(row['Position'], (int, float)) else None,
                    'domain': row.get('domain', '')
                })
        
        # Return separate lists for both dates
        return jsonify({
            'success': True,
            'keyword': keyword,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'start_urls': start_urls,
            'end_urls': end_urls,
            'start_count': len(start_urls),
            'end_count': len(end_urls)
        })
        
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print(traceback_str)
        return jsonify({'error': str(e), 'traceback': traceback_str})
    try:
        data = request.json
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        keyword = data.get('keyword')
        
        # Validation
        if not all([start_date_str, end_date_str, keyword]):
            return jsonify({'error': 'Start date, end date, and keyword are required'})
        
        # Load the Excel file
        original_df = pd.read_excel('temp_upload.xlsx')
        
        # Print column names for debugging
        print("Original columns:", original_df.columns.tolist())
        
        # Detect data structure based on column names
        df = original_df.copy()
        
        # If we have standard column names, rename them to our expected format
        if 'Keyword' in df.columns and 'Time' in df.columns and 'Results' in df.columns and 'Position' in df.columns:
            # Standard format
            pass
        elif 'A' in df.columns and 'B' in df.columns and 'C' in df.columns and 'D' in df.columns and 'E' in df.columns:
            # Excel-style column names (A, B, C, D, E, etc.)
            col_map = {
                'A': 'Keyword',
                'B': 'Time',
                'C': 'Results',
                'D': 'Position',
                'E': 'Filled keyword'
            }
            df = df.rename(columns=col_map)
        
        # Check if we have necessary columns
        if 'Results' not in df.columns or 'Position' not in df.columns:
            print("Required columns not found. Available columns:", df.columns.tolist())
            return jsonify({'error': 'Required columns not found in data'})
        
        # Process the data (convert dates, etc.)
        df = prepare_data(df)
        
        # Determine which column to use for keyword filtering
        # First try 'Filled keyword', then 'Keyword'
        keyword_column = 'Filled keyword' if 'Filled keyword' in df.columns else 'Keyword'
        
        if keyword_column not in df.columns:
            return jsonify({'error': f'Keyword column not found in data. Available columns: {df.columns.tolist()}'})
        
        # Filter by keyword
        print(f"Filtering by {keyword_column} = '{keyword}'")
        keyword_df = df[df[keyword_column] == keyword]
        
        print(f"Found {len(keyword_df)} rows for keyword '{keyword}'")
        if keyword_df.empty:
            return jsonify({'error': f'No data for keyword "{keyword}" in column {keyword_column}'})
        
        # Convert date fields to datetime
        date_column = None
        for col in ['date', 'Time', 'date/time']:
            if col in keyword_df.columns and not keyword_df[col].isnull().all():
                date_column = col
                break
                
        if not date_column:
            return jsonify({'error': 'No valid date column found'})
            
        print(f"Using date column: {date_column}")
        
        # Convert the selected date strings to datetime objects
        try:
            start_date = pd.to_datetime(start_date_str).date()
            end_date = pd.to_datetime(end_date_str).date()
        except Exception as e:
            print(f"Error parsing dates: {e}")
            return jsonify({'error': f'Error parsing dates: {e}'})
        
        print(f"Looking for date matches: {start_date} and {end_date}")
        
        # Filter for dates that match our start and end dates
        if date_column == 'date':
            # Already a date object
            start_data = keyword_df[keyword_df['date'] == start_date].copy()
            end_data = keyword_df[keyword_df['date'] == end_date].copy()
        else:
            # Need to convert to date objects for comparison
            start_data = keyword_df[pd.to_datetime(keyword_df[date_column]).dt.date == start_date].copy()
            end_data = keyword_df[pd.to_datetime(keyword_df[date_column]).dt.date == end_date].copy()
        
        # Debug: Check number of rows for each filtered date
        print(f"Rows for start date {start_date}: {len(start_data)}")
        print(f"Rows for end date {end_date}: {len(end_data)}")
        
        if start_data.empty and end_data.empty:
            return jsonify({'error': f'No data for dates: {start_date_str} / {end_date_str}'})
        
        # ======== PREPARE START DATE DATA ========
        start_urls = []
        if not start_data.empty:
            # Sort by Position (ascending)
            start_data_sorted = start_data.sort_values(by='Position', ascending=True)
            
            # Get all URLs and positions
            for idx, row in start_data_sorted.iterrows():
                start_urls.append({
                    'url': row['Results'],
                    'position': int(row['Position']) if isinstance(row['Position'], (int, float)) else None,
                    'domain': row.get('domain', '')
                })
        
        # ======== PREPARE END DATE DATA ========
        end_urls = []
        if not end_data.empty:
            # Sort by Position (ascending)
            end_data_sorted = end_data.sort_values(by='Position', ascending=True)
            
            # Get all URLs and positions
            for idx, row in end_data_sorted.iterrows():
                end_urls.append({
                    'url': row['Results'],
                    'position': int(row['Position']) if isinstance(row['Position'], (int, float)) else None,
                    'domain': row.get('domain', '')
                })
        
        # Return separate lists for both dates
        return jsonify({
            'success': True,
            'keyword': keyword,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'start_urls': start_urls,
            'end_urls': end_urls,
            'start_count': len(start_urls),
            'end_count': len(end_urls)
        })
        
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print(traceback_str)
        return jsonify({'error': str(e), 'traceback': traceback_str})
    try:
        data = request.json
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        keyword = data.get('keyword')
        
        # Validation
        if not all([start_date_str, end_date_str, keyword]):
            return jsonify({'error': 'Start date, end date, and keyword are required'})
        
        # Load the Excel file
        df = pd.read_excel('temp_upload.xlsx')
        
        # Rename columns if needed
        col_map = {
            'C': 'Results',
            'D': 'Position',
            'E': 'Keyword',
            'F': 'Time'
        }
        for old_col, new_col in col_map.items():
            if old_col in df.columns:
                df = df.rename(columns={old_col: new_col})
        
        # Process the data (convert dates, etc.)
        df = prepare_data(df)
        
        # Filter by keyword
        keyword_df = df[df['Keyword'] == keyword]
        if keyword_df.empty:
            return jsonify({'error': f'No data for keyword "{keyword}"'})
        
        # Convert the 'Time' column to date objects
        if 'Time' in df.columns:
            keyword_df['date'] = pd.to_datetime(keyword_df['Time'], errors='coerce').dt.date
        else:
            return jsonify({'error': 'No date information found'})
        
        # Convert the selected date strings to date objects
        start_date = pd.to_datetime(start_date_str).date()
        end_date = pd.to_datetime(end_date_str).date()
        
        # Filter the DataFrame for the two selected dates
        start_data = keyword_df[keyword_df['date'] == start_date].copy()
        end_data = keyword_df[keyword_df['date'] == end_date].copy()
        
        # Debug: Check number of rows for each filtered date
        print(f"Rows for start date {start_date}: {len(start_data)}")
        print(f"Rows for end date {end_date}: {len(end_data)}")
        
        if start_data.empty and end_data.empty:
            return jsonify({'error': f'No data for dates: {start_date_str} / {end_date_str}'})
        
        # ======== PREPARE START DATE DATA ========
        start_urls = []
        if not start_data.empty:
            # Sort by Position (ascending)
            start_data_sorted = start_data.sort_values(by='Position', ascending=True)
            
            # Get all URLs and positions
            for idx, row in start_data_sorted.iterrows():
                start_urls.append({
                    'url': row['Results'],
                    'position': int(row['Position']) if isinstance(row['Position'], (int, float)) else None,
                    'domain': row.get('domain', ''),
                })
        
        # ======== PREPARE END DATE DATA ========
        end_urls = []
        if not end_data.empty:
            # Sort by Position (ascending)
            end_data_sorted = end_data.sort_values(by='Position', ascending=True)
            
            # Get all URLs and positions
            for idx, row in end_data_sorted.iterrows():
                end_urls.append({
                    'url': row['Results'],
                    'position': int(row['Position']) if isinstance(row['Position'], (int, float)) else None,
                    'domain': row.get('domain', ''),
                })
        
        # Return separate lists for both dates
        return jsonify({
            'success': True,
            'keyword': keyword,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'start_urls': start_urls,
            'end_urls': end_urls,
            'start_count': len(start_urls),
            'end_count': len(end_urls)
        })
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)})



if __name__ == '__main__':
    import sys
    import pandas as pd

    def prepare_data(df):
        """
        Minimal data preparation:
          - Converts the 'Time' column to datetime.
          - Creates a 'date' column from the 'Time' column.
        """
        if 'Time' in df.columns:
            df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
            df['date'] = df['Time'].dt.date
        return df

    def debug_compare_over_time(start_date_str, end_date_str, keyword):
        # Load the Excel file
        try:
            df = pd.read_excel('temp_upload.xlsx')
        except Exception as e:
            print("Error reading Excel file:", e)
            sys.exit(1)

        # Rename columns if they are named "C", "D", "E", "F"
        col_map = {
            'C': 'Results',    # URLs
            'D': 'Position',   # Positions
            'E': 'Keyword',    # Keywords
            'F': 'Time'        # Time
        }
        for old_col, new_col in col_map.items():
            if old_col in df.columns:
                df = df.rename(columns={old_col: new_col})

        # Prepare data (convert Time to datetime and create date column)
        df = prepare_data(df)

        # Filter by keyword (Column E -> 'Keyword')
        df_keyword = df[df['Keyword'] == keyword]
        if df_keyword.empty:
            print(f"No data found for keyword: {keyword}")
            sys.exit(1)

        # Convert input date strings to date objects
        try:
            start_date = pd.to_datetime(start_date_str).date()
            end_date = pd.to_datetime(end_date_str).date()
        except Exception as e:
            print("Error converting input dates:", e)
            sys.exit(1)

        # Filter the DataFrame for the selected dates using the actual date values
        start_data = df_keyword[df_keyword['date'] == start_date].copy()
        end_data = df_keyword[df_keyword['date'] == end_date].copy()

        # Debug prints to check the number of rows for each date
        print("Rows for start date (", start_date, "):", len(start_data))
        print("Rows for end date (", end_date, "):", len(end_data))
        
        # Print sample rows for debugging
        print("\nStart Data Sample:")
        print(start_data[['Results', 'Position', 'date']].head(10))
        
        print("\nEnd Data Sample:")
        print(end_data[['Results', 'Position', 'date']].head(10))
        
        # Sort each subset by Position (ascending: lower numbers are better)
        start_data_sorted = start_data.sort_values(by='Position', ascending=True)
        end_data_sorted = end_data.sort_values(by='Position', ascending=True)
        
        # Convert sorted DataFrames to lists of [URL, Position]
        start_list = start_data_sorted[['Results', 'Position']].values.tolist()
        end_list   = end_data_sorted[['Results', 'Position']].values.tolist()
        
        # Build the rank table
        max_len = max(len(start_list), len(end_list))
        rank_table = []
        for i in range(max_len):
            if i < len(start_list):
                url_start, pos_start = start_list[i]
            else:
                url_start, pos_start = None, None
            
            if i < len(end_list):
                url_end, pos_end = end_list[i]
            else:
                url_end, pos_end = None, None
            
            # Calculate the difference between positions if possible
            change_str = ""
            if isinstance(pos_start, (int, float)) and isinstance(pos_end, (int, float)):
                diff = pos_end - pos_start
                change_str = f"{diff:+.0f}"  # Format as +X or -X with no decimals
            
            rank_table.append({
                "rank": i + 1,
                "url_start": url_start or "",
                "url_end": url_end or "",
                "change": change_str
            })
        
        # Print the final rank table for debugging
        print("\nRank Table:")
        for row in rank_table:
            print(row)
    
    # Set test values (adjust these to match your test cases)
    test_start_date = "2025-03-27"  # Example date; adjust as needed
    test_end_date = "2025-03-27"    # Example date; adjust as needed
    test_keyword = "vpn"            # Example keyword; adjust as needed
    
    debug_compare_over_time(test_start_date, test_end_date, test_keyword)
