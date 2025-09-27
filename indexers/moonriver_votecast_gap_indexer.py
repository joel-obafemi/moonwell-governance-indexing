#!/usr/bin/env python3
"""
Moonriver VoteCast Gap Indexer
Specifically indexes the gap between blocks 2,863,449 and 2,905,967
that was missed due to incorrect event signature.
"""

import requests
import json
import csv
import os
from Crypto.Hash import keccak
from typing import List, Dict, Any
from datetime import datetime
import time

# Configuration
MOONRIVER_RPC_URL = "https://moonriver.api.onfinality.io/public"
CONTRACT_ADDRESS = "0x2BE2e230e89c59c8E20E633C524AD2De246e7370"
START_BLOCK = 2863449  # First VoteCast event block
END_BLOCK = 2905966    # Last block before the indexer resumed

# Correct event signature for VoteCast(address,uint256,uint8,uint256)
VOTECAST_SIGNATURE = "VoteCast(address,uint256,uint8,uint256)"

def calculate_keccak256_topic(signature: str) -> str:
    """Calculate the keccak256 hash of an event signature."""
    hash_obj = keccak.new(digest_bits=256)
    hash_obj.update(signature.encode('utf-8'))
    return "0x" + hash_obj.hexdigest()

def make_rpc_request(method: str, params: List[Any], timeout: int = 30) -> Dict[Any, Any]:
    """Make an RPC request with error handling and retries."""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(MOONRIVER_RPC_URL, json=payload, timeout=timeout)
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                print(f"RPC Error: {result['error']}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return {}
            
            return result
        except Exception as e:
            print(f"Request failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return {}
    
    return {}

def decode_address_from_topic(topic: str) -> str:
    """Decode an address from a topic (remove padding zeros)."""
    if topic.startswith("0x"):
        topic = topic[2:]
    # Remove leading zeros and add 0x prefix
    return "0x" + topic[-40:]

def parse_votecast_event(event: Dict) -> Dict:
    """Parse a VoteCast event from raw log data."""
    try:
        # Extract voter from topics[1]
        voter = decode_address_from_topic(event["topics"][1]) if len(event["topics"]) > 1 else ""
        
        # Parse data field for proposal_id, support, votes
        data = event["data"]
        if data.startswith("0x"):
            data = data[2:]
        
        # Each parameter is 32 bytes (64 hex chars)
        proposal_id = int(data[0:64], 16) if len(data) >= 64 else 0
        support = int(data[64:128], 16) if len(data) >= 128 else 0
        votes = int(data[128:192], 16) if len(data) >= 192 else 0
        
        return {
            "block_number": int(event["blockNumber"], 16),
            "transaction_hash": event["transactionHash"],
            "log_index": int(event["logIndex"], 16),
            "voter": voter,
            "proposal_id": proposal_id,
            "support": support,
            "votes": votes,
            "raw_data": event["data"],
            "raw_topics": json.dumps(event["topics"])
        }
    except Exception as e:
        print(f"Error parsing event: {e}")
        return {}

def fetch_events_chunk(from_block: int, to_block: int, topic0: str) -> List[Dict]:
    """Fetch VoteCast events for a specific block range."""
    params = [{
        "fromBlock": hex(from_block),
        "toBlock": hex(to_block),
        "address": CONTRACT_ADDRESS,
        "topics": [topic0]
    }]
    
    result = make_rpc_request("eth_getLogs", params)
    
    if "result" in result:
        return result["result"]
    else:
        print(f"Failed to fetch events for blocks {from_block}-{to_block}")
        return []

def main():
    print("🔧 Starting Moonriver VoteCast Gap Indexer")
    print("=" * 60)
    print(f"Network: Moonriver")
    print(f"Contract: {CONTRACT_ADDRESS}")
    print(f"Event: VoteCast")
    print(f"Gap Range: {START_BLOCK:,} to {END_BLOCK:,}")
    print("=" * 60)
    
    # Calculate topic
    topic0 = calculate_keccak256_topic(VOTECAST_SIGNATURE)
    print(f"VoteCast topic[0]: {topic0}")
    
    # Initialize CSV file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"Moonriver_VoteCast_gap_{START_BLOCK}_{END_BLOCK}_{timestamp}.csv"
    
    # Write CSV header
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['block_number', 'transaction_hash', 'log_index', 'voter', 'proposal_id', 'support', 'votes', 'raw_data', 'raw_topics']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
    
    print(f"📝 Initialized CSV: {csv_filename}")
    
    # Process in chunks of 1000 blocks
    chunk_size = 1000
    total_events = 0
    
    current_block = START_BLOCK
    while current_block <= END_BLOCK:
        chunk_end = min(current_block + chunk_size - 1, END_BLOCK)
        
        print(f"🔍 Fetching chunk: blocks {current_block:,} to {chunk_end:,}")
        
        # Fetch events for this chunk
        raw_events = fetch_events_chunk(current_block, chunk_end, topic0)
        
        if raw_events:
            print(f"✅ Found {len(raw_events)} events in this chunk")
            
            # Parse and save events
            parsed_events = []
            for raw_event in raw_events:
                parsed_event = parse_votecast_event(raw_event)
                if parsed_event:
                    parsed_events.append(parsed_event)
            
            # Append to CSV
            if parsed_events:
                with open(csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['block_number', 'transaction_hash', 'log_index', 'voter', 'proposal_id', 'support', 'votes', 'raw_data', 'raw_topics']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writerows(parsed_events)
                
                total_events += len(parsed_events)
                print(f"💾 Saved {len(parsed_events)} events to CSV")
        else:
            print("📭 Found 0 events in this chunk")
        
        current_block = chunk_end + 1
        
        # Small delay to avoid overwhelming the RPC
        time.sleep(0.1)
    
    print("\n" + "=" * 60)
    print(f"🎉 Gap indexing completed!")
    print(f"📊 Total events found: {total_events:,}")
    print(f"📁 CSV file: {csv_filename}")
    print(f"🔢 Block range: {START_BLOCK:,} to {END_BLOCK:,}")
    print("=" * 60)

if __name__ == "__main__":
    main()