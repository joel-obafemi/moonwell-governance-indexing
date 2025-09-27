#!/usr/bin/env python3
"""
Analyze DelegateChanged events to get unique delegators and delegates (no pandas)
"""

import csv
from collections import Counter

def analyze_delegate_events():
    """Analyze the DelegateChanged events CSV file"""
    
    csv_file = "DelegateChanged_events_20250922_140357.csv"
    
    print("📊 Analyzing DelegateChanged Events")
    print("=" * 50)
    
    try:
        with open(csv_file, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            # Collect all data
            events = []
            delegators = set()
            delegates = set()
            from_delegates = set()
            delegator_counts = Counter()
            delegate_counts = Counter()
            
            zero_address = "0x0000000000000000000000000000000000000000"
            zero_from_count = 0
            zero_to_count = 0
            self_delegations = 0
            actual_delegations = 0
            
            block_numbers = []
            
            for row in reader:
                events.append(row)
                
                delegator = row['delegator']
                to_delegate = row['to_delegate']
                from_delegate = row['from_delegate']
                
                # Collect unique addresses
                delegators.add(delegator)
                delegates.add(to_delegate)
                from_delegates.add(from_delegate)
                
                # Count occurrences
                delegator_counts[delegator] += 1
                delegate_counts[to_delegate] += 1
                
                # Track block numbers
                block_numbers.append(int(row['block_number']))
                
                # Analyze delegation patterns
                if from_delegate == zero_address:
                    zero_from_count += 1
                if to_delegate == zero_address:
                    zero_to_count += 1
                if delegator == to_delegate:
                    self_delegations += 1
                if delegator != to_delegate and from_delegate != zero_address:
                    actual_delegations += 1
            
            total_events = len(events)
            
            print(f"✅ Successfully loaded CSV file")
            print(f"📈 Total events: {total_events:,}")
            print()
            
            # Basic statistics
            print("📋 Basic Statistics:")
            print(f"   • Total DelegateChanged events: {total_events:,}")
            print(f"   • Block range: {min(block_numbers):,} to {max(block_numbers):,}")
            print()
            
            # Unique counts
            print(f"👥 Unique Delegators: {len(delegators):,}")
            print(f"🎯 Unique Delegates (to_delegate): {len(delegates):,}")
            print(f"📤 Unique From Delegates: {len(from_delegates):,}")
            
            print()
            print("🔍 Detailed Analysis:")
            print(f"   • Events with zero address as from_delegate: {zero_from_count:,}")
            print(f"   • Events with zero address as to_delegate: {zero_to_count:,}")
            print(f"   • Self-delegations (delegator == to_delegate): {self_delegations:,}")
            print(f"   • Actual delegation changes: {actual_delegations:,}")
            
            print()
            print("📊 Top 10 Most Active Delegators:")
            top_delegators = delegator_counts.most_common(10)
            for i, (delegator, count) in enumerate(top_delegators, 1):
                print(f"   {i:2d}. {delegator}: {count} events")
            
            print()
            print("🎯 Top 10 Most Popular Delegates:")
            top_delegates = delegate_counts.most_common(10)
            for i, (delegate, count) in enumerate(top_delegates, 1):
                print(f"   {i:2d}. {delegate}: {count} times delegated to")
            
            print()
            print("📈 Summary:")
            print(f"   • Total unique addresses that have delegated: {len(delegators):,}")
            print(f"   • Total unique addresses that have been delegated to: {len(delegates):,}")
            print(f"   • Total DelegateChanged events captured: {total_events:,}")
            
            # Data quality check
            print()
            print("🔍 Data Quality Check:")
            
            # Check for potential duplicates by creating a set of unique identifiers
            unique_events = set()
            duplicates = 0
            
            for event in events:
                event_id = (event['block_number'], event['transaction_hash'], event['log_index'])
                if event_id in unique_events:
                    duplicates += 1
                else:
                    unique_events.add(event_id)
            
            print(f"   • Duplicate events: {duplicates}")
            
            # Check for missing critical data
            missing_data = 0
            for event in events:
                if not event['delegator'] or not event['to_delegate'] or not event['block_number']:
                    missing_data += 1
            
            print(f"   • Events with missing critical data: {missing_data}")
            
            if duplicates == 0 and missing_data == 0:
                print("   ✅ Data quality looks good!")
            
            print()
            print("🎉 Analysis Complete!")
            
    except FileNotFoundError:
        print(f"❌ Error: Could not find {csv_file}")
    except Exception as e:
        print(f"❌ Error analyzing file: {e}")

if __name__ == "__main__":
    analyze_delegate_events()