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
        tabs = st.tabs(["Overview", "Keyword Analysis", "Domain Analysis", "URL Comparison", "Time Comparison"])
        
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
                
        # Time Comparison Tab
        with tabs[4]:
            st.header("Time Comparison")
            
            # Keyword selector
            if 'Keyword' in df.columns:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    keywords = sorted(df['Keyword'].unique().tolist())
                    selected_keyword = st.selectbox("Select Keyword for Time Comparison", 
                                                  ["-- Select a keyword --"] + keywords, 
                                                  key="time_comparison_keyword")
                
                # Get available dates for the selected keyword
                if selected_keyword != "-- Select a keyword --":
                    keyword_df = df[df['Keyword'] == selected_keyword]
                    
                    if not keyword_df.empty:
                        # Debug: Show what date column contains
                        if st.checkbox("Debug: Show Date Information"):
                            st.write("Date column information:")
                            if 'date' in keyword_df.columns:
                                st.write(f"Date column exists with {keyword_df['date'].nunique()} unique values")
                                st.write("Sample dates:", keyword_df['date'].dropna().unique()[:5])
                            elif 'Time' in keyword_df.columns:
                                st.write(f"Time column exists with {keyword_df['Time'].nunique()} unique values")
                                st.write("Sample times:", keyword_df['Time'].dropna().unique()[:5])
                            else:
                                st.write("No date or time columns found")
                        
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
                                if start_date != "-- Select start date --" and end_date != "-- Select end date --":
                                    if st.button("Compare Over Time"):
                                        # Use more flexible date comparison
                                        # Filter by matching the string format of dates
                                        start_data = keyword_df[keyword_df[date_column].astype(str).str.startswith(start_date.split(' ')[0])].copy()
                                        end_data = keyword_df[keyword_df[date_column].astype(str).str.startswith(end_date.split(' ')[0])].copy()
                                        
                                        # Debug info
                                        if st.checkbox("Show detailed debug info"):
                                            st.write(f"Filtering for start date '{start_date}' found {len(start_data)} rows")
                                            st.write(f"Filtering for end date '{end_date}' found {len(end_data)} rows")
                                        
                                        # Check if data is available for both dates
                                        if start_data.empty or end_data.empty:
                                            st.warning(f"No data found for dates: {start_date} / {end_date}")
                                            
                                            # Offer suggestions
                                            st.info("Available dates format might be different. Try using the Debug checkbox above to see date formats in your data.")
                                        else:
                                            # Sort data by position (ascending)
                                            start_data_sorted = start_data.sort_values(by='Position', ascending=True)
                                            end_data_sorted = end_data.sort_values(by='Position', ascending=True)
                                            
                                            # Extract URLs and positions
                                            start_list = start_data_sorted[['Results', 'Position']].values.tolist()
                                            end_list = end_data_sorted[['Results', 'Position']].values.tolist()
                                            
                                            # Build comparison table
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
                                                
                                                # Calculate position change
                                                change_str = ""
                                                if isinstance(pos_start, (int, float)) and isinstance(pos_end, (int, float)):
                                                    diff = pos_end - pos_start
                                                    change_str = f"{diff:+.0f}"  # Format as +X or -X
                                                
                                                rank_table.append({
                                                    "rank": i + 1,
                                                    "url_start": url_start or "",
                                                    "url_end": url_end or "",
                                                    "change": change_str
                                                })
                                            
                                            # Display the comparison table
                                            st.subheader(f"Comparison: {start_date} vs {end_date}")
                                            rank_df = pd.DataFrame(rank_table)
                                            rank_df.columns = ["Rank", "URL (Start Date)", "URL (End Date)", "Position Change"]
                                            
                                            # Apply color to position changes
                                            def highlight_changes(val):
                                                if isinstance(val, str) and val.startswith('+'):
                                                    return 'color: red'  # Worse position (higher number)
                                                elif isinstance(val, str) and val.startswith('-'):
                                                    return 'color: green'  # Better position (lower number)
                                                return ''
                                            
                                            st.dataframe(rank_df.style.applymap(highlight_changes, subset=['Position Change']), 
                                                        use_container_width=True)
                                            
                                            # Add a visualization
                                            if len(rank_table) > 0:
                                                st.subheader("Top 10 Position Changes")
                                                # Create a bar chart for position changes
                                                changes_data = []
                                                
                                                for row in rank_table[:10]:  # Take top 10 positions
                                                    if row["change"] and row["url_start"] and row["url_end"]:
                                                        try:
                                                            changes_data.append({
                                                                "rank": row["rank"],
                                                                "url": row["url_start"],
                                                                "change": float(row["change"])
                                                            })
                                                        except:
                                                            pass
                                                
                                                if changes_data:
                                                    changes_df = pd.DataFrame(changes_data)
                                                    fig = px.bar(
                                                        changes_df,
                                                        x="rank",
                                                        y="change",
                                                        color="change",
                                                        color_continuous_scale="RdYlGn_r",
                                                        labels={"rank": "Position Rank", "change": "Position Change", "url": "URL"},
                                                        title=f"Position Changes for Top 10 URLs ({start_date} to {end_date})",
                                                        hover_data=["url"]
                                                    )
                                                    
                                                    fig.update_layout(
                                                        yaxis_title="Position Change (negative is better)",
                                                        xaxis_title="Position Rank"
                                                    )
                                                    
                                                    # Add a horizontal line at y=0
                                                    fig.add_shape(
                                                        type="line",
                                                        x0=0.5,
                                                        y0=0,
                                                        x1=10.5,
                                                        y1=0,
                                                        line=dict(color="black", width=1, dash="dash")
                                                    )
                                                    
                                                    st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.warning(f"No dates found for keyword '{selected_keyword}'")
                        else:
                            st.warning("No date or time column found in the data")
            else:
                st.warning("Keyword column not found in data")

if __name__ == "__main__":
    main()
