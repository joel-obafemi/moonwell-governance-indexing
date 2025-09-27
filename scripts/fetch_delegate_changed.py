#!/usr/bin/env python3
"""
Script to fetch DelegateChanged events from Moonbeam blockchain using Blast API
"""

import requests
import json
import csv
from Crypto.Hash import keccak
from typing import List, Dict, Any
from datetime import datetime

# Configuration
MOONBEAM_RPC_URL = "https://moonbeam.blastapi.io/757c063c-a925-415d-b8f6-79c7e94b1737"
CONTRACT_ADDRESS = "0x511aB53F793683763E5a8829738301368a2411E3"

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

def make_rpc_request(method: str, params: List[Any]) -> Dict[Any, Any]:
    """
    Make a JSON-RPC request to the Moonbeam endpoint
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
    
    try:
        response = requests.post(MOONBEAM_RPC_URL, json=payload, headers=headers)
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {response.headers}")
        print(f"Response text: {response.text[:500]}...")  # First 500 chars for debugging
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making RPC request: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
        return {"error": str(e)}

def get_latest_block() -> int:
    """
    Get the latest block number
    """
    result = make_rpc_request("eth_blockNumber", [])
    if "result" in result:
        return int(result["result"], 16)
    return 0

def fetch_delegate_changed_events(from_block: int = None, to_block: str = "latest") -> List[Dict[str, Any]]:
    """
    Fetch DelegateChanged events from the contract
    """
    # Calculate the topic hash for DelegateChanged event
    topic_hash = calculate_keccak256_topic(DELEGATE_CHANGED_SIGNATURE)
    print(f"DelegateChanged event topic hash: {topic_hash}")
    
    # If no from_block specified, get events from last 450 blocks (within API limit)
    if from_block is None:
        latest_block = get_latest_block()
        if latest_block:
            from_block = latest_block - 450  # Stay well within 500 block limit
            to_block_num = latest_block  # Use the actual latest block number
        else:
            print("Could not get latest block, using default range")
            from_block = "latest"
            to_block_num = None
    else:
        to_block_num = None
    
    # Convert to hex if it's an integer
    if isinstance(from_block, int):
        from_block_hex = hex(from_block)
    else:
        from_block_hex = from_block
    
    # For to_block, ensure we don't exceed the 500 block limit
    if to_block == "latest" and to_block_num is not None:
        # Ensure the range doesn't exceed 450 blocks
        if isinstance(from_block, int):
            actual_to_block = min(to_block_num, from_block + 450)
            to_block_hex = hex(actual_to_block)
            print(f"Block range: {from_block} to {actual_to_block} ({actual_to_block - from_block} blocks)")
        else:
            to_block_hex = "latest"
    else:
        to_block_hex = to_block
    
    print(f"Fetching DelegateChanged events from {from_block_hex} to {to_block_hex}")
    print(f"Contract address: {CONTRACT_ADDRESS}")
    
    # Prepare the filter parameters
    filter_params = {
        "address": CONTRACT_ADDRESS,
        "topics": [topic_hash],
        "fromBlock": from_block_hex,
        "toBlock": to_block_hex
    }
    
    # Make the RPC call
    response = make_rpc_request("eth_getLogs", [filter_params])
    
    if "error" in response:
        print(f"Error fetching events: {response['error']}")
        return []
    
    if "result" not in response:
        print("Unexpected response format")
        return []
    
    events = response["result"]
    print(f"Found {len(events)} DelegateChanged events")
    
    return events

def decode_address_from_topic(topic: str) -> str:
    """
    Decode an address from a 32-byte topic
    Addresses are padded with zeros to 32 bytes
    """
    if topic.startswith("0x"):
        topic = topic[2:]
    
    # Take the last 40 characters (20 bytes) for the address
    address = "0x" + topic[-40:]
    return address

def parse_delegate_changed_event(event: Dict) -> Dict:
    """
    Parse a DelegateChanged event log entry
    """
    parsed_event = {
        "block_number": int(event["blockNumber"], 16),
        "transaction_hash": event["transactionHash"],
        "log_index": int(event["logIndex"], 16),
        "address": event["address"]
    }
    
    # Parse topics
    topics = event.get("topics", [])
    if len(topics) >= 4:  # topic[0] + 3 indexed parameters
        parsed_event["event_signature"] = topics[0]
        parsed_event["delegator"] = decode_address_from_topic(topics[1])
        parsed_event["from_delegate"] = decode_address_from_topic(topics[2])
        parsed_event["to_delegate"] = decode_address_from_topic(topics[3])
    else:
        print(f"Warning: Event has {len(topics)} topics, expected 4")
        parsed_event["delegator"] = ""
        parsed_event["from_delegate"] = ""
        parsed_event["to_delegate"] = ""
    
    return parsed_event

def save_events_to_csv(events: List[Dict], filename: str = "DelegateChanged_events.csv"):
    """
    Save parsed events to a CSV file
    """
    if not events:
        print("No events to save")
        return
    
    fieldnames = [
        "block_number",
        "transaction_hash", 
        "log_index",
        "address",
        "delegator",
        "from_delegate",
        "to_delegate",
        "event_signature"
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for event in events:
            parsed_event = parse_delegate_changed_event(event)
            writer.writerow(parsed_event)
    
    print(f"Saved {len(events)} events to {filename}")

def main():
    """
    Main function to fetch and save DelegateChanged events
    """
    print("Fetching DelegateChanged events from Moonbeam...")
    print(f"Contract: {CONTRACT_ADDRESS}")
    print(f"RPC Endpoint: {MOONBEAM_RPC_URL}")
    
    # Get latest block for reference
    latest_block = get_latest_block()
    print(f"Latest block: {latest_block}")
    
    # Use a safe range of 400 blocks to stay within API limits
    from_block_num = max(0, latest_block - 400)
    to_block_num = from_block_num + 400
    from_block = hex(from_block_num)
    to_block = hex(to_block_num)
    
    print(f"Querying from block {from_block_num} ({from_block}) to {to_block_num} ({to_block})")
    print(f"Block range: {to_block_num - from_block_num} blocks")
    
    # Fetch the events
    events = fetch_delegate_changed_events(from_block, to_block)
    
    if events:
        # Save to CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"DelegateChanged_events_{timestamp}.csv"
        save_events_to_csv(events, filename)
        
        # Print some sample events
        print("\nSample events:")
        for i, event in enumerate(events[:3]):  # Show first 3 events
            parsed = parse_delegate_changed_event(event)
            print(f"Event {i+1}:")
            print(f"  Block: {parsed['block_number']}")
            print(f"  Delegator: {parsed['delegator']}")
            print(f"  From: {parsed['from_delegate']}")
            print(f"  To: {parsed['to_delegate']}")
            print()
    else:
        print("No DelegateChanged events found in the specified range")

if __name__ == "__main__":
    main()