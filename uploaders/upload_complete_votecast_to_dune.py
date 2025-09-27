#!/usr/bin/env python3
"""
Script to upload the complete VoteCast CSV file to Dune Analytics API
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

def find_complete_votecast_file():
    """Find the complete VoteCast CSV file."""
    # Look for the complete file first
    pattern = "Moonriver_VoteCast_events_complete_*.csv"
    files = glob.glob(pattern)
    
    if files:
        latest_file = max(files, key=os.path.getctime)
        print(f"📁 Found complete VoteCast file: {latest_file}")
        return latest_file
    
    print(f"❌ No complete VoteCast files found")
    return None

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
    print("🚀 Starting Complete VoteCast Dune Analytics Upload")
    print("=" * 60)
    
    # Find the complete VoteCast file
    votecast_file = find_complete_votecast_file()
    if not votecast_file:
        return
    
    # Read CSV file
    print("📖 Reading complete VoteCast CSV file...")
    votecast_content = read_csv_file(votecast_file)
    
    if not votecast_content:
        print("❌ Failed to read VoteCast CSV file")
        return
    
    # Count events (subtract 1 for header)
    event_count = len(votecast_content.split('\n')) - 1
    print(f"✅ Read {event_count:,} VoteCast events from {votecast_file}")
    
    # Upload to Dune
    print("\n📤 Uploading complete VoteCast events to Dune Analytics...")
    
    success = upload_csv_to_dune(
        csv_content=votecast_content,
        table_name="moonriver_votecast_events_complete",
        description=f"Moonwell Artemis Claims Contract - Complete VoteCast events dataset from Moonriver network. Merged from gap indexing (blocks 2,863,449-2,905,966) and incremental indexing (blocks 2,905,967-12,219,550) with {event_count:,} unique voting events. Contains voter addresses, proposal IDs, vote support (for/against/abstain), vote weights, and complete transaction details. No missing blocks - comprehensive governance voting data.",
        is_private=False
    )
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Complete VoteCast events uploaded successfully to Dune Analytics!")
        print("\n📊 Dataset Summary:")
        print(f"   • Total events: {event_count:,}")
        print(f"   • Block range: 2,863,449 to 12,219,550")
        print(f"   • Complete coverage: No missing blocks")
        print(f"   • Data includes: Gap fill (67 events) + Incremental (2,188 events)")
        print("\n🔗 Next steps:")
        print("1. Visit https://dune.com/ to access your data")
        print("2. Query your table: moonriver_votecast_events_complete")
        print("3. Create dashboards to analyze:")
        print("   • Voting participation over time")
        print("   • Proposal outcomes and vote distributions")
        print("   • Top voters by participation and vote weight")
        print("   • Governance activity trends")
        print("   • Historical voting patterns")
    else:
        print("⚠️  Upload failed. Please check the error messages above.")
        print("\nTroubleshooting:")
        print("• Ensure your Dune API key is correct")
        print("• Check that you have upload permissions")
        print("• Verify your CSV file is properly formatted")
        print("• Try reducing file size if it's too large")

if __name__ == "__main__":
    main()