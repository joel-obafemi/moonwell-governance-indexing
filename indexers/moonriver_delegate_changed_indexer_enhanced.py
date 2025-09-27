#!/usr/bin/env python3
"""
Enhanced Moonriver DelegateChanged Event Indexer
- Network interruption resistant with checkpoint/resume
- Incremental CSV saving (each event saved immediately)
- Progress tracking and recovery
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

# Configuration for Moonriver
MOONRIVER_RPC_URL = "https://moonriver.api.onfinality.io/public"
CONTRACT_ADDRESS = "0xBb8d88bcD9749636BC4D2bE22aaC4Bb3B01A58F1"
START_BLOCK = 1462096

# Event signature for DelegateChanged(address,address,address)
DELEGATE_CHANGED_SIGNATURE = "DelegateChanged(address,address,address)"

# Checkpoint and progress files
CHECKPOINT_FILE = "moonriver_delegate_checkpoint.pkl"
PROGRESS_FILE = "moonriver_delegate_progress.txt"

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
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(
                MOONRIVER_RPC_URL, 
                json=payload, 
                headers={"Content-Type": "application/json"},
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            print(f"RPC request failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise

def get_latest_block() -> int:
    """Get the latest block number"""
    response = make_rpc_request("eth_blockNumber", [])
    if "result" in response:
        return int(response["result"], 16)
    return 0

def decode_address_from_topic(topic: str) -> str:
    """Decode an address from a topic (removes padding zeros)"""
    if topic.startswith("0x"):
        topic = topic[2:]
    address = "0x" + topic[-40:]  # Last 40 characters (20 bytes)
    return address.lower()

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
        "raw_topics": json.dumps(topics)
    }

class EnhancedDelegateIndexer:
    def __init__(self):
        self.csv_filename = None
        self.csv_file = None
        self.csv_writer = None
        self.events_processed = 0
        self.last_processed_block = START_BLOCK - 1
        
    def load_checkpoint(self) -> Dict:
        """Load checkpoint data if exists"""
        if os.path.exists(CHECKPOINT_FILE):
            try:
                with open(CHECKPOINT_FILE, 'rb') as f:
                    checkpoint = pickle.load(f)
                print(f"📂 Loaded checkpoint: last block {checkpoint.get('last_block', START_BLOCK - 1)}")
                return checkpoint
            except Exception as e:
                print(f"⚠️ Error loading checkpoint: {e}")
        return {"last_block": START_BLOCK - 1, "events_count": 0}
    
    def save_checkpoint(self, last_block: int):
        """Save checkpoint data"""
        checkpoint = {
            "last_block": last_block,
            "events_count": self.events_processed,
            "timestamp": datetime.now().isoformat()
        }
        try:
            with open(CHECKPOINT_FILE, 'wb') as f:
                pickle.dump(checkpoint, f)
            
            # Also save human-readable progress
            with open(PROGRESS_FILE, 'w') as f:
                f.write(f"Last processed block: {last_block}\n")
                f.write(f"Events processed: {self.events_processed}\n")
                f.write(f"Last update: {datetime.now().isoformat()}\n")
                
        except Exception as e:
            print(f"⚠️ Error saving checkpoint: {e}")
    
    def initialize_csv(self):
        """Initialize CSV file for incremental writing"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_filename = f"Moonriver_DelegateChanged_events_incremental_{timestamp}.csv"
        
        headers = [
            "block_number",
            "transaction_hash", 
            "log_index",
            "delegator",
            "from_delegate",
            "to_delegate",
            "raw_topics"
        ]
        
        self.csv_file = open(self.csv_filename, 'w', newline='', encoding='utf-8')
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=headers)
        self.csv_writer.writeheader()
        self.csv_file.flush()
        
        print(f"📝 Initialized incremental CSV: {self.csv_filename}")
    
    def save_event_to_csv(self, event: Dict):
        """Save a single event to CSV immediately"""
        if self.csv_writer:
            self.csv_writer.writerow(event)
            self.csv_file.flush()  # Ensure data is written immediately
            self.events_processed += 1
    
    def fetch_events_chunk(self, from_block: int, to_block: int, topic0: str) -> List[Dict]:
        """Fetch events for a specific block range"""
        filter_params = {
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block),
            "address": CONTRACT_ADDRESS,
            "topics": [topic0]
        }
        
        response = make_rpc_request("eth_getLogs", [filter_params])
        
        if "result" in response:
            return response["result"]
        else:
            if "error" in response:
                print(f"❌ RPC Error: {response['error']}")
            return []
    
    def run_indexer(self):
        """Main indexer loop with checkpoint/resume functionality"""
        print("🚀 Starting Enhanced Moonriver DelegateChanged Event Indexer")
        print("=" * 70)
        print(f"Network: Moonriver")
        print(f"Contract: {CONTRACT_ADDRESS}")
        print(f"Event: DelegateChanged")
        print("=" * 70)
        
        # Load checkpoint
        checkpoint = self.load_checkpoint()
        self.last_processed_block = checkpoint.get("last_block", START_BLOCK - 1)
        self.events_processed = checkpoint.get("events_count", 0)
        
        if self.last_processed_block >= START_BLOCK:
            print(f"🔄 Resuming from block {self.last_processed_block + 1}")
        else:
            print(f"🆕 Starting fresh from block {START_BLOCK}")
        
        # Initialize CSV
        self.initialize_csv()
        
        try:
            # Calculate topic[0] for DelegateChanged event
            topic0 = calculate_keccak256_topic(DELEGATE_CHANGED_SIGNATURE)
            print(f"DelegateChanged topic[0]: {topic0}")
            
            # Get latest block
            latest_block = get_latest_block()
            print(f"Latest block: {latest_block}")
            
            current_from = max(self.last_processed_block + 1, START_BLOCK)
            chunk_size = 1000
            
            print(f"Fetching events from block {current_from} to {latest_block}")
            
            while current_from <= latest_block:
                current_to = min(current_from + chunk_size - 1, latest_block)
                
                print(f"Fetching chunk: blocks {current_from} to {current_to}")
                
                try:
                    chunk_events = self.fetch_events_chunk(current_from, current_to, topic0)
                    print(f"Found {len(chunk_events)} events in this chunk")
                    
                    # Process and save each event immediately
                    for event in chunk_events:
                        try:
                            parsed_event = parse_delegate_changed_event(event)
                            self.save_event_to_csv(parsed_event)
                        except Exception as e:
                            print(f"⚠️ Error parsing event: {e}")
                    
                    # Update checkpoint after each successful chunk
                    self.last_processed_block = current_to
                    self.save_checkpoint(current_to)
                    
                    if len(chunk_events) > 0:
                        print(f"✅ Processed {len(chunk_events)} events, total: {self.events_processed}")
                    
                except Exception as e:
                    print(f"❌ Error processing chunk {current_from}-{current_to}: {e}")
                    print("⏳ Waiting 5 seconds before retry...")
                    time.sleep(5)
                    continue
                
                current_from = current_to + 1
                time.sleep(0.1)  # Rate limiting
            
            print(f"🎉 Indexing completed! Total events processed: {self.events_processed}")
            
        except KeyboardInterrupt:
            print(f"\n⏹️ Indexing interrupted by user")
            print(f"📊 Progress saved: {self.events_processed} events processed")
            print(f"🔄 Resume from block: {self.last_processed_block + 1}")
        except Exception as e:
            print(f"❌ Fatal error: {e}")
            raise
        finally:
            if self.csv_file:
                self.csv_file.close()
                print(f"📁 CSV file saved: {self.csv_filename}")

def main():
    indexer = EnhancedDelegateIndexer()
    indexer.run_indexer()

if __name__ == "__main__":
    main()