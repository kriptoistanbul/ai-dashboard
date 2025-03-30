# SEO Position Tracking Dashboard

A Python-based web application for visualizing and analyzing SEO position tracking data from Excel files.

## Features

- Upload and analyze Excel data containing SEO position tracking information
- Interactive dashboard with key metrics and visualizations
- Keyword analysis with position distribution and domain performance
- Domain analysis showing keyword performance for specific domains
- Data tables with detailed rankings and metrics

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/seo-dashboard.git
   cd seo-dashboard
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```
   python app.py
   ```

2. Open your web browser and navigate to `http://localhost:5000`

3. Upload your Excel file containing SEO position tracking data. The file should have the following columns:
   - Keyword: The search term
   - Time: Timestamp of the search
   - Results: URLs from search results
   - Position: Ranking position of each URL
   - Filled keyword: Repeated keyword (optional)
   - date/time: Alternative timestamp (optional)

4. Explore the dashboard to analyze your SEO data:
   - View overall statistics and trends
   - Analyze performance for specific keywords
   - Track domain rankings and performance
   - Identify top-performing domains and keywords

## Data Format

Your Excel file should contain at least the following columns:
- Keyword: The search term used
- Time: When the search was performed
- Results: The URL of each search result
- Position: The ranking position of each URL

Optional columns:
- Filled keyword: Same as Keyword (for data integrity)
- date/time: Alternative timestamp format

## Development

To modify or extend this application:

1. The backend is built with Flask and uses pandas for data processing
2. Frontend uses Bootstrap 5 for styling and Plotly.js for visualizations
3. Main JavaScript logic is in `static/js/main.js`
4. HTML template is in `templates/index.html`

## License

MIT License