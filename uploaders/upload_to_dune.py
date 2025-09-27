#!/usr/bin/env python3
"""
Script to upload CSV files to Dune Analytics API

Before running this script, you need to:
1. Sign up for a Dune Analytics account
2. Get your API key from https://dune.com/settings/api
3. Set the DUNE_API_KEY environment variable or replace the placeholder below
"""

import os
import requests
import json
import time
from pathlib import Path

# Dune API configuration
DUNE_API_KEY = os.getenv('DUNE_API_KEY', '8XI046uBXhPsqM2BsK4aAe0qgR3ZQEgU')  # User provided API key
DUNE_UPLOAD_URL = "https://api.dune.com/api/v1/table/upload/csv"

# File paths
DELEGATE_CHANGED_CSV = "DelegateChanged_events_merged_20250923_131332.csv"
DELEGATE_VOTES_CHANGED_CSV = "DelegateVotesChanged_events.csv"

def read_csv_file(file_path):
    """Read CSV file and return its content as string"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
        return None
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def upload_csv_to_dune(csv_content, table_name, description, is_private=False):
    """Upload CSV content to Dune Analytics"""
    
    if DUNE_API_KEY == 'YOUR_DUNE_API_KEY_HERE':
        print("Error: Please set your Dune API key. Get it from https://dune.com/settings/api")
        print("You can set it as environment variable DUNE_API_KEY or replace in the script")
        return False
    
    headers = {
        'Content-Type': 'application/json',
        'X-DUNE-API-KEY': DUNE_API_KEY
    }
    
    payload = {
        "data": csv_content,
        "description": description,
        "table_name": table_name,
        "is_private": is_private
    }
    
    try:
        response = requests.post(DUNE_UPLOAD_URL, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Successfully uploaded {table_name} to Dune Analytics")
            print(f"   Table: {result.get('table_name')}")
            print(f"   Description: {description}")
            return True
        else:
            print(f"❌ Failed to upload {table_name}. Status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error uploading {table_name}: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error for {table_name}: {e}")
        return False

def main():
    print("🚀 Starting Dune Analytics CSV Upload Script")
    print("=" * 50)
    
    # Check if CSV files exist
    if not Path(DELEGATE_CHANGED_CSV).exists():
        print(f"❌ File {DELEGATE_CHANGED_CSV} not found")
        return
    
    if not Path(DELEGATE_VOTES_CHANGED_CSV).exists():
        print(f"❌ File {DELEGATE_VOTES_CHANGED_CSV} not found")
        return
    
    # Read CSV files
    print("📖 Reading CSV files...")
    delegate_changed_content = read_csv_file(DELEGATE_CHANGED_CSV)
    delegate_votes_content = read_csv_file(DELEGATE_VOTES_CHANGED_CSV)
    
    if not delegate_changed_content or not delegate_votes_content:
        print("❌ Failed to read CSV files")
        return
    
    print(f"✅ Read {len(delegate_changed_content.split(chr(10)))} lines from {DELEGATE_CHANGED_CSV}")
    print(f"✅ Read {len(delegate_votes_content.split(chr(10)))} lines from {DELEGATE_VOTES_CHANGED_CSV}")
    
    # Upload to Dune
    print("\n📤 Uploading to Dune Analytics...")
    
    # Upload DelegateChanged events
    success1 = upload_csv_to_dune(
        csv_content=delegate_changed_content,
        table_name="moonwell_delegate_changed_events_complete",
        description="Moonwell Artemis Claims Contract - Complete DelegateChanged events dataset. Merged from all sources covering blocks 1,295,023 to 12,637,732 with 3,369 unique events. Contains delegator addresses, from/to delegates, and transaction details.",
        is_private=False
    )
    
    # Wait a moment between uploads
    time.sleep(2)
    
    # Upload DelegateVotesChanged events
    success2 = upload_csv_to_dune(
        csv_content=delegate_votes_content,
        table_name="moonwell_delegate_votes_changed_events",
        description="Moonwell Artemis Claims Contract - DelegateVotesChanged events. Contains delegate addresses, previous and new vote balances.",
        is_private=False
    )
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 All files uploaded successfully to Dune Analytics!")
        print("\nNext steps:")
        print("1. Visit https://dune.com/ to access your data")
        print("2. Query your tables: moonwell_delegate_changed_events_complete and moonwell_delegate_votes_changed_events")
        print("3. Create dashboards and analyze the delegate activity")
    else:
        print("⚠️  Some uploads failed. Please check the error messages above.")
        print("\nTroubleshooting:")
        print("• Ensure your Dune API key is correct")
        print("• Check that you have upload permissions")
        print("• Verify your CSV files are properly formatted")

if __name__ == "__main__":
    main()