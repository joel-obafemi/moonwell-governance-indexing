#!/usr/bin/env python3
"""
Continue indexing DelegateChanged events from existing CSV file
"""

import requests
import json
import csv
from datetime import datetime
from Crypto.Hash import keccak

# Configuration - CORRECT CONTRACT ADDRESS
MOONBEAM_RPC_URL = "https://rpc.api.moonbeam.network"
CONTRACT_ADDRESS = "0x511aB53F793683763E5a8829738301368a2411E3"

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

def get_latest_block():
    """Get the latest block number"""
    result = make_rpc_request("eth_blockNumber", [])
    if result and "result" in result:
        return int(result["result"], 16)
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

def read_existing_csv():
    """Read existing CSV and find the last block processed"""
    try:
        with open("DelegateChanged_events_20250922_140357.csv", 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            if rows:
                last_block = max(int(row['block_number']) for row in rows)
                print(f"Found {len(rows)} existing events, last block: {last_block}")
                return last_block, rows
            return 0, []
    except FileNotFoundError:
        print("CSV file not found")
        return 0, []

def append_to_csv(new_events, existing_events):
    """Append new events to CSV"""
    if not new_events:
        print("No new events to add")
        return
    
    # Parse new events
    parsed_new = [parse_delegate_changed_event(event) for event in new_events]
    
    # Combine and sort all events
    all_events = existing_events + parsed_new
    all_events.sort(key=lambda x: int(x['block_number']))
    
    # Write back to CSV
    fieldnames = ["block_number", "transaction_hash", "log_index", "delegator", "from_delegate", "to_delegate", "raw_data", "raw_topics"]
    
    with open("DelegateChanged_events_20250922_140357.csv", 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_events)
    
    print(f"Added {len(parsed_new)} new events. Total events: {len(all_events)}")

def main():
    print("Continuing DelegateChanged event indexing...")
    print(f"Contract: {CONTRACT_ADDRESS}")
    
    # Read existing data
    last_block, existing_events = read_existing_csv()
    
    # Get latest block
    latest_block = get_latest_block()
    if not latest_block:
        print("Failed to get latest block")
        return
    
    print(f"Latest block: {latest_block}")
    
    # Continue from next block after last processed
    start_block = last_block + 1
    
    if start_block > latest_block:
        print("Already up to date!")
        return
    
    print(f"Searching from block {start_block} to {latest_block}")
    
    # Search in chunks
    all_new_events = []
    current_block = start_block
    
    while current_block <= latest_block:
        end_block = min(current_block + 400, latest_block)
        print(f"Searching blocks {current_block} to {end_block}...")
        
        events = fetch_events_in_range(current_block, end_block)
        if events:
            all_new_events.extend(events)
            print(f"  Found {len(events)} events")
        
        current_block = end_block + 1
    
    # Update CSV
    append_to_csv(all_new_events, existing_events)
    
    # Show summary
    if all_new_events:
        print(f"\nNew events summary:")
        for i, event in enumerate(all_new_events[:3]):
            parsed = parse_delegate_changed_event(event)
            print(f"Event {i+1}: Block {parsed['block_number']}, Delegator: {parsed['delegator']}")

if __name__ == "__main__":
    main()