#!/usr/bin/env python3
"""
Clean and standardize the merged VoteCast CSV file for Dune upload
"""

import pandas as pd
import glob
from datetime import datetime

def clean_votecast_csv():
    """Clean the merged VoteCast CSV file"""
    
    # Find the merged file
    pattern = "VoteCast_events_merged_*.csv"
    files = glob.glob(pattern)
    
    if not files:
        print(f"❌ No merged VoteCast files found")
        return
    
    input_file = max(files, key=lambda x: x)
    output_file = f"VoteCast_events_clean_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    print(f"🧹 Cleaning VoteCast CSV file: {input_file}")
    
    # Read the CSV file with error handling
    try:
        # Read with minimal processing first
        df = pd.read_csv(input_file, low_memory=False)
        print(f"📊 Original shape: {df.shape}")
        print(f"📊 Original columns: {list(df.columns)}")
        
        # Define the standard columns we want
        standard_columns = [
            'block_number',
            'transaction_hash', 
            'log_index',
            'voter',
            'proposal_id',
            'support',
            'votes',
            'raw_data',
            'raw_topics'
        ]
        
        # Create a clean dataframe with standard columns
        clean_df = pd.DataFrame()
        
        # Map existing columns to standard columns
        for col in standard_columns:
            if col in df.columns:
                clean_df[col] = df[col]
            else:
                # Handle missing columns
                if col == 'reason':
                    clean_df[col] = ''  # Empty string for missing reason
                else:
                    clean_df[col] = None
        
        # Clean up data types and values
        print("🔧 Cleaning data...")
        
        # Ensure block_number is integer
        clean_df['block_number'] = pd.to_numeric(clean_df['block_number'], errors='coerce')
        
        # Ensure log_index is integer
        clean_df['log_index'] = pd.to_numeric(clean_df['log_index'], errors='coerce')
        
        # Clean proposal_id (remove scientific notation)
        clean_df['proposal_id'] = clean_df['proposal_id'].astype(str)
        
        # Clean support values
        clean_df['support'] = pd.to_numeric(clean_df['support'], errors='coerce')
        
        # Clean votes (remove scientific notation)
        clean_df['votes'] = clean_df['votes'].astype(str)
        
        # Remove rows with missing critical data
        initial_count = len(clean_df)
        clean_df = clean_df.dropna(subset=['block_number', 'transaction_hash'])
        final_count = len(clean_df)
        
        print(f"🗑️  Removed {initial_count - final_count} rows with missing critical data")
        
        # Sort by block number
        clean_df = clean_df.sort_values('block_number')
        
        # Remove duplicates
        duplicate_count = len(clean_df)
        clean_df = clean_df.drop_duplicates(subset=['transaction_hash', 'log_index'])
        final_duplicate_count = len(clean_df)
        
        print(f"🗑️  Removed {duplicate_count - final_duplicate_count} duplicate rows")
        
        print(f"✅ Clean shape: {clean_df.shape}")
        print(f"✅ Clean columns: {list(clean_df.columns)}")
        
        # Display sample data
        print("\n📋 Sample of cleaned data:")
        print(clean_df.head(3).to_string())
        
        # Save cleaned file
        clean_df.to_csv(output_file, index=False)
        print(f"\n💾 Saved cleaned file: {output_file}")
        
        # Display statistics
        if not clean_df.empty:
            min_block = clean_df['block_number'].min()
            max_block = clean_df['block_number'].max()
            print(f"📈 Block range: {int(min_block)} to {int(max_block)}")
            print(f"📊 Total events: {len(clean_df)}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error cleaning CSV: {e}")
        return None

if __name__ == "__main__":
    clean_votecast_csv()