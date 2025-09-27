#!/usr/bin/env python3
"""
Upload Moonriver DelegateVotesChanged Events to Dune Analytics
"""

import requests
import os
import glob
import json
from datetime import datetime

# Dune API configuration
DUNE_API_KEY = os.getenv('DUNE_API_KEY', '8XI046uBXhPsqM2BsK4aAe0qgR3ZQEgU')  # User provided API key
DUNE_API_BASE_URL = "https://api.dune.com/api/v1"

def find_moonriver_delegatevotes_csv():
    """Find the most recent Moonriver DelegateVotesChanged CSV file"""
    pattern = "Moonriver_DelegateVotesChanged_events_*.csv"
    files = glob.glob(pattern)
    
    if not files:
        raise FileNotFoundError(f"No files found matching pattern: {pattern}")
    
    # Sort by modification time, get the most recent
    latest_file = max(files, key=os.path.getmtime)
    print(f"Found Moonriver DelegateVotesChanged CSV: {latest_file}")
    return latest_file

def read_csv_content(file_path):
    """Read CSV file content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        print(f"Successfully read CSV file: {len(content)} characters")
        return content
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        raise

def upload_to_dune(csv_content, table_name):
    """Upload CSV content to Dune Analytics"""
    headers = {
        "X-DUNE-API-KEY": DUNE_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "data": csv_content,
        "description": f"Moonriver DelegateVotesChanged events - uploaded on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "table_name": table_name,
        "is_private": False
    }
    
    try:
        print(f"Uploading to Dune with table name: {table_name}")
        response = requests.post(
            f"{DUNE_API_BASE_URL}/table/upload/csv",
            headers=headers,
            data=json.dumps(payload),
            timeout=300  # 5 minutes timeout for large files
        )
        
        if response.status_code == 200:
            print("✅ Upload successful!")
            print(f"Response: {response.text}")
            return True
        else:
            print(f"❌ Upload failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during upload: {e}")
        return False

def main():
    """Main function to upload Moonriver DelegateVotesChanged events to Dune"""
    print("🚀 Starting Moonriver DelegateVotesChanged upload to Dune Analytics...")
    
    try:
        # Find the CSV file
        csv_file = find_moonriver_delegatevotes_csv()
        
        # Read CSV content
        csv_content = read_csv_content(csv_file)
        
        # Count events (subtract 1 for header)
        event_count = len(csv_content.split('\n')) - 1
        print(f"📊 CSV contains approximately {event_count} events")
        
        # Define table name
        table_name = "moonriver_delegatevotes_changed_events"
        
        # Upload to Dune
        success = upload_to_dune(csv_content, table_name)
        
        if success:
            print(f"""
            🎉 Upload completed successfully!
            
            📋 Summary:
            - File: {csv_file}
            - Events: ~{event_count}
            - Table name: {table_name}
            - Data size: {len(csv_content)} characters
            
            🔗 Next steps:
            1. Visit https://dune.com/browse/queries
            2. Search for table: {table_name}
            3. Query the data using SQL
            
            📊 Sample query:
            SELECT * FROM {table_name} 
            ORDER BY block_number DESC 
            LIMIT 10;
            
            💡 Note: The 'previous_balance' and 'new_balance' columns contain raw values.
            To convert to readable amounts, divide by 10^18:
            SELECT 
                delegate,
                CAST(previous_balance AS DECIMAL(38,0)) / 1e18 as previous_balance_readable,
                CAST(new_balance AS DECIMAL(38,0)) / 1e18 as new_balance_readable
            FROM {table_name};
            """)
        else:
            print("❌ Upload failed. Please check the error messages above.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()