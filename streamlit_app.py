import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from urllib.parse import urlparse
import datetime
import re
import time
from io import BytesIO
import io

# Set page config
st.set_page_config(
    page_title="Advanced SEO Position Tracking Dashboard",
    page_icon="📈",
    layout="wide"
)

# Set up the main layout
def main():
    st.title("Advanced SEO Position Tracking Dashboard")
    
    # Show loading message while data is being fetched
    data_load_state = st.text('Loading data from Google Sheet...')
    df = load_data_from_gsheet()
    
    # Process the data
    if 'Keyword' in df.columns:
        df['Keyword'].fillna(method='ffill', inplace=True)
    df = prepare_data(df)
    
    # Update the loading message
    data_load_state.text('Data loaded successfully!')
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select a page:",
        [
            "Dashboard Overview",
            "Keyword Analysis",
            "Domain Analysis",
            "URL Comparison",
            "Time Comparison"
        ]
    )
    
    # Display the selected page
    if page == "Dashboard Overview":
        dashboard_overview(df)
    elif page == "Keyword Analysis":
        keyword_analysis(df)
    elif page == "Domain Analysis":
        domain_analysis(df)
    elif page == "URL Comparison":
        url_comparison(df)
    elif page == "Time Comparison":
        time_comparison(df)
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.info(
        "This application fetches data from a Google Sheet and provides "
        "various SEO position tracking analyses."
    )
    st.sidebar.markdown("©️ 2025 - SEO Position Tracking Dashboard")

# Helper functions
def get_domain(url):
    """Extract domain from URL"""
    try:
        return urlparse(url).netloc
    except (TypeError, ValueError):
        return None

@st.cache_data
def load_data_from_gsheet():
    """Load data from Google Sheet"""
    url = "https://docs.google.com/spreadsheets/d/1Z8S-lJygDcuB3gs120EoXLVMtZzgp7HQrjtNkkOqJQs/export?format=csv&gid=0"
    df = pd.read_csv(url)
    return df

def prepare_data(df):
    """Prepare data for analysis"""
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
    
    # Detect and standardize column names (some data sources use Excel column letters)
    if 'C' in df.columns and 'D' in df.columns and 'E' in df.columns:
        # Excel-style column names (A, B, C, D, E, etc.)
        col_map = {
            'A': 'Keyword',
            'B': 'Time',
            'C': 'Results',
            'D': 'Position',
            'E': 'Filled keyword',
            'F': 'date/time'
        }
        for old_col, new_col in col_map.items():
            if old_col in df.columns and new_col not in df.columns:
                df[new_col] = df[old_col]
    
    # Convert date columns to datetime
    date_columns = ['Time', 'date/time', 'B', 'F']
    for col in date_columns:
        if col in df.columns:
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except Exception as e:
                st.warning(f"Could not convert '{col}' to datetime: {str(e)}")
                continue
    
    # Add date column (without time)
    # Try multiple date columns
    df['date'] = pd.NaT
    for col in date_columns:
        if col in df.columns:
            mask = df[col].notna() & df['date'].isna()
            if mask.any():
                try:
                    df.loc[mask, 'date'] = df.loc[mask, col].dt.date
                except:
                    # Try a different approach for problematic dates
                    for idx, val in df.loc[mask, col].items():
                        try:
                            df.loc[idx, 'date'] = val.date()
                        except:
                            pass
    
    # If still no 'date' column with values, try a different approach
    if 'date' not in df.columns or df['date'].isna().all():
        # Create date column from string dates in any column
        for col in date_columns:
            if col in df.columns:
                try:
                    # Extract date pattern from strings
                    df['date_str'] = df[col].astype(str)
                    date_pattern = r'(\d{4}-\d{2}-\d{2})'
                    df['date_extract'] = df['date_str'].str.extract(date_pattern)
                    if not df['date_extract'].isna().all():
                        df['date'] = pd.to_datetime(df['date_extract'], errors='coerce').dt.date
                        break
                except:
                    continue
    
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

# Dashboard section
def dashboard_overview(df):
    st.header("SEO Position Tracking Dashboard")
    
    # Filter Section
    with st.expander("Filter Data", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            date_range = None
            use_date_filter = st.checkbox("Filter by Date Range")
            if use_date_filter:
                min_date = df['date'].min() if 'date' in df.columns and not df['date'].isna().all() else datetime.date(2023, 1, 1)
                max_date = df['date'].max() if 'date' in df.columns and not df['date'].isna().all() else datetime.date.today()
                
                start_date = st.date_input("Start Date", min_date)
                end_date = st.date_input("End Date", max_date)
                
                if start_date and end_date:
                    date_range = {'start': start_date, 'end': end_date}
        
        with col2:
            keyword = None
            use_keyword_filter = st.checkbox("Filter by Keyword")
            if use_keyword_filter and 'Keyword' in df.columns:
                keywords = [""] + sorted(df['Keyword'].unique().tolist())
                keyword = st.selectbox("Select Keyword", keywords)
        
        with col3:
            position_min = None
            position_max = None
            use_position_filter = st.checkbox("Filter by Position Range")
            if use_position_filter:
                position_min = st.number_input("Minimum Position", min_value=1, value=1)
                position_max = st.number_input("Maximum Position", min_value=1, value=100)
        
        # Top rank slider
        col1, col2 = st.columns(2)
        with col1:
            top_rank = st.slider("Select Top Rank for Position Charts", min_value=3, max_value=50, value=5, step=1)
        with col2:
            domain_rank = st.slider("Select Top Domain Rank for Charts", min_value=3, max_value=50, value=5, step=1)
        
        apply_filter = st.button("Apply Filters")
    
    # Apply filters
    filtered_df = df.copy()
    
    if apply_filter or 'filtered' not in st.session_state:
        if date_range:
            filtered_df = apply_date_filter(filtered_df, date_range)
        
        if keyword:
            filtered_df = apply_keyword_filter(filtered_df, keyword)
        
        if use_position_filter:
            filtered_df = apply_position_filter(filtered_df, position_min, position_max)
        
        st.session_state.filtered = True
    
    # Summary Cards
    st.subheader("Summary Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Keywords", filtered_df['Keyword'].nunique() if 'Keyword' in filtered_df.columns else 0)
    
    with col2:
        st.metric("Total Domains", filtered_df['domain'].nunique() if 'domain' in filtered_df.columns else 0)
    
    with col3:
        st.metric("Total URLs", filtered_df['Results'].nunique() if 'Results' in filtered_df.columns else 0)
    
    with col4:
        date_range = get_date_range(filtered_df)
        st.metric("Date Range", f"{date_range[0]} to {date_range[1]}")
    
    # Charts section
    col1, col2 = st.columns(2)
    
    with col1:
        # Position Distribution Chart
        if 'Position' in filtered_df.columns and not filtered_df.empty:
            pos_dist = px.histogram(
                filtered_df, 
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
            st.info("No position data available for visualization.")
    
    with col2:
        # Domain Distribution Chart
        if 'domain' in filtered_df.columns and 'Position' in filtered_df.columns and not filtered_df.empty:
            domain_positions = filtered_df.groupby('domain')['Position'].mean().reset_index()
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
            
            st.plotly_chart(top_domains_chart, use_container_width=True)
        else:
            st.info("No domain position data available for visualization.")
    
    # Data Tables
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Top Keywords by Volume")
        
        if 'Keyword' in filtered_df.columns and 'Results' in filtered_df.columns and not filtered_df.empty:
            keyword_volume = filtered_df.groupby('Keyword')['Results'].nunique().reset_index()
            keyword_volume = keyword_volume.sort_values('Results', ascending=False)
            
            st.dataframe(keyword_volume.head(20), height=400)
        else:
            st.info("No keyword data available.")
    
    with col2:
        st.subheader("Top Domains by Frequency")
        
        if 'domain' in filtered_df.columns and not filtered_df.empty:
            domain_freq = filtered_df['domain'].value_counts().reset_index()
            domain_freq.columns = ['domain', 'count']
            
            st.dataframe(domain_freq.head(20), height=400)
        else:
            st.info("No domain data available.")
    
    # Export button
    if not filtered_df.empty:
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="Export Data to CSV",
            data=csv,
            file_name="seo_dashboard_data.csv",
            mime="text/csv",
        )

# Keyword Analysis section
def keyword_analysis(df):
    st.header("Keyword Analysis")
    
    # Filter Section
    with st.expander("Select Keyword and Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if 'Keyword' in df.columns:
                keywords = [""] + sorted(df['Keyword'].unique().tolist())
                selected_keyword = st.selectbox("Select Keyword", keywords)
            else:
                st.error("No keyword data available.")
                return
        
        with col2:
            date_range = None
            use_date_filter = st.checkbox("Filter by Date Range", key="kw_date_filter")
            if use_date_filter:
                min_date = df['date'].min() if 'date' in df.columns and not df['date'].isna().all() else datetime.date(2023, 1, 1)
                max_date = df['date'].max() if 'date' in df.columns and not df['date'].isna().all() else datetime.date.today()
                
                start_date = st.date_input("Start Date", min_date, key="kw_start_date")
                end_date = st.date_input("End Date", max_date, key="kw_end_date")
                
                if start_date and end_date:
                    date_range = {'start': start_date, 'end': end_date}
        
        with col3:
            domain_filter = st.text_input("Filter by Domain (e.g., example.com)", "")
        
        # Top rank slider
        top_rank = st.slider("Select Top Rank for Charts", min_value=3, max_value=50, value=5, step=1, key="kw_top_rank")
        
        analyze_button = st.button("Analyze Keyword")
    
    # Check if we have a keyword selected
    if not selected_keyword:
        st.info("Please select a keyword to analyze.")
        return
    
    # Apply filters
    if analyze_button or 'kw_analyzed' not in st.session_state:
        filtered_df = df.copy()
        
        # Filter by keyword
        filtered_df = apply_keyword_filter(filtered_df, selected_keyword)
        
        if date_range:
            filtered_df = apply_date_filter(filtered_df, date_range)
        
        if domain_filter:
            filtered_df = apply_domain_filter(filtered_df, domain_filter)
        
        # Check if we have data after filtering
        if filtered_df.empty:
            st.error(f"No data found for keyword '{selected_keyword}' with the selected filters.")
            return
        
        # Store in session state
        st.session_state.kw_filtered_df = filtered_df
        st.session_state.kw_analyzed = True
    else:
        filtered_df = st.session_state.kw_filtered_df
    
    # Display available dates for this keyword
    if 'date' in filtered_df.columns:
        with st.expander("Available Dates for Selected Keyword"):
            dates = filtered_df['date'].dropna().unique()
            dates = [d.strftime('%Y-%m-%d') if isinstance(d, datetime.date) else str(d).split(' ')[0] 
                     for d in sorted(dates)]
            
            st.write(", ".join(dates))
    
    # Display analysis
    st.subheader(f"Analysis for Keyword: {selected_keyword}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Position Distribution Chart
        if 'Position' in filtered_df.columns:
            pos_dist = px.histogram(
                filtered_df, 
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
            st.info("No position data available for visualization.")
    
    with col2:
        # Domain Performance Chart
        if 'domain' in filtered_df.columns and 'Position' in filtered_df.columns:
            domain_positions = filtered_df.groupby('domain')['Position'].agg(['mean', 'min', 'max', 'count']).reset_index()
            domain_positions = domain_positions.sort_values('mean')
            
            domain_perf = px.bar(
                domain_positions.head(top_rank), 
                x='domain', 
                y='mean',
                error_y='count',
                title=f'Top {top_rank} Domains for "{selected_keyword}"',
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
            st.info("No domain position data available for visualization.")
    
    # Position Trend Over Time Chart
    st.subheader("Position Trend Over Time")
    
    if 'date' in filtered_df.columns and 'Position' in filtered_df.columns and 'domain' in filtered_df.columns:
        # Get top domains for this keyword
        top_domains = filtered_df.groupby('domain')['Position'].mean().sort_values().head(top_rank).index.tolist()
        
        # Filter data for these domains
        trend_data = filtered_df[filtered_df['domain'].isin(top_domains)]
        
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
            st.info("No trend data available for visualization.")
    else:
        st.info("No date or position data available for trend visualization.")
    
    # Domain Rankings Table
    st.subheader("Domain Rankings")
    
    if 'domain' in filtered_df.columns and 'Position' in filtered_df.columns:
        domain_data = filtered_df.groupby('domain')['Position'].agg(['mean', 'min', 'max', 'count']).reset_index()
        domain_data = domain_data.sort_values('mean')
        
        # Format the mean column to 2 decimal places
        domain_data['mean'] = domain_data['mean'].round(2)
        
        st.dataframe(domain_data, height=400)
    else:
        st.info("No domain position data available.")
    
    # Export button
    if not filtered_df.empty:
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="Export Keyword Analysis to CSV",
            data=csv,
            file_name=f"keyword_analysis_{selected_keyword}.csv",
            mime="text/csv",
        )

# Domain Analysis section
def domain_analysis(df):
    st.header("Domain Analysis")
    
    # Filter Section
    with st.expander("Enter Domain and Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            domain = st.text_input("Enter Domain (e.g., example.com)", "")
        
        with col2:
            date_range = None
            use_date_filter = st.checkbox("Filter by Date Range", key="domain_date_filter")
            if use_date_filter:
                min_date = df['date'].min() if 'date' in df.columns and not df['date'].isna().all() else datetime.date(2023, 1, 1)
                max_date = df['date'].max() if 'date' in df.columns and not df['date'].isna().all() else datetime.date.today()
                
                start_date = st.date_input("Start Date", min_date, key="domain_start_date")
                end_date = st.date_input("End Date", max_date, key="domain_end_date")
                
                if start_date and end_date:
                    date_range = {'start': start_date, 'end': end_date}
        
        with col3:
            position_min = None
            position_max = None
            use_position_filter = st.checkbox("Filter by Position Range", key="domain_pos_filter")
            if use_position_filter:
                position_min = st.number_input("Minimum Position", min_value=1, value=1, key="domain_pos_min")
                position_max = st.number_input("Maximum Position", min_value=1, value=100, key="domain_pos_max")
        
        # Top rank slider
        top_rank = st.slider("Select Top Rank for Charts", min_value=3, max_value=50, value=5, step=1, key="domain_top_rank")
        
        analyze_button = st.button("Analyze Domain")
    
    # Check if we have a domain entered
    if not domain:
        st.info("Please enter a domain to analyze.")
        return
    
    # Apply filters
    if analyze_button or 'domain_analyzed' not in st.session_state:
        filtered_df = df.copy()
        
        # Filter by domain
        filtered_df = apply_domain_filter(filtered_df, domain)
        
        if date_range:
            filtered_df = apply_date_filter(filtered_df, date_range)
        
        if use_position_filter:
            filtered_df = apply_position_filter(filtered_df, position_min, position_max)
        
        # Check if we have data after filtering
        if filtered_df.empty:
            st.error(f"No data found for domain '{domain}' with the selected filters.")
            return
        
        # Store in session state
        st.session_state.domain_filtered_df = filtered_df
        st.session_state.domain_analyzed = True
    else:
        filtered_df = st.session_state.domain_filtered_df
    
    # Display analysis
    st.subheader(f"Analysis for Domain: {domain}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Keyword Performance Chart
        if 'Keyword' in filtered_df.columns and 'Position' in filtered_df.columns:
            keyword_perf = filtered_df.groupby('Keyword')['Position'].agg(['mean', 'min', 'max', 'count']).reset_index()
            keyword_perf = keyword_perf.sort_values('mean')
            
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
            
            st.plotly_chart(keyword_chart, use_container_width=True)
        else:
            st.info("No keyword position data available for visualization.")
    
    with col2:
        # Position Trend Over Time Chart
        if 'date' in filtered_df.columns and 'Position' in filtered_df.columns and 'Keyword' in filtered_df.columns:
            # Get top keywords for this domain
            top_keywords = filtered_df.groupby('Keyword')['Position'].mean().sort_values().head(top_rank).index.tolist()
            
            # Filter data for these keywords
            trend_data = filtered_df[filtered_df['Keyword'].isin(top_keywords)]
            
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
                
                st.plotly_chart(trend_chart, use_container_width=True)
            else:
                st.info("No trend data available for visualization.")
        else:
            st.info("No date or keyword data available for trend visualization.")
    
    # Keyword Rankings Table
    st.subheader("Keyword Rankings")
    
    if 'Keyword' in filtered_df.columns and 'Position' in filtered_df.columns:
        keyword_data = filtered_df.groupby('Keyword')['Position'].agg(['mean', 'min', 'max', 'count']).reset_index()
        keyword_data = keyword_data.sort_values('mean')
        
        # Format the mean column to 2 decimal places
        keyword_data['mean'] = keyword_data['mean'].round(2)
        
        st.dataframe(keyword_data, height=400)
    else:
        st.info("No keyword position data available.")
    
    # Export button
    if not filtered_df.empty:
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="Export Domain Analysis to CSV",
            data=csv,
            file_name=f"domain_analysis_{domain}.csv",
            mime="text/csv",
        )

# URL Comparison section
def url_comparison(df):
    st.header("URL Comparison")
    
    # Get unique URLs
    if 'Results' in df.columns:
        urls = sorted(df['Results'].dropna().unique().tolist())
    else:
        st.error("No URL data available.")
        return
    
    # Filter Section
    with st.expander("Select URLs and Filters", expanded=True):
        selected_urls = st.multiselect("Select URLs to Compare", urls)
        
        col1, col2 = st.columns(2)
        
        with col1:
            date_range = None
            use_date_filter = st.checkbox("Filter by Date Range", key="url_date_filter")
            if use_date_filter:
                min_date = df['date'].min() if 'date' in df.columns and not df['date'].isna().all() else datetime.date(2023, 1, 1)
                max_date = df['date'].max() if 'date' in df.columns and not df['date'].isna().all() else datetime.date.today()
                
                start_date = st.date_input("Start Date", min_date, key="url_start_date")
                end_date = st.date_input("End Date", max_date, key="url_end_date")
                
                if start_date and end_date:
                    date_range = {'start': start_date, 'end': end_date}
        
        compare_button = st.button("Compare URLs")
    
    # Check if we have URLs selected
    if not selected_urls:
        st.info("Please select at least one URL to compare.")
        return
    
    # Apply filters
    if compare_button or 'url_compared' not in st.session_state:
        filtered_df = df.copy()
        
        # Filter by URLs
        filtered_df = filtered_df[filtered_df['Results'].isin(selected_urls)]
        
        if date_range:
            filtered_df = apply_date_filter(filtered_df, date_range)
        
        # Check if we have data after filtering
        if filtered_df.empty:
            st.error("No data found for the selected URLs with the current filters.")
            return
        
        # Store in session state
        st.session_state.url_filtered_df = filtered_df
        st.session_state.url_compared = True
    else:
        filtered_df = st.session_state.url_filtered_df
    
    # Display analysis
    st.subheader("URL Comparison Analysis")
    
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
    url_df = pd.DataFrame(url_data)
    
    # URL Comparison Chart
    if not url_df.empty:
        url_comparison_chart = px.bar(
            url_df,
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
        st.info("No position data available for the selected URLs.")
    
    # Keyword Performance by URL Chart
    keyword_comparison_data = []
    
    if 'Keyword' in filtered_df.columns and 'Position' in filtered_df.columns:
        # Get top 5 keywords by frequency across these URLs
        top_keywords = filtered_df['Keyword'].value_counts().head(5).index.tolist()
        
        # For each keyword, get position by URL
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
        st.info("No keyword data available for the selected URLs.")
    
    # Position Trend Over Time Chart
    if 'date' in filtered_df.columns and len(selected_urls) > 0:
        # For each URL, get positions over time
        trend_data = []
        for url in selected_urls:
            url_time_data = filtered_df[filtered_df['Results'] == url]
            
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
            st.info("No trend data available for the selected URLs.")
    else:
        st.info("No date data available for trend visualization.")
    
    # URL Comparison Data Table
    st.subheader("URL Comparison Data")
    
    if not url_df.empty:
        # Format the average position to 2 decimal places
        url_df['avg_position'] = url_df['avg_position'].round(2)
        
        st.dataframe(url_df, height=400)
    else:
        st.info("No data available for the selected URLs.")
    
    # Export button
    if not filtered_df.empty:
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="Export URL Comparison to CSV",
            data=csv,
            file_name="url_comparison.csv",
            mime="text/csv",
        )

# Time Comparison section
def time_comparison(df):
    st.header("Time Comparison")
    
    # Debug info
    st.sidebar.markdown("### Debug Info")
    show_debug = st.sidebar.checkbox("Show Debug Information")
    
    # Filter Section
    with st.expander("Select Keyword and Dates", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if 'Keyword' in df.columns:
                keywords = [""] + sorted(df['Keyword'].unique().tolist())
                selected_keyword = st.selectbox("Select Keyword", keywords, key="time_keyword")
            else:
                st.error("No keyword data available.")
                return
        
        # Check if we have a keyword selected before continuing
        if not selected_keyword:
            st.info("Please select a keyword to analyze.")
            return
        
        # Get available dates for this keyword
        keyword_df = df[df['Keyword'] == selected_keyword]
        
        if keyword_df.empty:
            st.error(f"No data found for keyword '{selected_keyword}'.")
            return
        
        # Show debug information if requested
        if show_debug:
            st.sidebar.write("#### Data Sample")
            st.sidebar.write(keyword_df.head(3))
            st.sidebar.write("#### Columns")
            st.sidebar.write(keyword_df.columns.tolist())
            
            # Display information about the date columns
            if 'date' in keyword_df.columns:
                st.sidebar.write("#### Date Column Info")
                st.sidebar.write("Date column type:", keyword_df['date'].dtype)
                st.sidebar.write("Date samples:", keyword_df['date'].head(5).tolist())
                st.sidebar.write("NaN values:", keyword_df['date'].isna().sum())
            
            if 'Time' in keyword_df.columns:
                st.sidebar.write("#### Time Column Info")
                st.sidebar.write("Time column type:", keyword_df['Time'].dtype)
                st.sidebar.write("Time samples:", keyword_df['Time'].head(5).tolist())
                st.sidebar.write("NaN values:", keyword_df['Time'].isna().sum())
        
        # Get available dates using multiple methods
        available_dates = []
        date_columns = ['date', 'Time', 'date/time']
        
        for col in date_columns:
            if col in keyword_df.columns and not keyword_df[col].isna().all():
                # Try to convert to datetime and extract unique dates
                try:
                    if col == 'date' and pd.api.types.is_datetime64_dtype(keyword_df[col]):
                        # If already datetime
                        dates = [d.strftime('%Y-%m-%d') if isinstance(d, datetime.date) else str(d).split(' ')[0]
                                for d in sorted(keyword_df[col].dropna().unique())]
                    else:
                        # Convert to datetime
                        dates = pd.to_datetime(keyword_df[col], errors='coerce').dt.strftime('%Y-%m-%d').dropna().unique().tolist()
                    
                    if dates:
                        available_dates = sorted(dates)
                        if show_debug:
                            st.sidebar.write(f"Found dates in column '{col}':", available_dates[:5])
                        break
                except Exception as e:
                    if show_debug:
                        st.sidebar.write(f"Error extracting dates from '{col}':", str(e))
        
        # If still no dates, try using string dates in any column
        if not available_dates:
            # Try to find date-like strings in any column
            for col in keyword_df.columns:
                try:
                    # Look for strings that match date patterns
                    if keyword_df[col].dtype == object:  # String column
                        date_pattern = r'\d{4}-\d{2}-\d{2}'
                        sample = keyword_df[col].astype(str).str.extract(f'({date_pattern})', expand=False)
                        dates = sample.dropna().unique().tolist()
                        if dates:
                            available_dates = sorted(dates)
                            if show_debug:
                                st.sidebar.write(f"Found date patterns in column '{col}':", available_dates[:5])
                            break
                except:
                    pass
        
        if not available_dates:
            # Last resort - create fake dates if we can't find real ones
            if show_debug:
                st.sidebar.write("Creating artificial dates as no real dates found")
            
            # Create two artificial dates
            from datetime import datetime, timedelta
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            available_dates = [yesterday.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')]
        
        with col2:
            start_date = st.selectbox("Select Start Date", available_dates, index=0)
        
        with col3:
            # Default to the last date
            end_date = st.selectbox("Select End Date", available_dates, index=len(available_dates)-1)
        
        compare_button = st.button("Compare Over Time")
    
    # Check if we have valid dates
    if not start_date or not end_date:
        st.error("Please select both start and end dates.")
        return
    
    # Apply comparison
    if compare_button or 'time_compared' not in st.session_state:
        # Filter the data for the selected keyword
        keyword_df = df[df['Keyword'] == selected_keyword].copy()
        
        # Try multiple methods to find data for the dates
        start_data = pd.DataFrame()
        end_data = pd.DataFrame()
        
        # Method 1: Try exact date match on 'date' column
        if 'date' in keyword_df.columns:
            try:
                start_date_dt = pd.to_datetime(start_date).date()
                end_date_dt = pd.to_datetime(end_date).date()
                
                start_data = keyword_df[keyword_df['date'] == start_date_dt]
                end_data = keyword_df[keyword_df['date'] == end_date_dt]
                
                if show_debug:
                    st.sidebar.write(f"Method 1 results - start: {len(start_data)} rows, end: {len(end_data)} rows")
            except Exception as e:
                if show_debug:
                    st.sidebar.write("Method 1 error:", str(e))
        
        # Method 2: Try string matching on various date columns
        if start_data.empty or end_data.empty:
            for col in ['date', 'Time', 'date/time']:
                if col in keyword_df.columns:
                    try:
                        # Convert column to string for contains search
                        keyword_df['temp_date_str'] = keyword_df[col].astype(str)
                        
                        if start_data.empty:
                            start_data = keyword_df[keyword_df['temp_date_str'].str.contains(start_date, na=False)]
                            if show_debug and not start_data.empty:
                                st.sidebar.write(f"Found start data using string match on '{col}'")
                        
                        if end_data.empty:
                            end_data = keyword_df[keyword_df['temp_date_str'].str.contains(end_date, na=False)]
                            if show_debug and not end_data.empty:
                                st.sidebar.write(f"Found end data using string match on '{col}'")
                        
                        if not start_data.empty and not end_data.empty:
                            break
                    except Exception as e:
                        if show_debug:
                            st.sidebar.write(f"Method 2 error on '{col}':", str(e))
        
        # Method 3: If still no matches, split the data in half
        if start_data.empty and end_data.empty:
            if show_debug:
                st.sidebar.write("Using data splitting as fallback")
            
            # Sort by any date column if available, otherwise by index
            sorted_df = keyword_df
            if 'date' in keyword_df.columns and not keyword_df['date'].isna().all():
                try:
                    sorted_df = keyword_df.sort_values('date')
                except:
                    pass
            elif 'Time' in keyword_df.columns and not keyword_df['Time'].isna().all():
                try:
                    sorted_df = keyword_df.sort_values('Time')
                except:
                    pass
            
            # Split the data
            mid_point = len(sorted_df) // 2
            start_data = sorted_df.iloc[:mid_point]
            end_data = sorted_df.iloc[mid_point:]
            
            if show_debug:
                st.sidebar.write(f"Split data - start: {len(start_data)} rows, end: {len(end_data)} rows")
        
        # Check if we have data for both dates
        if start_data.empty:
            st.error(f"No data found for start date: {start_date}")
            return
        
        if end_data.empty:
            st.error(f"No data found for end date: {end_date}")
            return
        
        # Store in session state
        st.session_state.start_data = start_data
        st.session_state.end_data = end_data
        st.session_state.time_compared = True
    else:
        start_data = st.session_state.start_data
        end_data = st.session_state.end_data
    
    # Display summary information
    st.subheader("Comparison Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Keyword", selected_keyword)
    
    with col2:
        st.metric("Start Date", start_date, f"{len(start_data)} URLs")
    
    with col3:
        st.metric("End Date", end_date, f"{len(end_data)} URLs")
    
    # Prepare the data for comparison
    # Start date URLs
    start_urls = []
    for _, row in start_data.sort_values(by='Position', ascending=True).iterrows():
        url = row['Results']
        position = row['Position']
        
        if pd.notna(url) and pd.notna(position):
            domain = get_domain(url)
            
            # Check if this URL exists in end data
            end_position = None
            if not end_data.empty:
                end_url_data = end_data[end_data['Results'] == url]
                if not end_url_data.empty:
                    end_position = end_url_data['Position'].values[0]
            
            # Calculate position change
            position_change = None
            position_change_text = "N/A"
            if end_position is not None:
                position_change = end_position - position
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
                'position': int(position) if isinstance(position, (int, float)) else position,
                'domain': domain,
                'position_change': position_change,
                'position_change_text': position_change_text
            })
    
    # End date URLs
    end_urls = []
    for _, row in end_data.sort_values(by='Position', ascending=True).iterrows():
        url = row['Results']
        position = row['Position']
        
        if pd.notna(url) and pd.notna(position):
            domain = get_domain(url)
            
            # Check if this URL exists in start data
            start_position = None
            if not start_data.empty:
                start_url_data = start_data[start_data['Results'] == url]
                if not start_url_data.empty:
                    start_position = start_url_data['Position'].values[0]
            
            # Calculate position change
            position_change = None
            position_change_text = "N/A"
            if start_position is not None:
                position_change = position - start_position
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
                'position': int(position) if isinstance(position, (int, float)) else position,
                'domain': domain,
                'position_change': position_change,
                'position_change_text': position_change_text
            })
    
    # Position Changes Analysis
    # Identify all URLs that exist in either start or end data
    all_urls = set()
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
            domain = get_domain(url)
            
            change_data = {
                'url': url,
                'start_position': start_pos,
                'end_position': end_pos,
                'domain': domain
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
        reverse=True)
    
    # Display the comparison tables
    st.subheader("URL Comparison Tables")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Start Date URLs ({start_date})**")
        
        if start_urls:
            # Create a dataframe for better display
            start_df = pd.DataFrame(start_urls)
            
            # Display relevant columns only and rename them for clarity
            display_df = start_df[['position', 'url', 'domain', 'position_change_text']].copy()
            display_df.columns = ['Position', 'URL', 'Domain', 'Change']
            
            # Apply subtle styling
            def highlight_changes_subtle(row):
                styles = [''] * len(row)
                if 'improved' in str(row['Change']):
                    styles = ['color: #028a0f'] * len(row)  # Dark green text
                elif 'declined' in str(row['Change']):
                    styles = ['color: #9c0000'] * len(row)  # Dark red text
                return styles
            
            # Display the styled dataframe
            st.dataframe(display_df.style.apply(highlight_changes_subtle, axis=1), height=400)
        else:
            st.info("No data available for start date.")
    
    with col2:
        st.write(f"**End Date URLs ({end_date})**")
        
        if end_urls:
            # Create a dataframe for better display
            end_df = pd.DataFrame(end_urls)
            
            # Display relevant columns only and rename them for clarity
            display_df = end_df[['position', 'url', 'domain', 'position_change_text']].copy()
            display_df.columns = ['Position', 'URL', 'Domain', 'Change']
            
            # Apply subtle styling
            def highlight_changes_subtle(row):
                styles = [''] * len(row)
                if 'improved' in str(row['Change']):
                    styles = ['color: #028a0f'] * len(row)  # Dark green text
                elif 'declined' in str(row['Change']):
                    styles = ['color: #9c0000'] * len(row)  # Dark red text
                elif 'New' in str(row['Change']):
                    styles = ['color: #0000cc'] * len(row)  # Dark blue text
                return styles
            
            # Display the styled dataframe
            st.dataframe(display_df.style.apply(highlight_changes_subtle, axis=1), height=400)
        else:
            st.info("No data available for end date.")
    
    # Position Changes Analysis Table
    st.subheader("Position Changes Analysis")
    
    if position_changes:
        # Create a dataframe for better display
        changes_df = pd.DataFrame(position_changes)
        
        # Display relevant columns only and rename them for clarity
        if all(col in changes_df.columns for col in ['url', 'domain', 'start_position', 'end_position', 'change_text']):
            display_df = changes_df[['url', 'domain', 'start_position', 'end_position', 'change_text']].copy()
            display_df.columns = ['URL', 'Domain', 'Start Position', 'End Position', 'Change']
            
            # Apply subtle styling - only color the Change column
            def highlight_changes_subtle_col(row):
                styles = [''] * len(row)
                change_idx = list(display_df.columns).index('Change')
                
                if 'improved' in str(row['Change']):
                    styles[change_idx] = 'color: #028a0f; font-weight: bold'  # Dark green text, bold
                elif 'declined' in str(row['Change']):
                    styles[change_idx] = 'color: #9c0000; font-weight: bold'  # Dark red text, bold
                elif 'New' in str(row['Change']):
                    styles[change_idx] = 'color: #0000cc; font-weight: bold'  # Dark blue text, bold
                elif 'Dropped' in str(row['Change']):
                    styles[change_idx] = 'color: #cc7000; font-weight: bold'  # Orange text, bold
                
                return styles
            
            # Display the styled dataframe
            st.dataframe(display_df.style.apply(highlight_changes_subtle_col, axis=1), height=400)
        else:
            # Fallback if columns are missing
            st.dataframe(changes_df, height=400)
    else:
        st.info("No position changes to display.")
    
    # Export button
    position_changes_df = pd.DataFrame(position_changes)
    if not position_changes_df.empty:
        csv = position_changes_df.to_csv(index=False)
        st.download_button(
            label="Export Time Comparison to CSV",
            data=csv,
            file_name=f"time_comparison_{selected_keyword}_{start_date}_vs_{end_date}.csv",
            mime="text/csv",
        )

if __name__ == '__main__':
    main()
