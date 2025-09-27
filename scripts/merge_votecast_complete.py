#!/usr/bin/env python3
"""
Merge VoteCast CSV Files
Combines the gap file with the main incremental file to create a complete dataset.
"""

import pandas as pd
from datetime import datetime
import os

def merge_votecast_files():
    """Merge the gap CSV with the main incremental CSV."""
    
    # File paths
    gap_file = "Moonriver_VoteCast_gap_2863449_2905966_20250925_144740.csv"
    main_file = "Moonriver_VoteCast_events_incremental_20250925_011527.csv"
    
    print("🔄 Merging VoteCast CSV files...")
    print("=" * 50)
    
    # Check if files exist
    if not os.path.exists(gap_file):
        print(f"❌ Gap file not found: {gap_file}")
        return
    
    if not os.path.exists(main_file):
        print(f"❌ Main file not found: {main_file}")
        return
    
    # Read CSV files
    print(f"📖 Reading gap file: {gap_file}")
    gap_df = pd.read_csv(gap_file)
    print(f"   Found {len(gap_df):,} events in gap file")
    
    print(f"📖 Reading main file: {main_file}")
    main_df = pd.read_csv(main_file)
    print(f"   Found {len(main_df):,} events in main file")
    
    # Combine dataframes
    print("🔗 Combining datasets...")
    combined_df = pd.concat([gap_df, main_df], ignore_index=True)
    
    # Sort by block number and log index for proper ordering
    print("📊 Sorting by block number and log index...")
    combined_df = combined_df.sort_values(['block_number', 'log_index'], ascending=True)
    combined_df = combined_df.reset_index(drop=True)
    
    # Remove duplicates if any (based on transaction_hash and log_index)
    print("🧹 Removing duplicates...")
    initial_count = len(combined_df)
    combined_df = combined_df.drop_duplicates(subset=['transaction_hash', 'log_index'], keep='first')
    final_count = len(combined_df)
    duplicates_removed = initial_count - final_count
    
    if duplicates_removed > 0:
        print(f"   Removed {duplicates_removed:,} duplicate events")
    else:
        print("   No duplicates found")
    
    # Generate output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"Moonriver_VoteCast_events_complete_{timestamp}.csv"
    
    # Save merged file
    print(f"💾 Saving complete dataset: {output_file}")
    combined_df.to_csv(output_file, index=False)
    
    # Summary
    print("\n" + "=" * 50)
    print("✅ Merge completed successfully!")
    print(f"📊 Total events: {len(combined_df):,}")
    print(f"📅 Block range: {combined_df['block_number'].min():,} to {combined_df['block_number'].max():,}")
    print(f"📁 Output file: {output_file}")
    
    # Show first few events from gap
    print(f"\n🔍 First 5 events from gap (block {combined_df['block_number'].min():,}):")
    print(combined_df.head()[['block_number', 'voter', 'proposal_id', 'support', 'votes']].to_string(index=False))
    
    print("=" * 50)
    
    return output_file

if __name__ == "__main__":
    merge_votecast_files()