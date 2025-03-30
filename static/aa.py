import pandas as pd

def prepare_data(df):
    """
    Minimal data preparation:
      - Converts the 'Time' column to datetime.
      - Creates a 'date' column from the 'Time' column.
    """
    if 'Time' in df.columns:
        df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
        df['date'] = df['Time'].dt.date
    return df

def debug_compare_over_time(start_date_str, end_date_str, keyword):
    # Load the Excel file
    try:
        df = pd.read_excel('temp_upload.xlsx')
    except Exception as e:
        print("Error reading Excel file:", e)
        return

    # Rename columns if they are named "C", "D", "E", "F"
    col_map = {
        'C': 'Results',    # URLs
        'D': 'Position',   # Positions
        'E': 'Keyword',    # Keywords
        'F': 'Time'        # Time
    }
    for old_col, new_col in col_map.items():
        if old_col in df.columns:
            df = df.rename(columns={old_col: new_col})

    # Prepare data (convert Time to datetime and create date column)
    df = prepare_data(df)

    # Filter by keyword (Column E -> 'Keyword')
    df_keyword = df[df['Keyword'] == keyword]
    if df_keyword.empty:
        print(f"No data found for keyword: {keyword}")
        return

    # Convert input date strings to date objects
    try:
        start_date = pd.to_datetime(start_date_str).date()
        end_date = pd.to_datetime(end_date_str).date()
    except Exception as e:
        print("Error converting input dates:", e)
        return

    # Filter the DataFrame for the selected dates using the actual date values
    start_data = df_keyword[df_keyword['date'] == start_date].copy()
    end_data = df_keyword[df_keyword['date'] == end_date].copy()

    # Debug prints to check the number of rows for each date
    print("Rows for start date (", start_date, "):", len(start_data))
    print("Rows for end date (", end_date, "):", len(end_data))
    
    # Print sample rows for debugging
    print("\nStart Data Sample:")
    print(start_data[['Results', 'Position', 'date']].head(10))
    
    print("\nEnd Data Sample:")
    print(end_data[['Results', 'Position', 'date']].head(10))
    
    # Sort each subset by Position (ascending: lower numbers are better)
    start_data_sorted = start_data.sort_values(by='Position', ascending=True)
    end_data_sorted = end_data.sort_values(by='Position', ascending=True)
    
    # Convert sorted DataFrames to lists of [URL, Position]
    start_list = start_data_sorted[['Results', 'Position']].values.tolist()
    end_list   = end_data_sorted[['Results', 'Position']].values.tolist()
    
    # Build the rank table
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
        
        # Calculate the difference between positions if possible
        change_str = ""
        if isinstance(pos_start, (int, float)) and isinstance(pos_end, (int, float)):
            diff = pos_end - pos_start
            change_str = f"{diff:+.0f}"  # Format as +X or -X with no decimals
        
        rank_table.append({
            "rank": i + 1,
            "url_start": url_start or "",
            "url_end": url_end or "",
            "change": change_str
        })
    
    # Print the final rank table for debugging
    print("\nRank Table:")
    for row in rank_table:
        print(row)

if __name__ == '__main__':
    # Replace these with your test dates and keyword.
    # For example, if you expect multiple rows on 2025-03-27 for keyword "vpn":
    test_start_date = "2025-03-27"
    test_end_date = "2025-03-27"
    test_keyword = "vpn"
    
    debug_compare_over_time(test_start_date, test_end_date, test_keyword)
