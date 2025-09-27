#!/usr/bin/env python3
"""
Script to fetch VoteCast events from Moonriver blockchain
Contract: 0x2BE2e230e89c59c8E20E633C524AD2De246e7370
Starting from block: 2762967
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
CONTRACT_ADDRESS = "0x2BE2e230e89c59c8E20E633C524AD2De246e7370"
START_BLOCK = 2762967

# VoteCast event signature: VoteCast(address,uint256,uint8,uint256,string)
# This represents: VoteCast(address indexed voter, uint256 proposalId, uint8 support, uint256 votes, string reason)
VOTECAST_SIGNATURE = "VoteCast(address,uint256,uint8,uint256,string)"

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

def fetch_votecast_events(from_block: int = None, to_block: str = "latest", chunk_size: int = 1000) -> List[Dict[str, Any]]:
    """
    Fetch VoteCast events from the specified contract with chunking for large ranges
    """
    if from_block is None:
        from_block = START_BLOCK
    
    # Calculate topic[0] for VoteCast event
    topic0 = calculate_keccak256_topic(VOTECAST_SIGNATURE)
    print(f"VoteCast topic[0]: {topic0}")
    
    # Get latest block if needed
    if to_block == "latest":
        latest_block = get_latest_block()
        print(f"Latest block: {latest_block}")
        to_block = latest_block
    else:
        to_block = int(to_block)
    
    all_events = []
    current_from = from_block
    
    print(f"Fetching VoteCast events from block {from_block} to {to_block}")
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
    
    print(f"Total VoteCast events found: {len(all_events)}")
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

def decode_uint256_from_data(data: str, offset: int) -> int:
    """
    Decode a uint256 value from event data at the specified offset (in 32-byte chunks)
    """
    if data.startswith("0x"):
        data = data[2:]
    
    start_pos = offset * 64  # Each 32-byte chunk is 64 hex characters
    end_pos = start_pos + 64
    hex_value = data[start_pos:end_pos]
    
    return int(hex_value, 16) if hex_value else 0

def decode_string_from_data(data: str, offset: int) -> str:
    """
    Decode a string value from event data starting at the specified offset
    This is more complex as strings are dynamically sized
    """
    if data.startswith("0x"):
        data = data[2:]
    
    try:
        # First, get the offset to the string data
        string_offset_pos = offset * 64
        string_offset_hex = data[string_offset_pos:string_offset_pos + 64]
        string_offset = int(string_offset_hex, 16) * 2  # Convert to hex character offset
        
        # Get the length of the string
        length_hex = data[string_offset:string_offset + 64]
        length = int(length_hex, 16)
        
        # Get the actual string data
        string_start = string_offset + 64
        string_end = string_start + (length * 2)  # Each byte is 2 hex chars
        string_hex = data[string_start:string_end]
        
        # Convert hex to string
        string_bytes = bytes.fromhex(string_hex)
        return string_bytes.decode('utf-8', errors='ignore')
    
    except Exception as e:
        print(f"Error decoding string: {e}")
        return ""

def parse_votecast_event(event: Dict) -> Dict:
    """
    Parse a VoteCast event log entry
    """
    topics = event.get("topics", [])
    data = event.get("data", "0x")
    
    # Extract voter address from topics[1] (indexed parameter)
    voter = decode_address_from_topic(topics[1]) if len(topics) > 1 else ""
    
    # Extract data from the data field
    # proposalId (uint256) - offset 0
    # support (uint8) - offset 1 
    # votes (uint256) - offset 2
    # reason (string) - offset 3
    
    proposal_id = decode_uint256_from_data(data, 0)
    support = decode_uint256_from_data(data, 1)  # uint8 but stored as uint256
    votes = decode_uint256_from_data(data, 2)
    reason = decode_string_from_data(data, 3)
    
    # Convert votes from wei to readable format (assuming 18 decimals)
    votes_formatted = votes / (10 ** 18) if votes > 0 else 0
    
    return {
        "block_number": int(event["blockNumber"], 16),
        "transaction_hash": event["transactionHash"],
        "log_index": int(event["logIndex"], 16),
        "voter": voter,
        "proposal_id": str(proposal_id),  # Keep as string to avoid scientific notation
        "support": int(support),
        "votes": votes_formatted,
        "reason": reason,
        "raw_data": data,
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
        filename = f"Moonriver_VoteCast_events_{timestamp}.csv"
    
    # Define CSV headers
    headers = [
        "block_number",
        "transaction_hash", 
        "log_index",
        "voter",
        "proposal_id",
        "support",
        "votes",
        "reason",
        "raw_data",
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
            unique_voters = len(set(event["voter"] for event in events))
            unique_proposals = len(set(event["proposal_id"] for event in events))
            
            # Support distribution
            support_counts = {}
            for event in events:
                support = event["support"]
                support_counts[support] = support_counts.get(support, 0) + 1
            
            print(f"📊 Summary:")
            print(f"   Block range: {min_block} → {max_block}")
            print(f"   Unique voters: {unique_voters}")
            print(f"   Unique proposals: {unique_proposals}")
            print(f"   Total votes: {len(events)}")
            print(f"   Support distribution: {support_counts}")
            
    except Exception as e:
        print(f"❌ Error saving to CSV: {e}")

def main():
    """
    Main function to fetch and save VoteCast events
    """
    print("🚀 Starting Moonriver VoteCast Event Indexer")
    print("=" * 60)
    print(f"Network: Moonriver")
    print(f"Contract: {CONTRACT_ADDRESS}")
    print(f"Starting block: {START_BLOCK}")
    print(f"Event: VoteCast")
    print("=" * 60)
    
    try:
        # Fetch events
        events = fetch_votecast_events(from_block=START_BLOCK)
        
        if not events:
            print("No VoteCast events found")
            return
        
        # Parse events
        print("Parsing events...")
        parsed_events = []
        for event in events:
            try:
                parsed_event = parse_votecast_event(event)
                parsed_events.append(parsed_event)
            except Exception as e:
                print(f"Error parsing event: {e}")
                continue
        
        print(f"Successfully parsed {len(parsed_events)} events")
        
        # Save to CSV
        save_events_to_csv(parsed_events)
        
        print("🎉 VoteCast event indexing completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during indexing: {e}")
        raise

if __name__ == "__main__":
    main()