#!/usr/bin/env python3
"""
Continue searching for DelegateChanged events from the last processed block to the current latest block
"""

import requests
import json
import csv
from datetime import datetime
from Crypto.Hash import keccak

# Configuration
MOONBEAM_RPC_URL = "https://rpc.api.moonbeam.network"
CONTRACT_ADDRESS = "0x511aB53F793683763E5a8829738301368a2411E3"

def keccak256(data):
    """Calculate keccak256 hash"""
    k = keccak.new(digest_bits=256)
    k.update(data)
    return k.hexdigest()

def get_delegate_changed_topic():
    """Get the topic hash for DelegateChanged event"""
    # DelegateChanged(address indexed delegator, address indexed fromDelegate, address indexed toDelegate)
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
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response text (first 500 chars): {response.text[:500]}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"HTTP Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Request failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Error response content: {e.response.text}")
        return None

def get_latest_block():
    """Get the latest block number"""
    result = make_rpc_request("eth_blockNumber", [])
    if result and "result" in result:
        return int(result["result"], 16)
    return None

def parse_delegate_changed_event(log):
    """Parse a DelegateChanged event log"""
    topics = log["topics"]
    
    # Extract addresses from topics (remove 0x prefix and leading zeros, then add 0x back)
    delegator = "0x" + topics[1][-40:]  # Last 40 chars (20 bytes)
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

def fetch_delegate_changed_events(from_block, to_block):
    """Fetch DelegateChanged events for a specific block range"""
    topic_hash = get_delegate_changed_topic()
    
    print(f"Searching blocks {from_block} to {to_block}")
    print(f"Contract: {CONTRACT_ADDRESS}")
    print(f"Topic hash: {topic_hash}")
    
    # Convert to hex
    from_block_hex = hex(from_block)
    to_block_hex = hex(to_block) if isinstance(to_block, int) else to_block
    
    filter_params = {
        "fromBlock": from_block_hex,
        "toBlock": to_block_hex,
        "address": CONTRACT_ADDRESS,
        "topics": [topic_hash]
    }
    
    print(f"Filter params: {filter_params}")
    
    result = make_rpc_request("eth_getLogs", [filter_params])
    
    if result and "result" in result:
        events = result["result"]
        print(f"Found {len(events)} events in this range")
        return events
    else:
        print("No events found or error occurred")
        return []

def read_existing_csv(filename):
    """Read existing CSV file and return the last block number processed"""
    try:
        with open(filename, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            if rows:
                last_block = max(int(row['block_number']) for row in rows)
                print(f"Last processed block in existing CSV: {last_block}")
                return last_block, rows
            return 0, []
    except FileNotFoundError:
        print(f"File {filename} not found, starting fresh")
        return 0, []

def append_events_to_csv(events, filename, existing_events):
    """Append new events to existing CSV file"""
    if not events:
        print("No new events to append")
        return
    
    # Parse events
    parsed_events = [parse_delegate_changed_event(event) for event in events]
    
    # Combine with existing events and sort by block number
    all_events = existing_events + parsed_events
    all_events.sort(key=lambda x: int(x['block_number']) if isinstance(x['block_number'], str) else x['block_number'])
    
    # Write all events to file
    fieldnames = ["block_number", "transaction_hash", "log_index", "delegator", "from_delegate", "to_delegate", "raw_data", "raw_topics"]
    
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_events)
    
    print(f"Updated {filename} with {len(parsed_events)} new events (total: {len(all_events)} events)")

def search_from_block_to_latest(start_block, existing_csv_file):
    """Search for events from start_block to latest block"""
    latest_block = get_latest_block()
    if not latest_block:
        print("Failed to get latest block")
        return []
    
    print(f"Latest block: {latest_block}")
    print(f"Searching from block {start_block} to {latest_block}")
    
    # Read existing events
    last_processed_block, existing_events = read_existing_csv(existing_csv_file)
    
    # Start from the block after the last processed one, or from start_block if no existing data
    search_start = max(start_block, last_processed_block + 1)
    
    if search_start > latest_block:
        print(f"Already up to date! Last processed block {last_processed_block} >= latest block {latest_block}")
        return existing_events
    
    print(f"Continuing search from block {search_start} to {latest_block}")
    
    all_new_events = []
    current_block = search_start
    
    # Search in chunks of 400 blocks to stay within API limits
    while current_block <= latest_block:
        end_block = min(current_block + 400, latest_block)
        
        print(f"\nRange {len(all_new_events)//400 + 1}: Blocks {current_block} to {end_block}")
        
        events = fetch_delegate_changed_events(current_block, end_block)
        if events:
            all_new_events.extend(events)
            print(f"  Found {len(events)} events in this range")
        else:
            print("  No events found in this range")
        
        current_block = end_block + 1
    
    # Update CSV file
    if all_new_events:
        append_events_to_csv(all_new_events, existing_csv_file, existing_events)
        
        # Show sample of new events
        print(f"\nNew events found: {len(all_new_events)}")
        for i, event in enumerate(all_new_events[:3]):  # Show first 3 new events
            parsed = parse_delegate_changed_event(event)
            print(f"New Event {i+1}:")
            print(f"  Block: {parsed['block_number']}")
            print(f"  Tx: {parsed['transaction_hash']}")
            print(f"  Delegator: {parsed['delegator']}")
            print(f"  From: {parsed['from_delegate']}")
            print(f"  To: {parsed['to_delegate']}")
            print()
    else:
        print("No new events found")
    
    return all_new_events

def main():
    """Main function"""
    print("Continuing DelegateChanged events search to latest block...")
    print(f"Contract: {CONTRACT_ADDRESS}")
    print(f"RPC Endpoint: {MOONBEAM_RPC_URL}")
    
    # Continue from the existing CSV file
    existing_csv = "DelegateChanged_events_20250922_140357.csv"
    
    # Continue from where we left off to the latest block
    new_events = search_from_block_to_latest(5326061, existing_csv)
    
    print(f"\nSearch completed!")

if __name__ == "__main__":
    main()