#!/usr/bin/env python3
"""
Upload Moonriver DelegateChanged events to Dune Analytics
"""

import requests
import pandas as pd
import json
import os
from datetime import datetime

# Dune API configuration
DUNE_API_KEY = os.getenv('DUNE_API_KEY', '8XI046uBXhPsqM2BsK4aAe0qgR3ZQEgU')  # User provided API key
DUNE_API_BASE_URL = "https://api.dune.com/api/v1"

def find_moonriver_delegate_file():
    """Find the Moonriver DelegateChanged CSV file"""
    target_file = "Moonriver_DelegateChanged_events_incremental_20250925_010508.csv"
    
    if os.path.exists(target_file):
        return target_file
    
    # Fallback: look for any Moonriver DelegateChanged files
    csv_files = []
    for file in os.listdir('.'):
        if file.startswith('Moonriver_DelegateChanged_events_') and file.endswith('.csv'):
            csv_files.append(file)
    
    if csv_files:
        # Return the most recent file
        return sorted(csv_files)[-1]
    
    return None

def read_csv_file(file_path):
    """Read CSV file and return as CSV string content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"Successfully read CSV file: {file_path}")
        return content
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return None

def upload_to_dune(csv_content, table_name, description):
    """Upload CSV content to Dune Analytics"""
    
    headers = {
        "X-DUNE-API-KEY": DUNE_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "data": csv_content,
        "description": description,
        "table_name": table_name,
        "is_private": False
    }
    
    try:
        print(f"Uploading CSV content to Dune table: {table_name}")
        print(f"Data size: {len(csv_content)} characters")
        
        response = requests.post(
            f"{DUNE_API_BASE_URL}/table/upload/csv",
            headers=headers,
            data=json.dumps(payload),
            timeout=300  # 5 minutes timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Successfully uploaded to Dune!")
            print(f"Table name: {table_name}")
            return True
        else:
            print(f"❌ Upload failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error uploading to Dune: {e}")
        return False

def main():
    """Main function to upload Moonriver DelegateChanged data to Dune"""
    
    print("🚀 Starting upload of Moonriver DelegateChanged events to Dune...")
    
    # Find the Moonriver DelegateChanged file
    csv_file = find_moonriver_delegate_file()
    if not csv_file:
        print("❌ No Moonriver DelegateChanged CSV files found!")
        return
    
    print(f"📁 Found file: {csv_file}")
    
    # Read the CSV file
    csv_content = read_csv_file(csv_file)
    if not csv_content:
        print("❌ Failed to read CSV file!")
        return
    
    # Count rows for display
    row_count = len(csv_content.split('\n')) - 1  # Subtract header
    
    # Prepare upload parameters
    table_name = "moonriver_delegate_changed_events"
    description = f"""
    Moonriver DelegateChanged Events - Complete Dataset
    
    This dataset contains DelegateChanged events from the Moonriver network governance system.
    
    Total events: {row_count}
    
    Data structure:
    - block_number: Block number where the event occurred
    - transaction_hash: Transaction hash containing the event
    - log_index: Index of the log within the transaction
    - delegator: Address of the account that changed delegation
    - from_delegate: Previous delegate address (0x0 for new delegations)
    - to_delegate: New delegate address
    - raw_topics: Raw event topics from the blockchain log
    
    Network: Moonriver (Kusama parachain)
    Contract: Moonwell Artemis Governor
    Event: DelegateChanged(address indexed delegator, address indexed fromDelegate, address indexed toDelegate)
    
    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    Source: Moonriver blockchain DelegateChanged events
    """
    
    # Upload to Dune
    success = upload_to_dune(csv_content, table_name, description)
    
    if success:
        print(f"""
        🎉 Upload completed successfully!
        
        📊 Data Summary:
        - File: {csv_file}
        - Total events: {row_count}
        - Table name: {table_name}
        - Network: Moonriver
        
        🔗 Next steps:
        1. Visit Dune Analytics: https://dune.com
        2. Go to Data Explorer
        3. Search for table: {table_name}
        4. Create queries using this data
        
        ✅ The Moonriver DelegateChanged data is now properly uploaded and available on Dune!
        """)
    else:
        print("❌ Upload failed. Please check the error messages above.")

if __name__ == "__main__":
    main()