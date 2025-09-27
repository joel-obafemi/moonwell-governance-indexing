#!/usr/bin/env python3
"""
Incremental indexing of DelegateChanged events - saves as it finds them
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

def get_last_processed_block():
    """Get the last block number from CSV file"""
    try:
        with open(CSV_FILE, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            if rows:
                last_block = max(int(row['block_number']) for row in rows)
                print(f"Found {len(rows)} existing events, last block: {last_block}")
                return last_block
            return 0
    except FileNotFoundError:
        print("CSV file not found, starting fresh")
        return 0

def append_events_immediately(events):
    """Append new events to CSV file immediately"""
    if not events:
        return
    
    # Parse events
    parsed_events = [parse_delegate_changed_event(event) for event in events]
    
    # Check if file exists and has header
    file_exists = os.path.exists(CSV_FILE)
    needs_header = not file_exists
    
    if file_exists:
        # Check if file is empty or only has header
        with open(CSV_FILE, 'r', newline='', encoding='utf-8') as file:
            content = file.read().strip()
            if not content or content.count('\n') == 0:
                needs_header = True
    
    # Append to CSV
    fieldnames = ["block_number", "transaction_hash", "log_index", "delegator", "from_delegate", "to_delegate", "raw_data", "raw_topics"]
    
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        if needs_header:
            writer.writeheader()
        
        writer.writerows(parsed_events)
    
    print(f"✓ Added {len(parsed_events)} new events to CSV")
    
    # Show the new events
    for event in parsed_events:
        print(f"  Block {event['block_number']}: {event['delegator']} -> {event['to_delegate']}")

def main():
    print("Starting incremental DelegateChanged event indexing...")
    print(f"Contract: {CONTRACT_ADDRESS}")
    print(f"CSV File: {CSV_FILE}")
    
    # Get last processed block
    last_block = get_last_processed_block()
    
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
    
    # Search in chunks and save immediately
    current_block = start_block
    total_new_events = 0
    
    while current_block <= latest_block:
        end_block = min(current_block + 400, latest_block)
        print(f"\nSearching blocks {current_block} to {end_block}...")
        
        events = fetch_events_in_range(current_block, end_block)
        if events:
            append_events_immediately(events)
            total_new_events += len(events)
        else:
            print("  No events found")
        
        current_block = end_block + 1
        
        # Show progress every 50 chunks
        if (current_block - start_block) % 20000 == 0:
            print(f"\n--- Progress: Processed up to block {end_block}, found {total_new_events} new events so far ---")
    
    print(f"\n🎉 Indexing completed!")
    print(f"Total new events found: {total_new_events}")
    
    # Final count
    final_count = get_last_processed_block()
    with open(CSV_FILE, 'r', newline='', encoding='utf-8') as file:
        total_rows = sum(1 for line in file) - 1  # Subtract header
    print(f"Total events in CSV: {total_rows}")

if __name__ == "__main__":
    main()