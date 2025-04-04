import streamlit as st
import pandas as pd
from urllib.parse import urlparse
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import io
import re
import datetime
from datetime import datetime
import requests

# Google Sheet Configuration
SHEET_ID = "1Z8S-lJygDcuB3gs120EoXLVMtZzgp7HQrjtNkkOqJQs"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=0"
SHEET_CSV_EXPORT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

# Set page configuration
st.set_page_config(
    page_title="Advanced SEO Position Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
        text-align: center;
    }
    .section-header {
        font-size: 1.8rem;
        font-weight: bold;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .filter-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .alert-box {
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
    }
    .warning-box {
        background-color: #fff3cd;
        color: #856404;
    }
    .error-box {
        background-color: #f8d7da;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions for date handling
def safe_format_date(date_value):
    """Safely format any date value to a string, handling any data type"""
    if date_value is None:
        return ""
    
    try:
        if isinstance(date_value, datetime.date) or isinstance(date_value, datetime.datetime):
            return date_value.strftime('%Y-%m-%d')
        elif isinstance(date_value, str):
            # Try to extract just the date part from string
            parts = date_value.split(' ')
            if len(parts) > 0:
                return parts[0]
            return date_value
        elif pd.isna(date_value):  # Handle NaN, NaT
            return ""
        else:
            # For any other type, convert to string safely
            return str(date_value)
    except Exception as e:
        # If all else fails, return empty string
        return ""

def get_safe_date_strings(dates_series):
    """Safely convert a series of dates to formatted strings"""
    if dates_series is None or len(dates_series) == 0:
        return []
    
    date_strings = []
    for d in dates_series:
        try:
            date_str = safe_format_date(d)
            if date_str:  # Only add non-empty strings
                date_strings.append(date_str)
        except:
            # Skip any date that causes an error
            pass
    
    return sorted(date_strings) if date_strings else []

# Helper functions
def get_domain(url):
    """Extract domain from URL"""
    try:
        return urlparse(url).netloc
    except (TypeError, ValueError):
        return None

def prepare_data(df):
    """Prepare data for analysis"""
    # Make a copy to avoid modifying the original
    df = df.copy()
    
    # Check for empty dataframe
    if df.empty:
        st.warning("Empty dataframe received. Using sample data instead.")
        return generate_sample_data()
    
    # Print column information
    st.write(f"Found columns: {df.columns.tolist()}")
    
    # Check for special format (position at end of URL)
    # Format: URL + Position + Keyword + DateTime (all in one row without proper columns)
    if len(df.columns) == 1:
        st.info("Detected single column data format - trying to parse")
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
                st.success(f"Successfully parsed {len(data_list)} rows from single column format")
                return pd.DataFrame(data_list)
            
        except Exception as e:
            st.error(f"Error parsing single column format: {str(e)}")
            
    # If we have a CSV without proper columns, try to identify and rename them
    if all(col.isdigit() or col.startswith('Unnamed:') for col in df.columns):
        st.info("CSV file with unnamed columns - trying to identify columns")
        # Check if it has the expected number of columns
        if len(df.columns) >= 4:
            # Rename columns based on position
            column_mapping = {
                df.columns[0]: 'Keyword',
                df.columns[1]: 'Time',
                df.columns[2]: 'Results',
                df.columns[3]: 'Position'
            }
            df = df.rename(columns=column_mapping)
            st.success("Successfully renamed columns")
    
    # Continue with normal processing
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
            except Exception as e:
                st.warning(f"Error converting {col} to datetime: {e}")
    
    # Add date column (without time)
    if 'Time' in df.columns:
        try:
            df['date'] = pd.NaT
            mask = df['Time'].notna()
            if mask.any():
                df.loc[mask, 'date'] = df.loc[mask, 'Time'].dt.date
        except Exception as e:
            st.warning(f"Error creating date column: {e}")
            # Create a simpler date column
            try:
                df['date'] = df['Time'].apply(lambda x: pd.to_datetime(x).date() if pd.notna(x) else None)
            except:
                pass
    
    # Handle case where we don't have expected columns
    if 'Keyword' not in df.columns or 'Results' not in df.columns or 'Position' not in df.columns:
        st.warning("Missing expected columns in the data. Using first rows as headers.")
        # Try to use the first row as header if possible
        try:
            new_header = df.iloc[0]
            df = df.iloc[1:]
            df.columns = new_header
            
            # Try again with key columns
            if 'Results' in df.columns:
                df['Results'] = df['Results'].astype(str)
                df['domain'] = df['Results'].apply(get_domain)
            if 'Keyword' in df.columns:
                df['Keyword'] = df['Keyword'].astype(str)
        except:
            st.error("Could not process data format")
    
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
        try:
            if isinstance(min_date, datetime.date):
                min_date_str = min_date.strftime('%Y-%m-%d')
            else:
                min_str = str(min_date)
                min_date_str = min_str.split(' ')[0] if ' ' in min_str else min_str
        except:
            min_date_str = "N/A"
            
        try:
            if isinstance(max_date, datetime.date):
                max_date_str = max_date.strftime('%Y-%m-%d')
            else:
                max_str = str(max_date)
                max_date_str = max_str.split(' ')[0] if ' ' in max_str else max_str
        except:
            max_date_str = "N/A"
        
        return [min_date_str, max_date_str]
    except:
        return ["N/A", "N/A"]

def apply_date_filter(df, start_date, end_date):
    """Apply date range filter to DataFrame"""
    if 'date' not in df.columns or not start_date or not end_date:
        return df
    
    try:
        start_date_dt = pd.to_datetime(start_date)
        end_date_dt = pd.to_datetime(end_date)
        return df[(df['date'] >= start_date_dt) & (df['date'] <= end_date_dt)]
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
    # Apply keyword filter
    if not keyword or 'Keyword' not in df.columns or keyword == "All Keywords":
        return df
    
    try:
        return df[df['Keyword'] == keyword]
    except Exception as e:
        st.warning(f"Error filtering by keyword: {e}")
        return df

def apply_domain_filter(df, domain):
    """Apply domain filter to DataFrame"""
    if not domain or 'domain' not in df.columns:
        return df
    
    return df[df['domain'] == domain]

def load_data_from_sheet():
    """Load data from Google Sheet CSV export"""
    try:
        # Use caching to prevent reloading the data on every UI interaction
        @st.cache_data(ttl=300)
        def fetch_sheet_data():
            try:
                # Fetch CSV data from the export URL
                try:
                    # First try with pandas read_csv
                    df = pd.read_csv(SHEET_CSV_EXPORT_URL)
                    return df
                except Exception as e1:
                    st.warning(f"Error with direct CSV read: {e1}")
                    # If that fails, try with requests
                    try:
                        response = requests.get(SHEET_CSV_EXPORT_URL)
                        if response.status_code == 200:
                            csv_content = response.content
                            df = pd.read_csv(io.StringIO(csv_content.decode('utf-8')))
                            return df
                        else:
                            raise Exception(f"Failed to fetch data: HTTP {response.status_code}")
                    except Exception as e2:
                        st.warning(f"Error with requests method: {e2}")
                        raise Exception("All connection methods failed")
            except Exception as e:
                st.warning(f"Could not connect to Google Sheet: {e}")
                st.info("Using sample data instead.")
                
                # Generate sample data if connection fails
                return generate_sample_data()
        
        return fetch_sheet_data()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def generate_sample_data():
    """Generate sample SEO position data for demonstration"""
    # Create sample keywords, domains, and dates
    keywords = ['best vpn', 'free vpn', 'vpn service', 'secure vpn', 'fast vpn']
    domains = ['nordvpn.com', 'expressvpn.com', 'surfshark.com', 'tunnelbear.com', 'privateinternetaccess.com', 
              'cyberghostvpn.com', 'vyprvpn.com', 'purevpn.com', 'ipvanish.com', 'torguard.net']
    
    # Generate dates for the last 30 days
    end_date = datetime.now()
    dates = [(end_date - datetime.timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
    
    # Generate data
    data = []
    for keyword in keywords:
        for date in dates:
            # Create a random set of URLs with positions for each keyword and date
            positions = list(range(1, 51))  # Top 50 positions
            np.random.shuffle(positions)
            
            for i, domain in enumerate(domains):
                if i < len(positions):
                    position = positions[i]
                    url = f"https://www.{domain}/page-{i+1}"
                    
                    data.append({
                        'Keyword': keyword,
                        'Time': date,
                        'Results': url,
                        'Position': position
                    })
    
    return pd.DataFrame(data)

# Main function to run the Streamlit app
def main():
    st.markdown('<h1 class="main-header">Advanced SEO Position Tracker</h1>', unsafe_allow_html=True)
    
    # Attempt to load data from Google Sheet
    with st.spinner("Loading data from Google Sheet..."):
        df = load_data_from_sheet()
        
        if not df.empty:
            # Process the data
            st.info(f"Processing data from: {SHEET_URL}")
            processed_df = prepare_data(df)
            
            # Store in session state
            st.session_state.data = df
            st.session_state.processed_data = processed_df
            
            # Extract unique values for filters
            if 'Keyword' in processed_df.columns:
                st.session_state.keywords = ["All Keywords"] + sorted(processed_df['Keyword'].unique().tolist())
            else:
                st.session_state.keywords = ["No keywords available"]
            
            if 'date' in processed_df.columns and not processed_df['date'].isna().all():
                # Filter out None values and safely get unique dates
                valid_dates = processed_df['date'].dropna().unique()
                date_strings = []
                
                for d in valid_dates:
                    try:
                        if isinstance(d, datetime.date):
                            date_strings.append(d.strftime('%Y-%m-%d'))
                        elif isinstance(d, str):
                            parts = d.split(' ')
                            if len(parts) > 0:
                                date_strings.append(parts[0])
                        else:
                            date_strings.append(str(d))
                    except:
                        # Skip dates that can't be formatted
                        pass
                
                st.session_state.dates = sorted(date_strings) if date_strings else []
            else:
                st.session_state.dates = []
            
            if 'Results' in processed_df.columns:
                st.session_state.urls = sorted(processed_df['Results'].dropna().unique().tolist())
            else:
                st.session_state.urls = []
            
            # Get summary statistics
            st.session_state.summary = {
                'total_keywords': processed_df['Keyword'].nunique() if 'Keyword' in processed_df.columns else 0,
                'total_domains': processed_df['domain'].nunique() if 'domain' in processed_df.columns else 0,
                'total_urls': processed_df['Results'].nunique() if 'Results' in processed_df.columns else 0,
                'date_range': get_date_range(processed_df)
            }
            
            st.success(f"Data loaded and processed successfully! {len(processed_df)} rows found.")
    
    # Create tabs for different sections
    tabs = st.tabs([
        "📊 Dashboard", 
        "🔑 Keyword Analysis", 
        "🌐 Domain Analysis", 
        "🔄 URL Comparison", 
        "⏱️ Time Comparison"
    ])
    
    # Initialize session state for data storage if not already done
    if 'data' not in st.session_state:
        st.session_state.data = None
    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = None
    if 'keywords' not in st.session_state:
        st.session_state.keywords = []
    if 'dates' not in st.session_state:
        st.session_state.dates = []
    if 'urls' not in st.session_state:
        st.session_state.urls = []
    if 'summary' not in st.session_state:
        st.session_state.summary = {}
    
    # Check if we have data before showing the tabs
    if st.session_state.processed_data is None:
        st.error("No data available. Please check your Google Sheet URL or try again later.")
        return
    
    # Display data summary
    st.sidebar.header("Data Summary")
    st.sidebar.metric("Total Keywords", st.session_state.summary.get('total_keywords', 0))
    st.sidebar.metric("Total Domains", st.session_state.summary.get('total_domains', 0))
    st.sidebar.metric("Total URLs", st.session_state.summary.get('total_urls', 0))
    date_range = st.session_state.summary.get('date_range', ["N/A", "N/A"])
    st.sidebar.metric("Date Range", f"{date_range[0]} to {date_range[1]}")
    
    # Display data preview
    if st.sidebar.checkbox("Show Data Preview"):
        st.sidebar.dataframe(st.session_state.processed_data.head(10), use_container_width=True)
    
    # Tab 1: Dashboard
    with tabs[0]:
        st.markdown('<h2 class="section-header">SEO Position Tracking Dashboard</h2>', unsafe_allow_html=True)
        
        # Filters for dashboard
        st.markdown('<div class="filter-container">', unsafe_allow_html=True)
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1, 1, 1, 1])
        
        with filter_col1:
            # Date range filter
            date_range = st.session_state.summary.get('date_range', ["N/A", "N/A"])
            
            if date_range[0] != "N/A":
                start_date = st.date_input(
                    "Start Date",
                    value=pd.to_datetime(date_range[0]).date(),
                    min_value=pd.to_datetime(date_range[0]).date(),
                    max_value=pd.to_datetime(date_range[1]).date()
                )
            else:
                start_date = st.date_input("Start Date", value=datetime.now().date())
            
            if date_range[1] != "N/A":
                end_date = st.date_input(
                    "End Date",
                    value=pd.to_datetime(date_range[1]).date(),
                    min_value=pd.to_datetime(date_range[0]).date(),
                    max_value=pd.to_datetime(date_range[1]).date()
                )
            else:
                end_date = st.date_input("End Date", value=datetime.now().date())
        
        with filter_col2:
            # Keyword filter
            keyword = st.selectbox(
                "Keyword Filter",
                options=st.session_state.keywords,
                index=0
            )
        
        with filter_col3:
            # Position range filter
            pos_col1, pos_col2 = st.columns(2)
            with pos_col1:
                position_min = st.number_input("Min Position", min_value=1, value=1)
            with pos_col2:
                position_max = st.number_input("Max Position", min_value=1, value=100)
        
        with filter_col4:
            top_n_options = [3, 5, 10, 20, 50, 100]
            
            top_n = st.selectbox(
                "Show Top N Results",
                options=top_n_options,
                index=1
            )
            
            # Apply filters button
            apply_button = st.button("Apply Filters", key="dashboard_apply")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Apply filters and generate dashboard
        if st.session_state.processed_data is not None:
            df = st.session_state.processed_data.copy()
            
            # Apply filters
            df = apply_date_filter(df, start_date, end_date)
            df = apply_keyword_filter(df, keyword)
            df = apply_position_filter(df, position_min, position_max)
            
            if len(df) == 0:
                st.warning("No data matches the selected filters.")
            else:
                # Create dashboard visualizations
                col1, col2 = st.columns(2)
                
                with col1:
                    # Position Distribution Chart
                    st.markdown('<h3>Position Distribution</h3>', unsafe_allow_html=True)
                    
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
                        
                        st.plotly_chart(pos_dist, use_container_width=True)
                    else:
                        st.error("Position data not available")
                
                with col2:
                    # Top Domains by Average Position
                    st.markdown('<h3>Top Domains by Average Position</h3>', unsafe_allow_html=True)
                    
                    if 'domain' in df.columns and 'Position' in df.columns:
                        domain_positions = df.groupby('domain')['Position'].mean().reset_index()
                        domain_positions = domain_positions.sort_values('Position')
                        
                        top_domains_chart = px.bar(
                            domain_positions.head(top_n), 
                            x='domain', 
                            y='Position',
                            title=f'Top {top_n} Domains by Average Position',
                            labels={'domain': 'Domain', 'Position': 'Average Position'},
                            color='Position',
                            color_continuous_scale='RdYlGn_r'
                        )
                        
                        top_domains_chart.update_layout(
                            xaxis_title="Domain",
                            yaxis_title="Average Position",
                            yaxis_autorange='reversed'  # Lower positions (better rankings) at the top
                        )
                        
                        st.plotly_chart(top_domains_chart, use_container_width=True)
                    else:
                        st.error("Domain and Position data not available")
                
                # Additional charts in new rows
                col3, col4 = st.columns(2)
                
                with col3:
                    # Top Keywords by Volume
                    st.markdown('<h3>Top Keywords by Volume</h3>', unsafe_allow_html=True)
                    
                    if 'Keyword' in df.columns and 'Results' in df.columns:
                        keyword_volume = df.groupby('Keyword')['Results'].nunique().reset_index()
                        keyword_volume = keyword_volume.sort_values('Results', ascending=False)
                        
                        keyword_chart = px.bar(
                            keyword_volume.head(top_n),
                            x='Keyword',
                            y='Results',
                            title=f'Top {top_n} Keywords by Number of URLs',
                            labels={'Keyword': 'Keyword', 'Results': 'Number of URLs'},
                            color='Results',
                            color_continuous_scale='Viridis'
                        )
                        
                        keyword_chart.update_layout(
                            xaxis_title="Keyword",
                            yaxis_title="Number of URLs",
                            xaxis_tickangle=-45
                        )
                        
                        st.plotly_chart(keyword_chart, use_container_width=True)
                    else:
                        st.error("Keyword and Results data not available")
                
                with col4:
                    # Top Domains by Frequency
                    st.markdown('<h3>Top Domains by Frequency</h3>', unsafe_allow_html=True)
                    
                    if 'domain' in df.columns:
                        domain_freq = df['domain'].value_counts().reset_index()
                        domain_freq.columns = ['domain', 'count']
                        
                        domain_freq_chart = px.bar(
                            domain_freq.head(top_n),
                            x='domain',
                            y='count',
                            title=f'Top {top_n} Domains by Frequency',
                            labels={'domain': 'Domain', 'count': 'Frequency'},
                            color='count',
                            color_continuous_scale='Viridis'
                        )
                        
                        domain_freq_chart.update_layout(
                            xaxis_title="Domain",
                            yaxis_title="Frequency",
                            xaxis_tickangle=-45
                        )
                        
                        st.plotly_chart(domain_freq_chart, use_container_width=True)
                    else:
                        st.error("Domain data not available")
    
    # Tab 2: Keyword Analysis
    with tabs[1]:
        st.markdown('<h2 class="section-header">Keyword Analysis</h2>', unsafe_allow_html=True)
        
        # Filters for keyword analysis
        st.markdown('<div class="filter-container">', unsafe_allow_html=True)
        kw_filter_col1, kw_filter_col2, kw_filter_col3, kw_filter_col4 = st.columns([1, 1, 1, 1])
        
        with kw_filter_col1:
            # Select keyword
            selected_keyword = st.selectbox(
                "Select Keyword",
                options=st.session_state.keywords if len(st.session_state.keywords) > 1 else ["No keywords available"],
                index=1 if len(st.session_state.keywords) > 1 else 0
            )
        
        with kw_filter_col2:
            # Date range filter
            date_range = st.session_state.summary.get('date_range', ["N/A", "N/A"])
            
            if date_range[0] != "N/A":
                kw_start_date = st.date_input(
                    "Start Date",
                    value=pd.to_datetime(date_range[0]).date(),
                    min_value=pd.to_datetime(date_range[0]).date(),
                    max_value=pd.to_datetime(date_range[1]).date(),
                    key="kw_start_date"
                )
            else:
                kw_start_date = st.date_input("Start Date", value=datetime.now().date(), key="kw_start_date")
            
            if date_range[1] != "N/A":
                kw_end_date = st.date_input(
                    "End Date",
                    value=pd.to_datetime(date_range[1]).date(),
                    min_value=pd.to_datetime(date_range[0]).date(),
                    max_value=pd.to_datetime(date_range[1]).date(),
                    key="kw_end_date"
                )
            else:
                kw_end_date = st.date_input("End Date", value=datetime.now().date(), key="kw_end_date")
        
        with kw_filter_col3:
            # Domain filter (optional)
            if 'domain' in st.session_state.processed_data.columns:
                domains = ["All Domains"] + sorted(st.session_state.processed_data['domain'].dropna().unique().tolist())
                selected_domain = st.selectbox(
                    "Domain Filter (Optional)",
                    options=domains,
                    index=0
                )
            else:
                selected_domain = None
        
        with kw_filter_col4:
            top_kw_n = st.selectbox(
                "Show Top N Domains",
                options=[3, 5, 10, 20, 50, 100],
                index=1,
                key="top_kw_n"
            )
            
            # Apply filters button
            apply_kw_button = st.button("Analyze Keyword", key="keyword_apply")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Apply filters and generate keyword analysis
        if selected_keyword != "All Keywords" and selected_keyword != "No keywords available":
            df = st.session_state.processed_data.copy()
            
            # Apply filters
            df = apply_date_filter(df, kw_start_date, kw_end_date)
            df = df[df['Keyword'] == selected_keyword]
            
            if selected_domain and selected_domain != "All Domains":
                df = df[df['domain'] == selected_domain]
            
            if len(df) == 0:
                st.warning(f"No data found for keyword '{selected_keyword}' with the selected filters.")
            else:
                # Available dates information
                st.markdown(f"<h3>Available Dates for '{selected_keyword}'</h3>", unsafe_allow_html=True)
                
                if 'date' in df.columns:
                    try:
                        valid_dates = df['date'].dropna().unique()
                        date_str = get_safe_date_strings(valid_dates)
                        
                        date_text = ", ".join(date_str)
                        st.info(f"Data available for dates: {date_text}")
                    except Exception as e:
                        st.warning(f"Error displaying dates: {e}")
                        # Just display the count
                        st.info(f"Data available for {df['date'].nunique()} unique dates")
                
                # Create keyword analysis visualizations
                kw_col1, kw_col2 = st.columns(2)
                
                with kw_col1:
                    # Position Distribution Chart
                    st.markdown('<h3>Position Distribution</h3>', unsafe_allow_html=True)
                    
                    if 'Position' in df.columns:
                        pos_dist = px.histogram(
                            df, 
                            x='Position',
                            title=f'Position Distribution for "{selected_keyword}"',
                            labels={'Position': 'Position', 'count': 'Count'},
                            nbins=20,
                            color_discrete_sequence=['#3366CC']
                        )
                        
                        pos_dist.update_layout(
                            xaxis_title="Position",
                            yaxis_title="Count",
                            bargap=0.1
                        )
                        
                        st.plotly_chart(pos_dist, use_container_width=True)
                    else:
                        st.error("Position data not available")
                
                with kw_col2:
                    # Domain Performance Chart
                    st.markdown('<h3>Domain Performance</h3>', unsafe_allow_html=True)
                    
                    if 'domain' in df.columns and 'Position' in df.columns:
                        domain_positions = df.groupby('domain')['Position'].agg(['mean', 'min', 'max', 'count']).reset_index()
                        domain_positions = domain_positions.sort_values('mean')
                        
                        domain_perf = px.bar(
                            domain_positions.head(top_kw_n), 
                            x='domain', 
                            y='mean',
                            error_y='count',
                            title=f'Top {top_kw_n} Domains for "{selected_keyword}"',
                            labels={'domain': 'Domain', 'mean': 'Average Position'},
                            color='mean',
                            color_continuous_scale='RdYlGn_r'
                        )
                        
                        domain_perf.update_layout(
                            xaxis_title="Domain",
                            yaxis_title="Average Position",
                            yaxis_autorange='reversed'  # Lower positions (better rankings) at the top
                        )
                        
                        st.plotly_chart(domain_perf, use_container_width=True)
                    else:
                        st.error("Domain and Position data not available")
                
                # Position Trend Over Time
                st.markdown('<h3>Position Trend Over Time</h3>', unsafe_allow_html=True)
                
                if 'date' in df.columns and 'Position' in df.columns and 'domain' in df.columns:
                    # Get top domains for this keyword
                    top_domains = domain_positions.head(top_kw_n)['domain'].tolist()
                    
                    # Filter data for these domains
                    trend_data = df[df['domain'].isin(top_domains)]
                    
                    if not trend_data.empty:
                        # Group by date and domain, calculate average position
                        trend_daily = trend_data.groupby(['date', 'domain'])['Position'].mean().reset_index()
                        
                        # Create trend chart
                        trend_chart = px.line(
                            trend_daily,
                            x='date',
                            y='Position',
                            color='domain',
                            title=f'Position Trend Over Time for "{selected_keyword}"',
                            labels={'date': 'Date', 'Position': 'Position', 'domain': 'Domain'}
                        )
                        
                        trend_chart.update_layout(
                            xaxis_title="Date",
                            yaxis_title="Position",
                            yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                            legend_title="Domain"
                        )
                        
                        st.plotly_chart(trend_chart, use_container_width=True)
                    else:
                        st.info("Not enough data to display trend over time.")
                else:
                    st.error("Required data for trend chart not available")
                
                # Domain Performance Table
                st.markdown('<h3>Domain Performance Details</h3>', unsafe_allow_html=True)
                
                if 'domain' in df.columns and 'Position' in df.columns:
                    # Round numeric columns to 2 decimal places
                    for col in ['mean', 'min', 'max']:
                        if col in domain_positions.columns:
                            domain_positions[col] = domain_positions[col].round(2)
                    
                    # Rename columns for better display
                    domain_positions = domain_positions.rename(columns={
                        'mean': 'Average Position',
                        'min': 'Best Position',
                        'max': 'Worst Position',
                        'count': 'Occurrences'
                    })
                    
                    st.dataframe(domain_positions, use_container_width=True)
                else:
                    st.error("Domain and Position data not available")
    
    # Tab 3: Domain Analysis
    with tabs[2]:
        st.markdown('<h2 class="section-header">Domain Analysis</h2>', unsafe_allow_html=True)
        
        # Filters for domain analysis
        st.markdown('<div class="filter-container">', unsafe_allow_html=True)
        dom_filter_col1, dom_filter_col2, dom_filter_col3, dom_filter_col4 = st.columns([1, 1, 1, 1])
        
        with dom_filter_col1:
            # Domain input
            if 'domain' in st.session_state.processed_data.columns:
                domains = sorted(st.session_state.processed_data['domain'].dropna().unique().tolist())
                selected_domain_analysis = st.selectbox(
                    "Select Domain",
                    options=domains,
                    index=0 if domains else None
                )
            else:
                selected_domain_analysis = st.text_input("Enter Domain", "example.com")
        
        with dom_filter_col2:
            # Date range filter
            date_range = st.session_state.summary.get('date_range', ["N/A", "N/A"])
            
            if date_range[0] != "N/A":
                dom_start_date = st.date_input(
                    "Start Date",
                    value=pd.to_datetime(date_range[0]).date(),
                    min_value=pd.to_datetime(date_range[0]).date(),
                    max_value=pd.to_datetime(date_range[1]).date(),
                    key="dom_start_date"
                )
            else:
                dom_start_date = st.date_input("Start Date", value=datetime.now().date(), key="dom_start_date")
            
            if date_range[1] != "N/A":
                dom_end_date = st.date_input(
                    "End Date",
                    value=pd.to_datetime(date_range[1]).date(),
                    min_value=pd.to_datetime(date_range[0]).date(),
                    max_value=pd.to_datetime(date_range[1]).date(),
                    key="dom_end_date"
                )
            else:
                dom_end_date = st.date_input("End Date", value=datetime.now().date(), key="dom_end_date")
        
        with dom_filter_col3:
            # Position range filter
            dom_pos_col1, dom_pos_col2 = st.columns(2)
            with dom_pos_col1:
                dom_position_min = st.number_input("Min Position", min_value=1, value=1, key="dom_pos_min")
            with dom_pos_col2:
                dom_position_max = st.number_input("Max Position", min_value=1, value=100, key="dom_pos_max")
        
        with dom_filter_col4:
            top_dom_n = st.selectbox(
                "Show Top N Keywords",
                options=[3, 5, 10, 20, 50, 100],
                index=1,
                key="top_dom_n"
            )
            
            # Apply filters button
            apply_dom_button = st.button("Analyze Domain", key="domain_apply")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Apply filters and generate domain analysis
        if selected_domain_analysis:
            df = st.session_state.processed_data.copy()
            
            # Apply filters
            df = apply_date_filter(df, dom_start_date, dom_end_date)
            df = apply_position_filter(df, dom_position_min, dom_position_max)
            
            # Filter by domain
            if 'domain' in df.columns:
                df = df[df['domain'] == selected_domain_analysis]
            else:
                st.error("Domain data not available in the dataset")
                return
            
            if len(df) == 0:
                st.warning(f"No data found for domain '{selected_domain_analysis}' with the selected filters.")
            else:
                # Create domain analysis visualizations
                dom_col1, dom_col2 = st.columns(2)
                
                with dom_col1:
                    # Keyword Performance Chart
                    st.markdown('<h3>Keyword Performance</h3>', unsafe_allow_html=True)
                    
                    if 'Keyword' in df.columns and 'Position' in df.columns:
                        keyword_perf = df.groupby('Keyword')['Position'].agg(['mean', 'min', 'max', 'count']).reset_index()
                        keyword_perf = keyword_perf.sort_values('mean')
                        
                        keyword_chart = px.bar(
                            keyword_perf.head(top_dom_n), 
                            x='Keyword', 
                            y='mean',
                            title=f'Top {top_dom_n} Keywords for "{selected_domain_analysis}"',
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
                        
                        st.plotly_chart(keyword_chart, use_container_width=True)
                    else:
                        st.error("Keyword and Position data not available")
                
                with dom_col2:
                    # Position Distribution Chart
                    st.markdown('<h3>Position Distribution</h3>', unsafe_allow_html=True)
                    
                    if 'Position' in df.columns:
                        pos_dist = px.histogram(
                            df, 
                            x='Position',
                            title=f'Position Distribution for "{selected_domain_analysis}"',
                            labels={'Position': 'Position', 'count': 'Count'},
                            nbins=20,
                            color_discrete_sequence=['#3366CC']
                        )
                        
                        pos_dist.update_layout(
                            xaxis_title="Position",
                            yaxis_title="Count",
                            bargap=0.1
                        )
                        
                        st.plotly_chart(pos_dist, use_container_width=True)
                    else:
                        st.error("Position data not available")
                
                # Position Trend Over Time
                st.markdown('<h3>Position Trend Over Time</h3>', unsafe_allow_html=True)
                
                if 'date' in df.columns and 'Position' in df.columns and 'Keyword' in df.columns:
                    # Get top keywords for this domain
                    top_keywords = keyword_perf.head(top_dom_n)['Keyword'].tolist()
                    
                    # Filter data for these keywords
                    trend_data = df[df['Keyword'].isin(top_keywords)]
                    
                    if not trend_data.empty:
                        # Group by date and keyword, calculate average position
                        trend_daily = trend_data.groupby(['date', 'Keyword'])['Position'].mean().reset_index()
                        
                        # Create trend chart
                        trend_chart = px.line(
                            trend_daily,
                            x='date',
                            y='Position',
                            color='Keyword',
                            title=f'Position Trend Over Time for "{selected_domain_analysis}"',
                            labels={'date': 'Date', 'Position': 'Position', 'Keyword': 'Keyword'}
                        )
                        
                        trend_chart.update_layout(
                            xaxis_title="Date",
                            yaxis_title="Position",
                            yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                            legend_title="Keyword"
                        )
                        
                        st.plotly_chart(trend_chart, use_container_width=True)
                    else:
                        st.info("Not enough data to display trend over time.")
                else:
                    st.error("Required data for trend chart not available")
                
                # Keyword Performance Table
                st.markdown('<h3>Keyword Performance Details</h3>', unsafe_allow_html=True)
                
                if 'Keyword' in df.columns and 'Position' in df.columns:
                    # Round numeric columns to 2 decimal places
                    for col in ['mean', 'min', 'max']:
                        if col in keyword_perf.columns:
                            keyword_perf[col] = keyword_perf[col].round(2)
                    
                    # Rename columns for better display
                    keyword_perf = keyword_perf.rename(columns={
                        'mean': 'Average Position',
                        'min': 'Best Position',
                        'max': 'Worst Position',
                        'count': 'Occurrences'
                    })
                    
                    st.dataframe(keyword_perf, use_container_width=True)
                else:
                    st.error("Keyword and Position data not available")
    
    # Tab 4: URL Comparison
    with tabs[3]:
        st.markdown('<h2 class="section-header">URL Comparison</h2>', unsafe_allow_html=True)
        
        # Filters for URL comparison
        st.markdown('<div class="filter-container">', unsafe_allow_html=True)
        url_filter_col1, url_filter_col2, url_filter_col3 = st.columns([2, 1, 1])
        
        with url_filter_col1:
            # URL selection
            if st.session_state.urls:
                selected_urls = st.multiselect(
                    "Select URLs to Compare",
                    options=st.session_state.urls,
                    default=st.session_state.urls[:2] if len(st.session_state.urls) >= 2 else st.session_state.urls[:1]
                )
            else:
                selected_urls = []
                st.error("No URLs available in the dataset")
        
        with url_filter_col2:
            # Date range filter
            date_range = st.session_state.summary.get('date_range', ["N/A", "N/A"])
            
            if date_range[0] != "N/A":
                url_start_date = st.date_input(
                    "Start Date",
                    value=pd.to_datetime(date_range[0]).date(),
                    min_value=pd.to_datetime(date_range[0]).date(),
                    max_value=pd.to_datetime(date_range[1]).date(),
                    key="url_start_date"
                )
            else:
                url_start_date = st.date_input("Start Date", value=datetime.now().date(), key="url_start_date")
            
            if date_range[1] != "N/A":
                url_end_date = st.date_input(
                    "End Date",
                    value=pd.to_datetime(date_range[1]).date(),
                    min_value=pd.to_datetime(date_range[0]).date(),
                    max_value=pd.to_datetime(date_range[1]).date(),
                    key="url_end_date"
                )
            else:
                url_end_date = st.date_input("End Date", value=datetime.now().date(), key="url_end_date")
        
        with url_filter_col3:
            # Apply comparison button
            st.write("")  # Adding space for alignment
            st.write("")  # Adding space for alignment
            apply_url_button = st.button("Compare URLs", key="url_compare")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Apply filters and generate URL comparison
        if selected_urls and len(selected_urls) > 0:
            df = st.session_state.processed_data.copy()
            
            # Apply date range filter
            df = apply_date_filter(df, url_start_date, url_end_date)
            
            # Filter by URLs
            if 'Results' in df.columns:
                url_df = df[df['Results'].isin(selected_urls)]
            else:
                st.error("URL data not available in the dataset")
                return
            
            if len(url_df) == 0:
                st.warning("No data found for the selected URLs with the given filters.")
            else:
                # Prepare URL performance data
                url_data = []
                for url in selected_urls:
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
                
                # Create URL comparison visualizations
                url_col1, url_col2 = st.columns(2)
                
                with url_col1:
                    # URL Comparison Chart
                    st.markdown('<h3>URL Position Comparison</h3>', unsafe_allow_html=True)
                    
                    if url_data:
                        url_comparison_df = pd.DataFrame(url_data)
                        
                        url_comparison_chart = px.bar(
                            url_comparison_df,
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
                        
                        st.plotly_chart(url_comparison_chart, use_container_width=True)
                    else:
                        st.error("Not enough data for URL comparison chart")
                
                with url_col2:
                    # Keyword Performance by URL Chart
                    st.markdown('<h3>URL Performance by Keyword</h3>', unsafe_allow_html=True)
                    
                    if 'Keyword' in url_df.columns and 'Position' in url_df.columns:
                        try:
                            # Get top 5 keywords by frequency across these URLs
                            top_keywords = url_df['Keyword'].value_counts().head(5).index.tolist()
                            
                            # For each keyword, get position by URL
                            keyword_comparison_data = []
                            
                            for keyword in top_keywords:
                                if keyword is not None:  # Only process non-None keywords
                                    keyword_data = url_df[url_df['Keyword'] == keyword]
                                    
                                    for url in selected_urls:
                                        if url is not None:  # Only process non-None URLs
                                            url_keyword_data = keyword_data[keyword_data['Results'] == url]
                                            
                                            if not url_keyword_data.empty:
                                                keyword_comparison_data.append({
                                                    'keyword': str(keyword),  # Convert to string for safety
                                                    'url': str(url),  # Convert to string for safety
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
                                
                                st.plotly_chart(keyword_comparison_chart, use_container_width=True)
                            else:
                                st.info("Not enough keyword data for the selected URLs.")
                        except Exception as e:
                            st.error(f"Error creating keyword comparison chart: {e}")
                            st.info("Not enough valid keyword data for the selected URLs.")
                    else:
                        st.error("Keyword and Position data not available")
                
                # Position Trend Over Time
                st.markdown('<h3>Position Trend Over Time</h3>', unsafe_allow_html=True)
                
                if 'date' in url_df.columns and len(selected_urls) > 0:
                    # For each URL, get positions over time
                    trend_data = []
                    for url in selected_urls:
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
                        
                        st.plotly_chart(time_comparison_chart, use_container_width=True)
                    else:
                        st.info("Not enough time data to display trend.")
                else:
                    st.error("Date data not available for trend chart")
                
                # URL Data Table
                st.markdown('<h3>URL Performance Details</h3>', unsafe_allow_html=True)
                
                if url_data:
                    # Create a DataFrame from the URL data
                    url_table_df = pd.DataFrame(url_data)
                    
                    # Round numeric columns to 2 decimal places
                    for col in ['avg_position', 'best_position', 'worst_position']:
                        if col in url_table_df.columns:
                            url_table_df[col] = url_table_df[col].round(2)
                    
                    # Rename columns for better display
                    url_table_df = url_table_df.rename(columns={
                        'url': 'URL',
                        'avg_position': 'Average Position',
                        'best_position': 'Best Position',
                        'worst_position': 'Worst Position',
                        'keywords_count': 'Keywords Count'
                    })
                    
                    st.dataframe(url_table_df, use_container_width=True)
                else:
                    st.error("URL performance data not available")
    
    # Tab 5: Time Comparison
    with tabs[4]:
        st.markdown('<h2 class="section-header">Time Comparison</h2>', unsafe_allow_html=True)
        
        # Filters for time comparison
        st.markdown('<div class="filter-container">', unsafe_allow_html=True)
        time_filter_col1, time_filter_col2, time_filter_col3, time_filter_col4 = st.columns([1, 1, 1, 1])
        
        with time_filter_col1:
            # Select keyword
            time_keyword = st.selectbox(
                "Select Keyword",
                options=st.session_state.keywords if len(st.session_state.keywords) > 1 else ["No keywords available"],
                index=1 if len(st.session_state.keywords) > 1 else 0,
                key="time_keyword"
            )
        
        # Initialize dates when a keyword is selected
        keyword_dates = []
        if 'processed_data' in st.session_state and st.session_state.processed_data is not None and time_keyword != "All Keywords" and time_keyword != "No keywords available":
            df = st.session_state.processed_data.copy()
            keyword_df = df[df['Keyword'] == time_keyword]
            
            if 'date' in keyword_df.columns:
                dates = sorted(keyword_df['date'].dropna().unique())
                keyword_dates = [d.strftime('%Y-%m-%d') if isinstance(d, datetime.date) else str(d).split(' ')[0] 
                                for d in dates]
        
        with time_filter_col2:
            # Start date selection
            if keyword_dates:
                time_start_date = st.selectbox(
                    "Start Date",
                    options=keyword_dates,
                    index=0,
                    key="time_start_date"
                )
            else:
                time_start_date = st.selectbox(
                    "Start Date",
                    options=["Select a keyword first"],
                    index=0,
                    disabled=True,
                    key="time_start_date_disabled"
                )
        
        with time_filter_col3:
            # End date selection
            if keyword_dates and len(keyword_dates) > 1:
                time_end_date = st.selectbox(
                    "End Date",
                    options=keyword_dates,
                    index=len(keyword_dates)-1,
                    key="time_end_date"
                )
            else:
                time_end_date = st.selectbox(
                    "End Date",
                    options=["Select a keyword first"],
                    index=0,
                    disabled=True,
                    key="time_end_date_disabled"
                )
        
        with time_filter_col4:
            # Apply comparison button
            st.write("")  # Adding space for alignment
            st.write("")  # Adding space for alignment
            apply_time_button = st.button("Compare Over Time", key="time_compare")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Apply filters and generate time comparison
        if (time_keyword != "All Keywords" and time_keyword != "No keywords available" and 
            time_start_date != "Select a keyword first" and time_end_date != "Select a keyword first"):
            
            df = st.session_state.processed_data.copy()
            
            # Filter by keyword
            df = df[df['Keyword'] == time_keyword]
            
            # Convert dates
            try:
                start_date_dt = pd.to_datetime(time_start_date).date()
                end_date_dt = pd.to_datetime(time_end_date).date()
                
                # Filter by dates
                if 'date' in df.columns:
                    start_data = df[df['date'] == start_date_dt].copy()
                    end_data = df[df['date'] == end_date_dt].copy()
                else:
                    st.error("Date data not available in the dataset")
                    return
                
                if len(start_data) == 0 and len(end_data) == 0:
                    st.warning(f"No data found for keyword '{time_keyword}' on the selected dates.")
                else:
                    # Sort data by position
                    if not start_data.empty:
                        start_data = start_data.sort_values(by='Position', ascending=True)
                    if not end_data.empty:
                        end_data = end_data.sort_values(by='Position', ascending=True)
                    
                    # Display summary
                    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
                    summary_col1, summary_col2, summary_col3 = st.columns(3)
                    
                    with summary_col1:
                        st.markdown(f"<b>Keyword:</b> {time_keyword}", unsafe_allow_html=True)
                    
                    with summary_col2:
                        start_count = len(start_data) if not start_data.empty else 0
                        st.markdown(f"<b>Start Date:</b> {time_start_date} ({start_count} URLs found)", unsafe_allow_html=True)
                    
                    with summary_col3:
                        end_count = len(end_data) if not end_data.empty else 0
                        st.markdown(f"<b>End Date:</b> {time_end_date} ({end_count} URLs found)", unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Create data for comparing positions
                    start_urls = []
                    if not start_data.empty:
                        for _, row in start_data.iterrows():
                            url = row['Results']
                            position = row['Position']
                            
                            if pd.notna(url) and pd.notna(position):
                                domain = row['domain'] if 'domain' in row else get_domain(url)
                                
                                start_urls.append({
                                    'url': url,
                                    'position': int(position) if isinstance(position, (int, float)) else position,
                                    'domain': domain
                                })
                    
                    end_urls = []
                    if not end_data.empty:
                        for _, row in end_data.iterrows():
                            url = row['Results']
                            position = row['Position']
                            
                            if pd.notna(url) and pd.notna(position):
                                domain = row['domain'] if 'domain' in row else get_domain(url)
                                
                                end_urls.append({
                                    'url': url,
                                    'position': int(position) if isinstance(position, (int, float)) else position,
                                    'domain': domain
                                })
                    
                    # Create start/end position maps for position change calculation
                    start_positions = {item['url']: item['position'] for item in start_urls}
                    end_positions = {item['url']: item['position'] for item in end_urls}
                    
                    # Add position change information
                    for url_data in start_urls:
                        if url_data['url'] in end_positions:
                            change = end_positions[url_data['url']] - url_data['position']
                            if change < 0:
                                url_data['position_change_text'] = f"↑ {abs(change)} (improved)"
                                url_data['position_change'] = change
                            elif change > 0:
                                url_data['position_change_text'] = f"↓ {change} (declined)"
                                url_data['position_change'] = change
                            else:
                                url_data['position_change_text'] = "No change"
                                url_data['position_change'] = 0
                        else:
                            url_data['position_change_text'] = "Not in end data"
                            url_data['position_change'] = None
                    
                    for url_data in end_urls:
                        if url_data['url'] in start_positions:
                            change = url_data['position'] - start_positions[url_data['url']]
                            if change < 0:
                                url_data['position_change_text'] = f"↑ {abs(change)} (improved)"
                                url_data['position_change'] = change
                            elif change > 0:
                                url_data['position_change_text'] = f"↓ {change} (declined)"
                                url_data['position_change'] = change
                            else:
                                url_data['position_change_text'] = "No change"
                                url_data['position_change'] = 0
                        else:
                            url_data['position_change_text'] = "New"
                            url_data['position_change'] = None
                    
                    # Create position changes analysis
                    all_urls = set()
                    for url_data in start_urls:
                        all_urls.add(url_data['url'])
                    
                    for url_data in end_urls:
                        all_urls.add(url_data['url'])
                    
                    position_changes = []
                    for url in all_urls:
                        start_pos = start_positions.get(url)
                        end_pos = end_positions.get(url)
                        
                        if start_pos is not None or end_pos is not None:
                            change_data = {
                                'url': url,
                                'domain': get_domain(url),
                                'start_position': start_pos,
                                'end_position': end_pos
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
                    
                    # Sort by absolute change value (biggest changes first)
                    position_changes = sorted(position_changes, 
                        key=lambda x: (
                            # Sort order: first by status (changed, then new/dropped, then unchanged)
                            0 if x['status'] in ('improved', 'declined') else (1 if x['status'] in ('new', 'dropped') else 2),
                            # Then by absolute change value (descending)
                            abs(x['change']) if x['change'] is not None else 0
                        ), 
                        reverse=True
                    )
                    
                    # Display data tables
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown('<h3>Start Date URLs</h3>', unsafe_allow_html=True)
                        st.markdown('<p>Sorted by position (best positions first)</p>', unsafe_allow_html=True)
                        
                        if start_urls:
                            start_urls_df = pd.DataFrame(start_urls)
                            # Streamlit doesn't support conditional formatting, so we'll just display the DataFrame
                            st.dataframe(start_urls_df[['position', 'url', 'domain', 'position_change_text']], use_container_width=True)
                        else:
                            st.info("No data available for the start date.")
                    
                    with col2:
                        st.markdown('<h3>End Date URLs</h3>', unsafe_allow_html=True)
                        st.markdown('<p>Sorted by position (best positions first)</p>', unsafe_allow_html=True)
                        
                        if end_urls:
                            end_urls_df = pd.DataFrame(end_urls)
                            st.dataframe(end_urls_df[['position', 'url', 'domain', 'position_change_text']], use_container_width=True)
                        else:
                            st.info("No data available for the end date.")
                    
                    # Position Changes Analysis
                    st.markdown('<h3>Position Changes Analysis</h3>', unsafe_allow_html=True)
                    st.markdown('<p>All URLs with their position changes</p>', unsafe_allow_html=True)
                    
                    if position_changes:
                        position_changes_df = pd.DataFrame(position_changes)
                        st.dataframe(position_changes_df[['url', 'domain', 'start_position', 'end_position', 'change_text']], use_container_width=True)
                        
                        # Create visualization of position changes
                        pos_changes_viz = []
                        for change_data in position_changes:
                            if change_data['start_position'] is not None and change_data['end_position'] is not None:
                                pos_changes_viz.append({
                                    'domain': change_data['domain'],
                                    'change': change_data['change'],
                                    'status': change_data['status']
                                })
                        
                        if pos_changes_viz:
                            pos_changes_df = pd.DataFrame(pos_changes_viz)
                            
                            # Filter out unchanged positions for clarity
                            pos_changes_df = pos_changes_df[pos_changes_df['status'].isin(['improved', 'declined'])]
                            
                            if not pos_changes_df.empty:
                                # Create color mapping for improved/declined
                                status_colors = {
                                    'improved': '#4CAF50',  # Green
                                    'declined': '#F44336'   # Red
                                }
                                
                                # Sort by absolute change
                                pos_changes_df = pos_changes_df.sort_values('change', key=abs, ascending=False)
                                
                                fig = px.bar(
                                    pos_changes_df,
                                    x='domain',
                                    y='change',
                                    color='status',
                                    title='Position Changes by Domain',
                                    labels={'domain': 'Domain', 'change': 'Position Change'},
                                    color_discrete_map=status_colors
                                )
                                
                                fig.update_layout(
                                    xaxis_title="Domain",
                                    yaxis_title="Position Change (negative = improved, positive = declined)",
                                    xaxis_tickangle=-45
                                )
                                
                                st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No position changes data available.")
                        
            except Exception as e:
                st.error(f"Error processing time comparison: {str(e)}")

# Run the Streamlit app
if __name__ == '__main__':
    main()
