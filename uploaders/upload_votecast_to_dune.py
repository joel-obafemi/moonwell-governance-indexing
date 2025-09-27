#!/usr/bin/env python3
"""
Script to upload merged VoteCast CSV file to Dune Analytics API
"""

import os
import requests
import json
import time
from pathlib import Path
import glob

# Dune API configuration
DUNE_API_KEY = os.getenv('DUNE_API_KEY', '8XI046uBXhPsqM2BsK4aAe0qgR3ZQEgU')  # User provided API key
DUNE_UPLOAD_URL = "https://api.dune.com/api/v1/table/upload/csv"

def find_merged_votecast_file():
    """Find the most recent VoteCast CSV file, prioritizing fixed > clean > merged."""
    # First try to find fixed files (highest priority)
    pattern = "VoteCast_events_fixed_*.csv"
    files = glob.glob(pattern)
    
    if files:
        latest_file = max(files, key=os.path.getctime)
        print(f"📁 Found fixed VoteCast file: {latest_file}")
        return latest_file
    
    # Then try to find cleaned files
    pattern = "VoteCast_events_clean_*.csv"
    files = glob.glob(pattern)
    
    if files:
        latest_file = max(files, key=os.path.getctime)
        print(f"📁 Found cleaned VoteCast file: {latest_file}")
        return latest_file
    
    # Fallback to merged files
    pattern = "VoteCast_events_merged_*.csv"
    files = glob.glob(pattern)
    
    if not files:
        print(f"❌ No VoteCast files found matching patterns")
        return None
    
    # Get the most recent file
    latest_file = max(files, key=os.path.getctime)
    print(f"📁 Found merged VoteCast file: {latest_file}")
    return latest_file

def read_csv_file(file_path):
    """Read CSV file and return its content as string"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            lines = content.split('\n')
            print(f"📊 File contains {len(lines)} lines")
            return content
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
        print(f"📤 Uploading to Dune Analytics...")
        print(f"   Table name: {table_name}")
        print(f"   Data size: {len(csv_content)} characters")
        
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
    print("🚀 Starting VoteCast Dune Analytics Upload")
    print("=" * 50)
    
    # Find the merged VoteCast file
    votecast_file = find_merged_votecast_file()
    if not votecast_file:
        return
    
    # Read CSV file
    print("📖 Reading merged VoteCast CSV file...")
    votecast_content = read_csv_file(votecast_file)
    
    if not votecast_content:
        print("❌ Failed to read VoteCast CSV file")
        return
    
    # Count events (subtract 1 for header)
    event_count = len(votecast_content.split('\n')) - 1
    print(f"✅ Read {event_count} VoteCast events from {votecast_file}")
    
    # Upload to Dune
    print("\n📤 Uploading VoteCast events to Dune Analytics...")
    
    success = upload_csv_to_dune(
        csv_content=votecast_content,
        table_name="moonwell_votecast_events_complete",
        description=f"Moonwell Artemis Claims Contract - Complete VoteCast events dataset. Merged from incremental and fast indexing covering blocks 5,803,712 to 12,655,028 with {event_count} unique voting events. Contains voter addresses, proposal IDs, vote support (for/against/abstain), vote weights, and transaction details.",
        is_private=False
    )
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 VoteCast events uploaded successfully to Dune Analytics!")
        print("\nNext steps:")
        print("1. Visit https://dune.com/ to access your data")
        print("2. Query your table: moonwell_votecast_events_complete")
        print("3. Create dashboards to analyze:")
        print("   • Voting participation over time")
        print("   • Proposal outcomes and vote distributions")
        print("   • Top voters by participation and vote weight")
        print("   • Governance activity trends")
    else:
        print("⚠️  Upload failed. Please check the error messages above.")
        print("\nTroubleshooting:")
        print("• Ensure your Dune API key is correct")
        print("• Check that you have upload permissions")
        print("• Verify your CSV file is properly formatted")
        print("• Try reducing file size if it's too large")

if __name__ == "__main__":
    main()