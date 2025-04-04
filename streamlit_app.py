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

# Set page title
st.set_page_config(page_title="SEO Position Tracking Dashboard", layout="wide")
st.title("SEO Position Tracking Dashboard")

# Function to get domain from URL
def get_domain(url):
    """Extract domain from URL"""
    try:
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
    # Convert Google Sheet URL to export URL (CSV format)
    sheet_id = "1Z8S-lJygDcuB3gs120EoXLVMtZzgp7HQrjtNkkOqJQs"
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
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
    except:
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

# Main app logic
def main():
    # Display loading spinner while fetching data
    with st.spinner("Loading data from Google Sheet..."):
        df = load_data()
    
    if df is not None:
        # Dashboard tabs
        tabs = st.tabs(["Overview", "Keyword Analysis", "Domain Analysis", "URL Comparison", "Time Comparison"])
        
        # Overview Tab
        with tabs[0]:
            st.header("SEO Position Tracking Dashboard")
            
            # Filter section
            with st.expander("Filters", expanded=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    date_range = st.date_input(
                        "Date Range",
                        value=(datetime.datetime.now() - datetime.timedelta(days=30), datetime.datetime.now()),
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
            
            col1.metric("Total Keywords", summary['total_keywords'])
            col2.metric("Total Domains", summary['total_domains'])
            col3.metric("Total URLs", summary['total_urls'])
            col4.metric("Date Range", f"{summary['date_range'][0]} to {summary['date_range'][1]}")
            
            # Position distribution chart
            if 'Position' in filtered_df.columns:
                st.subheader("Position Distribution")
                
                # Rank selector
                rank_options = ["Top 3", "Top 5", "Top 10", "Top 20"]
                default_idx = 1  # Default to "Top 5"
                selected_rank = st.radio("Position Range", rank_options, index=default_idx, horizontal=True)
                top_rank = int(selected_rank.split(" ")[1])
                
                fig = px.histogram(
                    filtered_df, 
                    x='Position',
                    title='Overall Position Distribution',
                    nbins=20,
                    color_discrete_sequence=['#3366CC']
                )
                
                fig.update_layout(
                    xaxis_title="Position",
                    yaxis_title="Count",
                    bargap=0.1
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Top domains chart
            if 'domain' in filtered_df.columns and 'Position' in filtered_df.columns:
                st.subheader("Top Domains by Average Position")
                
                # Domain rank selector
                domain_rank_options = ["Top 3", "Top 5", "Top 10", "Top 20"]
                default_domain_idx = 1  # Default to "Top 5"
                selected_domain_rank = st.radio("Domain Range", domain_rank_options, index=default_domain_idx, horizontal=True, key="domain_rank")
                domain_rank = int(selected_domain_rank.split(" ")[1])
                
                domain_positions = filtered_df.groupby('domain')['Position'].mean().reset_index()
                domain_positions = domain_positions.sort_values('Position')
                
                fig = px.bar(
                    domain_positions.head(domain_rank), 
                    x='domain', 
                    y='Position',
                    title=f'Top {domain_rank} Domains by Average Position',
                    labels={'domain': 'Domain', 'Position': 'Average Position'},
                    color='Position',
                    color_continuous_scale='RdYlGn_r'
                )
                
                fig.update_layout(
                    xaxis_title="Domain",
                    yaxis_title="Average Position",
                    yaxis_autorange='reversed'  # Lower positions (better rankings) at the top
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Display tables
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Top Keywords by Volume")
                if 'Keyword' in filtered_df.columns and 'Results' in filtered_df.columns:
                    keyword_volume = filtered_df.groupby('Keyword')['Results'].nunique().reset_index()
                    keyword_volume = keyword_volume.sort_values('Results', ascending=False)
                    st.dataframe(keyword_volume.head(10), use_container_width=True)
            
            with col2:
                st.subheader("Top Domains by Frequency")
                if 'domain' in filtered_df.columns:
                    domain_freq = filtered_df['domain'].value_counts().reset_index()
                    domain_freq.columns = ['domain', 'count']
                    st.dataframe(domain_freq.head(10), use_container_width=True)
        
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
                    domain_filter = st.text_input("Domain Filter", placeholder="e.g., example.com")
                
                if selected_keyword != "-- Select a keyword --":
                    # Filter data for selected keyword
                    keyword_df = df[df['Keyword'] == selected_keyword]
                    
                    # Apply date filter if selected
                    if len(keyword_date_range) == 2:
                        date_filter = {'start': keyword_date_range[0], 'end': keyword_date_range[1]}
                        keyword_df = apply_date_filter(keyword_df, date_filter)
                    
                    # Apply domain filter if provided
                    if domain_filter:
                        keyword_df = apply_domain_filter(keyword_df, domain_filter)
                    
                    # Available dates for this keyword
                    if 'date' in keyword_df.columns:
                        dates = sorted(keyword_df['date'].dropna().unique())
                        date_strings = [d.strftime('%Y-%m-%d') if isinstance(d, datetime.date) else str(d).split(' ')[0] for d in dates]
                        
                        st.subheader("Available Dates")
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
                        domain_positions = domain_positions.sort_values('mean')
                        
                        if not domain_positions.empty:
                            # Chart
                            fig = px.bar(
                                domain_positions.head(top_rank), 
                                x='domain', 
                                y='mean',
                                error_y='count',
                                title=f'Top {top_rank} Domains for "{selected_keyword}"',
                                labels={'domain': 'Domain', 'mean': 'Average Position'},
                                color='mean',
                                color_continuous_scale='RdYlGn_r'
                            )
                            
                            fig.update_layout(
                                xaxis_title="Domain",
                                yaxis_title="Average Position",
                                yaxis_autorange='reversed'  # Lower positions (better rankings) at the top
                            )
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
                                        labels={'date': 'Date', 'Position': 'Position', 'domain': 'Domain'}
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
                                color_continuous_scale='RdYlGn_r'
                            )
                            
                            fig.update_layout(
                                xaxis_title="Keyword",
                                yaxis_title="Average Position",
                                yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                                xaxis_tickangle=-45  # Rotate x-axis labels for better readability
                            )
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Table
                            st.subheader("Keyword Rankings")
                            st.dataframe(keyword_perf.rename(columns={
                                'mean': 'Avg Position',
                                'min': 'Best Position',
                                'max': 'Worst Position',
                                'count': 'Count'
                            }), use_container_width=True)
                            
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
                                        labels={'date': 'Date', 'Position': 'Position', 'Keyword': 'Keyword'}
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
                                    'avg_position': url_subset['Position'].mean(),
                                    'best_position': url_subset['Position'].min(),
                                    'worst_position': url_subset['Position'].max(),
                                    'keywords_count': url_subset['Keyword'].nunique() if 'Keyword' in url_subset.columns else 0
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
                                color_continuous_scale='RdYlGn_r'
                            )
                            
                            fig.update_layout(
                                xaxis_title="URL",
                                yaxis_title="Average Position",
                                yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                                xaxis_tickangle=-45  # Rotate x-axis labels for better readability
                            )
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # URL performance by keyword chart
                            if 'Keyword' in url_df.columns:
                                keyword_comparison_data = []
                                
                                # Get top 5 keywords by frequency across these URLs
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
                                                'position': url_keyword_data['Position'].mean()
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
                                        labels={'keyword': 'Keyword', 'position': 'Average Position', 'url': 'URL'}
                                    )
                                    
                                    fig.update_layout(
                                        xaxis_title="Keyword",
                                        yaxis_title="Average Position",
                                        yaxis_autorange='reversed',  # Lower positions (better rankings) at the top
                                        legend_title="URL"
                                    )
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
                                        labels={'date': 'Date', 'Position': 'Position', 'url': 'URL'}
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
                                'avg_position': 'Avg Position',
                                'best_position': 'Best Position',
                                'worst_position': 'Worst Position',
                                'keywords_count': 'Keywords Count'
                            }), use_container_width=True)
            else:
                st.warning("URL column not found in data")
        
        # Time Comparison Tab
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
                    keyword_df = df[df['Keyword'] == time_compare_keyword]
                    
                    if not keyword_df.empty:
                        # Extract dates from either 'date' or 'Time' column
                        date_column = 'date' if 'date' in keyword_df.columns else 'Time' if 'Time' in keyword_df.columns else None
                        
                        if date_column:
                            # Create a list of available dates
                            available_dates = keyword_df[date_column].dropna().unique()
                            
                            # Format dates for display in selectbox
                            date_strings = []
                            for d in available_dates:
                                try:
                                    if isinstance(d, datetime.datetime) or isinstance(d, datetime.date):
                                        date_strings.append(d.strftime('%Y-%m-%d'))
                                    elif isinstance(d, str):
                                        # Try to parse string as date
                                        date_strings.append(pd.to_datetime(d).strftime('%Y-%m-%d'))
                                    else:
                                        date_strings.append(str(d))
                                except:
                                    # If can't format, use string representation
                                    date_strings.append(str(d))
                            
                            date_strings = sorted(list(set(date_strings)))  # Remove duplicates and sort
                            
                            # Show a debug option to help with date issues
                            show_debug = st.checkbox("Debug date information")
                            if show_debug:
                                st.write("Date column information:")
                                st.write(f"Using column: {date_column}")
                                st.write(f"Found {len(available_dates)} unique dates")
                                st.write("Sample dates:", list(available_dates)[:5])
                                st.write("Formatted dates:", date_strings[:5])
                            
                            if date_strings:
                                # Date selectors
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
                                    # Use flexible date matching
                                    # Filter by matching the string format of dates
                                    start_data = keyword_df[keyword_df[date_column].astype(str).str.startswith(start_date.split(' ')[0])].copy()
                                    end_data = keyword_df[keyword_df[date_column].astype(str).str.startswith(end_date.split(' ')[0])].copy()
                                    
                                    # Debug info
                                    if show_debug:
                                        st.write(f"Filtering for start date '{start_date}' found {len(start_data)} rows")
                                        st.write(f"Filtering for end date '{end_date}' found {len(end_data)} rows")
                                    
                                    # Check if data is available for both dates
                                    if start_data.empty or end_data.empty:
                                        st.warning(f"No data found for dates: {start_date} / {end_date}")
                                        
                                        # Offer suggestions
                                        st.info("Available dates format might be different. Try using the Debug checkbox above to see date formats in your data.")
                                    else:
                                        # Show the comparison summary
                                        st.subheader("Comparison Summary")
                                        
                                        info_cols = st.columns(3)
                                        info_cols[0].info(f"**Keyword:** {time_compare_keyword}")
                                        info_cols[1].info(f"**Start Date:** {start_date} ({len(start_data)} URLs)")
                                        info_cols[2].info(f"**End Date:** {end_date} ({len(end_data)} URLs)")
                                        
                                        # Sort data by position (ascending)
                                        start_data_sorted = start_data.sort_values(by='Position', ascending=True)
                                        end_data_sorted = end_data.sort_values(by='Position', ascending=True)
                                        
                                        # Extract URLs and positions
                                        start_list = start_data_sorted[['Results', 'Position']].values.tolist()
                                        end_list = end_data_sorted[['Results', 'Position']].values.tolist()
                                        
                                        # Build the position changes data
                                        all_urls = set()
                                        start_pos_map = {}
                                        end_pos_map = {}
                                        
                                        for url, pos in start_list:
                                            all_urls.add(url)
                                            start_pos_map[url] = pos
                                        
                                        for url, pos in end_list:
                                            all_urls.add(url)
                                            end_pos_map[url] = pos
                                        
                                        # Build the position changes table
                                        position_changes = []
                                        for url in all_urls:
                                            start_pos = start_pos_map.get(url, None)
                                            end_pos = end_pos_map.get(url, None)
                                            
                                            if start_pos is not None or end_pos is not None:
                                                row = {
                                                    'url': url,
                                                    'domain': get_domain(url),
                                                    'start_position': start_pos,
                                                    'end_position': end_pos
                                                }
                                                
                                                if start_pos is not None and end_pos is not None:
                                                    change = end_pos - start_pos
                                                    if change < 0:
                                                        row['change_text'] = f"↑ {abs(change)} (improved)"
                                                        row['status'] = 'improved'
                                                    elif change > 0:
                                                        row['change_text'] = f"↓ {change} (declined)"
                                                        row['status'] = 'declined'
                                                    else:
                                                        row['change_text'] = "No change"
                                                        row['status'] = 'unchanged'
                                                else:
                                                    if start_pos is None:
                                                        row['change_text'] = "New"
                                                        row['status'] = 'new'
                                                    else:
                                                        row['change_text'] = "Dropped"
                                                        row['status'] = 'dropped'
                                                
                                                position_changes.append(row)
                                        
                                        # Sort by status and position change
                                        position_changes.sort(key=lambda x: (
                                            0 if x['status'] == 'improved' else
                                            1 if x['status'] == 'declined' else
                                            2 if x['status'] in ('new', 'dropped') else 3
                                        ))
                                        
                                        # Display results
                                        col1, col2 = st.columns(2)
                                        
                                        with col1:
                                            st.subheader("Start Date Rankings")
                                            start_df = pd.DataFrame([
                                                {'Rank': i+1, 'URL': url, 'Position': pos}
                                                for i, (url, pos) in enumerate(start_list)
                                            ])
                                            st.dataframe(start_df, use_container_width=True)
                                        
                                        with col2:
                                            st.subheader("End Date Rankings")
                                            end_df = pd.DataFrame([
                                                {'Rank': i+1, 'URL': url, 'Position': pos}
                                                for i, (url, pos) in enumerate(end_list)
                                            ])
                                            st.dataframe(end_df, use_container_width=True)
                                        
                                        st.subheader("Position Changes")
                                        changes_df = pd.DataFrame(position_changes)
                                        
                                        # Function to color rows based on status
                                        def highlight_status(val):
                                            if val == 'improved':
                                                return 'background-color: lightgreen'
                                            elif val == 'declined':
                                                return 'background-color: lightsalmon'
                                            elif val == 'new':
                                                return 'background-color: lightblue'
                                            elif val == 'dropped':
                                                return 'background-color: #FFCCCB'  # Light red
                                            return ''
                                        
                                        # Apply styling and display
                                        styled_df = changes_df.style.applymap(
                                            highlight_status, subset=['status']
                                        )
                                        
                                        st.dataframe(styled_df, use_container_width=True)
                                        
                                        # Visualization of position changes
                                        if len(position_changes) > 0:
                                            st.subheader("Position Change Visualization")
                                            
                                            # Prepare data for visualization
                                            viz_data = []
                                            for row in position_changes:
                                                if 'status' in row and row['status'] in ('improved', 'declined'):
                                                    viz_data.append({
                                                        'url': row['url'],
                                                        'change': row['end_position'] - row['start_position'] 
                                                            if row['start_position'] is not None and row['end_position'] is not None 
                                                            else 0
                                                    })
                                            
                                            if viz_data:
                                                viz_df = pd.DataFrame(viz_data)
                                                
                                                fig = px.bar(
                                                    viz_df,
                                                    x='url',
                                                    y='change',
                                                    color='change',
                                                    color_continuous_scale='RdBu_r',  # Blue for negative (improvement), Red for positive (decline)
                                                    title=f"Position Changes ({start_date} to {end_date})",
                                                )
                                                
                                                fig.update_layout(
                                                    xaxis_title="URL",
                                                    yaxis_title="Position Change (negative is better)",
                                                    xaxis_tickangle=-45
                                                )
                                                
                                                # Add a horizontal line at y=0
                                                fig.add_shape(
                                                    type="line",
                                                    x0=-0.5,
                                                    y0=0,
                                                    x1=len(viz_data) - 0.5,
                                                    y1=0,
                                                    line=dict(color="black", width=1, dash="dash")
                                                )
                                                
                                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.warning(f"No dates found for keyword '{time_compare_keyword}'")
                        else:
                            st.warning("No date column found in the data")
            else:
                st.warning("Keyword column not found in data")

if __name__ == "__main__":
    main()
