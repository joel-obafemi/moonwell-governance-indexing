import requests
import json
import csv
from Crypto.Hash import keccak
from typing import List, Dict, Any
from datetime import datetime
import time

# Configuration
MOONBEAM_RPC_URL = "https://moonbeam.blastapi.io/757c063c-a925-415d-b8f6-79c7e94b1737"
CONTRACT_ADDRESS = "0x511aB53F793683763E5a8829738301368a2411E3"

# DelegateChanged event signature: DelegateChanged(address,address,address)
DELEGATE_CHANGED_SIGNATURE = "DelegateChanged(address,address,address)"

def calculate_keccak256_topic(signature: str) -> str:
    """Calculate the keccak256 hash of an event signature to get the topic[0]"""
    k = keccak.new(digest_bits=256)
    k.update(signature.encode('utf-8'))
    return "0x" + k.hexdigest()

def make_rpc_request(method: str, params: List[Any]) -> Dict[Any, Any]:
    """Make a JSON-RPC request to the Moonbeam endpoint"""
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
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making RPC request: {e}")
        return {"error": str(e)}

def get_latest_block() -> int:
    """Get the latest block number"""
    response = make_rpc_request("eth_blockNumber", [])
    if "result" in response:
        return int(response["result"], 16)
    return 0

def fetch_events_in_range(from_block: int, to_block: int) -> List[Dict[str, Any]]:
    """Fetch DelegateChanged events in a specific block range"""
    topic_hash = calculate_keccak256_topic(DELEGATE_CHANGED_SIGNATURE)
    
    filter_params = {
        "address": CONTRACT_ADDRESS,
        "topics": [topic_hash],
        "fromBlock": hex(from_block),
        "toBlock": hex(to_block)
    }
    
    response = make_rpc_request("eth_getLogs", [filter_params])
    
    if "error" in response:
        print(f"Error fetching events from {from_block} to {to_block}: {response['error']}")
        return []
    
    if "result" not in response:
        return []
    
    return response["result"]

def search_from_specific_block(start_block: int, latest_block: int) -> List[Dict[str, Any]]:
    """Search for DelegateChanged events from a specific starting block to latest"""
    all_events = []
    range_size = 400  # Stay within API limits
    
    current_block = start_block
    total_ranges = ((latest_block - start_block) // range_size) + 1
    
    print(f"Searching for DelegateChanged events from block {start_block} to {latest_block}")
    print(f"Total blocks to search: {latest_block - start_block}")
    print(f"Will search in {total_ranges} ranges of {range_size} blocks each...")
    
    range_count = 0
    while current_block < latest_block and range_count < 50:  # Limit to 50 ranges to avoid too many API calls
        range_count += 1
        to_block = min(current_block + range_size, latest_block)
        
        print(f"Range {range_count}: Blocks {current_block} to {to_block}")
        
        events = fetch_events_in_range(current_block, to_block)
        if events:
            print(f"  Found {len(events)} events in this range")
            all_events.extend(events)
        else:
            print(f"  No events found in this range")
        
        current_block = to_block + 1
        
        # Add a small delay to be respectful to the API
        time.sleep(0.5)
    
    return all_events

def decode_address_from_topic(topic: str) -> str:
    """Decode an address from a 32-byte topic"""
    if topic.startswith("0x"):
        topic = topic[2:]
    # Address is the last 20 bytes (40 hex characters)
    address = "0x" + topic[-40:]
    return address

def parse_delegate_changed_event(event: Dict) -> Dict:
    """Parse a DelegateChanged event"""
    topics = event.get("topics", [])
    
    return {
        "block_number": int(event["blockNumber"], 16),
        "transaction_hash": event["transactionHash"],
        "log_index": int(event["logIndex"], 16),
        "delegator": decode_address_from_topic(topics[1]) if len(topics) > 1 else "",
        "from_delegate": decode_address_from_topic(topics[2]) if len(topics) > 2 else "",
        "to_delegate": decode_address_from_topic(topics[3]) if len(topics) > 3 else "",
        "raw_data": event.get("data", ""),
        "raw_topics": topics
    }

def save_events_to_csv(events: List[Dict], filename: str = "DelegateChanged_events.csv"):
    """Save events to a CSV file"""
    if not events:
        print("No events to save")
        return
    
    # Parse all events
    parsed_events = [parse_delegate_changed_event(event) for event in events]
    
    # Sort by block number
    parsed_events.sort(key=lambda x: x["block_number"])
    
    # Write to CSV
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            "block_number", "transaction_hash", "log_index",
            "delegator", "from_delegate", "to_delegate",
            "raw_data", "raw_topics"
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for event in parsed_events:
            # Convert raw_topics list to string for CSV
            event_copy = event.copy()
            event_copy["raw_topics"] = json.dumps(event["raw_topics"])
            writer.writerow(event_copy)
    
    print(f"Saved {len(parsed_events)} events to {filename}")

def main():
    """Main function to fetch and save DelegateChanged events"""
    print("Fetching DelegateChanged events from Moonbeam...")
    print(f"Contract: {CONTRACT_ADDRESS}")
    print(f"RPC Endpoint: {MOONBEAM_RPC_URL}")
    
    # Get latest block
    latest_block = get_latest_block()
    print(f"Latest block: {latest_block}")
    
    # Search from block 5326061 to latest as requested by user
    start_block = 5326061
    events = search_from_specific_block(start_block, latest_block)
    
    if events:
        # Save to CSV with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"DelegateChanged_events_{timestamp}.csv"
        save_events_to_csv(events, filename)
        
        # Print summary
        print(f"\nSummary:")
        print(f"Total events found: {len(events)}")
        
        # Show some sample events
        print("\nSample events:")
        for i, event in enumerate(events[:5]):  # Show first 5 events
            parsed = parse_delegate_changed_event(event)
            print(f"Event {i+1}:")
            print(f"  Block: {parsed['block_number']}")
            print(f"  Tx: {parsed['transaction_hash']}")
            print(f"  Delegator: {parsed['delegator']}")
            print(f"  From: {parsed['from_delegate']}")
            print(f"  To: {parsed['to_delegate']}")
            print()
    else:
        print("No DelegateChanged events found in the searched ranges")
        print("This could mean:")
        print("1. The contract hasn't had any delegation changes in the specified block range")
        print("2. The contract uses a different event signature")
        print("3. The contract address might be incorrect")

if __name__ == "__main__":
    main()