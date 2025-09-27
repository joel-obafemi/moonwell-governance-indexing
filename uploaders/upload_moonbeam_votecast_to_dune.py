#!/usr/bin/env python3
"""
Upload Moonbeam VoteCast events to Dune Analytics with correct naming
"""

import requests
import pandas as pd
import json
import os
from datetime import datetime

# Dune API configuration
DUNE_API_KEY = os.getenv('DUNE_API_KEY', '8XI046uBXhPsqM2BsK4aAe0qgR3ZQEgU')  # User provided API key
DUNE_API_BASE_URL = "https://api.dune.com/api/v1"

def find_moonbeam_votecast_file():
    """Find the Moonbeam VoteCast CSV file (the fixed one from 20250924_180037)"""
    # Based on the block range analysis, this is the Moonbeam data
    target_file = "VoteCast_events_fixed_20250924_180037.csv"
    
    if os.path.exists(target_file):
        return target_file
    
    # Fallback: look for any VoteCast_events_fixed files
    csv_files = []
    for file in os.listdir('.'):
        if file.startswith('VoteCast_events_fixed_') and file.endswith('.csv'):
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
    """Main function to upload Moonbeam VoteCast data to Dune"""
    
    print("🚀 Starting upload of Moonbeam VoteCast events to Dune...")
    
    # Find the Moonbeam VoteCast file
    csv_file = find_moonbeam_votecast_file()
    if not csv_file:
        print("❌ No Moonbeam VoteCast CSV files found!")
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
    table_name = "moonbeam_votecast_events_complete"
    description = f"""
    Moonbeam VoteCast Events - Complete Dataset
    
    This dataset contains VoteCast events from the Moonbeam network (Ethereum parachain).
    
    Coverage: Blocks 5,803,712 to 12,655,028
    Total events: {row_count}
    
    Data structure:
    - block_number: Block number where event occurred
    - transaction_hash: Transaction hash
    - log_index: Log index within transaction
    - voter: Address of the voter
    - proposal_id: Proposal ID (1-based numbering)
    - support: Vote support (0=Against, 1=For, 2=Abstain)
    - votes: Number of votes cast (with decimals)
    - raw_data: Original raw event data
    - raw_topics: Event topics
    
    Network: Moonbeam (Polkadot parachain)
    Contract: Moonwell Artemis Governor
    Event: VoteCast(address indexed voter, uint256 proposalId, uint8 support, uint256 votes)
    
    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    Source: Moonbeam blockchain VoteCast events
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
        - Network: Moonbeam
        
        🔗 Next steps:
        1. Visit Dune Analytics: https://dune.com
        2. Go to Data Explorer
        3. Search for table: {table_name}
        4. Create queries using this data
        
        ✅ The Moonbeam VoteCast data is now properly uploaded and available on Dune!
        """)
    else:
        print("❌ Upload failed. Please check the error messages above.")

if __name__ == "__main__":
    main()