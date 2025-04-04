import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from urllib.parse import urlparse
import datetime
import io
import re

# Set page title and layout
st.set_page_config(
    page_title="SEO Position Tracking Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("SEO Position Tracking Dashboard")

# Function to get domain from URL
def get_domain(url):
    """Extract domain from URL"""
    try:
        if pd.isna(url):
            return None
        return urlparse(url).netloc
    except (TypeError, ValueError):
        return None

# Function to prepare data for analysis
def prepare_data(df):
    """Prepare data for analysis"""
    # Convert key columns to strings to prevent type issues
    if 'Results' in df.columns:
        df['Results'] = df['Results'].astype(str)
    if 'Keyword' in df.columns:
        df['Keyword'] = df['Keyword'].astype(str)
    
    # Convert Position to numeric (if it exists)
    if 'Position' in df.columns:
        df['Position'] = pd.to_numeric(df['Position'], errors='coerce')
    
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

# Function to get date range from DataFrame
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

# Load data from Google Sheet
@st.cache_data(ttl=3600)  # Cache the data for 1 hour
def load_data():
    """Load data from Google Sheet and prepare it for analysis"""
    try:
        # Convert Google Sheet URL to export URL (CSV format)
        sheet_id = "1Z8S-lJygDcuB3gs120EoXLVMtZzgp7HQrjtNkkOqJQs"
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        
        df = pd.read_csv(sheet_url)
        return prepare_data(df)
    except Exception as e:
        st.error(f"Error loading data from Google Sheet: {str(e)}")
        return None

# Apply date filter
def apply_date_filter(df, date_range):
    """Apply date range filter to DataFrame"""
    if not date_range or 'date' not in df.columns:
        return df
    
    try:
        start_date = pd.to_datetime(date_range['start'])
        end_date = pd.to_datetime(date_range['end'])
        return df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    except Exception as e:
        st.warning(f"Error applying date filter: {str(e)}")
        return df

# Apply position filter
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

# Apply keyword filter
def apply_keyword_filter(df, keyword):
    """Apply keyword filter to DataFrame"""
    if not keyword or 'Keyword' not in df.columns:
        return df
    
    return df[df['Keyword'] == keyword]

# Apply domain filter
def apply_domain_filter(df, domain):
    """Apply domain filter to DataFrame"""
    if not domain or 'domain' not in df.columns:
        return df
    
    return df[df['domain'] == domain]

# Time Comparison Tab Function
def time_comparison_tab(df, tabs):
    with tabs[4]:
        st.header("Time Comparison")
        
        # Keyword selector
        if 'Keyword' in df.columns:
            # Controls layout
            col1, col2, col3 = st.columns(3)
            
            with col1:
                keywords = sorted(df['Keyword'].unique().tolist())
                time_compare_keyword = st.selectbox("Select Keyword", 
                                                  ["-- Select a keyword --"] + keywords, 
                                                  key="time_comparison_keyword")
            
            # Get available dates for the selected keyword
            if time_compare_keyword != "-- Select a keyword --":
                # Filter by keyword - important to use a copy to avoid SettingWithCopyWarning
                keyword_df = df[df['Keyword'] == time_compare_keyword].copy()
                
                # Show debug option
                show_debug = st.checkbox("Debug data information")
                
                if show_debug:
                    st.write("Data shape:", keyword_df.shape)
                    st.write("Columns:", keyword_df.columns.tolist())
                    st.write("Keyword data sample:")
                    st.write(keyword_df.head(3))
                
                if not keyword_df.empty:
                    # Determine date column
                    date_col = None
                    if 'date/time' in keyword_df.columns:
                        date_col = 'date/time'
                    elif 'Time' in keyword_df.columns:
                        date_col = 'Time'
                    elif 'date' in keyword_df.columns:
                        date_col = 'date'
                    
                    if show_debug:
                        st.write(f"Using date column: {date_col}")
                    
                    if date_col:
                        # Extract date strings from the date column
                        # For "date/time" column with format "Mon 2025-02-10 3:50:51",
                        # extract the "2025-02-10" part
                        if date_col == 'date/time':
                            # Extract YYYY-MM-DD pattern from date strings
                            keyword_df['date_extracted'] = keyword_df[date_col].astype(str).str.extract(r'(\d{4}-\d{2}-\d{2})')
                            date_values = keyword_df['date_extracted'].dropna().unique()
                        else:
                            # For other date columns, convert to string format
                            keyword_df['date_extracted'] = pd.to_datetime(keyword_df[date_col], errors='coerce').dt.strftime('%Y-%m-%d')
                            date_values = keyword_df['date_extracted'].dropna().unique()
                        
                        if show_debug:
                            st.write(f"Extracted dates: {date_values.tolist()}")
                        
                        # Date selectors
                        date_strings = sorted(date_values.tolist())
                        
                        if date_strings:
                            with col2:
                                start_date = st.selectbox("Start Date", 
                                                       ["-- Select start date --"] + date_strings,
                                                       key="time_comparison_start_date")
                            
                            with col3:
                                end_date = st.selectbox("End Date", 
                                                     ["-- Select end date --"] + date_strings,
                                                     key="time_comparison_end_date")
                            
                            # Compare button
                            compare_time = st.button("Compare Over Time")
                            
                            if start_date != "-- Select start date --" and end_date != "-- Select end date --" and compare_time:
                                # Filter data for the selected dates
                                start_data = keyword_df[keyword_df['date_extracted'] == start_date].copy()
                                end_data = keyword_df[keyword_df['date_extracted'] == end_date].copy()
                                
                                if show_debug:
                                    st.write(f"Start date '{start_date}' has {len(start_data)} records")
                                    st.write(f"End date '{end_date}' has {len(end_data)} records")
                                    
                                    if not start_data.empty:
                                        st.write("Start date data sample:")
                                        st.write(start_data[['Results', 'Position']].head())
                                    
                                    if not end_data.empty:
                                        st.write("End date data sample:")
                                        st.write(end_data[['Results', 'Position']].head())
                                
                                # Verify we have data for both dates
                                if start_data.empty or end_data.empty:
                                    st.warning(f"No data found for one or both selected dates.")
                                else:
                                    # Show comparison summary
                                    st.subheader("Comparison Summary")
                                    
                                    info_cols = st.columns(3)
                                    info_cols[0].info(f"**Keyword:** {time_compare_keyword}")
                                    info_cols[1].info(f"**Start Date:** {start_date} ({len(start_data)} URLs)")
                                    info_cols[2].info(f"**End Date:** {end_date} ({len(end_data)} URLs)")
                                    
                                    # Sort both datasets by position
                                    start_data_sorted = start_data.sort_values('Position', ascending=True)
                                    end_data_sorted = end_data.sort_values('Position', ascending=True)
                                    
                                    # Display start date rankings
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        st.subheader("Start Date Rankings")
                                        start_display = pd.DataFrame({
                                            'Position': start_data_sorted['Position'],
                                            'URL': start_data_sorted['Results'],
                                            'Domain': start_data_sorted['Results'].apply(get_domain)
                                        }).reset_index(drop=True)
                                        st.dataframe(start_display, use_container_width=True)
                                    
                                    with col2:
                                        st.subheader("End Date Rankings")
                                        end_display = pd.DataFrame({
                                            'Position': end_data_sorted['Position'],
                                            'URL': end_data_sorted['Results'],
                                            'Domain': end_data_sorted['Results'].apply(get_domain)
                                        }).reset_index(drop=True)
                                        st.dataframe(end_display, use_container_width=True)
                                    
                                    # Position changes analysis
                                    st.subheader("Position Changes")
                                    
                                    # Create position maps for quick lookup
                                    start_positions = dict(zip(start_data_sorted['Results'], start_data_sorted['Position']))
                                    end_positions = dict(zip(end_data_sorted['Results'], end_data_sorted['Position']))
                                    
                                    # Collect all unique URLs
                                    all_urls = set(start_positions.keys()) | set(end_positions.keys())
                                    
                                    # Create change data
                                    changes_data = []
                                    for url in all_urls:
                                        start_pos = start_positions.get(url)
                                        end_pos = end_positions.get(url)
                                        domain = get_domain(url)
                                        
                                        change_row = {
                                            'URL': url,
                                            'Domain': domain,
                                            'Start Position': start_pos,
                                            'End Position': end_pos
                                        }
                                        
                                        # Calculate change
                                        if start_pos is not None and end_pos is not None:
                                            change = end_pos - start_pos
                                            if change < 0:
                                                change_row['Change'] = f"↑ {abs(change)} (improved)"
                                                change_row['Status'] = 'improved'
                                                change_row['NumericChange'] = change
                                            elif change > 0:
                                                change_row['Change'] = f"↓ {change} (declined)"
                                                change_row['Status'] = 'declined'
                                                change_row['NumericChange'] = change
                                            else:
                                                change_row['Change'] = "No change"
                                                change_row['Status'] = 'unchanged'
                                                change_row['NumericChange'] = 0
                                        else:
                                            if start_pos is None:
                                                change_row['Change'] = "New"
                                                change_row['Status'] = 'new'
                                            else:
                                                change_row['Change'] = "Dropped"
                                                change_row['Status'] = 'dropped'
                                            change_row['NumericChange'] = None
                                        
                                        changes_data.append(change_row)
                                    
                                    # Convert to DataFrame
                                    changes_df = pd.DataFrame(changes_data)
                                    
                                    # Sort by status and change
                                    status_order = {
                                        'improved': 0,
                                        'declined': 1,
                                        'new': 2,
                                        'dropped': 3,
                                        'unchanged': 4
                                    }
                                    
                                    if not changes_df.empty and 'Status' in changes_df.columns:
                                        changes_df['StatusOrder'] = changes_df['Status'].map(status_order)
                                        
                                        # For numeric changes, sort by magnitude (abs value) descending
                                        changes_df['ChangeMagnitude'] = changes_df['NumericChange'].abs() if 'NumericChange' in changes_df.columns else 0
                                        
                                        # Apply sorting
                                        changes_df = changes_df.sort_values(
                                            by=['StatusOrder', 'ChangeMagnitude'],
                                            ascending=[True, False]
                                        )
                                        
                                        # Drop helper columns
                                        changes_df = changes_df.drop(columns=['StatusOrder', 'ChangeMagnitude', 'NumericChange'])
                                        
                                        # Apply styling
                                        def highlight_status(row):
                                            if row['Status'] == 'improved':
                                                return ['background-color: lightgreen'] * len(row)
                                            elif row['Status'] == 'declined':
                                                return ['background-color: lightsalmon'] * len(row)
                                            elif row['Status'] == 'new':
                                                return ['background-color: lightblue'] * len(row)
                                            elif row['Status'] == 'dropped':
                                                return ['background-color: #FFCCCB'] * len(row)
                                            return [''] * len(row)
                                        
                                        styled_df = changes_df.style.apply(highlight_status, axis=1)
                                        st.dataframe(styled_df, use_container_width=True)
                                    else:
                                        st.info("No changes to display")
                                    
                                    # Visualization
                                    if changes_data:
                                        st.subheader("Position Change Visualization")
                                        
                                        # Prepare data for visualization
                                        viz_data = []
                                        for item in changes_data:
                                            if item['Status'] in ('improved', 'declined') and 'NumericChange' in item:
                                                viz_data.append({
                                                    'url': item['URL'],
                                                    'domain': item['Domain'],
                                                    'change': item['NumericChange'],
                                                    'start_pos': item['Start Position'],
                                                    'end_pos': item['End Position'],
                                                    'status': item['Status']
                                                })
                                        
                                        if viz_data:
                                            viz_df = pd.DataFrame(viz_data)
                                            
                                            # Add label with position info
                                            viz_df['label'] = viz_df.apply(
                                                lambda x: f"{x['domain']} (Pos {x['start_pos']}→{x['end_pos']})",
                                                axis=1
                                            )
                                            
                                            # Sort by status and change magnitude
                                            viz_df['abs_change'] = viz_df['change'].abs()
                                            viz_df = viz_df.sort_values(['status', 'abs_change'], ascending=[True, False])
                                            
                                            # Create color map
                                            colors = {'improved': 'green', 'declined': 'red'}
                                            
                                            # Create chart
                                            fig = px.bar(
                                                viz_df,
                                                x='change',
                                                y='label',
                                                color='status',
                                                color_discrete_map=colors,
                                                title=f"Position Changes ({start_date} to {end_date})",
                                                labels={'change': 'Position Change', 'label': 'Domain', 'status': 'Status'},
                                                hover_data=['url']
                                            )
                                            
                                            # Update layout
                                            fig.update_layout(
                                                xaxis_title="Position Change (negative = better)",
                                                yaxis_title="Domain",
                                                height=max(400, 30 * len(viz_df))  # Dynamic height
                                            )
                                            
                                            # Add reference line at x=0
                                            fig.add_vline(x=0, line_dash="dash", line_color="black")
                                            
                                            st.plotly_chart(fig, use_container_width=True)
                                        
                                        # Summary statistics
                                        counts = {
                                            'improved': len([r for r in changes_data if r['Status'] == 'improved']),
                                            'declined': len([r for r in changes_data if r['Status'] == 'declined']),
                                            'unchanged': len([r for r in changes_data if r['Status'] == 'unchanged']),
                                            'new': len([r for r in changes_data if r['Status'] == 'new']),
                                            'dropped': len([r for r in changes_data if r['Status'] == 'dropped'])
                                        }
                                        
                                        st.subheader("Summary Statistics")
                                        stats_cols = st.columns(5)
                                        stats_cols[0].metric("Improved", counts['improved'])
                                        stats_cols[1].metric("Declined", counts['declined'])
                                        stats_cols[2].metric("Unchanged", counts['unchanged'])
                                        stats_cols[3].metric("New", counts['new'])
                                        stats_cols[4].metric("Dropped", counts['dropped'])
                        else:
                            st.warning("No valid dates found for this keyword")
                    else:
                        st.warning("No date column found in the data")
        else:
            st.warning("Keyword column not found in data")

# Main app logic
def main():
    # Display loading spinner while fetching data
    with st.spinner("Loading data from Google Sheet..."):
        df = load_data()
    
    if df is None:
        st.error("Failed to load data. Please check the Google Sheet URL and try again.")
        return
    
    # Dashboard tabs
    tabs = st.tabs(["Overview", "Keyword Analysis", "Domain Analysis", "URL Comparison", "Time Comparison"])
    
    # Overview Tab
    with tabs[0]:
        st.header("SEO Position Tracking Dashboard Overview")
        
        # Filter section
        with st.expander("Filters", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Get min and max dates from data for the date picker
                date_range_values = get_date_range(df)
                default_start = datetime.datetime.now() - datetime.timedelta(days=30)
                default_end = datetime.datetime.now()
                
                try:
                    if date_range_values[0] != "N/A":
                        default_start = pd.to_datetime(date_range_values[0])
                    if date_range_values[1] != "N/A":
                        default_end = pd.to_datetime(date_range_values[1])
                except:
                    pass
                
                date_range = st.date_input(
                    "Date Range",
                    value=(default_start, default_end),
                    format="YYYY-MM-DD"
                )
            
            with col2:
                all_keywords = ["All Keywords"] + sorted(df['Keyword'].unique().tolist()) if 'Keyword' in df.columns else ["No keywords found"]
                keyword_filter = st.selectbox("Keyword Filter", all_keywords)
            
            with col3:
                position_cols = st.columns(2)
                with position_cols[0]:
                    position_min = st.number_input("Min Position", min_value=1, value=1)
                with position_cols[1]:
                    position_max = st.number_input("Max Position", min_value=1, value=100)
        
        # Apply filters
        filtered_df = df.copy()
        
        # Apply date filter if selected
        if len(date_range) == 2:
            date_filter = {'start': date_range[0], 'end': date_range[1]}
            filtered_df = apply_date_filter(filtered_df, date_filter)
        
        # Apply keyword filter if selected
        if keyword_filter != "All Keywords" and keyword_filter != "No keywords found":
            filtered_df = apply_keyword_filter(filtered_df, keyword_filter)
        
        # Apply position filter
        filtered_df = apply_position_filter(filtered_df, position_min, position_max)
        
        # Summary cards
        st.subheader("Data Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        summary = {
            'total_keywords': filtered_df['Keyword'].nunique() if 'Keyword' in filtered_df.columns else 0,
            'total_domains': filtered_df['domain'].nunique() if 'domain' in filtered_df.columns else 0,
            'total_urls': filtered_df['Results'].nunique() if 'Results' in filtered_df.columns else 0,
            'date_range': get_date_range(filtered_df)
        }
        
        # Add delta metrics if we have time data
        if 'date' in filtered_df.columns and not filtered_df.empty:
            try:
                # Calculate change in metrics compared to previous period
                current_period = pd.to_datetime(date_range[1]) - pd.to_datetime(date_range[0])
                previous_start = pd.to_datetime(date_range[0]) - current_period
                previous_end = pd.to_datetime(date_range[0]) - datetime.timedelta(days=1)
                
                previous_date_filter = {'start': previous_start, 'end': previous_end}
                previous_df = apply_date_filter(df, previous_date_filter)
                
                # Calculate deltas
                keywords_delta = filtered_df['Keyword'].nunique() - previous_df['Keyword'].nunique()
                domains_delta = filtered_df['domain'].nunique() - previous_df['domain'].nunique()
                urls_delta = filtered_df['Results'].nunique() - previous_df['Results'].nunique()
                
                col1.metric("Total Keywords", summary['total_keywords'], delta=keywords_delta)
                col2.metric("Total Domains", summary['total_domains'], delta=domains_delta)
                col3.metric("Total URLs", summary['total_urls'], delta=urls_delta)
            except:
                col1.metric("Total Keywords", summary['total_keywords'])
                col2.metric("Total Domains", summary['total_domains'])
                col3.metric("Total URLs", summary['total_urls'])
        else:
            col1.metric("Total Keywords", summary['total_keywords'])
            col2.metric("Total Domains", summary['total_domains'])
            col3.metric("Total URLs", summary['total_urls'])
        
        col4.metric("Date Range", f"{summary['date_range'][0]} to {summary['date_range'][1]}")
        
        # Position distribution chart
        if 'Position' in filtered_df.columns and not filtered_df.empty:
            st.subheader("Position Distribution")
            
            # Rank selector
            rank_options = ["Top 3", "Top 5", "Top 10", "Top 20", "Top 50", "All"]
            default_idx = 1  # Default to "Top 5"
            selected_rank = st.radio("Position Range", rank_options, index=default_idx, horizontal=True)
            
            # Handle "All" option differently
            if selected_rank == "All":
                position_filtered_df = filtered_df
            else:
                top_rank = int(selected_rank.split(" ")[1])
                position_filtered_df = filtered_df[filtered_df['Position'] <= top_rank]
            
            if not position_filtered_df.empty:
                fig = px.histogram(
                    position_filtered_df, 
                    x='Position',
                    title=f'Position Distribution ({selected_rank})',
                    nbins=min(20, int(position_filtered_df['Position'].max())),
                    color_discrete_sequence=['#3366CC'],
                    opacity=0.8
                )
                
                fig.update_layout(
                    xaxis_title="Position",
                    yaxis_title="Count",
                    bargap=0.1,
                    xaxis={'categoryorder': 'total ascending'}
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No data available for position range: {selected_rank}")
        
        # Top domains chart
        if 'domain' in filtered_df.columns and 'Position' in filtered_df.columns and not filtered_df.empty:
            st.subheader("Top Domains by Average Position")
            
            # Domain rank selector
            domain_rank_options = ["Top 3", "Top 5", "Top 10", "Top 20"]
            default_domain_idx = 1  # Default to "Top 5"
            selected_domain_rank = st.radio("Domain Range", domain_rank_options, index=default_domain_idx, horizontal=True, key="domain_rank")
            domain_rank = int(selected_domain_rank.split(" ")[1])
            
            # Calculate domain metrics
            domain_positions = filtered_df.groupby('domain').agg(
                avg_position=('Position', 'mean'),
                count=('Position', 'count')
            ).reset_index()
            
            # Only include domains with sufficient data
            min_entries = 3  # Minimum number of entries required
            domain_positions = domain_positions[domain_positions['count'] >= min_entries]
            
            if not domain_positions.empty:
                # Sort by average position (ascending is better)
                domain_positions = domain_positions.sort_values('avg_position')
                
                fig = px.bar(
                    domain_positions.head(domain_rank), 
                    x='domain', 
                    y='avg_position',
                    title=f'Top {domain_rank} Domains by Average Position',
                    labels={'domain': 'Domain', 'avg_position': 'Average Position'},
                    color='avg_position',
                    color_continuous_scale='RdYlGn_r',
                    text='count'
                )
                
                fig.update_layout(
                    xaxis_title="Domain",
                    yaxis_title="Average Position",
                    yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                    xaxis_tickangle=-45
                )
                
                fig.update_traces(texttemplate='%{text} entries', textposition='outside')
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Not enough domain data to display rankings")
        
        # Display keyword and domain tables
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top Keywords by Volume")
            if 'Keyword' in filtered_df.columns and 'Results' in filtered_df.columns and not filtered_df.empty:
                keyword_volume = filtered_df.groupby('Keyword')['Results'].nunique().reset_index()
                keyword_volume = keyword_volume.sort_values('Results', ascending=False)
                
                if not keyword_volume.empty:
                    keyword_volume.columns = ['Keyword', 'Number of URLs']
                    st.dataframe(keyword_volume.head(10), use_container_width=True)
                else:
                    st.info("No keyword volume data available")
            else:
                st.info("Keyword or URL data not available")
        
        with col2:
            st.subheader("Top Domains by Frequency")
            if 'domain' in filtered_df.columns and not filtered_df.empty:
                domain_freq = filtered_df['domain'].value_counts().reset_index()
                
                if not domain_freq.empty:
                    domain_freq.columns = ['Domain', 'Count']
                    st.dataframe(domain_freq.head(10), use_container_width=True)
                else:
                    st.info("No domain frequency data available")
            else:
                st.info("Domain data not available")
    
    # Keyword Analysis Tab
    with tabs[1]:
        st.header("Keyword Analysis")
        
        # Keyword selector
        if 'Keyword' in df.columns:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                keywords = sorted(df['Keyword'].unique().tolist())
                selected_keyword = st.selectbox("Select Keyword", ["-- Select a keyword --"] + keywords, key="keyword_analysis")
            
            with col2:
                keyword_date_range = st.date_input(
                    "Date Range for Keyword",
                    value=(datetime.datetime.now() - datetime.timedelta(days=30), datetime.datetime.now()),
                    format="YYYY-MM-DD",
                    key="keyword_date_range"
                )
            
            with col3:
                domain_filter = st.text_input("Domain Filter (optional)", placeholder="e.g., example.com")
            
            if selected_keyword != "-- Select a keyword --":
                # Filter data for selected keyword
                keyword_df = df[df['Keyword'] == selected_keyword]
                
                if keyword_df.empty:
                    st.warning(f"No data found for keyword '{selected_keyword}'")
                else:
                    # Apply date filter if selected
                    if len(keyword_date_range) == 2:
                        date_filter = {'start': keyword_date_range[0], 'end': keyword_date_range[1]}
                        keyword_df = apply_date_filter(keyword_df, date_filter)
                    
                    # Apply domain filter if provided
                    if domain_filter:
                        keyword_df = apply_domain_filter(keyword_df, domain_filter)
                    
                    # Show data summary
                    st.subheader(f"Data for: {selected_keyword}")
                    
                    summary_cols = st.columns(3)
                    summary_cols[0].metric("Total URLs", keyword_df['Results'].nunique() if 'Results' in keyword_df.columns else 0)
                    summary_cols[1].metric("Total Domains", keyword_df['domain'].nunique() if 'domain' in keyword_df.columns else 0)
                    
                    # Calculate average position
                    if 'Position' in keyword_df.columns and not keyword_df.empty:
                        avg_position = keyword_df['Position'].mean()
                        summary_cols[2].metric("Average Position", f"{avg_position:.1f}")
                    
                    # Available dates for this keyword
                    if 'date' in keyword_df.columns:
                        dates = sorted(keyword_df['date'].dropna().unique())
                        date_strings = [d.strftime('%Y-%m-%d') if isinstance(d, datetime.date) else str(d).split(' ')[0] for d in dates]
                        
                        st.subheader("Available Dates for Selected Keyword")
                        if date_strings:
                            st.write(", ".join(date_strings))
                        else:
                            st.info("No dates available for this keyword with the current filters")
                    
                    # Domain performance for this keyword
                    if 'domain' in keyword_df.columns and 'Position' in keyword_df.columns and not keyword_df.empty:
                        st.subheader("Domain Performance for this Keyword")
                        
                        # Rank selector for the chart
                        domain_rank_options = ["Top 3", "Top 5", "Top 10", "Top 20"]
                        default_domain_idx = 1  # Default to "Top 5"
                        selected_keyword_rank = st.radio("Show", domain_rank_options, index=default_domain_idx, horizontal=True, key="keyword_domain_rank")
                        top_rank = int(selected_keyword_rank.split(" ")[1])
                        
                        domain_positions = keyword_df.groupby('domain')['Position'].agg(['mean', 'min', 'max', 'count']).reset_index()
                        
                        # Only include domains with sufficient data
                        domain_positions = domain_positions[domain_positions['count'] >= 2]
                        domain_positions = domain_positions.sort_values('mean')
                        
                        if not domain_positions.empty:
                            # Chart
                            fig = px.bar(
                                domain_positions.head(top_rank), 
                                x='domain', 
                                y='mean',
                                error_y=domain_positions.head(top_rank)['count'],
                                title=f'Top {top_rank} Domains for "{selected_keyword}"',
                                labels={'domain': 'Domain', 'mean': 'Average Position'},
                                color='mean',
                                color_continuous_scale='RdYlGn_r',
                                text='count'
                            )
                            
                            fig.update_layout(
                                xaxis_title="Domain",
                                yaxis_title="Average Position",
                                yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                                xaxis_tickangle=-45
                            )
                            
                            fig.update_traces(texttemplate='%{text} entries', textposition='outside')
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Table
                            st.subheader("Domain Rankings")
                            st.dataframe(domain_positions.rename(columns={
                                'mean': 'Avg Position',
                                'min': 'Best Position',
                                'max': 'Worst Position',
                                'count': 'Count'
                            }), use_container_width=True)
                            
                            # Trend over time chart (if we have date data)
                            if 'date' in keyword_df.columns and len(domain_positions) > 0:
                                st.subheader("Position Trend Over Time")
                                
                                # Get top domains
                                top_domains = domain_positions.head(top_rank)['domain'].tolist()
                                
                                # Filter data for these domains
                                trend_data = keyword_df[keyword_df['domain'].isin(top_domains)]
                                
                                if not trend_data.empty:
                                    # Group by date and domain, calculate average position
                                    trend_daily = trend_data.groupby(['date', 'domain'])['Position'].mean().reset_index()
                                    
                                    # Create trend chart
                                    fig = px.line(
                                        trend_daily,
                                        x='date',
                                        y='Position',
                                        color='domain',
                                        title=f'Position Trend Over Time for "{selected_keyword}"',
                                        labels={'date': 'Date', 'Position': 'Position', 'domain': 'Domain'},
                                        markers=True
                                    )
                                    
                                    fig.update_layout(
                                        xaxis_title="Date",
                                        yaxis_title="Position",
                                        yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                                        legend_title="Domain"
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("No domain performance data available for this keyword")
            else:
                st.info("Please select a keyword to analyze")
        else:
            st.warning("Keyword column not found in data")
    
    # Domain Analysis Tab
    with tabs[2]:
        st.header("Domain Analysis")
        
        # Domain selector
        col1, col2, col3 = st.columns(3)
        
        with col1:
            domain_input = st.text_input("Enter Domain", placeholder="e.g., example.com")
        
        with col2:
            domain_date_range = st.date_input(
                "Date Range for Domain",
                value=(datetime.datetime.now() - datetime.timedelta(days=30), datetime.datetime.now()),
                format="YYYY-MM-DD",
                key="domain_date_range"
            )
        
        with col3:
            position_cols = st.columns(2)
            with position_cols[0]:
                domain_position_min = st.number_input("Min Position", min_value=1, value=1, key="domain_min_pos")
            with position_cols[1]:
                domain_position_max = st.number_input("Max Position", min_value=1, value=100, key="domain_max_pos")
        
        analyze_domain = st.button("Analyze Domain")
        
        if domain_input and analyze_domain:
            # Filter data for selected domain
            domain_df = df[df['domain'] == domain_input]
            
            if domain_df.empty:
                st.warning(f"No data found for domain '{domain_input}'")
            else:
                # Apply date filter if selected
                if len(domain_date_range) == 2:
                    date_filter = {'start': domain_date_range[0], 'end': domain_date_range[1]}
                    domain_df = apply_date_filter(domain_df, date_filter)
                
                # Apply position filter
                domain_df = apply_position_filter(domain_df, domain_position_min, domain_position_max)
                
                # Show domain summary
                st.subheader(f"Analysis for: {domain_input}")
                
                summary_cols = st.columns(4)
                summary_cols[0].metric("Total Keywords", domain_df['Keyword'].nunique() if 'Keyword' in domain_df.columns else 0)
                summary_cols[1].metric("Total URLs", domain_df['Results'].nunique() if 'Results' in domain_df.columns else 0)
                
                # Calculate position metrics
                if 'Position' in domain_df.columns and not domain_df.empty:
                    avg_position = domain_df['Position'].mean()
                    best_position = domain_df['Position'].min()
                    summary_cols[2].metric("Average Position", f"{avg_position:.1f}")
                    summary_cols[3].metric("Best Position", f"{best_position:.0f}")
                
                # Keyword performance for this domain
                if 'Keyword' in domain_df.columns and 'Position' in domain_df.columns and not domain_df.empty:
                    # Rank selector for the chart
                    keyword_rank_options = ["Top 3", "Top 5", "Top 10", "Top 20"]
                    default_keyword_idx = 1  # Default to "Top 5"
                    selected_domain_keyword_rank = st.radio("Show", keyword_rank_options, index=default_keyword_idx, horizontal=True, key="domain_keyword_rank")
                    top_rank = int(selected_domain_keyword_rank.split(" ")[1])
                    
                    keyword_perf = domain_df.groupby('Keyword')['Position'].agg(['mean', 'min', 'max', 'count']).reset_index()
                    keyword_perf = keyword_perf.sort_values('mean')
                    
                    if not keyword_perf.empty:
                        st.subheader("Keyword Performance for this Domain")
                        
                        # Chart
                        fig = px.bar(
                            keyword_perf.head(top_rank), 
                            x='Keyword', 
                            y='mean',
                            title=f'Top {top_rank} Keywords for "{domain_input}"',
                            labels={'Keyword': 'Keyword', 'mean': 'Average Position'},
                            color='mean',
                            color_continuous_scale='RdYlGn_r',
                            text='count'
                        )
                        
                        fig.update_layout(
                            xaxis_title="Keyword",
                            yaxis_title="Average Position",
                            yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                            xaxis_tickangle=-45  # Rotate x-axis labels for better readability
                        )
                        
                        fig.update_traces(texttemplate='%{text} entries', textposition='outside')
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Table
                        st.subheader("Keyword Rankings")
                        st.dataframe(keyword_perf.rename(columns={
                            'mean': 'Avg Position',
                            'min': 'Best Position',
                            'max': 'Worst Position',
                            'count': 'Count'
                        }), use_container_width=True)
                        
                        # Position distribution
                        st.subheader("Position Distribution")
                        
                        fig = px.histogram(
                            domain_df,
                            x='Position',
                            nbins=20,
                            title=f'Position Distribution for "{domain_input}"',
                            color_discrete_sequence=['#3366CC'],
                            opacity=0.8
                        )
                        
                        fig.update_layout(
                            xaxis_title="Position",
                            yaxis_title="Count",
                            bargap=0.1
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Trend over time chart (if we have date data)
                        if 'date' in domain_df.columns and len(keyword_perf) > 0:
                            st.subheader("Position Trend Over Time")
                            
                            # Get top keywords
                            top_keywords = keyword_perf.head(top_rank)['Keyword'].tolist()
                            
                            # Filter data for these keywords
                            trend_data = domain_df[domain_df['Keyword'].isin(top_keywords)]
                            
                            if not trend_data.empty:
                                # Group by date and keyword, calculate average position
                                trend_daily = trend_data.groupby(['date', 'Keyword'])['Position'].mean().reset_index()
                                
                                # Create trend chart
                                fig = px.line(
                                    trend_daily,
                                    x='date',
                                    y='Position',
                                    color='Keyword',
                                    title=f'Position Trend Over Time for "{domain_input}"',
                                    labels={'date': 'Date', 'Position': 'Position', 'Keyword': 'Keyword'},
                                    markers=True
                                )
                                
                                fig.update_layout(
                                    xaxis_title="Date",
                                    yaxis_title="Position",
                                    yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                                    legend_title="Keyword"
                                )
                                st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No keyword performance data available for this domain")
                else:
                    st.warning("Required data columns missing or no data found for this domain")
    
    # URL Comparison Tab
    with tabs[3]:
        st.header("URL Comparison")
        
        # URL selector
        if 'Results' in df.columns:
            urls = sorted(df['Results'].unique().tolist())
            selected_urls = st.multiselect("Select URLs to Compare", urls)
            
            # Date filter
            url_compare_date_range = st.date_input(
                "Date Range for URL Comparison",
                value=(datetime.datetime.now() - datetime.timedelta(days=30), datetime.datetime.now()),
                format="YYYY-MM-DD",
                key="url_compare_date_range"
            )
            
            compare_urls = st.button("Compare URLs")
            
            if selected_urls and compare_urls:
                # Filter data for selected URLs
                url_df = df[df['Results'].isin(selected_urls)]
                
                # Apply date filter if selected
                if len(url_compare_date_range) == 2:
                    date_filter = {'start': url_compare_date_range[0], 'end': url_compare_date_range[1]}
                    url_df = apply_date_filter(url_df, date_filter)
                
                if url_df.empty:
                    st.warning("No data found for the selected URLs with the current filters")
                else:
                    # Prepare URL performance data
                    url_data = []
                    for url in selected_urls:
                        url_subset = url_df[url_df['Results'] == url]
                        
                        if not url_subset.empty and 'Position' in url_subset.columns:
                            url_data.append({
                                'url': url,
                                'domain': get_domain(url),
                                'avg_position': url_subset['Position'].mean(),
                                'best_position': url_subset['Position'].min(),
                                'worst_position': url_subset['Position'].max(),
                                'keywords_count': url_subset['Keyword'].nunique() if 'Keyword' in url_subset.columns else 0,
                                'data_points': len(url_subset)
                            })
                    
                    # Sort by average position
                    url_data = sorted(url_data, key=lambda x: x['avg_position'])
                    url_df_summary = pd.DataFrame(url_data)
                    
                    # URL comparison chart
                    if not url_df_summary.empty:
                        st.subheader("URL Position Comparison")
                        
                        fig = px.bar(
                            url_df_summary,
                            x='url',
                            y='avg_position',
                            error_y=[(d['worst_position'] - d['avg_position']) for d in url_data],
                            title='URL Position Comparison',
                            labels={'url': 'URL', 'avg_position': 'Average Position'},
                            color='avg_position',
                            color_continuous_scale='RdYlGn_r',
                            text='keywords_count'
                        )
                        
                        fig.update_layout(
                            xaxis_title="URL",
                            yaxis_title="Average Position",
                            yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                            xaxis_tickangle=-45  # Rotate x-axis labels for better readability
                        )
                        
                        fig.update_traces(texttemplate='%{text} keywords', textposition='outside')
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # URL performance by keyword chart
                        if 'Keyword' in url_df.columns:
                            keyword_comparison_data = []
                            
                            # Get top keywords by frequency across these URLs
                            top_keywords = url_df['Keyword'].value_counts().head(5).index.tolist()
                            
                            # For each keyword, get position by URL
                            for keyword in top_keywords:
                                keyword_data = url_df[url_df['Keyword'] == keyword]
                                
                                for url in selected_urls:
                                    url_keyword_data = keyword_data[keyword_data['Results'] == url]
                                    
                                    if not url_keyword_data.empty:
                                        keyword_comparison_data.append({
                                            'keyword': keyword,
                                            'url': url,
                                            'position': url_keyword_data['Position'].mean(),
                                            'count': len(url_keyword_data)
                                        })
                            
                            if keyword_comparison_data:
                                st.subheader("URL Performance by Keyword")
                                
                                keyword_comparison_df = pd.DataFrame(keyword_comparison_data)
                                
                                fig = px.bar(
                                    keyword_comparison_df,
                                    x='keyword',
                                    y='position',
                                    color='url',
                                    barmode='group',
                                    title='URL Performance by Keyword',
                                    labels={'keyword': 'Keyword', 'position': 'Average Position', 'url': 'URL'},
                                    text='count'
                                )
                                
                                fig.update_layout(
                                    xaxis_title="Keyword",
                                    yaxis_title="Average Position",
                                    yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                                    legend_title="URL"
                                )
                                
                                fig.update_traces(texttemplate='%{text} entries', textposition='outside')
                                
                                st.plotly_chart(fig, use_container_width=True)
                        
                        # URL position trend over time
                        if 'date' in url_df.columns:
                            st.subheader("URL Position Trend Over Time")
                            
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
                                fig = px.line(
                                    all_trend_data,
                                    x='date',
                                    y='Position',
                                    color='url',
                                    title='URL Position Trend Over Time',
                                    labels={'date': 'Date', 'Position': 'Position', 'url': 'URL'},
                                    markers=True
                                )
                                
                                fig.update_layout(
                                    xaxis_title="Date",
                                    yaxis_title="Position",
                                    yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                                    legend_title="URL"
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        
                        # URL comparison table
                        st.subheader("URL Comparison Data")
                        st.dataframe(pd.DataFrame(url_data).rename(columns={
                            'url': 'URL',
                            'domain': 'Domain',
                            'avg_position': 'Avg Position',
                            'best_position': 'Best Position',
                            'worst_position': 'Worst Position',
                            'keywords_count': 'Keywords Count',
                            'data_points': 'Data Points'
                        }), use_container_width=True)
            else:
                st.info("Please select URLs to compare and click 'Compare URLs'")
        else:
            st.warning("URL column not found in data")
    
    # Time Comparison Tab (call the separate function)
    time_comparison_tab(df, tabs)

if __name__ == "__main__":
    main()
