#!/usr/bin/env python3
"""
Merge VoteCast CSV files and remove duplicates
"""

import pandas as pd
import os
from datetime import datetime

def merge_votecast_files():
    """Merge VoteCast_events_incremental.csv and VoteCast_events_fast.csv"""
    
    # File paths
    incremental_file = "VoteCast_events_incremental.csv"
    fast_file = "VoteCast_events_fast.csv"
    merged_file = f"VoteCast_events_merged_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    print("🔄 Merging VoteCast CSV files...")
    
    # Check if files exist
    if not os.path.exists(incremental_file):
        print(f"❌ {incremental_file} not found!")
        return
    
    if not os.path.exists(fast_file):
        print(f"❌ {fast_file} not found!")
        return
    
    # Read CSV files
    print(f"📖 Reading {incremental_file}...")
    df_incremental = pd.read_csv(incremental_file)
    print(f"   Found {len(df_incremental)} events")
    
    print(f"📖 Reading {fast_file}...")
    df_fast = pd.read_csv(fast_file)
    print(f"   Found {len(df_fast)} events")
    
    # Display column info
    print(f"\n📊 Incremental CSV columns: {list(df_incremental.columns)}")
    print(f"📊 Fast CSV columns: {list(df_fast.columns)}")
    
    # Combine dataframes
    print("\n🔗 Combining dataframes...")
    df_combined = pd.concat([df_incremental, df_fast], ignore_index=True)
    print(f"   Combined total: {len(df_combined)} events")
    
    # Remove duplicates based on transaction hash and log index
    print("\n🧹 Removing duplicates...")
    initial_count = len(df_combined)
    
    # Assuming the CSV has columns like 'block_number', 'transaction_hash', 'log_index'
    # Adjust column names based on actual CSV structure
    if 'transaction_hash' in df_combined.columns and 'log_index' in df_combined.columns:
        df_combined = df_combined.drop_duplicates(subset=['transaction_hash', 'log_index'])
    elif 'block_number' in df_combined.columns:
        df_combined = df_combined.drop_duplicates(subset=['block_number'])
    else:
        # Fallback: remove duplicates based on all columns
        df_combined = df_combined.drop_duplicates()
    
    duplicates_removed = initial_count - len(df_combined)
    print(f"   Removed {duplicates_removed} duplicates")
    print(f"   Final count: {len(df_combined)} events")
    
    # Sort by block number if available
    if 'block_number' in df_combined.columns:
        df_combined = df_combined.sort_values('block_number')
        print("✅ Sorted by block number")
    
    # Save merged file
    print(f"\n💾 Saving merged file: {merged_file}")
    df_combined.to_csv(merged_file, index=False)
    
    print(f"\n🎉 Merge completed!")
    print(f"📁 Output file: {merged_file}")
    print(f"📊 Total events: {len(df_combined)}")
    
    # Display block range
    if 'block_number' in df_combined.columns:
        min_block = df_combined['block_number'].min()
        max_block = df_combined['block_number'].max()
        print(f"📈 Block range: {min_block} to {max_block}")
    
    return merged_file

if __name__ == "__main__":
    merge_votecast_files()