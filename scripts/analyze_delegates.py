#!/usr/bin/env python3
"""
Analyze DelegateChanged events to get unique delegators and delegates
"""

import csv
import pandas as pd

def analyze_delegate_events():
    """Analyze the DelegateChanged events CSV file"""
    
    csv_file = "DelegateChanged_events_20250922_140357.csv"
    
    print("📊 Analyzing DelegateChanged Events")
    print("=" * 50)
    
    # Read the CSV file
    try:
        df = pd.read_csv(csv_file)
        print(f"✅ Successfully loaded CSV file")
        print(f"📈 Total events: {len(df)}")
        print()
        
        # Basic statistics
        print("📋 Basic Statistics:")
        print(f"   • Total DelegateChanged events: {len(df)}")
        print(f"   • Block range: {df['block_number'].min():,} to {df['block_number'].max():,}")
        print()
        
        # Unique delegators
        unique_delegators = df['delegator'].nunique()
        print(f"👥 Unique Delegators: {unique_delegators:,}")
        
        # Unique delegates (to_delegate)
        unique_delegates = df['to_delegate'].nunique()
        print(f"🎯 Unique Delegates (to_delegate): {unique_delegates:,}")
        
        # Unique from_delegates
        unique_from_delegates = df['from_delegate'].nunique()
        print(f"📤 Unique From Delegates: {unique_from_delegates:,}")
        
        print()
        print("🔍 Detailed Analysis:")
        
        # Check for zero address delegations
        zero_address = "0x0000000000000000000000000000000000000000"
        zero_from_count = len(df[df['from_delegate'] == zero_address])
        zero_to_count = len(df[df['to_delegate'] == zero_address])
        
        print(f"   • Events with zero address as from_delegate: {zero_from_count}")
        print(f"   • Events with zero address as to_delegate: {zero_to_count}")
        
        # Self-delegations (where delegator == to_delegate)
        self_delegations = len(df[df['delegator'] == df['to_delegate']])
        print(f"   • Self-delegations (delegator == to_delegate): {self_delegations}")
        
        # Delegation changes (not self-delegations and not from zero)
        actual_delegations = len(df[(df['delegator'] != df['to_delegate']) & 
                                   (df['from_delegate'] != zero_address)])
        print(f"   • Actual delegation changes: {actual_delegations}")
        
        print()
        print("📊 Top 10 Most Active Delegators:")
        top_delegators = df['delegator'].value_counts().head(10)
        for i, (delegator, count) in enumerate(top_delegators.items(), 1):
            print(f"   {i:2d}. {delegator}: {count} events")
        
        print()
        print("🎯 Top 10 Most Popular Delegates:")
        top_delegates = df['to_delegate'].value_counts().head(10)
        for i, (delegate, count) in enumerate(top_delegates.items(), 1):
            print(f"   {i:2d}. {delegate}: {count} times delegated to")
        
        print()
        print("📈 Summary:")
        print(f"   • Total unique addresses that have delegated: {unique_delegators:,}")
        print(f"   • Total unique addresses that have been delegated to: {unique_delegates:,}")
        print(f"   • Total DelegateChanged events captured: {len(df):,}")
        
        # Check for any potential data quality issues
        print()
        print("🔍 Data Quality Check:")
        
        # Check for duplicate events (same block, tx, log_index)
        duplicates = df.duplicated(subset=['block_number', 'transaction_hash', 'log_index']).sum()
        print(f"   • Duplicate events: {duplicates}")
        
        # Check for missing data
        missing_data = df.isnull().sum().sum()
        print(f"   • Missing data points: {missing_data}")
        
        if duplicates == 0 and missing_data == 0:
            print("   ✅ Data quality looks good!")
        
    except FileNotFoundError:
        print(f"❌ Error: Could not find {csv_file}")
    except Exception as e:
        print(f"❌ Error analyzing file: {e}")

if __name__ == "__main__":
    analyze_delegate_events()