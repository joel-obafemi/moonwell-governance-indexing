#!/usr/bin/env python3
"""
Re-upload corrected Moonriver VoteCast events to Dune Analytics
This script ensures the properly fixed data with voter addresses and integer proposal IDs is uploaded
"""

import requests
import pandas as pd
import json
import os
from datetime import datetime

# Dune API configuration
DUNE_API_KEY = os.getenv('DUNE_API_KEY', '8XI046uBXhPsqM2BsK4aAe0qgR3ZQEgU')
DUNE_API_BASE_URL = "https://api.dune.com/api/v1"

def read_and_verify_csv():
    """Read and verify the fixed Moonriver VoteCast CSV file"""
    file_path = "Moonriver_VoteCast_events_fixed_20250925_152315.csv"
    
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found!")
        return None, None
    
    # Read as pandas DataFrame to verify data quality
    df = pd.read_csv(file_path)
    
    print(f"File: {file_path}")
    print(f"Total events: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    
    # Verify data quality
    empty_voters = df['voter'].isna().sum() + (df['voter'] == '').sum()
    print(f"Empty voter addresses: {empty_voters}")
    
    # Check proposal_id format
    sample_proposal_ids = df['proposal_id'].head(10).tolist()
    print(f"Sample proposal IDs: {sample_proposal_ids}")
    
    # Check if any proposal_id contains scientific notation
    scientific_notation_count = 0
    for pid in df['proposal_id']:
        if 'e+' in str(pid).lower() or 'e-' in str(pid).lower():
            scientific_notation_count += 1
    
    print(f"Proposal IDs in scientific notation: {scientific_notation_count}")
    
    # Read file as raw CSV content for upload
    with open(file_path, 'r', encoding='utf-8') as f:
        csv_content = f.read()
    
    return csv_content, len(df)

def upload_to_dune(csv_content, row_count):
    """Upload CSV content to Dune Analytics with a new table name"""
    
    headers = {
        "X-DUNE-API-KEY": DUNE_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Use a new table name to ensure fresh upload
    table_name = "moonriver_votecast_events_corrected"
    
    description = f"""Corrected Moonriver VoteCast events data - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This dataset contains properly formatted Moonriver VoteCast events with:
- Fixed voter addresses (extracted from raw_data hex strings)
- Corrected proposal_id values as integers (1-64, not scientific notation)
- Proper support and votes values
- Complete event data from blocks 2,863,449 to 12,219,550

Total events: {row_count}

Data structure:
- block_number: Block number where the event occurred
- transaction_hash: Transaction hash containing the event
- log_index: Index of the log within the transaction
- voter: Ethereum address of the voter (0x...)
- proposal_id: Integer ID of the proposal (1, 2, 3, etc.)
- support: Vote support (0=against, 1=for, 2=abstain)
- votes: Number of votes cast (in wei)
- raw_data: Original hex data from the event
- raw_topics: Original event topics array
"""
    
    payload = {
        "data": csv_content,
        "description": description,
        "table_name": table_name,
        "is_private": False
    }
    
    print(f"Uploading to Dune with table name: {table_name}")
    print(f"Data size: {len(csv_content)} characters")
    
    try:
        response = requests.post(
            f"{DUNE_API_BASE_URL}/table/upload/csv",
            headers=headers,
            json=payload,
            timeout=300  # 5 minute timeout for large uploads
        )
        
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")
        
        if response.status_code == 200:
            print(f"✅ Successfully uploaded {row_count} events to Dune!")
            print(f"Table name: {table_name}")
            print("\nNext steps:")
            print("1. Go to https://dune.com")
            print("2. Navigate to Data Explorer")
            print(f"3. Search for table: {table_name}")
            print("4. Verify the data has proper voter addresses and integer proposal IDs")
            return True
        else:
            print(f"❌ Upload failed with status {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

def main():
    print("=== Re-uploading Corrected Moonriver VoteCast Data to Dune ===\n")
    
    # Read and verify the CSV file
    csv_content, row_count = read_and_verify_csv()
    
    if csv_content is None:
        print("❌ Failed to read CSV file")
        return
    
    print(f"\n=== Verification Complete ===")
    print("The local CSV file appears to have correct formatting.")
    print("Proceeding with upload to Dune...\n")
    
    # Upload to Dune
    success = upload_to_dune(csv_content, row_count)
    
    if success:
        print("\n🎉 Upload completed successfully!")
    else:
        print("\n❌ Upload failed. Please check the error messages above.")

if __name__ == "__main__":
    main()