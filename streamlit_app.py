import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from urllib.parse import urlparse
import datetime
import io

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

# Main app logic
def main():
    # Display loading spinner while fetching data
    with st.spinner("Loading data from Google Sheet..."):
        df = load_data()
    
    if df is not None:
        # Dashboard tabs
        tabs = st.tabs(["Overview", "Keyword Analysis", "Domain Analysis", "URL Comparison"])
        
        # Overview Tab
        with tabs[0]:
            st.header("SEO Position Tracking Dashboard")
            
            # Summary cards
            st.subheader("Data Summary")
            col1, col2, col3, col4 = st.columns(4)
            
            summary = {
                'total_keywords': df['Keyword'].nunique() if 'Keyword' in df.columns else 0,
                'total_domains': df['domain'].nunique() if 'domain' in df.columns else 0,
                'total_urls': df['Results'].nunique() if 'Results' in df.columns else 0,
                'date_range': get_date_range(df)
            }
            
            col1.metric("Total Keywords", summary['total_keywords'])
            col2.metric("Total Domains", summary['total_domains'])
            col3.metric("Total URLs", summary['total_urls'])
            col4.metric("Date Range", f"{summary['date_range'][0]} to {summary['date_range'][1]}")
            
            # Position distribution chart
            if 'Position' in df.columns:
                st.subheader("Position Distribution")
                fig = px.histogram(
                    df, 
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
            if 'domain' in df.columns and 'Position' in df.columns:
                st.subheader("Top Domains by Average Position")
                
                domain_positions = df.groupby('domain')['Position'].mean().reset_index()
                domain_positions = domain_positions.sort_values('Position')
                
                fig = px.bar(
                    domain_positions.head(5), 
                    x='domain', 
                    y='Position',
                    title='Top 5 Domains by Average Position',
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
                if 'Keyword' in df.columns and 'Results' in df.columns:
                    keyword_volume = df.groupby('Keyword')['Results'].nunique().reset_index()
                    keyword_volume = keyword_volume.sort_values('Results', ascending=False)
                    st.dataframe(keyword_volume.head(10), use_container_width=True)
            
            with col2:
                st.subheader("Top Domains by Frequency")
                if 'domain' in df.columns:
                    domain_freq = df['domain'].value_counts().reset_index()
                    domain_freq.columns = ['domain', 'count']
                    st.dataframe(domain_freq.head(10), use_container_width=True)
        
        # Keyword Analysis Tab
        with tabs[1]:
            st.header("Keyword Analysis")
            
            # Keyword selector
            if 'Keyword' in df.columns:
                keywords = sorted(df['Keyword'].unique().tolist())
                selected_keyword = st.selectbox("Select Keyword", ["-- Select a keyword --"] + keywords)
                
                if selected_keyword != "-- Select a keyword --":
                    # Filter data for selected keyword
                    keyword_df = df[df['Keyword'] == selected_keyword]
                    
                    # Available dates for this keyword
                    if 'date' in keyword_df.columns:
                        dates = sorted(keyword_df['date'].dropna().unique())
                        date_strings = [d.strftime('%Y-%m-%d') if isinstance(d, datetime.date) else str(d).split(' ')[0] for d in dates]
                        
                        st.subheader("Available Dates")
                        st.write(", ".join(date_strings))
                    
                    # Domain performance for this keyword
                    if 'domain' in keyword_df.columns and 'Position' in keyword_df.columns:
                        st.subheader("Domain Performance for this Keyword")
                        domain_positions = keyword_df.groupby('domain')['Position'].agg(['mean', 'min', 'max', 'count']).reset_index()
                        domain_positions = domain_positions.sort_values('mean')
                        
                        # Chart
                        fig = px.bar(
                            domain_positions.head(5), 
                            x='domain', 
                            y='mean',
                            error_y='count',
                            title=f'Top 5 Domains for "{selected_keyword}"',
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
                        st.dataframe(domain_positions.rename(columns={
                            'mean': 'Avg Position',
                            'min': 'Best Position',
                            'max': 'Worst Position',
                            'count': 'Count'
                        }))
            else:
                st.warning("Keyword column not found in data")
        
        # Domain Analysis Tab
        with tabs[2]:
            st.header("Domain Analysis")
            
            # Domain selector
            if 'domain' in df.columns:
                domains = sorted(df['domain'].unique().tolist())
                selected_domain = st.selectbox("Select Domain", ["-- Select a domain --"] + domains)
                
                if selected_domain != "-- Select a domain --":
                    # Filter data for selected domain
                    domain_df = df[df['domain'] == selected_domain]
                    
                    # Keyword performance for this domain
                    if 'Keyword' in domain_df.columns and 'Position' in domain_df.columns:
                        st.subheader("Keyword Performance for this Domain")
                        keyword_perf = domain_df.groupby('Keyword')['Position'].agg(['mean', 'min', 'max', 'count']).reset_index()
                        keyword_perf = keyword_perf.sort_values('mean')
                        
                        # Chart
                        fig = px.bar(
                            keyword_perf.head(5), 
                            x='Keyword', 
                            y='mean',
                            title=f'Top 5 Keywords for "{selected_domain}"',
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
                        st.dataframe(keyword_perf.rename(columns={
                            'mean': 'Avg Position',
                            'min': 'Best Position',
                            'max': 'Worst Position',
                            'count': 'Count'
                        }))
            else:
                st.warning("Domain column not found in data")
        
        # URL Comparison Tab
        with tabs[3]:
            st.header("URL Comparison")
            
            # URL selector (multi-select)
            if 'Results' in df.columns:
                urls = sorted(df['Results'].unique().tolist())
                selected_urls = st.multiselect("Select URLs to Compare", urls)
                
                if selected_urls:
                    # Filter data for selected URLs
                    url_df = df[df['Results'].isin(selected_urls)]
                    
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
                    url_df = pd.DataFrame(url_data)
                    
                    # Chart
                    if not url_df.empty:
                        st.subheader("URL Position Comparison")
                        fig = px.bar(
                            url_df,
                            x='url',
                            y='avg_position',
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
                        
                        # Table
                        st.dataframe(url_df.rename(columns={
                            'url': 'URL',
                            'avg_position': 'Avg Position',
                            'best_position': 'Best Position',
                            'worst_position': 'Worst Position',
                            'keywords_count': 'Keywords Count'
                        }))
            else:
                st.warning("URL column not found in data")

if __name__ == "__main__":
    main()
