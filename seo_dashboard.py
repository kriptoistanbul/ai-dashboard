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

# =========================
# NEW TIME COMPARISON LOGIC
# =========================
def time_comparison_logic(df: pd.DataFrame, keyword: str, start_date_str: str, end_date_str: str):
    """
    Mimics your Flask '/compare_over_time' logic:
      - Tries to detect relevant date/time columns (e.g. 'date/time', 'Time', 'F')
      - Matches dates exactly, then .contains() fallback
      - Picks earliest/latest if empty
      - Removes duplicates (same URL) from each date
      - Sorts by ascending Position
      - Calculates position-change text (improved, declined, new, dropped, etc.)
    Returns a dict: { success: True, start_urls: [...], end_urls: [...], position_changes: [...], etc. }
    """

    # 1) Decide which column is the "keyword" column: 'Filled keyword' or 'Keyword'
    if 'Filled keyword' in df.columns:
        keyword_col = 'Filled keyword'
    elif 'Keyword' in df.columns:
        keyword_col = 'Keyword'
    else:
        return {
            'error': "No 'Filled keyword' or 'Keyword' column found in DataFrame."
        }

    # 2) Filter by that keyword
    df_keyword = df[df[keyword_col] == keyword]
    if df_keyword.empty:
        return {'error': f'No rows found for keyword "{keyword}".'}

    # 3) Identify which column is our date/time column
    possible_date_cols = ['date/time', 'Time', 'F']
    date_col = None
    for c in possible_date_cols:
        if c in df_keyword.columns:
            date_col = c
            break

    if not date_col:
        return {
            'error': "No suitable date/time column found. Tried ['date/time', 'Time', 'F']."
        }

    # 4) Extract the date part (YYYY-MM-DD) from each row
    df_keyword['date_str_full'] = df_keyword[date_col].astype(str)
    # e.g., "Mon 2025-03-27 08:59:12" => "2025-03-27"
    df_keyword['date_part'] = df_keyword['date_str_full'].str.extract(r'(\d{4}-\d{2}-\d{2})')

    # 5) Sort the unique date parts
    unique_dates = sorted(df_keyword['date_part'].dropna().unique().tolist())

    # Attempt exact match for start/end date
    start_data = df_keyword[df_keyword['date_part'] == start_date_str].copy()
    end_data   = df_keyword[df_keyword['date_part'] == end_date_str].copy()

    # If empty, try .contains() fallback
    if start_data.empty and start_date_str:
        start_data = df_keyword[df_keyword['date_str_full'].str.contains(start_date_str, na=False)]
    if end_data.empty and end_date_str:
        end_data = df_keyword[df_keyword['date_str_full'].str.contains(end_date_str, na=False)]

    # If STILL empty, fallback to earliest & latest
    if start_data.empty and len(unique_dates) > 0:
        earliest = unique_dates[0]
        start_data = df_keyword[df_keyword['date_part'] == earliest]
    if end_data.empty and len(unique_dates) > 1:
        latest = unique_dates[-1]
        end_data = df_keyword[df_keyword['date_part'] == latest]

    # Remove duplicates by 'Results' to fix double positions
    if not start_data.empty:
        start_data = start_data.drop_duplicates(subset=['Results'])
    if not end_data.empty:
        end_data = end_data.drop_duplicates(subset=['Results'])

    # Sort each subset by ascending Position
    if 'Position' in start_data.columns:
        start_data.sort_values(by='Position', ascending=True, inplace=True)
    if 'Position' in end_data.columns:
        end_data.sort_values(by='Position', ascending=True, inplace=True)

    # Prepare final lists for Start & End
    start_urls = []
    end_urls   = []

    # Build a map from end_data so we can compute position_change for each start URL
    end_pos_map = {}
    if not end_data.empty and 'Results' in end_data.columns and 'Position' in end_data.columns:
        for _, row in end_data.iterrows():
            url_e = row['Results']
            pos_e = row['Position']
            if pd.notna(url_e) and pd.notna(pos_e):
                end_pos_map[url_e] = pos_e

    if not start_data.empty and 'Results' in start_data.columns and 'Position' in start_data.columns:
        for _, row in start_data.iterrows():
            url_s = row['Results']
            pos_s = row['Position']
            domain_s = urlparse(url_s).netloc if isinstance(url_s, str) else ''

            position_change_text = "N/A"
            if url_s in end_pos_map:
                diff = end_pos_map[url_s] - pos_s
                if diff < 0:
                    position_change_text = f"↑ {abs(diff)} (improved)"
                elif diff > 0:
                    position_change_text = f"↓ {diff} (declined)"
                else:
                    position_change_text = "No change"
            else:
                position_change_text = "Not in end data"

            start_urls.append({
                'url': url_s,
                'position': pos_s,
                'domain': domain_s,
                'position_change_text': position_change_text,
            })

    # Build a map from start_data to compute position_change for each end URL
    start_pos_map = {}
    if not start_data.empty and 'Results' in start_data.columns and 'Position' in start_data.columns:
        for _, row in start_data.iterrows():
            url_s = row['Results']
            pos_s = row['Position']
            if pd.notna(url_s) and pd.notna(pos_s):
                start_pos_map[url_s] = pos_s

    if not end_data.empty and 'Results' in end_data.columns and 'Position' in end_data.columns:
        for _, row in end_data.iterrows():
            url_e = row['Results']
            pos_e = row['Position']
            domain_e = urlparse(url_e).netloc if isinstance(url_e, str) else ''

            position_change_text = "N/A"
            if url_e in start_pos_map:
                diff = pos_e - start_pos_map[url_e]
                if diff < 0:
                    position_change_text = f"↑ {abs(diff)} (improved)"
                elif diff > 0:
                    position_change_text = f"↓ {diff} (declined)"
                else:
                    position_change_text = "No change"
            else:
                position_change_text = "New"

            end_urls.append({
                'url': url_e,
                'position': pos_e,
                'domain': domain_e,
                'position_change_text': position_change_text,
            })

    # Build a combined position_changes table
    # First gather all unique URLs from start & end
    all_urls = set(x['url'] for x in start_urls).union(set(x['url'] for x in end_urls))

    position_changes = []
    start_pos_map_for_changes = { x['url']: x['position'] for x in start_urls }
    end_pos_map_for_changes   = { x['url']: x['position'] for x in end_urls }

    for url_ in all_urls:
        sp = start_pos_map_for_changes.get(url_, None)
        ep = end_pos_map_for_changes.get(url_, None)
        domain_ = urlparse(url_).netloc if isinstance(url_, str) else ''
        if sp is None and ep is None:
            continue

        status = 'unchanged'
        change_text = 'No change'
        numeric_change = None

        if sp is not None and ep is not None:
            diff = ep - sp
            numeric_change = diff
            if diff < 0:
                status = 'improved'
                change_text = f"↑ {abs(diff)} (improved)"
            elif diff > 0:
                status = 'declined'
                change_text = f"↓ {diff} (declined)"
            else:
                status = 'unchanged'
                change_text = "No change"
        else:
            if sp is None:
                # New
                status = 'new'
                change_text = "New"
            else:
                # Dropped
                status = 'dropped'
                change_text = "Dropped"

        position_changes.append({
            'url': url_,
            'domain': domain_,
            'start_position': sp,
            'end_position': ep,
            'change_text': change_text,
            'status': status,
            'change': numeric_change,
        })

    # Sort position_changes in a similar “biggest changes first” style
    position_changes.sort(
        key=lambda x: (
            0 if x['status'] in ('improved','declined') else
            (1 if x['status'] in ('new','dropped') else 2),
            abs(x['change']) if x['change'] is not None else 0
        ),
        reverse=True
    )

    return {
        'success': True,
        'keyword': keyword,
        'start_urls': start_urls,
        'end_urls': end_urls,
        'position_changes': position_changes,
        'start_count': len(start_urls),
        'end_count': len(end_urls),
        'available_dates': unique_dates,
    }

# =====================================
# Original Streamlit code from your app
# =====================================

st.set_page_config(page_title="SEO Position Tracking Dashboard", layout="wide")
st.title("SEO Position Tracking Dashboard")

def get_domain(url):
    """Extract domain from URL."""
    try:
        return urlparse(url).netloc
    except (TypeError, ValueError):
        return None

def prepare_data(df):
    """Prepare data for analysis."""
    # Convert key columns to strings
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

def load_data():
    """
    Example: you can replace this with your own logic:
      e.g. reading from a local Excel file, or from a Google Sheet.
    Below is just an example stub.
    """
    # For demonstration, read from CSV or XLSX:
    # df = pd.read_csv("myfile.csv")
    # or:
    # df = pd.read_excel("myfile.xlsx")
    #
    # Just be sure to call prepare_data(df) at the end.
    #
    # Since your code references a Google sheet with ID, you might do:
    #
    #   sheet_id = "1Z8S-lJygDcuB3gs120E..."
    #   sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    #   df = pd.read_csv(sheet_url)
    #
    # Return the prepared DataFrame:
    # return prepare_data(df)

    st.warning("Replace `load_data()` with your own data-loading logic.")
    # For now, just return an empty DataFrame
    return pd.DataFrame()

def apply_date_filter(df, date_range):
    """Apply date range filter to DataFrame."""
    if not date_range or 'date' not in df.columns:
        return df

    try:
        start_date = pd.to_datetime(date_range['start'])
        end_date = pd.to_datetime(date_range['end'])
        return df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    except:
        return df

def apply_position_filter(df, position_min=None, position_max=None):
    """Apply position range filter to DataFrame."""
    if 'Position' not in df.columns:
        return df

    filtered_df = df.copy()
    if position_min is not None:
        filtered_df = filtered_df[filtered_df['Position'] >= position_min]
    if position_max is not None:
        filtered_df = filtered_df[filtered_df['Position'] <= position_max]
    return filtered_df

def apply_keyword_filter(df, keyword):
    """Apply keyword filter to DataFrame."""
    if not keyword or 'Keyword' not in df.columns:
        return df
    return df[df['Keyword'] == keyword]

def apply_domain_filter(df, domain):
    """Apply domain filter to DataFrame."""
    if not domain or 'domain' not in df.columns:
        return df
    return df[df['domain'] == domain]

def get_date_range(df):
    """Safely get date range from dataframe."""
    if 'date' not in df.columns or df['date'].isna().all():
        return ["N/A", "N/A"]

    valid_dates = df['date'].dropna()
    if len(valid_dates) == 0:
        return ["N/A", "N/A"]

    min_date = valid_dates.min()
    max_date = valid_dates.max()

    min_date_str = min_date.strftime('%Y-%m-%d') if isinstance(min_date, datetime.date) else str(min_date).split(' ')[0]
    max_date_str = max_date.strftime('%Y-%m-%d') if isinstance(max_date, datetime.date) else str(max_date).split(' ')[0]

    return [min_date_str, max_date_str]

# =======================
# Main Streamlit function
# =======================

def main():
    with st.spinner("Loading data..."):
        df = load_data()
        if df is not None and not df.empty:
            df = prepare_data(df)
        else:
            st.error("No data loaded. Check `load_data()` function.")
            return

    # Create tabs
    tabs = st.tabs(["Overview", "Keyword Analysis", "Domain Analysis", "URL Comparison", "Time Comparison"])

    # ---------------------------
    # Overview Tab
    # ---------------------------
    with tabs[0]:
        st.header("SEO Position Tracking Dashboard")

        # Filters
        with st.expander("Filters", expanded=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                date_range = st.date_input(
                    "Date Range",
                    value=(datetime.datetime.now() - datetime.timedelta(days=30), datetime.datetime.now()),
                    format="YYYY-MM-DD"
                )

            with col2:
                all_keywords = ["All Keywords"] + sorted(df['Keyword'].dropna().unique().tolist()) if 'Keyword' in df.columns else []
                keyword_filter = st.selectbox("Keyword Filter", all_keywords)

            with col3:
                pos_min = st.number_input("Min Position", min_value=1, value=1)
                pos_max = st.number_input("Max Position", min_value=1, value=100)

        # Apply filters
        filtered_df = df.copy()
        if len(date_range) == 2:
            date_filter = {'start': date_range[0], 'end': date_range[1]}
            filtered_df = apply_date_filter(filtered_df, date_filter)

        if keyword_filter and keyword_filter != "All Keywords":
            filtered_df = apply_keyword_filter(filtered_df, keyword_filter)

        filtered_df = apply_position_filter(filtered_df, pos_min, pos_max)

        # Summary
        st.subheader("Data Summary")
        c1, c2, c3, c4 = st.columns(4)
        summary = {
            'total_keywords': filtered_df['Keyword'].nunique() if 'Keyword' in filtered_df.columns else 0,
            'total_domains': filtered_df['domain'].nunique() if 'domain' in filtered_df.columns else 0,
            'total_urls': filtered_df['Results'].nunique() if 'Results' in filtered_df.columns else 0,
            'date_range': get_date_range(filtered_df)
        }
        c1.metric("Total Keywords", summary['total_keywords'])
        c2.metric("Total Domains", summary['total_domains'])
        c3.metric("Total URLs", summary['total_urls'])
        c4.metric("Date Range", f"{summary['date_range'][0]} to {summary['date_range'][1]}")

        # Position distribution chart
        if 'Position' in filtered_df.columns:
            st.subheader("Position Distribution")
            rank_choices = ["Top 3", "Top 5", "Top 10", "Top 20"]
            selected_rank = st.radio("Position Range", rank_choices, index=1, horizontal=True)
            top_rank = int(selected_rank.split()[1])

            fig_pos = px.histogram(
                filtered_df,
                x='Position',
                nbins=20,
                title="Overall Position Distribution"
            )
            fig_pos.update_layout(
                xaxis_title="Position",
                yaxis_title="Count",
                bargap=0.1
            )
            st.plotly_chart(fig_pos, use_container_width=True)

        # Domain distribution
        if 'domain' in filtered_df.columns and 'Position' in filtered_df.columns:
            st.subheader("Top Domains by Average Position")
            domain_choices = ["Top 3", "Top 5", "Top 10", "Top 20"]
            selected_domain_rank = st.radio("Domain Range", domain_choices, index=1, horizontal=True, key="domain_range")
            domain_rank = int(selected_domain_rank.split()[1])

            domain_positions = filtered_df.groupby('domain')['Position'].mean().reset_index()
            domain_positions = domain_positions.sort_values('Position')
            fig_dom = px.bar(
                domain_positions.head(domain_rank),
                x='domain',
                y='Position',
                title=f"Top {domain_rank} Domains by Average Position",
                color='Position',
                color_continuous_scale='RdYlGn_r'
            )
            fig_dom.update_layout(
                xaxis_title="Domain",
                yaxis_title="Average Position",
                yaxis_autorange='reversed'
            )
            st.plotly_chart(fig_dom, use_container_width=True)

        # Top Keywords & Domains by frequency
        cA, cB = st.columns(2)
        with cA:
            st.subheader("Top Keywords by Volume")
            if 'Keyword' in filtered_df.columns and 'Results' in filtered_df.columns:
                kv = filtered_df.groupby('Keyword')['Results'].nunique().reset_index().sort_values('Results', ascending=False)
                st.dataframe(kv.head(10), use_container_width=True)

        with cB:
            st.subheader("Top Domains by Frequency")
            if 'domain' in filtered_df.columns:
                dfreq = filtered_df['domain'].value_counts().reset_index()
                dfreq.columns = ['domain','count']
                st.dataframe(dfreq.head(10), use_container_width=True)

    # ---------------------------
    # Keyword Analysis Tab
    # ---------------------------
    with tabs[1]:
        st.header("Keyword Analysis")
        colKA1, colKA2, colKA3 = st.columns(3)

        with colKA1:
            if 'Keyword' in df.columns:
                all_kw = sorted(df['Keyword'].dropna().unique().tolist())
                selected_keyword = st.selectbox("Select Keyword", ["-- Select a keyword --"] + all_kw)
            else:
                selected_keyword = None

        with colKA2:
            keyword_date_range = st.date_input(
                "Date Range for Keyword",
                value=(datetime.datetime.now() - datetime.timedelta(days=30), datetime.datetime.now()),
                format="YYYY-MM-DD",
                key="keyword_date_range"
            )

        with colKA3:
            domain_filter = st.text_input("Domain Filter", placeholder="e.g., example.com")

        if selected_keyword and selected_keyword != "-- Select a keyword --":
            keyword_df = df[df['Keyword'] == selected_keyword].copy()

            # Filter by date
            if len(keyword_date_range) == 2:
                k_start, k_end = keyword_date_range
                date_filter = {'start': k_start, 'end': k_end}
                keyword_df = apply_date_filter(keyword_df, date_filter)
            # Filter by domain
            if domain_filter:
                keyword_df = keyword_df[keyword_df['domain'] == domain_filter]

            if keyword_df.empty:
                st.warning("No data for the selected keyword (and filters).")
            else:
                st.subheader(f"Domain Performance for '{selected_keyword}'")
                rank_options = ["Top 3", "Top 5", "Top 10", "Top 20"]
                sel_domain_rank = st.radio("Show", rank_options, index=1, horizontal=True, key="kw_domain_rank")
                top_rank_val = int(sel_domain_rank.split()[1])

                if 'domain' in keyword_df.columns and 'Position' in keyword_df.columns:
                    domain_positions = keyword_df.groupby('domain')['Position'].agg(['mean','min','max','count']).reset_index()
                    domain_positions = domain_positions.sort_values('mean')

                    fig_kw_dom = px.bar(
                        domain_positions.head(top_rank_val),
                        x='domain',
                        y='mean',
                        color='mean',
                        color_continuous_scale='RdYlGn_r',
                        title=f"Top {top_rank_val} Domains for '{selected_keyword}'"
                    )
                    fig_kw_dom.update_layout(
                        xaxis_title="Domain",
                        yaxis_title="Average Position",
                        yaxis_autorange='reversed'
                    )
                    st.plotly_chart(fig_kw_dom, use_container_width=True)

                    # Show table
                    st.dataframe(domain_positions.rename(columns={
                        'mean': 'Avg Position',
                        'min': 'Best Position',
                        'max': 'Worst Position',
                        'count': 'Count'
                    }), use_container_width=True)

                    # Trend over time
                    if 'date' in keyword_df.columns:
                        st.subheader("Position Trend Over Time")
                        top_domains_list = domain_positions.head(top_rank_val)['domain'].tolist()
                        trend_data = keyword_df[keyword_df['domain'].isin(top_domains_list)]
                        if not trend_data.empty:
                            trend_df = trend_data.groupby(['date','domain'])['Position'].mean().reset_index()
                            fig_kw_trend = px.line(
                                trend_df,
                                x='date',
                                y='Position',
                                color='domain',
                                title=f"Position Trend for '{selected_keyword}'"
                            )
                            fig_kw_trend.update_layout(
                                xaxis_title="Date",
                                yaxis_title="Position",
                                yaxis_autorange='reversed'
                            )
                            st.plotly_chart(fig_kw_trend, use_container_width=True)
                else:
                    st.info("No domain/position data for this keyword.")

    # ---------------------------
    # Domain Analysis Tab
    # ---------------------------
    with tabs[2]:
        st.header("Domain Analysis")
        cDA1, cDA2, cDA3 = st.columns(3)

        with cDA1:
            domain_input = st.text_input("Enter Domain", placeholder="example.com")
        with cDA2:
            domain_date_range = st.date_input(
                "Date Range for Domain",
                value=(datetime.datetime.now() - datetime.timedelta(days=30), datetime.datetime.now()),
                format="YYYY-MM-DD",
                key="domain_date_range"
            )
        with cDA3:
            posc1, posc2 = st.columns(2)
            with posc1:
                domain_pos_min = st.number_input("Min Pos", min_value=1, value=1, key="dom_min")
            with posc2:
                domain_pos_max = st.number_input("Max Pos", min_value=1, value=100, key="dom_max")

        analyze_btn = st.button("Analyze Domain")
        if domain_input and analyze_btn:
            domain_df = df[df['domain'] == domain_input].copy()
            if domain_df.empty:
                st.warning(f"No data found for domain '{domain_input}'.")
            else:
                if len(domain_date_range) == 2:
                    d_start, d_end = domain_date_range
                    date_filter = {'start': d_start, 'end': d_end}
                    domain_df = apply_date_filter(domain_df, date_filter)

                domain_df = apply_position_filter(domain_df, domain_pos_min, domain_pos_max)
                if domain_df.empty:
                    st.warning("No data after date/position filtering.")
                else:
                    st.subheader(f"Keyword Performance for Domain '{domain_input}'")
                    kw_rank_opts = ["Top 3", "Top 5", "Top 10", "Top 20"]
                    sel_kw_rank = st.radio("Show", kw_rank_opts, index=1, horizontal=True, key="dom_kw_rank")
                    top_k = int(sel_kw_rank.split()[1])

                    if 'Keyword' in domain_df.columns and 'Position' in domain_df.columns:
                        kperf = domain_df.groupby('Keyword')['Position'].agg(['mean','min','max','count']).reset_index()
                        kperf = kperf.sort_values('mean')
                        fig_dom_kw = px.bar(
                            kperf.head(top_k),
                            x='Keyword',
                            y='mean',
                            color='mean',
                            color_continuous_scale='RdYlGn_r',
                            title=f"Top {top_k} Keywords for '{domain_input}'"
                        )
                        fig_dom_kw.update_layout(
                            xaxis_title="Keyword",
                            yaxis_title="Average Position",
                            yaxis_autorange='reversed',
                            xaxis_tickangle=-45
                        )
                        st.plotly_chart(fig_dom_kw, use_container_width=True)

                        st.dataframe(kperf.rename(columns={
                            'mean': 'Avg Position',
                            'min': 'Best',
                            'max': 'Worst',
                            'count': 'Count'
                        }), use_container_width=True)

                        # Trend over time
                        if 'date' in domain_df.columns:
                            st.subheader("Position Trend Over Time")
                            top_kws = kperf.head(top_k)['Keyword'].tolist()
                            trend_dom = domain_df[domain_df['Keyword'].isin(top_kws)]
                            if not trend_dom.empty:
                                td = trend_dom.groupby(['date','Keyword'])['Position'].mean().reset_index()
                                fig_dom_trend = px.line(
                                    td,
                                    x='date',
                                    y='Position',
                                    color='Keyword',
                                    title=f"Position Trend for '{domain_input}'"
                                )
                                fig_dom_trend.update_layout(
                                    xaxis_title="Date",
                                    yaxis_title="Position",
                                    yaxis_autorange='reversed'
                                )
                                st.plotly_chart(fig_dom_trend, use_container_width=True)
                    else:
                        st.info("No 'Keyword' or 'Position' columns found for this domain.")

    # ---------------------------
    # URL Comparison Tab
    # ---------------------------
    with tabs[3]:
        st.header("URL Comparison")
        if 'Results' in df.columns:
            urls_all = sorted(df['Results'].dropna().unique().tolist())
            selected_urls = st.multiselect("Select URLs to Compare", urls_all)
            url_compare_date_range = st.date_input(
                "Date Range for URL Comparison",
                value=(datetime.datetime.now() - datetime.timedelta(days=30), datetime.datetime.now()),
                format="YYYY-MM-DD",
                key="url_compare_date_range"
            )

            compare_btn = st.button("Compare URLs")
            if compare_btn and selected_urls:
                url_df = df[df['Results'].isin(selected_urls)].copy()
                if len(url_compare_date_range) == 2:
                    ustart, uend = url_compare_date_range
                    ufilter = {'start': ustart, 'end': uend}
                    url_df = apply_date_filter(url_df, ufilter)

                if url_df.empty:
                    st.warning("No data found for the selected URLs/date range.")
                else:
                    # Summaries
                    url_data = []
                    for u in selected_urls:
                        subset = url_df[url_df['Results'] == u]
                        if not subset.empty and 'Position' in subset.columns:
                            url_data.append({
                                'url': u,
                                'avg_position': subset['Position'].mean(),
                                'best_position': subset['Position'].min(),
                                'worst_position': subset['Position'].max(),
                                'keywords_count': subset['Keyword'].nunique() if 'Keyword' in subset.columns else 0
                            })
                    url_data = sorted(url_data, key=lambda x: x['avg_position'])
                    url_df_summary = pd.DataFrame(url_data)

                    if not url_df_summary.empty:
                        st.subheader("URL Position Comparison")
                        fig_url_comp = px.bar(
                            url_df_summary,
                            x='url',
                            y='avg_position',
                            error_y=[(d['worst_position'] - d['avg_position']) for d in url_data],
                            title='URL Position Comparison',
                            color='avg_position',
                            color_continuous_scale='RdYlGn_r'
                        )
                        fig_url_comp.update_layout(
                            xaxis_title="URL",
                            yaxis_title="Average Position",
                            yaxis_autorange='reversed',
                            xaxis_tickangle=-45
                        )
                        st.plotly_chart(fig_url_comp, use_container_width=True)

                        # Keyword performance
                        if 'Keyword' in url_df.columns and 'Position' in url_df.columns:
                            st.subheader("URL Performance by Keyword")
                            keyword_cmp_data = []
                            top_keywords_5 = url_df['Keyword'].value_counts().head(5).index.tolist()
                            for kw in top_keywords_5:
                                kw_df = url_df[url_df['Keyword'] == kw]
                                for u in selected_urls:
                                    each_ = kw_df[kw_df['Results'] == u]
                                    if not each_.empty:
                                        keyword_cmp_data.append({
                                            'keyword': kw,
                                            'url': u,
                                            'position': each_['Position'].mean()
                                        })
                            if keyword_cmp_data:
                                kw_cmp_df = pd.DataFrame(keyword_cmp_data)
                                fig_kw_cmp = px.bar(
                                    kw_cmp_df,
                                    x='keyword',
                                    y='position',
                                    color='url',
                                    barmode='group',
                                    title='URL Performance by Keyword'
                                )
                                fig_kw_cmp.update_layout(
                                    xaxis_title="Keyword",
                                    yaxis_title="Avg Position",
                                    yaxis_autorange='reversed'
                                )
                                st.plotly_chart(fig_kw_cmp, use_container_width=True)

                        # Trend over time
                        if 'date' in url_df.columns:
                            st.subheader("URL Position Trend Over Time")
                            trend_list = []
                            for u in selected_urls:
                                sub_ = url_df[url_df['Results'] == u]
                                if not sub_.empty and 'Position' in sub_.columns:
                                    d_agg = sub_.groupby('date')['Position'].mean().reset_index()
                                    d_agg['url'] = u
                                    trend_list.append(d_agg)
                            if trend_list:
                                all_trends = pd.concat(trend_list)
                                fig_url_trend = px.line(
                                    all_trends,
                                    x='date',
                                    y='Position',
                                    color='url',
                                    title='URL Position Trend Over Time'
                                )
                                fig_url_trend.update_layout(
                                    xaxis_title="Date",
                                    yaxis_title="Position",
                                    yaxis_autorange='reversed'
                                )
                                st.plotly_chart(fig_url_trend, use_container_width=True)

                        # Table
                        st.subheader("URL Comparison Data")
                        st.dataframe(url_df_summary.rename(columns={
                            'avg_position': 'Avg Position',
                            'best_position': 'Best',
                            'worst_position': 'Worst',
                            'keywords_count': 'Keywords'
                        }), use_container_width=True)

        else:
            st.warning("No 'Results' column found in data.")

    # ---------------------------
    # TIME COMPARISON TAB
    # ---------------------------
    with tabs[4]:
        st.header("Time Comparison")

        # 1) Pick a keyword
        if 'Keyword' in df.columns:
            keywords_all = sorted(df['Keyword'].dropna().unique().tolist())
            time_compare_keyword = st.selectbox("Select Keyword for Time Comparison",
                                               ["-- Select a keyword --"] + keywords_all)

            if time_compare_keyword != "-- Select a keyword --":
                # 2) We also need user to pick start_date_str and end_date_str
                #    You can show them all unique date parts or just let them type it in, etc.
                st.write("Below, pick or type your start & end dates in YYYY-MM-DD (or partial) format. "
                         "We will replicate the fallback logic used in your Flask code.")
                colTC1, colTC2 = st.columns(2)
                with colTC1:
                    start_date_str = st.text_input("Start Date (YYYY-MM-DD)", "")
                with colTC2:
                    end_date_str   = st.text_input("End Date (YYYY-MM-DD)", "")

                compare_time_btn = st.button("Compare Over Time")
                if compare_time_btn and start_date_str and end_date_str:
                    # 3) Call the advanced logic
                    results = time_comparison_logic(df, time_compare_keyword, start_date_str, end_date_str)
                    if 'error' in results:
                        st.error(results['error'])
                    else:
                        st.subheader("Comparison Summary")
                        c1, c2, c3 = st.columns(3)
                        c1.info(f"**Keyword**: {results['keyword']}")
                        c2.info(f"**Start Date**: {start_date_str}  ({results['start_count']} URLs)")
                        c3.info(f"**End Date**: {end_date_str}    ({results['end_count']} URLs)")

                        # Show Start/End tables
                        left_, right_ = st.columns(2)
                        with left_:
                            st.subheader("Start Date URLs")
                            st.dataframe(pd.DataFrame(results['start_urls']), use_container_width=True)
                        with right_:
                            st.subheader("End Date URLs")
                            st.dataframe(pd.DataFrame(results['end_urls']), use_container_width=True)

                        # Show changes
                        st.subheader("Position Changes Analysis")
                        pc_df = pd.DataFrame(results['position_changes'])
                        # Example styling
                        def highlight_status(row):
                            if row['status'] == 'improved':
                                return ['background-color: lightgreen']*len(row)
                            elif row['status'] == 'declined':
                                return ['background-color: lightsalmon']*len(row)
                            elif row['status'] == 'new':
                                return ['background-color: lightblue']*len(row)
                            elif row['status'] == 'dropped':
                                return ['background-color: #FFCCCB']*len(row)
                            return ['background-color: white']*len(row)
                        st.dataframe(
                            pc_df.style.apply(highlight_status, axis=1),
                            use_container_width=True
                        )
        else:
            st.warning("No 'Keyword' column in data. Cannot perform time comparison.")

if __name__ == "__main__":
    main()
