#!/usr/bin/env python3
"""
Index early DelegateChanged events from contract creation to fill the gap
"""

import requests
import json
import csv
import os
from datetime import datetime
from Crypto.Hash import keccak

# Configuration
MOONBEAM_RPC_URL = "https://rpc.api.moonbeam.network"
CONTRACT_ADDRESS = "0x511aB53F793683763E5a8829738301368a2411E3"
CSV_FILE = "DelegateChanged_events_20250922_140357.csv"
TEMP_CSV_FILE = "early_events_temp.csv"

# Block range for early events
START_BLOCK = 1005779  # Contract creation block
END_BLOCK = 5329264    # Just before our current earliest event (5329265)

def keccak256(data):
    """Calculate keccak256 hash"""
    k = keccak.new(digest_bits=256)
    k.update(data)
    return k.hexdigest()

def get_delegate_changed_topic():
    """Get the topic hash for DelegateChanged event"""
    event_signature = "DelegateChanged(address,address,address)"
    topic_hash = keccak256(event_signature.encode('utf-8'))
    return "0x" + topic_hash

def make_rpc_request(method, params):
    """Make RPC request to Moonbeam"""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }
    
    try:
        response = requests.post(MOONBEAM_RPC_URL, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"HTTP Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def parse_delegate_changed_event(log):
    """Parse a DelegateChanged event log"""
    topics = log["topics"]
    
    # Extract addresses from topics
    delegator = "0x" + topics[1][-40:]
    from_delegate = "0x" + topics[2][-40:]
    to_delegate = "0x" + topics[3][-40:]
    
    return {
        "block_number": int(log["blockNumber"], 16),
        "transaction_hash": log["transactionHash"],
        "log_index": int(log["logIndex"], 16),
        "delegator": delegator,
        "from_delegate": from_delegate,
        "to_delegate": to_delegate,
        "raw_data": log["data"],
        "raw_topics": json.dumps(topics)
    }

def fetch_events_in_range(from_block, to_block):
    """Fetch DelegateChanged events for a specific block range"""
    topic_hash = get_delegate_changed_topic()
    
    filter_params = {
        "fromBlock": hex(from_block),
        "toBlock": hex(to_block),
        "address": CONTRACT_ADDRESS,
        "topics": [topic_hash]
    }
    
    result = make_rpc_request("eth_getLogs", [filter_params])
    
    if result and "result" in result:
        return result["result"]
    return []

def save_early_events_to_temp(events):
    """Save early events to temporary CSV file"""
    if not events:
        return
    
    # Parse events
    parsed_events = [parse_delegate_changed_event(event) for event in events]
    
    # Sort by block number
    parsed_events.sort(key=lambda x: x['block_number'])
    
    # Write to temporary CSV
    fieldnames = ["block_number", "transaction_hash", "log_index", "delegator", "from_delegate", "to_delegate", "raw_data", "raw_topics"]
    
    file_exists = os.path.exists(TEMP_CSV_FILE)
    
    with open(TEMP_CSV_FILE, 'a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerows(parsed_events)
    
    print(f"✓ Added {len(parsed_events)} early events to temporary file")
    
    # Show the new events
    for event in parsed_events:
        print(f"  Block {event['block_number']}: {event['delegator']} -> {event['to_delegate']}")

def merge_csv_files():
    """Merge early events with existing events and create final sorted CSV"""
    print("\n🔄 Merging early events with existing events...")
    
    all_events = []
    
    # Read early events from temp file
    if os.path.exists(TEMP_CSV_FILE):
        with open(TEMP_CSV_FILE, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            early_events = list(reader)
            all_events.extend(early_events)
            print(f"📥 Loaded {len(early_events)} early events")
    
    # Read existing events
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            existing_events = list(reader)
            all_events.extend(existing_events)
            print(f"📥 Loaded {len(existing_events)} existing events")
    
    # Sort all events by block number
    all_events.sort(key=lambda x: int(x['block_number']))
    
    # Write merged and sorted events to main CSV
    fieldnames = ["block_number", "transaction_hash", "log_index", "delegator", "from_delegate", "to_delegate", "raw_data", "raw_topics"]
    
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_events)
    
    print(f"✅ Merged CSV created with {len(all_events)} total events")
    
    # Clean up temp file
    if os.path.exists(TEMP_CSV_FILE):
        os.remove(TEMP_CSV_FILE)
        print("🧹 Cleaned up temporary file")

def main():
    print("🔍 Indexing Early DelegateChanged Events")
    print("=" * 50)
    print(f"Contract: {CONTRACT_ADDRESS}")
    print(f"Block range: {START_BLOCK:,} to {END_BLOCK:,}")
    print(f"Total blocks to search: {END_BLOCK - START_BLOCK + 1:,}")
    print()
    
    # Remove temp file if it exists
    if os.path.exists(TEMP_CSV_FILE):
        os.remove(TEMP_CSV_FILE)
    
    # Search in chunks
    current_block = START_BLOCK
    total_early_events = 0
    chunk_size = 1000  # Larger chunks for older blocks
    
    while current_block <= END_BLOCK:
        end_block = min(current_block + chunk_size - 1, END_BLOCK)
        print(f"Searching blocks {current_block:,} to {end_block:,}...")
        
        events = fetch_events_in_range(current_block, end_block)
        if events:
            save_early_events_to_temp(events)
            total_early_events += len(events)
        else:
            print("  No events found")
        
        current_block = end_block + 1
        
        # Show progress every 50,000 blocks
        if (current_block - START_BLOCK) % 50000 == 0:
            progress = ((current_block - START_BLOCK) / (END_BLOCK - START_BLOCK + 1)) * 100
            print(f"\n--- Progress: {progress:.1f}% complete, found {total_early_events} early events so far ---\n")
    
    print(f"\n🎉 Early event indexing completed!")
    print(f"Total early events found: {total_early_events}")
    
    # Merge with existing events
    merge_csv_files()
    
    print(f"\n📊 Final Result:")
    # Count final events
    with open(CSV_FILE, 'r', newline='', encoding='utf-8') as file:
        total_final_events = sum(1 for line in file) - 1  # Subtract header
    print(f"Total events in final CSV: {total_final_events}")

if __name__ == "__main__":
    main()