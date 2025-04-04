import streamlit as st
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
    # Format: URL + Position + Keyword + DateTime (all in one row without proper columns)
    if len(df.columns) == 1:
        st.write("Detected single column data format - trying to parse")
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
                st.write(f"Successfully parsed {len(data_list)} rows from single column format")
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

def to_excel(df):
    """Convert DataFrame to Excel bytes for downloading"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    
    output.seek(0)
    return output.getvalue()

def load_data_from_gsheet(url):
    """Load data from Google Sheets URL"""
    try:
        # Extract the key/ID from the URL
        if '/d/' in url:
            sheet_id = url.split('/d/')[1].split('/')[0]
        else:
            st.error("Invalid Google Sheets URL format")
            return None, "Invalid URL format"
        
        # Create the export URL (CSV format)
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        
        # Load data from CSV export URL
        df = pd.read_csv(export_url)
        
        # Prepare data for analysis
        df = prepare_data(df)
        
        return df, None
    except Exception as e:
        return None, str(e)

# Tab Functions
def upload_data_tab():
    st.header("Upload Excel Data")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Select Excel File")
        uploaded_file = st.file_uploader("Your Excel file should contain columns for Keyword, Results, Position, and Time.", type=["xlsx", "xls", "csv"])
        
        st.divider()
        
        st.subheader("OR Use Google Sheet")
        url = st.text_input("Google Sheet URL", value="https://docs.google.com/spreadsheets/d/1Z8S-lJygDcuB3gs120EoXLVMtZzgp7HQrjtNkkOqJQs/edit?pli=1&gid=0#gid=0")
        load_button = st.button("Load from Google Sheet")
    
    with col2:
        if uploaded_file is not None:
            with st.spinner("Processing file..."):
                try:
                    # Determine the file type and read accordingly
                    if uploaded_file.name.endswith('.csv'):
                        df = pd.read_csv(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)
                    
                    # Process the data
                    if 'Keyword' in df.columns:
                        df['Keyword'].fillna(method='ffill', inplace=True)
                    
                    # Check for special format
                    if len(df.columns) == 1:
                        df = prepare_data(df)
                    else:
                        df = prepare_data(df)
                    
                    # Store the processed data
                    st.session_state.data = df
                    
                    # Display success message
                    st.success("File uploaded and processed successfully!")
                    
                    # Display data summary
                    display_data_summary(df)
                except Exception as e:
                    st.error(f"Error processing file: {str(e)}")
        
        elif load_button:
            with st.spinner("Loading data from Google Sheet..."):
                df, error = load_data_from_gsheet(url)
                
                if error:
                    st.error(f"Error loading data: {error}")
                else:
                    # Store the processed data
                    st.session_state.data = df
                    
                    # Display success message
                    st.success("Data loaded from Google Sheet successfully!")
                    
                    # Display data summary
                    display_data_summary(df)
                    
    # Auto-load Google Sheet on first run
    if 'data' not in st.session_state or st.session_state.data is None:
        with st.spinner("Loading data from Google Sheet..."):
            df, error = load_data_from_gsheet("https://docs.google.com/spreadsheets/d/1Z8S-lJygDcuB3gs120EoXLVMtZzgp7HQrjtNkkOqJQs/edit?pli=1&gid=0#gid=0")
            
            if error:
                st.error(f"Error auto-loading data: {error}")
            else:
                # Store the processed data
                st.session_state.data = df
                
                # Display success message
                st.success("Data loaded from Google Sheet automatically!")
                
                # Display data summary
                display_data_summary(df)

def display_data_summary(df):
    """Display a summary of the loaded data"""
    st.subheader("Data Summary")
    
    # Calculate summary statistics
    summary = {
        'total_keywords': df['Keyword'].nunique() if 'Keyword' in df.columns else 0,
        'total_domains': df['domain'].nunique() if 'domain' in df.columns else 0,
        'total_urls': df['Results'].nunique() if 'Results' in df.columns else 0,
        'date_range': get_date_range(df)
    }
    
    # Create columns for summary statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Keywords", summary['total_keywords'])
    
    with col2:
        st.metric("Domains", summary['total_domains'])
    
    with col3:
        st.metric("URLs", summary['total_urls'])
    
    with col4:
        if summary['date_range'][0] != "N/A":
            st.metric("Date Range", f"{summary['date_range'][0]} to {summary['date_range'][1]}")
        else:
            st.metric("Date Range", "N/A")
    
    # Show a preview of the data
    st.subheader("Data Preview")
    st.dataframe(df.head(10), use_container_width=True)

def dashboard_tab():
    st.header("SEO Position Tracking Dashboard")
    
    # Check if data is loaded
    if 'data' not in st.session_state or st.session_state.data is None:
        st.info("Please upload data or load from Google Sheet first.")
        return
    
    # Get the data
    df = st.session_state.data
    
    # Create filter controls
    st.subheader("Filter Data")
    
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    
    with col1:
        # Date range filter
        date_range = None
        if 'date' in df.columns:
            min_date = df['date'].min()
            max_date = df['date'].max()
            
            if pd.notna(min_date) and pd.notna(max_date):
                date_range = st.date_input(
                    "Date Range:",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
    
    with col2:
        # Keyword filter
        if 'Keyword' in df.columns:
            keywords = df['Keyword'].unique().tolist()
            keywords.insert(0, "All Keywords")
            keyword = st.selectbox("Keyword Filter:", keywords)
        else:
            keyword = None
    
    with col3:
        # Position range filter
        col3_1, col3_2 = st.columns(2)
        with col3_1:
            position_min = st.number_input("Position Min:", min_value=1, value=1)
        with col3_2:
            position_max = st.number_input("Position Max:", min_value=1, value=100)
    
    # Apply filters button
    with col4:
        filter_button = st.button("Apply Filters")
    
    # Apply filters
    if filter_button or 'dashboard_filtered' not in st.session_state:
        st.session_state.dashboard_filtered = True
        
        filtered_df = df.copy()
        
        if date_range and len(date_range) == 2:
            date_filter = {'start': date_range[0], 'end': date_range[1]}
            filtered_df = apply_date_filter(filtered_df, date_filter)
        
        if keyword and keyword != "All Keywords":
            filtered_df = apply_keyword_filter(filtered_df, keyword)
        
        filtered_df = apply_position_filter(filtered_df, position_min, position_max)
        
        st.session_state.dashboard_df = filtered_df
    else:
        filtered_df = st.session_state.dashboard_df
    
    # Create metrics
    st.subheader("Key Metrics")
    
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    
    with metric_col1:
        st.metric("Total Keywords", filtered_df['Keyword'].nunique() if 'Keyword' in filtered_df.columns else 0)
    
    with metric_col2:
        st.metric("Total Domains", filtered_df['domain'].nunique() if 'domain' in filtered_df.columns else 0)
    
    with metric_col3:
        st.metric("Total URLs", filtered_df['Results'].nunique() if 'Results' in filtered_df.columns else 0)
    
    with metric_col4:
        if 'Position' in filtered_df.columns:
            avg_position = filtered_df['Position'].mean()
            st.metric("Average Position", f"{avg_position:.2f}")
        else:
            st.metric("Average Position", "N/A")
    
    # Download button for filtered data
    st.download_button(
        label="Export to Excel",
        data=to_excel(filtered_df),
        file_name="seo_dashboard_export.xlsx",
        mime="application/vnd.ms-excel"
    )
    
    # Create visualizations
    st.subheader("Visualizations")
    
    # Position Distribution
    position_col1, position_col2 = st.columns(2)
    
    with position_col1:
        st.write("#### Position Distribution")
        top_n = st.radio("Show:", ["Top 3", "Top 5", "Top 10", "Top 20"], horizontal=True, key="pos_dist")
        top_n_value = int(top_n.split()[1])
        
        if 'Position' in filtered_df.columns:
            pos_dist = px.histogram(
                filtered_df[filtered_df['Position'] <= top_n_value], 
                x='Position',
                nbins=top_n_value,
                title=f'Position Distribution (Top {top_n_value})',
                color_discrete_sequence=['#3366CC']
            )
            
            pos_dist.update_layout(
                xaxis_title="Position",
                yaxis_title="Count",
                bargap=0.1
            )
            
            st.plotly_chart(pos_dist, use_container_width=True)
        else:
            st.info("No position data available.")
    
    with position_col2:
        st.write("#### Top Domains by Average Position")
        domain_top_n = st.radio("Show:", ["Top 3", "Top 5", "Top 10", "Top 20"], horizontal=True, key="domain_dist")
        domain_top_n_value = int(domain_top_n.split()[1])
        
        if 'domain' in filtered_df.columns and 'Position' in filtered_df.columns:
            domain_positions = filtered_df.groupby('domain')['Position'].mean().reset_index()
            domain_positions = domain_positions.sort_values('Position')
            
            top_domains_chart = px.bar(
                domain_positions.head(domain_top_n_value), 
                x='domain', 
                y='Position',
                title=f'Top {domain_top_n_value} Domains by Average Position',
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
            st.info("No domain position data available.")
    
    # Top Keywords and Domains
    keyword_col1, keyword_col2 = st.columns(2)
    
    with keyword_col1:
        st.write("#### Top Keywords by Volume")
        
        if 'Keyword' in filtered_df.columns and 'Results' in filtered_df.columns:
            keyword_volume = filtered_df.groupby('Keyword')['Results'].nunique().reset_index()
            keyword_volume = keyword_volume.sort_values('Results', ascending=False).head(10)
            
            st.dataframe(
                keyword_volume.rename(columns={'Keyword': 'Keyword', 'Results': 'Number of URLs'}),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No keyword data available.")
    
    with keyword_col2:
        st.write("#### Top Domains by Frequency")
        
        if 'domain' in filtered_df.columns:
            domain_freq = filtered_df['domain'].value_counts().reset_index()
            domain_freq.columns = ['domain', 'count']
            domain_freq = domain_freq.head(10)
            
            st.dataframe(
                domain_freq.rename(columns={'domain': 'Domain', 'count': 'Frequency'}),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No domain data available.")

def keyword_analysis_tab():
    st.header("Keyword Analysis")
    
    # Check if data is loaded
    if 'data' not in st.session_state or st.session_state.data is None:
        st.info("Please upload data or load from Google Sheet first.")
        return
    
    # Get the data
    df = st.session_state.data
    
    # Create filter controls
    st.subheader("Filter Data")
    
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    
    with col1:
        # Keyword filter
        if 'Keyword' in df.columns:
            keywords = ["-- Select a keyword --"] + df['Keyword'].unique().tolist()
            keyword = st.selectbox("Select Keyword:", keywords)
        else:
            st.error("No keyword data available.")
            return
    
    with col2:
        # Date range filter
        date_range = None
        if 'date' in df.columns:
            min_date = df['date'].min()
            max_date = df['date'].max()
            
            if pd.notna(min_date) and pd.notna(max_date):
                date_range = st.date_input(
                    "Date Range:",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
    
    with col3:
        # Domain filter
        if 'domain' in df.columns:
            domains = ["All Domains"] + df['domain'].unique().tolist()
            domain = st.selectbox("Domain Filter:", domains)
        else:
            domain = None
    
    # Apply filters button
    with col4:
        filter_button = st.button("Apply Filters")
    
    # Validate keyword selection
    if keyword == "-- Select a keyword --":
        st.info("Please select a keyword to analyze.")
        return
    
    # Apply filters
    if filter_button or 'keyword_filtered' not in st.session_state or st.session_state.selected_keyword != keyword:
        st.session_state.keyword_filtered = True
        st.session_state.selected_keyword = keyword
        
        filtered_df = df.copy()
        
        # Filter by keyword
        filtered_df = apply_keyword_filter(filtered_df, keyword)
        
        if date_range and len(date_range) == 2:
            date_filter = {'start': date_range[0], 'end': date_range[1]}
            filtered_df = apply_date_filter(filtered_df, date_filter)
        
        if domain and domain != "All Domains":
            filtered_df = apply_domain_filter(filtered_df, domain)
        
        st.session_state.keyword_df = filtered_df
    else:
        filtered_df = st.session_state.keyword_df
    
    # Display dates for selected keyword
    if 'date' in filtered_df.columns:
        unique_dates = filtered_df['date'].dropna().unique()
        formatted_dates = [d.strftime('%Y-%m-%d') if isinstance(d, datetime.date) else str(d) 
                          for d in sorted(unique_dates)]
        
        st.write(f"#### Available Dates for Selected Keyword")
        st.write(", ".join(formatted_dates))
    
    # Download button for filtered data
    st.download_button(
        label="Export to Excel",
        data=to_excel(filtered_df),
        file_name=f"keyword_analysis_{keyword}.xlsx",
        mime="application/vnd.ms-excel"
    )
    
    # Check if data is available after filtering
    if filtered_df.empty:
        st.warning(f"No data available for keyword '{keyword}' with the selected filters.")
        return
    
    # Create visualizations
    st.subheader("Visualizations")
    
    # Position Distribution
    if 'Position' in filtered_df.columns:
        pos_dist = px.histogram(
            filtered_df, 
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
        
        st.plotly_chart(pos_dist, use_container_width=True)
    
    # Top Domains for this keyword
    if 'domain' in filtered_df.columns and 'Position' in filtered_df.columns:
        domain_positions = filtered_df.groupby('domain')['Position'].agg(['mean', 'min', 'max', 'count']).reset_index()
        domain_positions = domain_positions.sort_values('mean')
        
        top_n = st.radio("Top Domains:", [3, 5, 10, 20], horizontal=True)
        
        domain_perf = px.bar(
            domain_positions.head(top_n), 
            x='domain', 
            y='mean',
            error_y='count',
            title=f'Top {top_n} Domains for "{keyword}"',
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
        
        # Position trend over time chart
        if 'date' in filtered_df.columns:
            # Get top domains for this keyword
            top_domains = domain_positions.head(top_n)['domain'].tolist()
            
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
                    title=f'Position Trend Over Time for "{keyword}"',
                    labels={'date': 'Date', 'Position': 'Position', 'domain': 'Domain'}
                )
                
                trend_chart.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Position",
                    yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                    legend_title="Domain"
                )
                
                st.plotly_chart(trend_chart, use_container_width=True)

def domain_analysis_tab():
    st.header("Domain Analysis")
    
    # Check if data is loaded
    if 'data' not in st.session_state or st.session_state.data is None:
        st.info("Please upload data or load from Google Sheet first.")
        return
    
    # Get the data
    df = st.session_state.data
    
    # Create filter controls
    st.subheader("Filter Data")
    
    col1, col2, col3_container, col4 = st.columns([1, 1, 1, 1])
    
    with col1:
        # Domain filter
        if 'domain' in df.columns:
            domains = df['domain'].unique().tolist()
            domain_input = st.selectbox("Select Domain:", [""] + domains)
        else:
            domain_input = st.text_input("Enter Domain:")
    
    with col2:
        # Date range filter
        date_range = None
        if 'date' in df.columns:
            min_date = df['date'].min()
            max_date = df['date'].max()
            
            if pd.notna(min_date) and pd.notna(max_date):
                date_range = st.date_input(
                    "Date Range:",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
    
    with col3_container:
        # Position range filter
        col3_1, col3_2 = st.columns(2)
        with col3_1:
            position_min = st.number_input("Position Min:", min_value=1, value=1, key="domain_pos_min")
        with col3_2:
            position_max = st.number_input("Position Max:", min_value=1, value=100, key="domain_pos_max")
    
    # Analyze button
    with col4:
        analyze_button = st.button("Analyze Domain")
    
    if analyze_button and domain_input:
        # Apply filters
        filtered_df = df.copy()
        
        # Filter by domain
        if 'domain' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['domain'] == domain_input]
        else:
            # Try to extract domain from URLs if domain column doesn't exist
            if 'Results' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['Results'].str.contains(domain_input, na=False)]
        
        if date_range and len(date_range) == 2:
            date_filter = {'start': date_range[0], 'end': date_range[1]}
            filtered_df = apply_date_filter(filtered_df, date_filter)
        
        filtered_df = apply_position_filter(filtered_df, position_min, position_max)
        
        # Check if data is available after filtering
        if filtered_df.empty:
            st.warning(f"No data available for domain '{domain_input}' with the selected filters.")
            return
        
        # Download button for filtered data
        st.download_button(
            label="Export to Excel",
            data=to_excel(filtered_df),
            file_name=f"domain_analysis_{domain_input}.xlsx",
            mime="application/vnd.ms-excel"
        )
        
        # Create visualizations
        st.subheader("Visualizations")
        
        # Top Keywords for this domain
        if 'Keyword' in filtered_df.columns and 'Position' in filtered_df.columns:
            keyword_perf = filtered_df.groupby('Keyword')['Position'].agg(['mean', 'min', 'max', 'count']).reset_index()
            keyword_perf = keyword_perf.sort_values('mean')
            
            top_n = st.radio("Top Keywords:", [3, 5, 10, 20], horizontal=True)
            
            keyword_chart = px.bar(
                keyword_perf.head(top_n), 
                x='Keyword', 
                y='mean',
                title=f'Top {top_n} Keywords for "{domain_input}"',
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
            
            # Position trend over time chart
            if 'date' in filtered_df.columns:
                # Get top keywords for this domain
                top_keywords = keyword_perf.head(top_n)['Keyword'].tolist()
                
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
                        title=f'Position Trend Over Time for "{domain_input}"',
                        labels={'date': 'Date', 'Position': 'Position', 'Keyword': 'Keyword'}
                    )
                    
                    trend_chart.update_layout(
                        xaxis_title="Date",
                        yaxis_title="Position",
                        yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                        legend_title="Keyword"
                    )
                    
                    st.plotly_chart(trend_chart, use_container_width=True)

def url_comparison_tab():
    st.header("URL Comparison")
    
    # Check if data is loaded
    if 'data' not in st.session_state or st.session_state.data is None:
        st.info("Please upload data or load from Google Sheet first.")
        return
    
    # Get the data
    df = st.session_state.data
    
    # Create filter controls
    st.subheader("Filter Data")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        # URL multi-select
        if 'Results' in df.columns:
            urls = df['Results'].unique().tolist()
            selected_urls = st.multiselect("Select URLs to Compare:", urls, help="Hold Ctrl/Cmd to select multiple URLs")
        else:
            st.error("No URL data available.")
            return
    
    with col2:
        # Date range filter
        date_range = None
        if 'date' in df.columns:
            min_date = df['date'].min()
            max_date = df['date'].max()
            
            if pd.notna(min_date) and pd.notna(max_date):
                date_range = st.date_input(
                    "Date Range:",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
    
    with col3:
        compare_button = st.button("Compare URLs")
    
    if compare_button and selected_urls:
        # Apply filters
        filtered_df = df.copy()
        
        # Filter by URLs
        filtered_df = filtered_df[filtered_df['Results'].isin(selected_urls)]
        
        if date_range and len(date_range) == 2:
            date_filter = {'start': date_range[0], 'end': date_range[1]}
            filtered_df = apply_date_filter(filtered_df, date_filter)
        
        # Check if data is available after filtering
        if filtered_df.empty:
            st.warning("No data available for the selected URLs with the selected filters.")
            return
        
        # Download button for filtered data
        st.download_button(
            label="Export to Excel",
            data=to_excel(filtered_df),
            file_name="url_comparison.xlsx",
            mime="application/vnd.ms-excel"
        )
        
        # Create visualizations
        st.subheader("Visualizations")
        
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
        
        # Create URL comparison chart
        if url_data:
            url_df = pd.DataFrame(url_data)
            
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
        
        # Create keyword performance by URL chart
        if 'Keyword' in filtered_df.columns and 'Position' in filtered_df.columns:
            # Get top 5 keywords by frequency across these URLs
            top_keywords = filtered_df['Keyword'].value_counts().head(5).index.tolist()
            
            # For each keyword, get position by URL
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
        
        # Position trend over time chart
        if 'date' in filtered_df.columns:
            trend_data = []
            
            for url in selected_urls:
                url_time_data = filtered_df[filtered_df['Results'] == url]
                
                if not url_time_data.empty:
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

def time_comparison_tab():
    st.header("Time Comparison")
    
    # Check if data is loaded
    if 'data' not in st.session_state or st.session_state.data is None:
        st.info("Please upload data or load from Google Sheet first.")
        return
    
    # Get the data
    df = st.session_state.data
    
    # Create filter controls
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Keyword filter
        if 'Keyword' in df.columns:
            keywords = ["-- Select a keyword --"] + df['Keyword'].unique().tolist()
            keyword = st.selectbox("Select Keyword:", keywords, key="time_comp_keyword")
        else:
            st.error("No keyword data available.")
            return
    
    # If keyword is selected, get available dates for that keyword
    available_dates = []
    if keyword != "-- Select a keyword --":
        keyword_df = df[df['Keyword'] == keyword]
        
        if 'date' in keyword_df.columns:
            available_dates = sorted(keyword_df['date'].dropna().unique())
            available_date_strings = [d.strftime('%Y-%m-%d') if isinstance(d, datetime.date) else str(d) 
                                     for d in available_dates]
        
    with col2:
        # Start date selection
        if keyword != "-- Select a keyword --" and available_dates:
            start_date = st.selectbox(
                "Start Date:",
                ["Select a date"] + available_date_strings,
                key="time_comp_start_date"
            )
        else:
            start_date = st.selectbox(
                "Start Date:",
                ["Select a keyword first"],
                disabled=True,
                key="time_comp_start_date_disabled"
            )
    
    with col3:
        # End date selection
        if keyword != "-- Select a keyword --" and available_dates:
            end_date = st.selectbox(
                "End Date:",
                ["Select a date"] + available_date_strings,
                index=len(available_date_strings) if available_date_strings else 0,
                key="time_comp_end_date"
            )
        else:
            end_date = st.selectbox(
                "End Date:",
                ["Select a keyword first"],
                disabled=True,
                key="time_comp_end_date_disabled"
            )
    
    with col4:
        compare_button = st.button("Compare Over Time")
    
    if compare_button and keyword != "-- Select a keyword --" and start_date != "Select a date" and end_date != "Select a date":
        # Apply filters
        keyword_df = df[df['Keyword'] == keyword].copy()
        
        # Filter by dates
        start_data = pd.DataFrame()
        end_data = pd.DataFrame()
        
        if 'date' in keyword_df.columns:
            try:
                # Convert dates to datetime.date objects for comparison
                start_date_obj = pd.to_datetime(start_date).date() if not isinstance(start_date, datetime.date) else start_date
                end_date_obj = pd.to_datetime(end_date).date() if not isinstance(end_date, datetime.date) else end_date
                
                start_data = keyword_df[keyword_df['date'] == start_date_obj]
                end_data = keyword_df[keyword_df['date'] == end_date_obj]
            except Exception as e:
                st.error(f"Error filtering by dates: {str(e)}")
        
        # Check if we have data for both dates
        if start_data.empty:
            st.warning(f"No data available for start date: {start_date}")
            return
        
        if end_data.empty:
            st.warning(f"No data available for end date: {end_date}")
            return
        
        # Download button for filtered data
        combined_df = pd.concat([start_data, end_data])
        combined_df['date_label'] = combined_df['date'].apply(lambda x: 'Start' if x == start_date_obj else 'End')
        
        st.download_button(
            label="Export to Excel",
            data=to_excel(combined_df),
            file_name=f"time_comparison_{keyword}.xlsx",
            mime="application/vnd.ms-excel"
        )
        
        # Remove any duplicated URLs to fix double position issues
        start_data = start_data.drop_duplicates(subset=['Results'])
        end_data = end_data.drop_duplicates(subset=['Results'])
        
        # Prepare data for display
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
                        st.error(f"Error processing start URL {url}: {str(e)}")
                        continue
        
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
                        st.error(f"Error processing end URL {url}: {str(e)}")
                        continue
        
        # Prepare position changes analysis
        # Identify all URLs that exist in either start or end data
        all_urls = set()
        position_changes = []
        
        for url_data in start_urls:
            all_urls.add(url_data['url'])
        
        for url_data in end_urls:
            all_urls.add(url_data['url'])
        
        # Create combined start and end mappings
        start_pos_map = {item['url']: item['position'] for item in start_urls}
        end_pos_map = {item['url']: item['position'] for item in end_urls}
        
        # Build the position changes data for ALL URLs
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
        
        # Display comparison summary
        st.subheader("Comparison Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"**Keyword:** {keyword}")
        
        with col2:
            st.write(f"**Start Date:** {start_date}")
            st.write(f"({len(start_urls)} URLs found)")
        
        with col3:
            st.write(f"**End Date:** {end_date}")
            st.write(f"({len(end_urls)} URLs found)")
        
        # Display start date URLs
        st.subheader("Start Date URLs")
        st.write("Sorted by position (best positions first)")
        
        start_urls_df = pd.DataFrame(start_urls)
        if not start_urls_df.empty:
            st.dataframe(
                start_urls_df[['position', 'url', 'domain', 'position_change_text']].rename(
                    columns={
                        'position': 'Position',
                        'url': 'URL',
                        'domain': 'Domain',
                        'position_change_text': 'Position Change'
                    }
                ),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No URLs found for start date.")
        
        # Display end date URLs
        st.subheader("End Date URLs")
        st.write("Sorted by position (best positions first)")
        
        end_urls_df = pd.DataFrame(end_urls)
        if not end_urls_df.empty:
            st.dataframe(
                end_urls_df[['position', 'url', 'domain', 'position_change_text']].rename(
                    columns={
                        'position': 'Position',
                        'url': 'URL',
                        'domain': 'Domain',
                        'position_change_text': 'Position Change'
                    }
                ),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No URLs found for end date.")
        
        # Display position changes analysis
        st.subheader("Position Changes Analysis")
        st.write("All URLs with their position changes")
        
        position_changes_df = pd.DataFrame(position_changes)
        if not position_changes_df.empty:
            # Format the dataframe for display
            display_df = position_changes_df.copy()
            
            # Add styling for improved/declined
            display_df['start_position'] = display_df['start_position'].apply(lambda x: str(x) if pd.notna(x) else "N/A")
            display_df['end_position'] = display_df['end_position'].apply(lambda x: str(x) if pd.notna(x) else "N/A")
            
            st.dataframe(
                display_df[['url', 'domain', 'start_position', 'end_position', 'change_text']].rename(
                    columns={
                        'url': 'URL',
                        'domain': 'Domain',
                        'start_position': 'Start Position',
                        'end_position': 'End Position',
                        'change_text': 'Change'
                    }
                ),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No position changes to display.")

# Main function
def main():
    st.set_page_config(
        page_title="Advanced SEO Position Tracker",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS to make the app look better
    st.markdown("""
    <style>
    .main .block-container {
        padding-top: 2rem;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #1E3A8A;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 16px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #E0E7FF;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Title
    st.title("Advanced SEO Position Tracker")
    
    # Initialize session state for data
    if 'data' not in st.session_state:
        st.session_state.data = None
    
    if 'dashboard_filtered' not in st.session_state:
        st.session_state.dashboard_filtered = False
        st.session_state.dashboard_df = None
    
    if 'keyword_filtered' not in st.session_state:
        st.session_state.keyword_filtered = False
        st.session_state.keyword_df = None
        st.session_state.selected_keyword = None
    
    # Create tabs
    tabs = st.tabs([
        "Upload Data",
        "Dashboard",
        "Keyword Analysis",
        "Domain Analysis",
        "URL Comparison",
        "Time Comparison"
    ])
    
    # Populate each tab
    with tabs[0]:
        upload_data_tab()
    
    with tabs[1]:
        dashboard_tab()
    
    with tabs[2]:
        keyword_analysis_tab()
    
    with tabs[3]:
        domain_analysis_tab()
    
    with tabs[4]:
        url_comparison_tab()
    
    with tabs[5]:
        time_comparison_tab()

if __name__ == '__main__':
    main()
