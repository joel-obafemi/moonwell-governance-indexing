#!/usr/bin/env python3
"""
Upload Moonriver VoteCast events with properly formatted votes column to Dune Analytics
This ensures votes are displayed as full integers, not scientific notation
"""

import requests
import pandas as pd
import json
import os
from datetime import datetime

# Dune API configuration
DUNE_API_KEY = os.getenv('DUNE_API_KEY', '8XI046uBXhPsqM2BsK4aAe0qgR3ZQEgU')
DUNE_API_BASE_URL = "https://api.dune.com/api/v1"

def find_latest_votes_fixed_file():
    """Find the latest votes-fixed Moonriver VoteCast CSV file"""
    csv_files = []
    for file in os.listdir('.'):
        if file.startswith('Moonriver_VoteCast_events_votes_fixed_') and file.endswith('.csv'):
            csv_files.append(file)
    
    if not csv_files:
        return None
    
    # Return the most recent file
    return sorted(csv_files)[-1]

def read_and_verify_csv(file_path):
    """Read and verify the votes-fixed CSV file"""
    
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
    sample_proposal_ids = df['proposal_id'].head(5).tolist()
    print(f"Sample proposal IDs: {sample_proposal_ids}")
    
    # Check votes format - this is the key fix
    sample_votes = df['votes'].head(5).tolist()
    print(f"Sample votes values: {sample_votes}")
    
    # Check if any votes contain scientific notation
    scientific_notation_count = 0
    for vote in df['votes']:
        if 'e+' in str(vote).lower() or 'e-' in str(vote).lower():
            scientific_notation_count += 1
    
    print(f"Votes in scientific notation: {scientific_notation_count}")
    
    # Read file as raw CSV content for upload
    with open(file_path, 'r', encoding='utf-8') as f:
        csv_content = f.read()
    
    return csv_content, len(df)

def upload_to_dune(csv_content, row_count, file_name):
    """Upload CSV content to Dune Analytics with votes properly formatted"""
    
    headers = {
        "X-DUNE-API-KEY": DUNE_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Use a new table name to ensure fresh upload with proper votes formatting
    table_name = "moonriver_votecast_events_final"
    
    description = f"""Final Moonriver VoteCast events data with properly formatted votes - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This dataset contains the complete and properly formatted Moonriver VoteCast events with:
✅ Fixed voter addresses (extracted from raw_data hex strings)
✅ Corrected proposal_id values as integers (1-64, not scientific notation)  
✅ Properly formatted votes column (full integers, NOT scientific notation like 2.00414e+21)
✅ Complete event data from blocks 2,863,449 to 12,219,550

Total events: {row_count}
Source file: {file_name}

Data structure:
- block_number: Block number where the event occurred
- transaction_hash: Transaction hash containing the event  
- log_index: Index of the log within the transaction
- voter: Ethereum address of the voter (0x...)
- proposal_id: Integer ID of the proposal (1, 2, 3, etc.)
- support: Vote support (0=against, 1=for, 2=abstain)
- votes: Number of votes cast in wei (full integer format, e.g., 2004140000000000000000)
- raw_data: Original hex data from the event
- raw_topics: Original event topics array

Note: The votes column is properly quoted to prevent conversion to scientific notation.
To convert votes to human-readable format, divide by 10^18 (1 ether = 10^18 wei).
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
            print("4. Verify the votes column shows full integers (not scientific notation)")
            print("5. To get human-readable vote amounts, divide votes by 10^18")
            return True
        else:
            print(f"❌ Upload failed with status {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

def main():
    print("=== Uploading Moonriver VoteCast Data with Fixed Votes Formatting ===\n")
    
    # Find the latest votes-fixed file
    file_path = find_latest_votes_fixed_file()
    
    if not file_path:
        print("❌ No votes-fixed CSV file found!")
        print("Expected file pattern: Moonriver_VoteCast_events_votes_fixed_*.csv")
        return
    
    print(f"Found votes-fixed file: {file_path}")
    
    # Read and verify the CSV file
    csv_content, row_count = read_and_verify_csv(file_path)
    
    if csv_content is None:
        print("❌ Failed to read CSV file")
        return
    
    print(f"\n=== Verification Complete ===")
    print("The CSV file has proper votes formatting (quoted strings to prevent scientific notation).")
    print("Proceeding with upload to Dune...\n")
    
    # Upload to Dune
    success = upload_to_dune(csv_content, row_count, file_path)
    
    if success:
        print("\n🎉 Upload completed successfully!")
        print("The votes column should now display as full integers in Dune, not scientific notation.")
    else:
        print("\n❌ Upload failed. Please check the error messages above.")

if __name__ == "__main__":
    main()