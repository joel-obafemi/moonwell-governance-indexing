#!/usr/bin/env python3

import pandas as pd
import os
from datetime import datetime

def merge_delegate_changed_events():
    """
    Merge all DelegateChanged events from different CSV files into one consolidated file
    """
    print("🔄 Merging DelegateChanged Events")
    print("=" * 40)
    
    # Define input files and their characteristics
    input_files = [
        {
            'file': 'DelegateChanged_events_20250922_140357.csv',
            'description': 'Main events file (blocks 1,295,023 to ~5,329,264)',
            'format': 'standard'
        },
        {
            'file': 'early_events_continue.csv', 
            'description': 'Early events continuation (blocks 3,800,122+)',
            'format': 'standard'
        },
        {
            'file': 'DelegateChanged_events.csv',
            'description': 'Recent events (blocks 5,767,061+)',
            'format': 'extended'  # Has extra 'event_type' column
        },
        {
            'file': 'retry_failed_blocks.csv',
            'description': 'Retry results (should be empty)',
            'format': 'standard'
        }
    ]
    
    all_events = []
    file_stats = {}
    
    for file_info in input_files:
        filename = file_info['file']
        
        if not os.path.exists(filename):
            print(f"⚠️  File not found: {filename}")
            continue
            
        print(f"\n📂 Processing: {filename}")
        print(f"   Description: {file_info['description']}")
        
        try:
            # Read the CSV file
            df = pd.read_csv(filename)
            
            if df.empty:
                print(f"   📊 Empty file - skipping")
                file_stats[filename] = {'original': 0, 'processed': 0}
                continue
            
            original_count = len(df)
            print(f"   📊 Original records: {original_count:,}")
            
            # Handle different formats
            if file_info['format'] == 'extended':
                # Remove the 'event_type' column and 'data' column, rename if needed
                if 'event_type' in df.columns:
                    df = df.drop('event_type', axis=1)
                if 'data' in df.columns and 'raw_data' not in df.columns:
                    df = df.rename(columns={'data': 'raw_data'})
                # Add missing raw_topics column if not present
                if 'raw_topics' not in df.columns:
                    df['raw_topics'] = ''
            
            # Ensure all required columns are present
            required_columns = ['block_number', 'transaction_hash', 'log_index', 'delegator', 'from_delegate', 'to_delegate', 'raw_data', 'raw_topics']
            
            for col in required_columns:
                if col not in df.columns:
                    df[col] = ''
                    print(f"   ⚠️  Added missing column: {col}")
            
            # Select only the required columns in the correct order
            df = df[required_columns]
            
            # Convert block_number to int for proper sorting
            df['block_number'] = pd.to_numeric(df['block_number'], errors='coerce')
            df['log_index'] = pd.to_numeric(df['log_index'], errors='coerce')
            
            # Remove rows with invalid block numbers
            df = df.dropna(subset=['block_number', 'log_index'])
            df['block_number'] = df['block_number'].astype(int)
            df['log_index'] = df['log_index'].astype(int)
            
            processed_count = len(df)
            print(f"   📊 Processed records: {processed_count:,}")
            
            # Add to the main list
            all_events.append(df)
            file_stats[filename] = {'original': original_count, 'processed': processed_count}
            
            # Show block range
            if processed_count > 0:
                min_block = df['block_number'].min()
                max_block = df['block_number'].max()
                print(f"   📊 Block range: {min_block:,} to {max_block:,}")
            
        except Exception as e:
            print(f"   ❌ Error processing {filename}: {e}")
            file_stats[filename] = {'original': 0, 'processed': 0, 'error': str(e)}
    
    if not all_events:
        print("\n❌ No valid data found in any files!")
        return
    
    print(f"\n🔄 Combining all events...")
    
    # Combine all dataframes
    combined_df = pd.concat(all_events, ignore_index=True)
    total_before_dedup = len(combined_df)
    print(f"📊 Total events before deduplication: {total_before_dedup:,}")
    
    # Remove duplicates based on transaction_hash and log_index
    print(f"🔄 Removing duplicates...")
    combined_df = combined_df.drop_duplicates(subset=['transaction_hash', 'log_index'], keep='first')
    total_after_dedup = len(combined_df)
    duplicates_removed = total_before_dedup - total_after_dedup
    print(f"📊 Duplicates removed: {duplicates_removed:,}")
    print(f"📊 Unique events: {total_after_dedup:,}")
    
    # Sort by block number and log index for chronological order
    print(f"🔄 Sorting events chronologically...")
    combined_df = combined_df.sort_values(['block_number', 'log_index'], ascending=[True, True])
    combined_df = combined_df.reset_index(drop=True)
    
    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"DelegateChanged_events_merged_{timestamp}.csv"
    
    # Save the merged file
    print(f"💾 Saving merged events to: {output_file}")
    combined_df.to_csv(output_file, index=False)
    
    # Final statistics
    print(f"\n✅ Merge completed successfully!")
    print(f"📊 Final Statistics:")
    print(f"   Total unique events: {total_after_dedup:,}")
    print(f"   Block range: {combined_df['block_number'].min():,} to {combined_df['block_number'].max():,}")
    print(f"   Output file: {output_file}")
    print(f"   File size: {os.path.getsize(output_file) / 1024 / 1024:.2f} MB")
    
    print(f"\n📋 File Processing Summary:")
    for filename, stats in file_stats.items():
        if 'error' in stats:
            print(f"   {filename}: ERROR - {stats['error']}")
        else:
            print(f"   {filename}: {stats['processed']:,} events processed (from {stats['original']:,} original)")
    
    # Show sample of merged data
    print(f"\n📋 Sample of merged data (first 3 events):")
    print(combined_df.head(3).to_string(index=False))
    
    print(f"\n📋 Sample of merged data (last 3 events):")
    print(combined_df.tail(3).to_string(index=False))
    
    return output_file

if __name__ == "__main__":
    merge_delegate_changed_events()