// static/js/main.js

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
    // Hide all sections
    const sections = document.querySelectorAll('.dashboard-section');
    sections.forEach(section => {
        section.style.display = 'none';
    });
    
    // Show the selected section
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
    const statusDiv = document.getElementById('upload-status');
    statusDiv.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
}

function populateKeywordDropdown(keywords) {
    const select = document.getElementById('keyword-select');
    
    // Clear existing options except the first one
    while (select.options.length > 1) {
        select.options.remove(1);
    }
    
    // Add new options
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
                // Create summary cards
                createSummaryCards(data.summary);
                
                // Render charts
                Plotly.newPlot('position-distribution-chart', data.charts.position_distribution.data, data.charts.position_distribution.layout);
                Plotly.newPlot('top-domains-chart', data.charts.top_domains.data, data.charts.top_domains.layout);
                
                // Populate tables
                populateKeywordVolumeTable(data.keyword_data);
                populateDomainFrequencyTable(data.domain_data);
            } else if (data.error) {
                showDashboardError(data.error);
            }
        })
        .catch(error => {
            console.error('Error loading overall stats:', error);
            showDashboardError('Failed to load dashboard data');
        });
}

function showDashboardError(message) {
    const summaryCards = document.getElementById('summary-cards');
    summaryCards.innerHTML = `
        <div class="col-12">
            <div class="alert alert-danger">
                ${message}
            </div>
        </div>
    `;
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
            <td><a href="#" class="keyword-link" data-keyword="${item.Keyword}">${item.Keyword}</a></td>
            <td>${item.Results}</td>
        `;
        table.appendChild(row);
    });
    
    // Add click event to keyword links
    document.querySelectorAll('.keyword-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const keyword = this.getAttribute('data-keyword');
            document.getElementById('keyword-select').value = keyword;
            showSection('keyword-section');
            analyzeKeyword(keyword);
        });
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
            <td><a href="#" class="domain-link" data-domain="${item.domain}">${item.domain}</a></td>
            <td>${item.count}</td>
        `;
        table.appendChild(row);
    });
    
    // Add click event to domain links
    document.querySelectorAll('.domain-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const domain = this.getAttribute('data-domain');
            document.getElementById('domain-input').value = domain;
            showSection('domain-section');
            analyzeDomain(domain);
        });
    });
}

function analyzeKeyword(keyword) {
    // Show loading indicator
    document.getElementById('keyword-loading').classList.remove('d-none');
    document.getElementById('keyword-content').classList.add('d-none');
    
    fetch('/keyword_analytics', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ keyword: keyword })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('keyword-loading').classList.add('d-none');
        
        if (data.success) {
            // Show content
            document.getElementById('keyword-content').classList.remove('d-none');
            
            // Render charts
            Plotly.newPlot('keyword-position-chart', data.charts.position_distribution.data, data.charts.position_distribution.layout);
            Plotly.newPlot('keyword-domain-chart', data.charts.domain_performance.data, data.charts.domain_performance.layout);
            
            // Populate domain ranking table
            populateDomainRankingTable(data.domain_data);
        } else if (data.error) {
            showAnalysisError('keyword', data.error);
        }
    })
    .catch(error => {
        document.getElementById('keyword-loading').classList.add('d-none');
        console.error('Error analyzing keyword:', error);
        showAnalysisError('keyword', 'Failed to analyze keyword data');
    });
}

function showAnalysisError(type, message) {
    const contentDiv = document.getElementById(`${type}-content`);
    contentDiv.classList.remove('d-none');
    contentDiv.innerHTML = `
        <div class="alert alert-danger">
            ${message}
        </div>
    `;
}

function populateDomainRankingTable(data) {
    const table = document.getElementById('domain-ranking-table');
    table.innerHTML = '';
    
    if (!data || data.length === 0) {
        table.innerHTML = '<tr><td colspan="5" class="text-center">No data available</td></tr>';
        return;
    }
    
    data.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><a href="#" class="domain-link-2" data-domain="${item.domain}">${item.domain}</a></td>
            <td>${item.mean.toFixed(2)}</td>
            <td>${item.min}</td>
            <td>${item.max}</td>
            <td>${item.count}</td>
        `;
        table.appendChild(row);
    });
    
    // Add click event to domain links
    document.querySelectorAll('.domain-link-2').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const domain = this.getAttribute('data-domain');
            document.getElementById('domain-input').value = domain;
            showSection('domain-section');
            analyzeDomain(domain);
        });
    });
}

function analyzeDomain(domain) {
    // Show loading indicator
    document.getElementById('domain-loading').classList.remove('d-none');
    document.getElementById('domain-content').classList.add('d-none');
    
    fetch('/domain_analytics', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ domain: domain })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('domain-loading').classList.add('d-none');
        
        if (data.success) {
            // Show content
            document.getElementById('domain-content').classList.remove('d-none');
            
            // Render charts
            Plotly.newPlot('domain-keyword-chart', data.charts.keyword_performance.data, data.charts.keyword_performance.layout);
            
            // Populate keyword ranking table
            populateKeywordRankingTable(data.keyword_data);
        } else if (data.error) {
            showAnalysisError('domain', data.error);
        }
    })
    .catch(error => {
        document.getElementById('domain-loading').classList.add('d-none');
        console.error('Error analyzing domain:', error);
        showAnalysisError('domain', 'Failed to analyze domain data');
    });
}

function populateKeywordRankingTable(data) {
    const table = document.getElementById('keyword-ranking-table');
    table.innerHTML = '';
    
    if (!data || data.length === 0) {
        table.innerHTML = '<tr><td colspan="5" class="text-center">No data available</td></tr>';
        return;
    }
    
    data.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><a href="#" class="keyword-link-2" data-keyword="${item.Keyword}">${item.Keyword}</a></td>
            <td>${item.mean.toFixed(2)}</td>
            <td>${item.min}</td>
            <td>${item.max}</td>
            <td>${item.count}</td>
        `;
        table.appendChild(row);
    });
    
    // Add click event to keyword links
    document.querySelectorAll('.keyword-link-2').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const keyword = this.getAttribute('data-keyword');
            document.getElementById('keyword-select').value = keyword;
            showSection('keyword-section');
            analyzeKeyword(keyword);
        });
    });
}