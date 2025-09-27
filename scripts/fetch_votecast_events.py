#!/usr/bin/env python3
"""
Script to fetch VoteCast events from Moonbeam blockchain using Blast API
Contract: 0x9A8464C4C11CeA17e191653Deb7CdC1bE30F1Af4
Starting from block: 5783212
"""

import requests
import json
import csv
from Crypto.Hash import keccak
from typing import List, Dict, Any
from datetime import datetime
import time

# Configuration
MOONBEAM_RPC_URL = "https://moonbeam.blastapi.io/757c063c-a925-415d-b8f6-79c7e94b1737"
CONTRACT_ADDRESS = "0x9A8464C4C11CeA17e191653Deb7CdC1bE30F1Af4"
START_BLOCK = 5783212

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
    Make a JSON-RPC request to the Moonbeam endpoint with timeout and retry logic
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
            response = requests.post(MOONBEAM_RPC_URL, json=payload, headers=headers, timeout=timeout)
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"HTTP error {response.status_code}: {response.text}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    raise Exception(f"HTTP error {response.status_code}")
                    
        except requests.exceptions.Timeout:
            print(f"Request timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                raise Exception("Request timeout after all retries")
        except Exception as e:
            print(f"Request error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                raise

def get_latest_block() -> int:
    """
    Get the latest block number from the blockchain
    """
    response = make_rpc_request("eth_blockNumber", [])
    if "result" in response:
        return int(response["result"], 16)
    else:
        raise Exception(f"Failed to get latest block: {response}")

def fetch_votecast_events(from_block: int = None, to_block: str = "latest", chunk_size: int = 500) -> List[Dict[str, Any]]:
    """
    Fetch VoteCast events from the blockchain in chunks
    """
    if from_block is None:
        from_block = START_BLOCK
    
    # Calculate the topic hash for VoteCast event
    topic_hash = calculate_keccak256_topic(VOTECAST_SIGNATURE)
    print(f"VoteCast event topic hash: {topic_hash}")
    
    # Get latest block if needed
    if to_block == "latest":
        latest_block = get_latest_block()
        print(f"Latest block: {latest_block}")
        to_block = latest_block
    
    all_events = []
    current_block = from_block
    
    print(f"Fetching VoteCast events from block {from_block} to {to_block}")
    print(f"Contract address: {CONTRACT_ADDRESS}")
    
    while current_block <= to_block:
        chunk_end = min(current_block + chunk_size - 1, to_block)
        
        print(f"Processing blocks {current_block} to {chunk_end}")
        
        # Prepare the filter parameters
        filter_params = {
            "fromBlock": hex(current_block),
            "toBlock": hex(chunk_end),
            "address": CONTRACT_ADDRESS,
            "topics": [topic_hash]  # Only filter by event signature
        }
        
        try:
            response = make_rpc_request("eth_getLogs", [filter_params])
            
            if "result" in response:
                events = response["result"]
                print(f"Found {len(events)} VoteCast events in blocks {current_block}-{chunk_end}")
                all_events.extend(events)
            else:
                print(f"Error in response: {response}")
                
        except Exception as e:
            print(f"Error fetching events for blocks {current_block}-{chunk_end}: {e}")
            # Continue with next chunk
            
        current_block = chunk_end + 1
        time.sleep(0.1)  # Small delay to avoid rate limiting
    
    print(f"Total VoteCast events found: {len(all_events)}")
    return all_events

def decode_address_from_topic(topic: str) -> str:
    """
    Decode an address from a topic (32-byte hex string)
    """
    # Remove '0x' prefix and take the last 40 characters (20 bytes)
    address_hex = topic[2:][-40:]
    return "0x" + address_hex

def decode_uint256_from_data(data: str, offset: int) -> int:
    """
    Decode a uint256 value from event data at the specified offset
    """
    # Each parameter is 32 bytes (64 hex characters)
    start_pos = 2 + (offset * 64)  # Skip '0x' prefix
    end_pos = start_pos + 64
    hex_value = data[start_pos:end_pos]
    return int(hex_value, 16)

def decode_string_from_data(data: str, offset: int) -> str:
    """
    Decode a string value from event data at the specified offset
    """
    try:
        # Get the offset to the string data
        string_offset = decode_uint256_from_data(data, offset)
        
        # Get the length of the string
        length_offset = string_offset // 32
        string_length = decode_uint256_from_data(data, length_offset)
        
        # Get the string data
        data_offset = length_offset + 1
        start_pos = 2 + (data_offset * 64)
        
        # Calculate how many 32-byte chunks we need
        chunks_needed = (string_length + 31) // 32
        hex_string = ""
        
        for i in range(chunks_needed):
            chunk_start = start_pos + (i * 64)
            chunk_end = chunk_start + 64
            hex_string += data[chunk_start:chunk_end]
        
        # Convert hex to bytes and decode, taking only the specified length
        string_bytes = bytes.fromhex(hex_string)[:string_length]
        return string_bytes.decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error decoding string: {e}")
        return ""

def parse_votecast_event(event: Dict) -> Dict:
    """
    Parse a VoteCast event and extract the relevant information
    """
    # Extract voter address from topics[1] (indexed parameter)
    voter = decode_address_from_topic(event["topics"][1]) if len(event["topics"]) > 1 else ""
    
    # Extract data parameters: proposalId, support, votes, reason
    data = event["data"]
    
    proposal_id = decode_uint256_from_data(data, 0)  # First parameter
    support = decode_uint256_from_data(data, 1)      # Second parameter (uint8 but stored as uint256)
    votes = decode_uint256_from_data(data, 2)        # Third parameter
    reason = decode_string_from_data(data, 3)        # Fourth parameter (string)
    
    return {
        "block_number": int(event["blockNumber"], 16),
        "transaction_hash": event["transactionHash"],
        "log_index": int(event["logIndex"], 16),
        "voter": voter,
        "proposal_id": proposal_id,
        "support": support,
        "votes": votes,
        "reason": reason,
        "raw_data": data,
        "raw_topics": json.dumps(event["topics"])
    }

def save_events_to_csv(events: List[Dict], filename: str = None):
    """
    Save the parsed events to a CSV file
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"VoteCast_events_{timestamp}.csv"
    
    if not events:
        print("No events to save")
        return
    
    # Define CSV headers
    headers = [
        "block_number", "transaction_hash", "log_index", 
        "voter", "proposal_id", "support", "votes", "reason",
        "raw_data", "raw_topics"
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for event in events:
            writer.writerow(event)
    
    print(f"Saved {len(events)} VoteCast events to {filename}")
    
    # Print some statistics
    if events:
        min_block = min(event["block_number"] for event in events)
        max_block = max(event["block_number"] for event in events)
        unique_voters = len(set(event["voter"] for event in events))
        unique_proposals = len(set(event["proposal_id"] for event in events))
        
        print(f"Block range: {min_block} to {max_block}")
        print(f"Unique voters: {unique_voters}")
        print(f"Unique proposals: {unique_proposals}")
        
        # Support distribution
        support_counts = {}
        for event in events:
            support = event["support"]
            support_counts[support] = support_counts.get(support, 0) + 1
        
        print("Support distribution:")
        for support, count in sorted(support_counts.items()):
            support_text = {0: "Against", 1: "For", 2: "Abstain"}.get(support, f"Unknown({support})")
            print(f"  {support_text}: {count}")

def main():
    """
    Main function to fetch and save VoteCast events
    """
    print("🗳️  Starting VoteCast Events Indexing")
    print("=" * 50)
    print(f"Contract: {CONTRACT_ADDRESS}")
    print(f"Starting block: {START_BLOCK}")
    print(f"Event signature: {VOTECAST_SIGNATURE}")
    
    try:
        # Fetch events
        events = fetch_votecast_events(from_block=START_BLOCK)
        
        if events:
            # Parse events
            parsed_events = []
            for event in events:
                try:
                    parsed_event = parse_votecast_event(event)
                    parsed_events.append(parsed_event)
                except Exception as e:
                    print(f"Error parsing event: {e}")
                    print(f"Event data: {event}")
            
            # Sort by block number and log index
            parsed_events.sort(key=lambda x: (x["block_number"], x["log_index"]))
            
            # Save to CSV
            save_events_to_csv(parsed_events)
            
        else:
            print("No VoteCast events found")
            
    except Exception as e:
        print(f"Error in main execution: {e}")
        raise

if __name__ == "__main__":
    main()