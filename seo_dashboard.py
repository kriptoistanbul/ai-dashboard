##############################
# streamlit_app.py
##############################

import streamlit as st
import pandas as pd
import plotly.express as px
from urllib.parse import urlparse
import datetime
import re
import numpy as np


#####################################
# 1) HELPER: parse domain from URL
#####################################
def get_domain(url: str):
    try:
        return urlparse(url).netloc
    except:
        return None

#####################################
# 2) HELPER: prepare data
#####################################
def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Replicates your local code's advanced fallback approach:
      - If single column, parse special patterns.
      - Convert columns to string
      - Extract domain
      - Convert 'Time' -> datetime
      - Add a 'Time_str' => 'YYYY-MM-DD'
      - Add 'date' => actual date object
    """
    # If only 1 column, attempt special parse
    if len(df.columns) == 1:
        col0 = df.columns[0]
        # Attempt your special "URL + Position + Keyword" parse
        data_list = []
        for _, row in df.iterrows():
            text = str(row[col0])
            pattern = r'(https?://[^\s]+)(\d+)([\w\s]+)(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[\s\d:-]+'
            matches = re.findall(pattern, text)
            for match in matches:
                url_ = match[0]
                pos_ = int(match[1])
                kw_  = match[2]
                # date/time fallback might be the rest
                # This is a big assumption – modify if needed
                data_list.append({
                    'Results': url_,
                    'Position': pos_,
                    'Keyword': kw_,
                    'Time': match[3]  # not necessarily correct
                })
        if data_list:
            df = pd.DataFrame(data_list)

    # Convert 'Results'/'Keyword' to str
    for col in ['Results','Keyword']:
        if col in df.columns:
            df[col] = df[col].astype(str)

    # If we have 'Results', derive domain
    if 'Results' in df.columns:
        df['domain'] = df['Results'].apply(get_domain)
    else:
        df['domain'] = None

    # If we have 'Time' or 'date/time', convert to datetime => create 'Time_str'
    for c in ['Time','date/time']:
        if c in df.columns:
            # Force parse
            df[c] = pd.to_datetime(df[c], errors='coerce')
            # Add string
            df[f"{c}_str"] = df[c].dt.strftime('%Y-%m-%d')

    # We also create a simpler 'date' col if 'Time' exists
    if 'Time' in df.columns:
        df['date'] = df['Time'].dt.date

    return df

#####################################
# 3) TIME COMPARISON LOGIC
#####################################
def advanced_time_compare(df: pd.DataFrame, keyword: str, start_date_str: str, end_date_str: str):
    """
    This merges your "compare_over_time" fallback approach from the local code:
      1) Filter by keyword (either 'Filled keyword' or 'Keyword')
      2) Attempt exact match on 'Time_str' or 'date/time_str'
      3) If empty, do .contains() fallback
      4) If still empty => pick earliest or latest
      5) Remove duplicates
      6) Sort, build "start_urls" and "end_urls" with position changes
    """
    # 1) Figure out if we have a "Filled keyword" or "Keyword"
    kw_col = None
    if 'Filled keyword' in df.columns:
        kw_col = 'Filled keyword'
    elif 'Keyword' in df.columns:
        kw_col = 'Keyword'
    else:
        return {"error":"No keyword column found."}

    # 2) Filter by that keyword
    df_kw = df[df[kw_col] == keyword].copy()
    if df_kw.empty:
        return {"error": f"No data found for keyword '{keyword}'"}

    # 3) Which time-str col to use?
    # We'll prefer 'Time_str' if we have it, else 'date/time_str'
    # If neither exists, we can't do time comparison
    time_col_str = None
    for candidate in ['Time_str','date/time_str']:
        if candidate in df_kw.columns:
            time_col_str = candidate
            break
    if not time_col_str:
        return {"error": "No recognized time string column found (Time_str or date/time_str)."}

    # Sort the unique time values
    unique_timevals = sorted(df_kw[time_col_str].dropna().unique().tolist())

    # 4) Attempt direct match
    start_data = df_kw[df_kw[time_col_str] == start_date_str].copy()
    end_data   = df_kw[df_kw[time_col_str] == end_date_str].copy()

    # If no match, attempt .contains()
    if start_data.empty:
        start_data = df_kw[df_kw[time_col_str].str.contains(start_date_str, na=False)]
    if end_data.empty:
        end_data = df_kw[df_kw[time_col_str].str.contains(end_date_str, na=False)]

    # If STILL empty, pick earliest & latest from unique_timevals
    if start_data.empty and len(unique_timevals)>0:
        earliest = unique_timevals[0]
        start_data = df_kw[df_kw[time_col_str] == earliest]
    if end_data.empty and len(unique_timevals)>1:
        latest = unique_timevals[-1]
        end_data = df_kw[df_kw[time_col_str] == latest]

    # Remove duplicates
    if not start_data.empty and 'Results' in start_data.columns:
        start_data.drop_duplicates(subset=['Results'], keep='first', inplace=True)
    if not end_data.empty and 'Results' in end_data.columns:
        end_data.drop_duplicates(subset=['Results'], keep='first', inplace=True)

    # Sort each by ascending position
    if not start_data.empty and 'Position' in start_data.columns:
        start_data = start_data.sort_values(by='Position', ascending=True)
    if not end_data.empty and 'Position' in end_data.columns:
        end_data = end_data.sort_values(by='Position', ascending=True)

    # Build start_urls
    start_urls = []
    end_positions = {}
    if not end_data.empty and 'Results' in end_data.columns and 'Position' in end_data.columns:
        for _, row in end_data.iterrows():
            end_positions[row['Results']] = row['Position']

    if not start_data.empty and 'Results' in start_data.columns and 'Position' in start_data.columns:
        for _, row in start_data.iterrows():
            url_ = row['Results']
            pos_ = row['Position']
            dom_ = row['domain'] if 'domain' in row else ''
            pos_change_text = "N/A"
            pos_change = None
            if url_ in end_positions:
                diff = end_positions[url_] - pos_
                pos_change = diff
                if diff < 0:
                    pos_change_text = f"↑ {abs(diff)} (improved)"
                elif diff > 0:
                    pos_change_text = f"↓ {diff} (declined)"
                else:
                    pos_change_text = "No change"
            else:
                pos_change_text = "Not in end data"

            start_urls.append({
                'url': url_,
                'position': pos_,
                'domain': dom_,
                'position_change': pos_change,
                'position_change_text': pos_change_text
            })

    # Build end_urls
    start_positions = {}
    if not start_data.empty:
        for _, row in start_data.iterrows():
            start_positions[row['Results']] = row['Position']

    end_urls = []
    if not end_data.empty and 'Results' in end_data.columns and 'Position' in end_data.columns:
        for _, row in end_data.iterrows():
            url_ = row['Results']
            pos_ = row['Position']
            dom_ = row['domain'] if 'domain' in row else ''
            pos_change_text = "N/A"
            pos_change = None
            if url_ in start_positions:
                diff = pos_ - start_positions[url_]
                pos_change = diff
                if diff < 0:
                    pos_change_text = f"↑ {abs(diff)} (improved)"
                elif diff > 0:
                    pos_change_text = f"↓ {diff} (declined)"
                else:
                    pos_change_text = "No change"
            else:
                pos_change_text = "New"

            end_urls.append({
                'url': url_,
                'position': pos_,
                'domain': dom_,
                'position_change': pos_change,
                'position_change_text': pos_change_text
            })

    # Combine position-changes across all URLs
    all_urls = set(x['url'] for x in start_urls).union(set(x['url'] for x in end_urls))
    position_changes = []
    start_map = {x['url']: x['position'] for x in start_urls}
    end_map   = {x['url']: x['position'] for x in end_urls}

    for u in all_urls:
        sp = start_map.get(u, None)
        ep = end_map.get(u, None)
        domain_ = get_domain(u)
        if sp is None and ep is None:
            continue
        change_data = {
            'url': u,
            'domain': domain_,
            'start_position': sp,
            'end_position': ep,
        }
        # compute difference
        if sp is not None and ep is not None:
            diff = ep - sp
            if diff < 0:
                change_data['change_text'] = f"↑ {abs(diff)} (improved)"
                change_data['status'] = 'improved'
            elif diff > 0:
                change_data['change_text'] = f"↓ {diff} (declined)"
                change_data['status'] = 'declined'
            else:
                change_data['change_text'] = "No change"
                change_data['status'] = 'unchanged'
            change_data['change'] = diff
        else:
            change_data['change'] = None
            if sp is None:
                change_data['change_text'] = "New"
                change_data['status'] = 'new'
            else:
                change_data['change_text'] = "Dropped"
                change_data['status'] = 'dropped'

        position_changes.append(change_data)

    # Sort changes with your custom approach:
    # improved/declined first, then new/dropped, then unchanged
    # within that, sort by absolute change desc
    def sortkey(x):
        # status priority
        if x['status'] in ('improved','declined'):
            rankstat = 0
        elif x['status'] in ('new','dropped'):
            rankstat = 1
        else:
            rankstat = 2
        # abs change
        c = abs(x['change']) if x['change'] is not None else 0
        return (rankstat, c)

    position_changes.sort(key=sortkey, reverse=True)

    return {
        'success': True,
        'keyword': keyword,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'start_urls': start_urls,
        'end_urls': end_urls,
        'position_changes': position_changes,
        'start_count': len(start_urls),
        'end_count': len(end_urls),
        'available_dates': unique_timevals
    }

#####################################
# 4) LOAD DATA
#####################################
@st.cache_data
def load_data() -> pd.DataFrame:
    """
    Provide your actual data loading logic here.
    E.g. read from 'temp_upload.xlsx' or from CSV or from Google Sheet.
    For demonstration, we'll load an empty DF or you can place real code:
    """
    # Example:
    # df = pd.read_excel('temp_upload.xlsx')
    # df = prepare_data(df)
    # return df

    st.warning("Replace `load_data()` with real logic (Excel/CSV/Google sheet).")
    return pd.DataFrame()

#####################################
# 5) MAIN STREAMLIT APP
#####################################
def main():
    st.set_page_config(page_title="SEO Position Tracking", layout="wide")
    st.title("SEO Position Tracking Dashboard (Optimized)")

    # 1) Load the data once
    with st.spinner("Loading data..."):
        df = load_data()
    if df.empty:
        st.warning("No data loaded. Please adjust your `load_data()` function.")
        return
    # 2) Prepare data
    df = prepare_data(df)

    # TABS
    tab_overview, tab_timecompare = st.tabs(["Overview", "Time Comparison"])

    ############################################
    # TAB: Overview
    ############################################
    with tab_overview:
        st.header("Overview")
        st.write("Basic overview or your other tabs/logic here.")
        # e.g. show a sample
        st.write(df.head())

    ############################################
    # TAB: Time Comparison
    ############################################
    with tab_timecompare:
        st.header("Time Comparison")

        # Let user pick a "Keyword" from the data
        # We unify 'Filled keyword' or 'Keyword'
        possible_keywords = []
        if 'Filled keyword' in df.columns:
            possible_keywords = sorted(df['Filled keyword'].dropna().unique().tolist())
        elif 'Keyword' in df.columns:
            possible_keywords = sorted(df['Keyword'].dropna().unique().tolist())

        chosen_kw = st.selectbox("Select Keyword", ["--select--"] + possible_keywords)
        start_date_str = st.text_input("Start Date (YYYY-MM-DD or partial e.g. '03-27')", "")
        end_date_str   = st.text_input("End Date (YYYY-MM-DD or partial e.g. '03-29')", "")

        if st.button("Compare Over Time"):
            if chosen_kw == "--select--" or not start_date_str or not end_date_str:
                st.error("Please pick a keyword and fill start/end date.")
            else:
                # run advanced_time_compare
                results = advanced_time_compare(df, chosen_kw, start_date_str, end_date_str)
                if 'error' in results:
                    st.error(results['error'])
                elif not results.get('success'):
                    st.error("Unknown error in compare function.")
                else:
                    st.subheader("Comparison Summary")
                    c1, c2, c3 = st.columns(3)
                    c1.info(f"**Keyword**: {results['keyword']}")
                    c2.info(f"**Start Date**: {results['start_date']}  (Rows={results['start_count']})")
                    c3.info(f"**End Date**: {results['end_date']}  (Rows={results['end_count']})")

                    # Show Start Table
                    left, right = st.columns(2)
                    with left:
                        st.markdown("**Start Date URLs** (sorted ascending by position)")
                        if results['start_count'] == 0:
                            st.info("No data for start date.")
                        else:
                            sdf = pd.DataFrame(results['start_urls'])
                            st.dataframe(sdf, use_container_width=True)
                    with right:
                        st.markdown("**End Date URLs** (sorted ascending by position)")
                        if results['end_count'] == 0:
                            st.info("No data for end date.")
                        else:
                            edf = pd.DataFrame(results['end_urls'])
                            st.dataframe(edf, use_container_width=True)

                    # Show changes
                    st.subheader("Position Changes (merged for all URLs found at start or end)")
                    pcdf = pd.DataFrame(results['position_changes'])
                    if pcdf.empty:
                        st.info("No position changes to show.")
                    else:
                        # color rows by status
                        def color_status(row):
                            if row['status'] == 'improved':
                                return ['background-color: lightgreen']*len(row)
                            elif row['status'] == 'declined':
                                return ['background-color: lightsalmon']*len(row)
                            elif row['status'] == 'new':
                                return ['background-color: lightblue']*len(row)
                            elif row['status'] == 'dropped':
                                return ['background-color: pink']*len(row)
                            return ['background-color: white']*len(row)

                        st.dataframe(pcdf.style.apply(color_status, axis=1), use_container_width=True)


if __name__ == "__main__":
    main()
