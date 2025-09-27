#!/usr/bin/env python3
"""
Script to fetch DelegateChanged events from Moonriver blockchain
Contract: 0xBb8d88bcD9749636BC4D2bE22aaC4Bb3B01A58F1
Starting from block: 1462096
"""

import requests
import json
import csv
from Crypto.Hash import keccak
from typing import List, Dict, Any
from datetime import datetime
import time

# Configuration for Moonriver
MOONRIVER_RPC_URL = "https://moonriver.api.onfinality.io/public"
CONTRACT_ADDRESS = "0xBb8d88bcD9749636BC4D2bE22aaC4Bb3B01A58F1"
START_BLOCK = 1462096

# DelegateChanged event signature: DelegateChanged(address,address,address)
# This represents: DelegateChanged(address indexed delegator, address indexed fromDelegate, address indexed toDelegate)
DELEGATE_CHANGED_SIGNATURE = "DelegateChanged(address,address,address)"

def calculate_keccak256_topic(signature: str) -> str:
    """
    Calculate the keccak256 hash of an event signature to get the topic[0]
    Using pycryptodome for proper keccak256 implementation
    """
    k = keccak.new(digest_bits=256)
    k.update(signature.encode('utf-8'))
    return "0x" + k.hexdigest()

def make_rpc_request(method: str, params: List[Any], timeout: int = 30) -> Dict[Any, Any]:
    """
    Make a JSON-RPC request to the Moonriver endpoint with timeout and retry logic
    """
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(MOONRIVER_RPC_URL, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            result = response.json()
            if "error" in result:
                print(f"RPC Error: {result['error']}")
                if attempt < max_retries - 1:
                    print(f"Retrying... (attempt {attempt + 2}/{max_retries})")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return result
            
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise
    
    return {}

def get_latest_block() -> int:
    """
    Get the latest block number from Moonriver
    """
    response = make_rpc_request("eth_blockNumber", [])
    if "result" in response:
        return int(response["result"], 16)
    return 0

def fetch_delegate_changed_events(from_block: int = None, to_block: str = "latest", chunk_size: int = 1000) -> List[Dict[str, Any]]:
    """
    Fetch DelegateChanged events from the specified contract with chunking for large ranges
    """
    if from_block is None:
        from_block = START_BLOCK
    
    # Calculate topic[0] for DelegateChanged event
    topic0 = calculate_keccak256_topic(DELEGATE_CHANGED_SIGNATURE)
    print(f"DelegateChanged topic[0]: {topic0}")
    
    # Get latest block if needed
    if to_block == "latest":
        latest_block = get_latest_block()
        print(f"Latest block: {latest_block}")
        to_block = latest_block
    else:
        to_block = int(to_block)
    
    all_events = []
    current_from = from_block
    
    print(f"Fetching DelegateChanged events from block {from_block} to {to_block}")
    print(f"Contract address: {CONTRACT_ADDRESS}")
    
    while current_from <= to_block:
        current_to = min(current_from + chunk_size - 1, to_block)
        
        print(f"Fetching chunk: blocks {current_from} to {current_to}")
        
        filter_params = {
            "fromBlock": hex(current_from),
            "toBlock": hex(current_to),
            "address": CONTRACT_ADDRESS,
            "topics": [topic0]
        }
        
        response = make_rpc_request("eth_getLogs", [filter_params])
        
        if "result" in response:
            chunk_events = response["result"]
            print(f"Found {len(chunk_events)} events in this chunk")
            all_events.extend(chunk_events)
        else:
            print(f"No result in response for chunk {current_from}-{current_to}")
            if "error" in response:
                print(f"Error: {response['error']}")
        
        current_from = current_to + 1
        
        # Small delay to avoid rate limiting
        time.sleep(0.1)
    
    print(f"Total DelegateChanged events found: {len(all_events)}")
    return all_events

def decode_address_from_topic(topic: str) -> str:
    """
    Decode an address from a topic (removes padding zeros)
    """
    if topic.startswith("0x"):
        topic = topic[2:]
    # Remove leading zeros and add 0x prefix
    address = "0x" + topic[-40:]  # Last 40 characters (20 bytes)
    return address.lower()

def parse_delegate_changed_event(event: Dict) -> Dict:
    """
    Parse a DelegateChanged event log entry
    """
    topics = event.get("topics", [])
    
    # Extract addresses from topics
    delegator = decode_address_from_topic(topics[1]) if len(topics) > 1 else ""
    from_delegate = decode_address_from_topic(topics[2]) if len(topics) > 2 else ""
    to_delegate = decode_address_from_topic(topics[3]) if len(topics) > 3 else ""
    
    return {
        "block_number": int(event["blockNumber"], 16),
        "transaction_hash": event["transactionHash"],
        "log_index": int(event["logIndex"], 16),
        "delegator": delegator,
        "from_delegate": from_delegate,
        "to_delegate": to_delegate,
        "raw_topics": json.dumps(topics)
    }

def save_events_to_csv(events: List[Dict], filename: str = None):
    """
    Save events to CSV file with timestamp
    """
    if not events:
        print("No events to save")
        return
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Moonriver_DelegateChanged_events_{timestamp}.csv"
    
    # Define CSV headers
    headers = [
        "block_number",
        "transaction_hash", 
        "log_index",
        "delegator",
        "from_delegate",
        "to_delegate",
        "raw_topics"
    ]
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for event in events:
                writer.writerow(event)
        
        print(f"✅ Successfully saved {len(events)} events to {filename}")
        
        # Print summary statistics
        if events:
            min_block = min(event["block_number"] for event in events)
            max_block = max(event["block_number"] for event in events)
            unique_delegators = len(set(event["delegator"] for event in events))
            
            print(f"📊 Summary:")
            print(f"   Block range: {min_block} → {max_block}")
            print(f"   Unique delegators: {unique_delegators}")
            print(f"   Total delegation changes: {len(events)}")
            
    except Exception as e:
        print(f"❌ Error saving to CSV: {e}")

def main():
    """
    Main function to fetch and save DelegateChanged events
    """
    print("🚀 Starting Moonriver DelegateChanged Event Indexer")
    print("=" * 60)
    print(f"Network: Moonriver")
    print(f"Contract: {CONTRACT_ADDRESS}")
    print(f"Starting block: {START_BLOCK}")
    print(f"Event: DelegateChanged")
    print("=" * 60)
    
    try:
        # Fetch events
        events = fetch_delegate_changed_events(from_block=START_BLOCK)
        
        if not events:
            print("No DelegateChanged events found")
            return
        
        # Parse events
        print("Parsing events...")
        parsed_events = []
        for event in events:
            try:
                parsed_event = parse_delegate_changed_event(event)
                parsed_events.append(parsed_event)
            except Exception as e:
                print(f"Error parsing event: {e}")
                continue
        
        print(f"Successfully parsed {len(parsed_events)} events")
        
        # Save to CSV
        save_events_to_csv(parsed_events)
        
        print("🎉 DelegateChanged event indexing completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during indexing: {e}")
        raise

if __name__ == "__main__":
    main()