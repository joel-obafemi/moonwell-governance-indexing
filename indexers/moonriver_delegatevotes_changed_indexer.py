#!/usr/bin/env python3
"""
Enhanced Moonriver DelegateVotesChanged Event Indexer
- Network interruption resistant with checkpoint/resume
- Incremental CSV saving (each event saved immediately)
- Progress tracking and recovery
- Fail-proof with automatic retries and error handling
"""

import requests
import json
import csv
import os
import pickle
from Crypto.Hash import keccak
from typing import List, Dict, Any, Optional
from datetime import datetime
import time

# Configuration for Moonriver DelegateVotesChanged
MOONRIVER_RPC_URL = "https://moonriver.api.onfinality.io/public"
CONTRACT_ADDRESS = "0x8568A675384d761f36eC269D695d6Ce4423cfaB1"
START_BLOCK = 2676660

# Event signature for DelegateVotesChanged(address,uint256,uint256)
DELEGATE_VOTES_CHANGED_SIGNATURE = "DelegateVotesChanged(address,uint256,uint256)"

# Checkpoint and progress files
CHECKPOINT_FILE = "moonriver_delegatevotes_checkpoint.pkl"
PROGRESS_FILE = "moonriver_delegatevotes_progress.txt"

def calculate_keccak256_topic(signature: str) -> str:
    """Calculate Keccak256 hash for event signature"""
    keccak_hash = keccak.new(digest_bits=256)
    keccak_hash.update(signature.encode('utf-8'))
    return "0x" + keccak_hash.hexdigest()

def make_rpc_request(method: str, params: List[Any], timeout: int = 30) -> Dict[Any, Any]:
    """Make JSON-RPC request with error handling and retries"""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = requests.post(
                MOONRIVER_RPC_URL, 
                json=payload, 
                timeout=timeout,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            
            result = response.json()
            if 'error' in result:
                print(f"RPC Error: {result['error']}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise Exception(f"RPC Error: {result['error']}")
            
            return result
            
        except Exception as e:
            print(f"Request attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise

def get_latest_block() -> int:
    """Get the latest block number"""
    result = make_rpc_request("eth_blockNumber", [])
    return int(result["result"], 16)

def decode_address_from_topic(topic: str) -> str:
    """Decode address from topic (remove padding)"""
    if topic.startswith("0x"):
        topic = topic[2:]
    return "0x" + topic[-40:]

def parse_delegate_votes_changed_event(event: Dict) -> Dict:
    """Parse DelegateVotesChanged event data"""
    topics = event.get("topics", [])
    data = event.get("data", "0x")
    
    # Extract delegate address from first indexed parameter
    delegate = decode_address_from_topic(topics[1]) if len(topics) > 1 else ""
    
    # Parse data field for previousBalance and newBalance (uint256 values)
    data_hex = data[2:] if data.startswith("0x") else data
    
    # Each uint256 is 64 hex characters (32 bytes)
    previous_balance = "0x" + data_hex[:64] if len(data_hex) >= 64 else "0x0"
    new_balance = "0x" + data_hex[64:128] if len(data_hex) >= 128 else "0x0"
    
    # Convert to decimal
    previous_balance_dec = str(int(previous_balance, 16))
    new_balance_dec = str(int(new_balance, 16))
    
    return {
        "block_number": int(event["blockNumber"], 16),
        "transaction_hash": event["transactionHash"],
        "log_index": int(event["logIndex"], 16),
        "delegate": delegate,
        "previous_balance": previous_balance_dec,
        "new_balance": new_balance_dec,
        "raw_topics": json.dumps(topics),
        "raw_data": data
    }

class EnhancedDelegateVotesIndexer:
    def __init__(self):
        self.topic0 = calculate_keccak256_topic(DELEGATE_VOTES_CHANGED_SIGNATURE)
        print(f"Event topic0: {self.topic0}")
        
        # Generate timestamp for CSV filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_filename = f"Moonriver_DelegateVotesChanged_events_{timestamp}.csv"
        
    def load_checkpoint(self) -> Dict:
        """Load checkpoint data if exists"""
        if os.path.exists(CHECKPOINT_FILE):
            try:
                with open(CHECKPOINT_FILE, 'rb') as f:
                    checkpoint = pickle.load(f)
                print(f"Loaded checkpoint: last processed block {checkpoint.get('last_block', START_BLOCK)}")
                return checkpoint
            except Exception as e:
                print(f"Error loading checkpoint: {e}")
        return {"last_block": START_BLOCK - 1, "total_events": 0}
    
    def save_checkpoint(self, last_block: int, total_events: int):
        """Save checkpoint data"""
        checkpoint = {
            "last_block": last_block,
            "total_events": total_events,
            "timestamp": datetime.now().isoformat(),
            "csv_filename": self.csv_filename
        }
        
        try:
            with open(CHECKPOINT_FILE, 'wb') as f:
                pickle.dump(checkpoint, f)
            
            # Also save human-readable progress
            with open(PROGRESS_FILE, 'w') as f:
                f.write(f"Last processed block: {last_block}\n")
                f.write(f"Total events found: {total_events}\n")
                f.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"CSV file: {self.csv_filename}\n")
                
        except Exception as e:
            print(f"Error saving checkpoint: {e}")
    
    def initialize_csv(self):
        """Initialize CSV file with headers"""
        headers = [
            "block_number",
            "transaction_hash", 
            "log_index",
            "delegate",
            "previous_balance",
            "new_balance",
            "raw_topics",
            "raw_data"
        ]
        
        try:
            with open(self.csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
            print(f"Initialized CSV file: {self.csv_filename}")
        except Exception as e:
            print(f"Error initializing CSV: {e}")
            raise
    
    def save_event_to_csv(self, event: Dict):
        """Save single event to CSV immediately"""
        try:
            with open(self.csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    event["block_number"],
                    event["transaction_hash"],
                    event["log_index"],
                    event["delegate"],
                    event["previous_balance"],
                    event["new_balance"],
                    event["raw_topics"],
                    event["raw_data"]
                ])
        except Exception as e:
            print(f"Error saving event to CSV: {e}")
            raise
    
    def fetch_events_chunk(self, from_block: int, to_block: int, topic0: str) -> List[Dict]:
        """Fetch events for a block range"""
        params = {
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block),
            "address": CONTRACT_ADDRESS,
            "topics": [topic0]
        }
        
        try:
            result = make_rpc_request("eth_getLogs", [params])
            return result.get("result", [])
        except Exception as e:
            print(f"Error fetching events from block {from_block} to {to_block}: {e}")
            raise
    
    def run_indexer(self):
        """Main indexer loop with fail-proof mechanisms"""
        print(f"🚀 Starting Moonriver DelegateVotesChanged indexer...")
        print(f"📋 Contract: {CONTRACT_ADDRESS}")
        print(f"🔍 Event: {DELEGATE_VOTES_CHANGED_SIGNATURE}")
        print(f"📊 Topic0: {self.topic0}")
        
        # Load checkpoint or start fresh
        checkpoint = self.load_checkpoint()
        current_block = checkpoint["last_block"] + 1
        total_events = checkpoint["total_events"]
        
        # Initialize CSV if starting fresh
        if current_block == START_BLOCK:
            self.initialize_csv()
            print(f"📁 Created new CSV file: {self.csv_filename}")
        else:
            print(f"📁 Resuming with existing CSV file: {self.csv_filename}")
        
        # Get latest block
        try:
            latest_block = get_latest_block()
            print(f"📈 Latest block: {latest_block}")
            print(f"🎯 Starting from block: {current_block}")
        except Exception as e:
            print(f"❌ Error getting latest block: {e}")
            return
        
        # Process blocks in chunks
        chunk_size = 1000  # Smaller chunks for reliability
        
        while current_block <= latest_block:
            chunk_end = min(current_block + chunk_size - 1, latest_block)
            
            try:
                print(f"🔍 Processing blocks {current_block} to {chunk_end}...")
                
                # Fetch events for this chunk
                events = self.fetch_events_chunk(current_block, chunk_end, self.topic0)
                
                # Process each event
                chunk_events = 0
                for event in events:
                    try:
                        parsed_event = parse_delegate_votes_changed_event(event)
                        self.save_event_to_csv(parsed_event)
                        chunk_events += 1
                        total_events += 1
                        
                        if chunk_events % 10 == 0:
                            print(f"  💾 Saved {chunk_events} events from this chunk...")
                            
                    except Exception as e:
                        print(f"❌ Error processing event: {e}")
                        print(f"Event data: {event}")
                        continue
                
                print(f"✅ Chunk complete: {chunk_events} events found")
                
                # Save checkpoint after each successful chunk
                self.save_checkpoint(chunk_end, total_events)
                
                # Move to next chunk
                current_block = chunk_end + 1
                
                # Small delay to avoid overwhelming the RPC
                time.sleep(0.1)
                
            except Exception as e:
                print(f"❌ Error processing chunk {current_block}-{chunk_end}: {e}")
                print("⏳ Waiting 5 seconds before retry...")
                time.sleep(5)
                continue
        
        print(f"""
        🎉 Indexing completed successfully!
        
        📊 Final Statistics:
        - Total events indexed: {total_events}
        - Blocks processed: {START_BLOCK} to {latest_block}
        - CSV file: {self.csv_filename}
        - Contract: {CONTRACT_ADDRESS}
        - Network: Moonriver
        
        ✅ All DelegateVotesChanged events have been saved to CSV!
        """)

def main():
    """Main function"""
    indexer = EnhancedDelegateVotesIndexer()
    indexer.run_indexer()

if __name__ == "__main__":
    main()