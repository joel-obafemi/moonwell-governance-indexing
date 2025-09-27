#!/usr/bin/env python3

import requests
import json
import csv
import time
from datetime import datetime

# Configuration
RPC_URL = "https://rpc.api.moonbeam.network"
CONTRACT_ADDRESS = "0x511aB53F793683763E5a8829738301368a2411E3"
DELEGATE_CHANGED_TOPIC = "0x3134e8a2e6d97e929a7e54011ea5485d7d196dd5f0ba4d4ef95803e8e3fc257f"

# Block range - continuing from where we left off
START_BLOCK = 3800122  # Next block after last recorded event
END_BLOCK = 5329264    # Block before our existing data starts
CHUNK_SIZE = 1000      # Process 1000 blocks at a time

def make_rpc_call(method, params):
    """Make RPC call with error handling and retries"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": 1
            }
            
            response = requests.post(RPC_URL, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if "error" in result:
                print(f"RPC Error: {result['error']}")
                return None
                
            return result.get("result")
            
        except requests.exceptions.RequestException as e:
            print(f"Request failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                return None
    
    return None

def parse_delegate_changed_event(log):
    """Parse DelegateChanged event from log entry"""
    try:
        topics = log.get('topics', [])
        if len(topics) != 4:
            return None
            
        # Extract addresses from topics (remove 0x and pad to get address)
        delegator = "0x" + topics[1][-40:]
        from_delegate = "0x" + topics[2][-40:]
        to_delegate = "0x" + topics[3][-40:]
        
        return {
            'block_number': int(log['blockNumber'], 16),
            'transaction_hash': log['transactionHash'],
            'log_index': int(log['logIndex'], 16),
            'delegator': delegator,
            'from_delegate': from_delegate,
            'to_delegate': to_delegate,
            'raw_data': log.get('data', ''),
            'raw_topics': json.dumps(topics)
        }
    except Exception as e:
        print(f"Error parsing event: {e}")
        return None

def search_events_in_range(start_block, end_block):
    """Search for DelegateChanged events in a block range"""
    print(f"Searching blocks {start_block:,} to {end_block:,}...")
    
    params = [
        {
            "fromBlock": hex(start_block),
            "toBlock": hex(end_block),
            "address": CONTRACT_ADDRESS,
            "topics": [DELEGATE_CHANGED_TOPIC]
        }
    ]
    
    logs = make_rpc_call("eth_getLogs", params)
    if logs is None:
        print(f"  Failed to get logs for blocks {start_block:,} to {end_block:,}")
        return []
    
    events = []
    for log in logs:
        event = parse_delegate_changed_event(log)
        if event:
            events.append(event)
    
    if events:
        print(f"  Found {len(events)} events")
    else:
        print(f"  No events found")
    
    return events

def main():
    print("🔍 Continue Indexing Early DelegateChanged Events")
    print("=" * 50)
    print(f"Contract: {CONTRACT_ADDRESS}")
    print(f"Block range: {START_BLOCK:,} to {END_BLOCK:,}")
    print(f"Total blocks to search: {END_BLOCK - START_BLOCK + 1:,}")
    print()
    
    # Output file for continuing early events
    output_file = "early_events_continue.csv"
    
    # Write CSV header
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['block_number', 'transaction_hash', 'log_index', 'delegator', 'from_delegate', 'to_delegate', 'raw_data', 'raw_topics'])
    
    all_events = []
    current_block = START_BLOCK
    
    try:
        while current_block <= END_BLOCK:
            chunk_end = min(current_block + CHUNK_SIZE - 1, END_BLOCK)
            
            # Search for events in this chunk
            events = search_events_in_range(current_block, chunk_end)
            
            # Save events immediately if found
            if events:
                with open(output_file, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    for event in events:
                        writer.writerow([
                            event['block_number'],
                            event['transaction_hash'],
                            event['log_index'],
                            event['delegator'],
                            event['from_delegate'],
                            event['to_delegate'],
                            event['raw_data'],
                            event['raw_topics']
                        ])
                
                all_events.extend(events)
                print(f"  💾 Saved {len(events)} events to {output_file}")
            
            # Progress update every 50,000 blocks
            if (current_block - START_BLOCK) % 50000 == 0 and current_block > START_BLOCK:
                progress = ((current_block - START_BLOCK) / (END_BLOCK - START_BLOCK)) * 100
                print(f"📊 Progress: {progress:.1f}% - Block {current_block:,} - Total events found: {len(all_events)}")
            
            current_block = chunk_end + 1
            
            # Small delay to avoid overwhelming the RPC
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print(f"\n⏸️  Indexing interrupted at block {current_block:,}")
        print(f"📊 Events found so far: {len(all_events)}")
        print(f"💾 Data saved to: {output_file}")
        return
    
    print(f"\n✅ Early events indexing completed!")
    print(f"📊 Total events found: {len(all_events)}")
    print(f"📁 Block range covered: {START_BLOCK:,} to {END_BLOCK:,}")
    print(f"💾 Data saved to: {output_file}")
    
    if all_events:
        print(f"\n📈 Event Summary:")
        print(f"   First event: Block {min(event['block_number'] for event in all_events):,}")
        print(f"   Last event:  Block {max(event['block_number'] for event in all_events):,}")
        
        # Show sample of events found
        print(f"\n🔍 Sample events:")
        for i, event in enumerate(all_events[:3]):
            print(f"   {i+1}. Block {event['block_number']:,}: {event['delegator']} -> {event['to_delegate']}")
        if len(all_events) > 3:
            print(f"   ... and {len(all_events) - 3} more events")

if __name__ == "__main__":
    main()