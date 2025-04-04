import streamlit as st
import pandas as pd
from urllib.parse import urlparse
import datetime
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import re
import io
import base64

# Page configuration
st.set_page_config(page_title="SEO Position Tracker", page_icon="📈", layout="wide")

# Add custom CSS
st.markdown("""
<style>
    .main .block-container {padding-top: 2rem;}
    h1, h2, h3 {color: #1E3A8A;}
    .stTabs [data-baseweb="tab-list"] {gap: 24px;}
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 16px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {background-color: #E0E7FF;}
</style>
""", unsafe_allow_html=True)

# Utility Functions
def get_domain(url):
    """Extract domain from URL"""
    try:
        return urlparse(url).netloc
    except (TypeError, ValueError):
        return None

def prepare_data(df):
    """Prepare data for analysis"""
    # Check for special format (position at end of URL)
    if len(df.columns) == 1:
        st.write("Detected single column data format - trying to parse")
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
                st.write(f"Successfully parsed {len(data_list)} rows from single column format")
                return pd.DataFrame(data_list)
        except Exception as e:
            st.error(f"Error parsing single column format: {str(e)}")
    
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

def apply_date_filter(df, start_date, end_date):
    """Apply date range filter to DataFrame"""
    if 'date' not in df.columns:
        return df
    
    filtered_df = df.copy()
    
    if start_date:
        filtered_df = filtered_df[filtered_df['date'] >= start_date]
    
    if end_date:
        filtered_df = filtered_df[filtered_df['date'] <= end_date]
    
    return filtered_df

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
    if not keyword or keyword == "All Keywords" or 'Keyword' not in df.columns:
        return df
    
    return df[df['Keyword'] == keyword]

def apply_domain_filter(df, domain):
    """Apply domain filter to DataFrame"""
    if not domain or domain == "All Domains" or 'domain' not in df.columns:
        return df
    
    return df[df['domain'] == domain]

def load_data_from_gsheet(url):
    """Load data from Google Sheets URL"""
    try:
        # Extract the key/ID from the URL
        if '/d/' in url:
            sheet_id = url.split('/d/')[1].split('/')[0]
        else:
            return None, "Invalid Google Sheets URL format"
        
        # Create the export URL (CSV format)
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        
        # Load data from CSV export URL
        df = pd.read_csv(export_url)
        
        # Prepare data for analysis
        df = prepare_data(df)
        
        return df, None
    except Exception as e:
        return None, str(e)

def to_excel(df):
    """Convert DataFrame to Excel bytes for downloading"""
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Sheet1', index=False)
    writer.save()
    processed_data = output.getvalue()
    return processed_data

def get_table_download_link(df, filename="data.xlsx", text="Download Excel file"):
    """Generates a link to download the provided dataframe as an Excel file"""
    excel_file = to_excel(df)
    b64 = base64.b64encode(excel_file).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">{text}</a>'
    return href

# Initialize session state for data storage
if 'data' not in st.session_state:
    st.session_state.data = None

# Main application title
st.title("Advanced SEO Position Tracker")

# Create tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Upload Data", 
    "Dashboard", 
    "Keyword Analysis", 
    "Domain Analysis", 
    "URL Comparison", 
    "Time Comparison"
])

# Tab 1: Upload Data
with tab1:
    st.header("Upload Excel Data")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Option 1: Upload File")
        uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx", "xls", "csv"])
        
        st.divider()
        
        st.subheader("Option 2: Google Sheet")
        gsheet_url = st.text_input(
            "Enter Google Sheet URL",
            value="https://docs.google.com/spreadsheets/d/1Z8S-lJygDcuB3gs120EoXLVMtZzgp7HQrjtNkkOqJQs/edit?pli=1&gid=0#gid=0"
        )
        load_gsheet = st.button("Load from Google Sheet")
    
    with col2:
        if uploaded_file is not None:
            with st.spinner("Processing file..."):
                try:
                    # Determine file type and read accordingly
                    if uploaded_file.name.endswith('.csv'):
                        df = pd.read_csv(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)
                    
                    # Process the data
                    if 'Keyword' in df.columns:
                        df['Keyword'].fillna(method='ffill', inplace=True)
                    
                    # Process the data through the prepare_data function
                    df = prepare_data(df)
                    
                    # Store the data in session state
                    st.session_state.data = df
                    
                    # Display success and data summary
                    st.success("File uploaded and processed successfully!")
                    
                    # Show data summary
                    st.subheader("Data Summary")
                    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
                    
                    with metrics_col1:
                        st.metric("Total Keywords", df['Keyword'].nunique() if 'Keyword' in df.columns else 0)
                    
                    with metrics_col2:
                        st.metric("Total Domains", df['domain'].nunique() if 'domain' in df.columns else 0)
                    
                    with metrics_col3:
                        st.metric("Total URLs", df['Results'].nunique() if 'Results' in df.columns else 0)
                    
                    with metrics_col4:
                        date_range = get_date_range(df)
                        date_display = f"{date_range[0]} to {date_range[1]}" if date_range[0] != "N/A" else "N/A"
                        st.metric("Date Range", date_display)
                    
                    # Show data preview
                    st.subheader("Data Preview")
                    st.dataframe(df.head())
                    
                except Exception as e:
                    st.error(f"Error processing file: {str(e)}")
        
        elif load_gsheet:
            with st.spinner("Loading data from Google Sheet..."):
                df, error = load_data_from_gsheet(gsheet_url)
                
                if error:
                    st.error(f"Error loading data: {error}")
                else:
                    # Store the data in session state
                    st.session_state.data = df
                    
                    # Display success and data summary
                    st.success("Data loaded from Google Sheet successfully!")
                    
                    # Show data summary
                    st.subheader("Data Summary")
                    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
                    
                    with metrics_col1:
                        st.metric("Total Keywords", df['Keyword'].nunique() if 'Keyword' in df.columns else 0)
                    
                    with metrics_col2:
                        st.metric("Total Domains", df['domain'].nunique() if 'domain' in df.columns else 0)
                    
                    with metrics_col3:
                        st.metric("Total URLs", df['Results'].nunique() if 'Results' in df.columns else 0)
                    
                    with metrics_col4:
                        date_range = get_date_range(df)
                        date_display = f"{date_range[0]} to {date_range[1]}" if date_range[0] != "N/A" else "N/A"
                        st.metric("Date Range", date_display)
                    
                    # Show data preview
                    st.subheader("Data Preview")
                    st.dataframe(df.head())
    
    # Auto-load Google Sheet data on first run
    if st.session_state.data is None:
        with st.spinner("Auto-loading data from Google Sheet..."):
            df, error = load_data_from_gsheet("https://docs.google.com/spreadsheets/d/1Z8S-lJygDcuB3gs120EoXLVMtZzgp7HQrjtNkkOqJQs/edit?pli=1&gid=0#gid=0")
            
            if error:
                st.info("Please upload a file or load data from Google Sheet.")
            else:
                # Store the data in session state
                st.session_state.data = df
                
                # Display success and data summary
                st.success("Data auto-loaded from Google Sheet!")
                
                # Show data summary
                st.subheader("Data Summary")
                metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
                
                with metrics_col1:
                    st.metric("Total Keywords", df['Keyword'].nunique() if 'Keyword' in df.columns else 0)
                
                with metrics_col2:
                    st.metric("Total Domains", df['domain'].nunique() if 'domain' in df.columns else 0)
                
                with metrics_col3:
                    st.metric("Total URLs", df['Results'].nunique() if 'Results' in df.columns else 0)
                
                with metrics_col4:
                    date_range = get_date_range(df)
                    date_display = f"{date_range[0]} to {date_range[1]}" if date_range[0] != "N/A" else "N/A"
                    st.metric("Date Range", date_display)
                
                # Show data preview
                st.subheader("Data Preview")
                st.dataframe(df.head())

# Tab 2: Dashboard
with tab2:
    st.header("SEO Position Tracking Dashboard")
    
    if st.session_state.data is None:
        st.info("Please upload data or load from Google Sheet first.")
    else:
        df = st.session_state.data
        
        # Filter section
        st.subheader("Filter Data")
        
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1, 1, 1, 1])
        
        with filter_col1:
            # Date range filter
            if 'date' in df.columns:
                min_date = df['date'].min()
                max_date = df['date'].max()
                
                if not pd.isna(min_date) and not pd.isna(max_date):
                    date_range = st.date_input(
                        "Date Range",
                        value=(min_date, max_date),
                        min_value=min_date,
                        max_value=max_date
                    )
                    
                    if len(date_range) == 2:
                        start_date, end_date = date_range
                    else:
                        start_date = end_date = None
                else:
                    start_date = end_date = None
                    st.write("No valid dates available")
            else:
                start_date = end_date = None
                st.write("No date data available")
        
        with filter_col2:
            # Keyword filter
            if 'Keyword' in df.columns:
                keywords = ["All Keywords"] + sorted(df['Keyword'].unique().tolist())
                selected_keyword = st.selectbox("Keyword Filter", keywords)
            else:
                selected_keyword = None
                st.write("No keyword data available")
        
        with filter_col3:
            # Position range filter
            position_col1, position_col2 = st.columns(2)
            
            with position_col1:
                position_min = st.number_input("Min Position", min_value=1, value=1)
            
            with position_col2:
                position_max = st.number_input("Max Position", min_value=1, value=100)
        
        with filter_col4:
            # Apply filters button
            st.write("")  # Add some space
            apply_filter = st.button("Apply Filters")
        
        # Apply filters
        if apply_filter or 'dashboard_filtered' not in st.session_state:
            st.session_state.dashboard_filtered = True
            
            filtered_df = df.copy()
            
            # Apply date filter
            if start_date and end_date:
                filtered_df = apply_date_filter(filtered_df, start_date, end_date)
            
            # Apply keyword filter
            filtered_df = apply_keyword_filter(filtered_df, selected_keyword)
            
            # Apply position filter
            filtered_df = apply_position_filter(filtered_df, position_min, position_max)
            
            st.session_state.dashboard_df = filtered_df
        else:
            filtered_df = st.session_state.dashboard_df
        
        # Display metrics
        st.subheader("Key Metrics")
        
        metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
        
        with metrics_col1:
            st.metric("Total Keywords", filtered_df['Keyword'].nunique() if 'Keyword' in filtered_df.columns else 0)
        
        with metrics_col2:
            st.metric("Total Domains", filtered_df['domain'].nunique() if 'domain' in filtered_df.columns else 0)
        
        with metrics_col3:
            st.metric("Total URLs", filtered_df['Results'].nunique() if 'Results' in filtered_df.columns else 0)
        
        with metrics_col4:
            avg_position = filtered_df['Position'].mean() if 'Position' in filtered_df.columns else None
            st.metric("Average Position", f"{avg_position:.2f}" if avg_position else "N/A")
        
        # Download button
        st.download_button(
            label="Download Filtered Data",
            data=to_excel(filtered_df),
            file_name="seo_dashboard_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # Charts
        st.subheader("Visualizations")
        
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.write("#### Position Distribution")
            
            # Position distribution controls
            top_n_options = ["Top 3", "Top 5", "Top 10", "Top 20"]
            top_n = st.radio("Show", top_n_options, index=1, horizontal=True, key="pos_dist")
            top_n_value = int(top_n.split()[1])
            
            if 'Position' in filtered_df.columns:
                # Filter data
                pos_df = filtered_df[filtered_df['Position'] <= top_n_value]
                
                if not pos_df.empty:
                    # Create position distribution chart
                    pos_fig = px.histogram(
                        pos_df,
                        x='Position',
                        title=f'Position Distribution (Top {top_n_value})',
                        nbins=top_n_value,
                        color_discrete_sequence=['#3366CC']
                    )
                    
                    pos_fig.update_layout(
                        xaxis_title="Position",
                        yaxis_title="Count",
                        bargap=0.1
                    )
                    
                    st.plotly_chart(pos_fig, use_container_width=True)
                else:
                    st.info(f"No positions within top {top_n_value} found.")
            else:
                st.info("No position data available.")
        
        with chart_col2:
            st.write("#### Top Domains by Average Position")
            
            # Domain rank controls
            domain_top_n_options = ["Top 3", "Top 5", "Top 10", "Top 20"]
            domain_top_n = st.radio("Show", domain_top_n_options, index=1, horizontal=True, key="domain_dist")
            domain_top_n_value = int(domain_top_n.split()[1])
            
            if 'domain' in filtered_df.columns and 'Position' in filtered_df.columns:
                # Group by domain and calculate average position
                domain_df = filtered_df.groupby('domain')['Position'].mean().reset_index()
                domain_df = domain_df.sort_values('Position')
                
                if not domain_df.empty:
                    # Create top domains chart
                    domain_fig = px.bar(
                        domain_df.head(domain_top_n_value),
                        x='domain',
                        y='Position',
                        title=f'Top {domain_top_n_value} Domains by Average Position',
                        labels={'domain': 'Domain', 'Position': 'Average Position'},
                        color='Position',
                        color_continuous_scale='RdYlGn_r'
                    )
                    
                    domain_fig.update_layout(
                        xaxis_title="Domain",
                        yaxis_title="Average Position",
                        yaxis_autorange='reversed'  # Lower positions (better rankings) at the top
                    )
                    
                    st.plotly_chart(domain_fig, use_container_width=True)
                else:
                    st.info("No domain position data available.")
            else:
                st.info("No domain or position data available.")
        
        # Data tables
        table_col1, table_col2 = st.columns(2)
        
        with table_col1:
            st.write("#### Top Keywords by Volume")
            
            if 'Keyword' in filtered_df.columns and 'Results' in filtered_df.columns:
                # Group by keyword and count unique URLs
                keyword_volume = filtered_df.groupby('Keyword')['Results'].nunique().reset_index()
                keyword_volume = keyword_volume.sort_values('Results', ascending=False)
                keyword_volume.columns = ['Keyword', 'Number of URLs']
                
                # Display the table
                st.dataframe(keyword_volume.head(10), use_container_width=True)
            else:
                st.info("No keyword or URL data available.")
        
        with table_col2:
            st.write("#### Top Domains by Frequency")
            
            if 'domain' in filtered_df.columns:
                # Count domain frequencies
                domain_freq = filtered_df['domain'].value_counts().reset_index()
                domain_freq.columns = ['Domain', 'Frequency']
                
                # Display the table
                st.dataframe(domain_freq.head(10), use_container_width=True)
            else:
                st.info("No domain data available.")

# Tab 3: Keyword Analysis
with tab3:
    st.header("Keyword Analysis")
    
    if st.session_state.data is None:
        st.info("Please upload data or load from Google Sheet first.")
    else:
        df = st.session_state.data
        
        # Filter section
        st.subheader("Filter Data")
        
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1, 1, 1, 1])
        
        with filter_col1:
            # Keyword selector
            if 'Keyword' in df.columns:
                keywords = ["-- Select a keyword --"] + sorted(df['Keyword'].unique().tolist())
                selected_keyword = st.selectbox("Select Keyword", keywords, key="keyword_analysis_select")
            else:
                selected_keyword = None
                st.error("No keyword data available.")
        
        with filter_col2:
            # Date range filter
            if 'date' in df.columns:
                min_date = df['date'].min()
                max_date = df['date'].max()
                
                if not pd.isna(min_date) and not pd.isna(max_date):
                    date_range = st.date_input(
                        "Date Range",
                        value=(min_date, max_date),
                        min_value=min_date,
                        max_value=max_date,
                        key="keyword_date_range"
                    )
                    
                    if len(date_range) == 2:
                        start_date, end_date = date_range
                    else:
                        start_date = end_date = None
                else:
                    start_date = end_date = None
                    st.write("No valid dates available")
            else:
                start_date = end_date = None
                st.write("No date data available")
        
        with filter_col3:
            # Domain filter
            if 'domain' in df.columns:
                domains = ["All Domains"] + sorted(df['domain'].unique().tolist())
                selected_domain = st.selectbox("Domain Filter", domains, key="keyword_domain_filter")
            else:
                selected_domain = None
                st.write("No domain data available")
        
        with filter_col4:
            # Apply filters button
            st.write("")  # Add some space
            apply_filter = st.button("Analyze Keyword", key="analyze_keyword_btn")
        
        # Check if a keyword is selected
        if selected_keyword == "-- Select a keyword --" or selected_keyword is None:
            st.info("Please select a keyword to analyze.")
        else:
            # Apply filters
            if apply_filter or 'keyword_analyzed' not in st.session_state or st.session_state.keyword_analyzed != selected_keyword:
                st.session_state.keyword_analyzed = selected_keyword
                
                filtered_df = df.copy()
                
                # Apply keyword filter
                filtered_df = apply_keyword_filter(filtered_df, selected_keyword)
                
                # Apply date filter
                if start_date and end_date:
                    filtered_df = apply_date_filter(filtered_df, start_date, end_date)
                
                # Apply domain filter
                filtered_df = apply_domain_filter(filtered_df, selected_domain)
                
                st.session_state.keyword_df = filtered_df
            else:
                filtered_df = st.session_state.keyword_df
            
            # Check if there's data after filtering
            if filtered_df.empty:
                st.warning(f"No data available for keyword '{selected_keyword}' with the selected filters.")
            else:
                # Display available dates
                if 'date' in filtered_df.columns:
                    unique_dates = filtered_df['date'].dropna().unique()
                    formatted_dates = [d.strftime('%Y-%m-%d') if isinstance(d, datetime.date) else str(d) 
                                     for d in sorted(unique_dates)]
                    
                    with st.expander("Available Dates for Selected Keyword"):
                        st.write(", ".join(formatted_dates))
                
                # Download button
                st.download_button(
                    label="Download Analysis Data",
                    data=to_excel(filtered_df),
                    file_name=f"keyword_analysis_{selected_keyword}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                # Charts
                st.subheader("Visualizations")
                
                # Position distribution
                if 'Position' in filtered_df.columns:
                    pos_dist_fig = px.histogram(
                        filtered_df,
                        x='Position',
                        title=f'Position Distribution for "{selected_keyword}"',
                        nbins=20,
                        color_discrete_sequence=['#3366CC']
                    )
                    
                    pos_dist_fig.update_layout(
                        xaxis_title="Position",
                        yaxis_title="Count",
                        bargap=0.1
                    )
                    
                    st.plotly_chart(pos_dist_fig, use_container_width=True)
                
                # Domain analysis
                if 'domain' in filtered_df.columns and 'Position' in filtered_df.columns:
                    # Group by domain
                    domain_data = filtered_df.groupby('domain')['Position'].agg([
                        ('mean', 'mean'), 
                        ('min', 'min'), 
                        ('max', 'max'), 
                        ('count', 'count')
                    ]).reset_index()
                    
                    domain_data = domain_data.sort_values('mean')
                    
                    # Domain rank selector
                    domain_top_n = st.radio(
                        "Show top domains:", 
                        [3, 5, 10, 20], 
                        index=1,  # Default to 5
                        horizontal=True,
                        key="keyword_domain_top_n"
                    )
                    
                    # Domain performance chart
                    domain_fig = px.bar(
                        domain_data.head(domain_top_n),
                        x='domain',
                        y='mean',
                        error_y='count',
                        title=f'Top {domain_top_n} Domains for "{selected_keyword}"',
                        labels={'domain': 'Domain', 'mean': 'Average Position'},
                        color='mean',
                        color_continuous_scale='RdYlGn_r'
                    )
                    
                    domain_fig.update_layout(
                        xaxis_title="Domain",
                        yaxis_title="Average Position",
                        yaxis_autorange='reversed'  # Lower positions (better rankings) at the top
                    )
                    
                    st.plotly_chart(domain_fig, use_container_width=True)
                    
                    # Position trend over time
                    if 'date' in filtered_df.columns:
                        # Get top domains
                        top_domains = domain_data.head(domain_top_n)['domain'].tolist()
                        
                        # Filter data for these domains
                        trend_data = filtered_df[filtered_df['domain'].isin(top_domains)]
                        
                        if not trend_data.empty:
                            # Group by date and domain
                            trend_daily = trend_data.groupby(['date', 'domain'])['Position'].mean().reset_index()
                            
                            # Create trend chart
                            trend_fig = px.line(
                                trend_daily,
                                x='date',
                                y='Position',
                                color='domain',
                                title=f'Position Trend Over Time for "{selected_keyword}"',
                                labels={'date': 'Date', 'Position': 'Position', 'domain': 'Domain'}
                            )
                            
                            trend_fig.update_layout(
                                xaxis_title="Date",
                                yaxis_title="Position",
                                yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                                legend_title="Domain"
                            )
                            
                            st.plotly_chart(trend_fig, use_container_width=True)
                    
                    # Domain data table
                    st.subheader("Domain Performance")
                    
                    # Rename columns for display
                    display_df = domain_data.copy()
                    display_df.columns = ['Domain', 'Average Position', 'Best Position', 'Worst Position', 'Count']
                    
                    # Round average position to 2 decimal places
                    display_df['Average Position'] = display_df['Average Position'].round(2)
                    
                    st.dataframe(display_df, use_container_width=True)

# Tab 4: Domain Analysis
with tab4:
    st.header("Domain Analysis")
    
    if st.session_state.data is None:
        st.info("Please upload data or load from Google Sheet first.")
    else:
        df = st.session_state.data
        
        # Filter section
        st.subheader("Filter Data")
        
        filter_col1, filter_col2 = st.columns(2)
        
        with filter_col1:
            # Domain selector
            if 'domain' in df.columns:
                domains = ["-- Select a domain --"] + sorted(df['domain'].unique().tolist())
                selected_domain = st.selectbox("Select Domain", domains, key="domain_analysis_select")
            else:
                # If no domain column, provide text input
                selected_domain = st.text_input("Enter Domain", placeholder="example.com")
            
            # Date range filter
            if 'date' in df.columns:
                min_date = df['date'].min()
                max_date = df['date'].max()
                
                if not pd.isna(min_date) and not pd.isna(max_date):
                    date_range = st.date_input(
                        "Date Range",
                        value=(min_date, max_date),
                        min_value=min_date,
                        max_value=max_date,
                        key="domain_date_range"
                    )
                    
                    if len(date_range) == 2:
                        start_date, end_date = date_range
                    else:
                        start_date = end_date = None
                else:
                    start_date = end_date = None
                    st.write("No valid dates available")
            else:
                start_date = end_date = None
                st.write("No date data available")
        
        with filter_col2:
            # Position range filter
            position_col1, position_col2 = st.columns(2)
            
            with position_col1:
                position_min = st.number_input("Min Position", min_value=1, value=1, key="domain_pos_min")
            
            with position_col2:
                position_max = st.number_input("Max Position", min_value=1, value=100, key="domain_pos_max")
            
            # Apply filters button
            analyze_domain = st.button("Analyze Domain", key="analyze_domain_btn")
        
        # Check if a domain is selected
        if (selected_domain == "-- Select a domain --" or not selected_domain) and not analyze_domain:
            st.info("Please select or enter a domain to analyze.")
        elif analyze_domain or ('domain_analyzed' in st.session_state and st.session_state.domain_analyzed == selected_domain):
            st.session_state.domain_analyzed = selected_domain
            
            filtered_df = df.copy()
            
            # Apply domain filter
            if 'domain' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['domain'] == selected_domain]
            else:
                # If no domain column, filter by URL containing the domain
                filtered_df = filtered_df[filtered_df['Results'].str.contains(selected_domain, case=False)]
            
            # Apply date filter
            if start_date and end_date:
                filtered_df = apply_date_filter(filtered_df, start_date, end_date)
            
            # Apply position filter
            filtered_df = apply_position_filter(filtered_df, position_min, position_max)
            
            # Check if there's data after filtering
            if filtered_df.empty:
                st.warning(f"No data available for domain '{selected_domain}' with the selected filters.")
            else:
                # Download button
                st.download_button(
                    label="Download Domain Data",
                    data=to_excel(filtered_df),
                    file_name=f"domain_analysis_{selected_domain}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                # Keyword analysis
                if 'Keyword' in filtered_df.columns and 'Position' in filtered_df.columns:
                    # Group by keyword
                    keyword_data = filtered_df.groupby('Keyword')['Position'].agg([
                        ('mean', 'mean'), 
                        ('min', 'min'), 
                        ('max', 'max'), 
                        ('count', 'count')
                    ]).reset_index()
                    
                    keyword_data = keyword_data.sort_values('mean')
                    
                    # Keyword rank selector
                    keyword_top_n = st.radio(
                        "Show top keywords:", 
                        [3, 5, 10, 20], 
                        index=1,  # Default to 5
                        horizontal=True,
                        key="domain_keyword_top_n"
                    )
                    
                    # Keyword performance chart
                    st.subheader("Keyword Performance")
                    
                    keyword_fig = px.bar(
                        keyword_data.head(keyword_top_n),
                        x='Keyword',
                        y='mean',
                        title=f'Top {keyword_top_n} Keywords for "{selected_domain}"',
                        labels={'Keyword': 'Keyword', 'mean': 'Average Position'},
                        color='mean',
                        color_continuous_scale='RdYlGn_r'
                    )
                    
                    keyword_fig.update_layout(
                        xaxis_title="Keyword",
                        yaxis_title="Average Position",
                        yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                        xaxis_tickangle=-45  # Rotate x-axis labels for better readability
                    )
                    
                    st.plotly_chart(keyword_fig, use_container_width=True)
                    
                    # Position trend over time
                    if 'date' in filtered_df.columns:
                        # Get top keywords
                        top_keywords = keyword_data.head(keyword_top_n)['Keyword'].tolist()
                        
                        # Filter data for these keywords
                        trend_data = filtered_df[filtered_df['Keyword'].isin(top_keywords)]
                        
                        if not trend_data.empty:
                            # Group by date and keyword
                            trend_daily = trend_data.groupby(['date', 'Keyword'])['Position'].mean().reset_index()
                            
                            # Create trend chart
                            st.subheader("Position Trend Over Time")
                            
                            trend_fig = px.line(
                                trend_daily,
                                x='date',
                                y='Position',
                                color='Keyword',
                                title=f'Position Trend Over Time for "{selected_domain}"',
                                labels={'date': 'Date', 'Position': 'Position', 'Keyword': 'Keyword'}
                            )
                            
                            trend_fig.update_layout(
                                xaxis_title="Date",
                                yaxis_title="Position",
                                yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                                legend_title="Keyword"
                            )
                            
                            st.plotly_chart(trend_fig, use_container_width=True)
                    
                    # Keyword data table
                    st.subheader("Keyword Rankings")
                    
                    # Rename columns for display
                    display_df = keyword_data.copy()
                    display_df.columns = ['Keyword', 'Average Position', 'Best Position', 'Worst Position', 'Count']
                    
                    # Round average position to 2 decimal places
                    display_df['Average Position'] = display_df['Average Position'].round(2)
                    
                    st.dataframe(display_df, use_container_width=True)

# Tab 5: URL Comparison
with tab5:
    st.header("URL Comparison")
    
    if st.session_state.data is None:
        st.info("Please upload data or load from Google Sheet first.")
    else:
        df = st.session_state.data
        
        # Filter section
        st.subheader("Select URLs to Compare")
        
        filter_col1, filter_col2 = st.columns([2, 1])
        
        with filter_col1:
            # URL selector
            if 'Results' in df.columns:
                urls = sorted(df['Results'].unique().tolist())
                selected_urls = st.multiselect("Select URLs", urls, help="Hold Ctrl/Cmd to select multiple URLs")
            else:
                st.error("No URL data available.")
                selected_urls = []
            
            # Date range filter
            if 'date' in df.columns:
                min_date = df['date'].min()
                max_date = df['date'].max()
                
                if not pd.isna(min_date) and not pd.isna(max_date):
                    date_range = st.date_input(
                        "Date Range",
                        value=(min_date, max_date),
                        min_value=min_date,
                        max_value=max_date,
                        key="url_date_range"
                    )
                    
                    if len(date_range) == 2:
                        start_date, end_date = date_range
                    else:
                        start_date = end_date = None
                else:
                    start_date = end_date = None
                    st.write("No valid dates available")
            else:
                start_date = end_date = None
                st.write("No date data available")
        
        with filter_col2:
            # Compare button
            compare_urls = st.button("Compare URLs", key="compare_urls_btn")
        
        # Check if URLs are selected
        if not selected_urls:
            st.info("Please select URLs to compare.")
        elif compare_urls or ('urls_compared' in st.session_state and st.session_state.urls_compared == selected_urls):
            st.session_state.urls_compared = selected_urls
            
            filtered_df = df.copy()
            
            # Filter to selected URLs
            filtered_df = filtered_df[filtered_df['Results'].isin(selected_urls)]
            
            # Apply date filter
            if start_date and end_date:
                filtered_df = apply_date_filter(filtered_df, start_date, end_date)
            
            # Check if there's data after filtering
            if filtered_df.empty:
                st.warning("No data available for the selected URLs with the selected filters.")
            else:
                # Download button
                st.download_button(
                    label="Download Comparison Data",
                    data=to_excel(filtered_df),
                    file_name="url_comparison.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                # Prepare URL performance data
                url_data = []
                for url in selected_urls:
                    url_subset = filtered_df[filtered_df['Results'] == url]
                    
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
                
                # URL comparison chart
                st.subheader("URL Position Comparison")
                
                if url_data:
                    url_df = pd.DataFrame(url_data)
                    
                    url_fig = px.bar(
                        url_df,
                        x='url',
                        y='avg_position',
                        error_y=[(d['worst_position'] - d['avg_position']) for d in url_data],
                        title='URL Position Comparison',
                        labels={'url': 'URL', 'avg_position': 'Average Position'},
                        color='avg_position',
                        color_continuous_scale='RdYlGn_r'
                    )
                    
                    url_fig.update_layout(
                        xaxis_title="URL",
                        yaxis_title="Average Position",
                        yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                        xaxis_tickangle=-45  # Rotate x-axis labels for better readability
                    )
                    
                    st.plotly_chart(url_fig, use_container_width=True)
                
                # Keyword performance by URL
                st.subheader("Keyword Performance by URL")
                
                if 'Keyword' in filtered_df.columns and 'Position' in filtered_df.columns:
                    # Get top keywords by frequency
                    top_keywords = filtered_df['Keyword'].value_counts().head(5).index.tolist()
                    
                    # Prepare data
                    keyword_comparison_data = []
                    
                    for keyword in top_keywords:
                        keyword_data = filtered_df[filtered_df['Keyword'] == keyword]
                        
                        for url in selected_urls:
                            url_keyword_data = keyword_data[keyword_data['Results'] == url]
                            
                            if not url_keyword_data.empty:
                                keyword_comparison_data.append({
                                    'keyword': keyword,
                                    'url': url,
                                    'position': url_keyword_data['Position'].mean()
                                })
                    
                    if keyword_comparison_data:
                        # Create comparison chart
                        keyword_df = pd.DataFrame(keyword_comparison_data)
                        
                        keyword_fig = px.bar(
                            keyword_df,
                            x='keyword',
                            y='position',
                            color='url',
                            barmode='group',
                            title='URL Performance by Keyword',
                            labels={'keyword': 'Keyword', 'position': 'Average Position', 'url': 'URL'}
                        )
                        
                        keyword_fig.update_layout(
                            xaxis_title="Keyword",
                            yaxis_title="Average Position",
                            yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                            legend_title="URL"
                        )
                        
                        st.plotly_chart(keyword_fig, use_container_width=True)
                    else:
                        st.info("No keyword performance data available for comparison.")
                
                # Position trend over time
                st.subheader("Position Trend Over Time")
                
                if 'date' in filtered_df.columns:
                    # Prepare trend data
                    trend_data = []
                    
                    for url in selected_urls:
                        url_data = filtered_df[filtered_df['Results'] == url]
                        
                        if not url_data.empty:
                            # Group by date
                            url_daily = url_data.groupby('date')['Position'].mean().reset_index()
                            url_daily['url'] = url
                            trend_data.append(url_daily)
                    
                    if trend_data:
                        # Combine all data
                        all_trend_data = pd.concat(trend_data)
                        
                        # Create trend chart
                        trend_fig = px.line(
                            all_trend_data,
                            x='date',
                            y='Position',
                            color='url',
                            title='URL Position Trend Over Time',
                            labels={'date': 'Date', 'Position': 'Position', 'url': 'URL'}
                        )
                        
                        trend_fig.update_layout(
                            xaxis_title="Date",
                            yaxis_title="Position",
                            yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                            legend_title="URL"
                        )
                        
                        st.plotly_chart(trend_fig, use_container_width=True)
                    else:
                        st.info("No trend data available for the selected URLs.")
                
                # URL data table
                st.subheader("URL Performance Data")
                
                if url_data:
                    # Create display dataframe
                    display_df = pd.DataFrame(url_data)
                    display_df.columns = ['URL', 'Average Position', 'Best Position', 'Worst Position', 'Keywords Count']
                    display_df['Average Position'] = display_df['Average Position'].round(2)
                    
                    st.dataframe(display_df, use_container_width=True)

# Tab 6: Time Comparison
with tab6:
    st.header("Time Comparison")
    
    if st.session_state.data is None:
        st.info("Please upload data or load from Google Sheet first.")
    else:
        df = st.session_state.data
        
        # Filter section
        st.subheader("Compare Positions Over Time")
        
        # Keyword selector
        if 'Keyword' in df.columns:
            keywords = ["-- Select a keyword --"] + sorted(df['Keyword'].unique().tolist())
            selected_keyword = st.selectbox("Select Keyword", keywords, key="time_comp_keyword")
        else:
            selected_keyword = None
            st.error("No keyword data available.")
            st.stop()
        
        # Check if a keyword is selected
        if selected_keyword == "-- Select a keyword --":
            st.info("Please select a keyword to analyze.")
            st.stop()
        
        # Get available dates for the keyword
        keyword_df = df[df['Keyword'] == selected_keyword]
        
        if keyword_df.empty:
            st.warning(f"No data found for keyword: {selected_keyword}")
            st.stop()
        
        # Get unique dates
        available_dates = []
        if 'date' in keyword_df.columns:
            available_dates = keyword_df['date'].dropna().unique()
            available_dates = sorted(available_dates)
            
            # Format dates for display
            formatted_dates = [d.strftime('%Y-%m-%d') if isinstance(d, datetime.date) else str(d) for d in available_dates]
        
        if not available_dates:
            st.warning(f"No dates available for keyword: {selected_keyword}")
            st.stop()
        
        # Create date selectors
        col1, col2, col3 = st.columns(3)
        
        with col1:
            start_date_idx = st.selectbox(
                "Start Date",
                options=range(len(formatted_dates)),
                format_func=lambda x: formatted_dates[x],
                index=0
            )
            
            start_date_str = formatted_dates[start_date_idx]
            start_date = available_dates[start_date_idx]
        
        with col2:
            end_date_idx = st.selectbox(
                "End Date",
                options=range(len(formatted_dates)),
                format_func=lambda x: formatted_dates[x],
                index=len(formatted_dates)-1 if len(formatted_dates) > 1 else 0
            )
            
            end_date_str = formatted_dates[end_date_idx]
            end_date = available_dates[end_date_idx]
        
        with col3:
            compare_button = st.button("Compare Over Time", key="time_compare_btn")
        
        # Check if comparison can be performed
        if start_date_str == end_date_str and not compare_button:
            st.warning("Start date and end date are the same. Please select different dates.")
        elif compare_button or 'time_compared' in st.session_state:
            if compare_button:
                st.session_state.time_compared = True
            
            # Filter data for the selected dates
            start_data = keyword_df[keyword_df['date'] == start_date].copy()
            end_data = keyword_df[keyword_df['date'] == end_date].copy()
            
            # Handle empty data
            if start_data.empty:
                st.warning(f"No data available for start date: {start_date_str}")
                st.stop()
            
            if end_data.empty:
                st.warning(f"No data available for end date: {end_date_str}")
                st.stop()
            
            # Remove any duplicated URLs
            start_data = start_data.drop_duplicates(subset=['Results'])
            end_data = end_data.drop_duplicates(subset=['Results'])
            
            # Download button for combined data
            combined_df = pd.concat([start_data, end_data])
            combined_df['date_label'] = combined_df['date'].apply(lambda x: 'Start' if x == start_date else 'End')
            
            st.download_button(
                label="Download Comparison Data",
                data=to_excel(combined_df),
                file_name=f"time_comparison_{selected_keyword}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            # Display summary
            st.subheader("Comparison Summary")
            
            summary_col1, summary_col2, summary_col3 = st.columns(3)
            
            with summary_col1:
                st.info(f"**Keyword:** {selected_keyword}")
            
            with summary_col2:
                st.info(f"**Start Date:** {start_date_str} ({len(start_data)} URLs found)")
            
            with summary_col3:
                st.info(f"**End Date:** {end_date_str} ({len(end_data)} URLs found)")
            
            # Prepare data for comparison
            # Create mapping of URLs to positions
            start_positions = {}
            for _, row in start_data.iterrows():
                if pd.notna(row['Results']) and pd.notna(row['Position']):
                    start_positions[row['Results']] = int(row['Position']) if isinstance(row['Position'], (int, float)) else row['Position']
            
            end_positions = {}
            for _, row in end_data.iterrows():
                if pd.notna(row['Results']) and pd.notna(row['Position']):
                    end_positions[row['Results']] = int(row['Position']) if isinstance(row['Position'], (int, float)) else row['Position']
            
            # Create lists for display
            start_urls_list = []
            
            for _, row in start_data.sort_values(by='Position', ascending=True).iterrows():
                url = row['Results']
                pos = row['Position']
                domain = get_domain(url)
                
                # Calculate position change
                position_change_text = "N/A"
                if url in end_positions:
                    change = end_positions[url] - pos
                    if change < 0:
                        position_change_text = f"↑ {abs(change)} (improved)"
                    elif change > 0:
                        position_change_text = f"↓ {change} (declined)"
                    else:
                        position_change_text = "No change"
                else:
                    position_change_text = "Not in end data"
                
                start_urls_list.append({
                    'Position': int(pos) if isinstance(pos, (int, float)) else pos,
                    'URL': url,
                    'Domain': domain,
                    'Position Change': position_change_text
                })
            
            end_urls_list = []
            
            for _, row in end_data.sort_values(by='Position', ascending=True).iterrows():
                url = row['Results']
                pos = row['Position']
                domain = get_domain(url)
                
                # Calculate position change
                position_change_text = "N/A"
                if url in start_positions:
                    change = pos - start_positions[url]
                    if change < 0:
                        position_change_text = f"↑ {abs(change)} (improved)"
                    elif change > 0:
                        position_change_text = f"↓ {change} (declined)"
                    else:
                        position_change_text = "No change"
                else:
                    position_change_text = "New"
                
                end_urls_list.append({
                    'Position': int(pos) if isinstance(pos, (int, float)) else pos,
                    'URL': url,
                    'Domain': domain,
                    'Position Change': position_change_text
                })
            
            # Get all unique URLs
            all_urls = set(list(start_positions.keys()) + list(end_positions.keys()))
            
            # Create change analysis
            position_changes = []
            
            for url in all_urls:
                start_pos = start_positions.get(url, None)
                end_pos = end_positions.get(url, None)
                domain = get_domain(url)
                
                if start_pos is not None or end_pos is not None:
                    change_data = {
                        'URL': url,
                        'Domain': domain,
                        'Start Position': start_pos if start_pos is not None else "N/A",
                        'End Position': end_pos if end_pos is not None else "N/A"
                    }
                    
                    # Calculate change text
                    if start_pos is not None and end_pos is not None:
                        change = end_pos - start_pos
                        if change < 0:
                            change_data['Change'] = f"↑ {abs(change)} (improved)"
                            change_data['status'] = 'improved'
                        elif change > 0:
                            change_data['Change'] = f"↓ {change} (declined)"
                            change_data['status'] = 'declined'
                        else:
                            change_data['Change'] = "No change"
                            change_data['status'] = 'unchanged'
                        change_data['change_value'] = abs(change)
                    else:
                        if start_pos is None:
                            change_data['Change'] = "New"
                            change_data['status'] = 'new'
                        else:
                            change_data['Change'] = "Dropped"
                            change_data['status'] = 'dropped'
                        change_data['change_value'] = 0
                    
                    position_changes.append(change_data)
            
            # Sort by status and change value
            position_changes = sorted(
                position_changes,
                key=lambda x: (
                    0 if x.get('status') in ('improved', 'declined') else
                    1 if x.get('status') in ('new', 'dropped') else 2,
                    x.get('change_value', 0)
                ),
                reverse=True
            )
            
            # Display tables
            table_col1, table_col2 = st.columns(2)
            
            with table_col1:
                st.subheader("Start Date URLs")
                st.write("Sorted by position (best positions first)")
                
                if start_urls_list:
                    st.dataframe(pd.DataFrame(start_urls_list), use_container_width=True)
                else:
                    st.info("No URLs found for start date.")
            
            with table_col2:
                st.subheader("End Date URLs")
                st.write("Sorted by position (best positions first)")
                
                if end_urls_list:
                    st.dataframe(pd.DataFrame(end_urls_list), use_container_width=True)
                else:
                    st.info("No URLs found for end date.")
            
            # Position changes analysis
            st.subheader("Position Changes Analysis")
            st.write("All URLs with their position changes")
            
            if position_changes:
                # Create DataFrame for display
                changes_df = pd.DataFrame(position_changes)
                
                # Apply conditional styling
                def highlight_changes(val):
                    """Apply color highlighting based on change status"""
                    if 'improved' in str(val).lower():
                        return 'background-color: #d4edda; color: #155724'
                    elif 'declined' in str(val).lower():
                        return 'background-color: #fff3cd; color: #856404'
                    elif 'new' == str(val).lower():
                        return 'background-color: #cce5ff; color: #004085'
                    elif 'dropped' == str(val).lower():
                        return 'background-color: #f8d7da; color: #721c24'
                    return ''
                
                # Display the table
                st.dataframe(
                    changes_df.style.apply(lambda x: [highlight_changes(x['Change'])] * len(x), axis=1),
                    use_container_width=True
                )
            else:
                st.info("No position changes to display.")
