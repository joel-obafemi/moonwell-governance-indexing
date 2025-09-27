#!/usr/bin/env python3
"""
Script to fetch DelegateChanged and DelegateVotesChanged events from Moonwell contract
using Blast API endpoint.
"""

import requests
import json
import csv
import time
from typing import List, Dict, Any

# Configuration
BLAST_API_URL = "https://moonbeam.blastapi.io/757c063c-a925-415d-b8f6-79c7e94b1737"
CONTRACT_ADDRESS = "0x933fCDf708481c57E9FD82f6BAA084f42e98B60e"
START_BLOCK = 5763056  # Corrected start block

# Event signatures (keccak256 hashes of event signatures)
DELEGATE_CHANGED_TOPIC = "0x3134e8a2e6d97e929a7e54011ea5485d7d196dd5f0ba4d4ef95803e8e3fc257f"
DELEGATE_VOTES_CHANGED_TOPIC = "0xdec2bacdd2f05b59de34da9b523dff8be42e5e38e818c82fdb0bae774387a724"

def get_latest_block() -> int:
    """Get the latest block number from the blockchain"""
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_blockNumber",
        "params": [],
        "id": 1
    }
    
    try:
        response = requests.post(BLAST_API_URL, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        return int(result['result'], 16)
    except Exception as e:
        print(f"Error getting latest block: {e}")
        return START_BLOCK + 10000  # Fallback

def get_logs(from_block: int, to_block: int, topics: List[str]) -> List[Dict[str, Any]]:
    """Fetch logs for a specific block range and topics"""
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getLogs",
        "params": [{
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block),
            "address": CONTRACT_ADDRESS,
            "topics": [topics]
        }],
        "id": 1
    }
    
    try:
        response = requests.post(BLAST_API_URL, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        
        if 'error' in result:
            print(f"API Error: {result['error']}")
            return []
        
        return result.get('result', [])
    except requests.exceptions.SSLError as e:
        print(f"SSL Error: {e}. Trying without SSL verification...")
        try:
            response = requests.post(BLAST_API_URL, json=payload, timeout=60, verify=False)
            response.raise_for_status()
            result = response.json()
            
            if 'error' in result:
                print(f"API Error: {result['error']}")
                return []
            
            return result.get('result', [])
        except Exception as e2:
            print(f"Error fetching logs (without SSL): {e2}")
            return []
    except Exception as e:
        print(f"Error fetching logs from block {from_block} to {to_block}: {e}")
        return []

def parse_delegate_changed_event(log: Dict[str, Any]) -> Dict[str, Any]:
    """Parse DelegateChanged event data"""
    # DelegateChanged(indexed address delegator, indexed address fromDelegate, indexed address toDelegate)
    topics = log['topics']
    return {
        'event_type': 'DelegateChanged',
        'block_number': int(log['blockNumber'], 16),
        'transaction_hash': log['transactionHash'],
        'log_index': int(log['logIndex'], 16),
        'delegator': '0x' + topics[1][26:],  # Remove padding
        'from_delegate': '0x' + topics[2][26:],
        'to_delegate': '0x' + topics[3][26:],
        'data': log['data']
    }

def parse_delegate_votes_changed_event(log: Dict[str, Any]) -> Dict[str, Any]:
    """Parse DelegateVotesChanged event data"""
    # DelegateVotesChanged(indexed address delegate, uint256 previousBalance, uint256 newBalance)
    topics = log['topics']
    
    # Parse data field (contains previousBalance and newBalance as uint256)
    data = log['data'][2:]  # Remove '0x' prefix
    previous_balance = int(data[:64], 16)
    new_balance = int(data[64:128], 16)
    
    return {
        'event_type': 'DelegateVotesChanged',
        'block_number': int(log['blockNumber'], 16),
        'transaction_hash': log['transactionHash'],
        'log_index': int(log['logIndex'], 16),
        'delegate': '0x' + topics[1][26:],  # Remove padding
        'previous_balance': previous_balance,
        'new_balance': new_balance
    }

def save_to_csv(data: List[Dict[str, Any]], filename: str):
    """Save data to CSV file"""
    if not data:
        print(f"No data to save for {filename}")
        return
    
    fieldnames = data[0].keys()
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"Saved {len(data)} records to {filename}")

def main():
    print("Starting log fetching process...")
    print(f"Contract: {CONTRACT_ADDRESS}")
    print(f"Events: DelegateChanged, DelegateVotesChanged")
    print(f"Start block: {START_BLOCK}")
    
    # Get latest block number
    latest_block = get_latest_block()
    print(f"Latest block: {latest_block}")
    
    # Initialize data storage
    delegate_changed_events = []
    delegate_votes_changed_events = []
    
    # Process in chunks of 500 blocks (API limit)
    BLOCK_CHUNK = 500
    current_block = START_BLOCK
    
    while current_block <= latest_block:
        to_block = min(current_block + BLOCK_CHUNK - 1, latest_block)
        
        print(f"Fetching logs from block {current_block} to {to_block}...")
        
        # Fetch DelegateChanged events
        delegate_changed_logs = get_logs(current_block, to_block, DELEGATE_CHANGED_TOPIC)
        for log in delegate_changed_logs:
            parsed = parse_delegate_changed_event(log)
            delegate_changed_events.append(parsed)
        
        # Fetch DelegateVotesChanged events
        delegate_votes_changed_logs = get_logs(current_block, to_block, DELEGATE_VOTES_CHANGED_TOPIC)
        for log in delegate_votes_changed_logs:
            parsed = parse_delegate_votes_changed_event(log)
            delegate_votes_changed_events.append(parsed)
        
        print(f"Found {len(delegate_changed_logs)} DelegateChanged and {len(delegate_votes_changed_logs)} DelegateVotesChanged events in this chunk")
        
        # Move to next chunk
        current_block = to_block + 1
        
        # Rate limiting
        time.sleep(0.5)
    
    # Save results to CSV files
    save_to_csv(delegate_changed_events, "DelegateChanged_events.csv")
    save_to_csv(delegate_votes_changed_events, "DelegateVotesChanged_events.csv")
    
    print("\nSummary:")
    print(f"Total DelegateChanged events: {len(delegate_changed_events)}")
    print(f"Total DelegateVotesChanged events: {len(delegate_votes_changed_events)}")
    print("CSV files have been created in the current directory.")

if __name__ == "__main__":
    main()