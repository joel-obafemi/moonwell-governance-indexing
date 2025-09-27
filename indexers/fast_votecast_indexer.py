#!/usr/bin/env python3
"""
Fast VoteCast Events Indexer - Optimized for speed and reliability
Key improvements:
- Smaller chunk sizes for faster processing
- Simplified event parsing (skip complex string decoding)
- Better error handling and timeout management
- More frequent checkpointing
"""

import requests
import json
import csv
import os
from Crypto.Hash import keccak
from typing import List, Dict, Any, Optional
from datetime import datetime
import time
import pickle

# Configuration - Resume from problematic block
MOONBEAM_RPC_URL = "https://rpc.api.moonbeam.network"
CONTRACT_ADDRESS = "0x9A8464C4C11CeA17e191653Deb7CdC1bE30F1Af4"
VOTECAST_SIGNATURE = "VoteCast(address,uint256,uint8,uint256)"
START_BLOCK = 12069712  # Resume from the problematic block
SMALL_CHUNK_SIZE = 100  # Small chunks for problematic area
LARGE_CHUNK_SIZE = 1000  # Normal chunk size after getting past issues
SWITCH_BLOCK = 12080000  # Switch to large chunks after this block
REQUEST_TIMEOUT = 10  # Shorter timeout

# File paths
CSV_FILENAME = "VoteCast_events_fast.csv"
CHECKPOINT_FILENAME = "fast_votecast_checkpoint.pkl"

class FastVoteCastIndexer:
    def __init__(self):
        """Initialize the fast VoteCast indexer"""
        self.rpc_url = MOONBEAM_RPC_URL
        self.contract_address = CONTRACT_ADDRESS
        self.votecast_signature = VOTECAST_SIGNATURE
        self.topic_hash = self.calculate_keccak256_topic(VOTECAST_SIGNATURE)
        self.start_block = START_BLOCK
        self.chunk_size = SMALL_CHUNK_SIZE  # Start with small chunks
        self.csv_filename = CSV_FILENAME
        self.checkpoint_filename = CHECKPOINT_FILENAME
        
        self.total_events_found = 0
        self.current_block = START_BLOCK
        self.latest_block = None
        
        # Initialize CSV file
        self.initialize_csv()
        
        # Load checkpoint if exists
        self.load_checkpoint()
        
        print(f"🚀 Fast VoteCast Events Indexer")
        print("=" * 40)
        print(f"Contract: {self.contract_address}")
        print(f"Signature: {self.votecast_signature}")
        print(f"Topic Hash: {self.topic_hash}")
        print(f"Resume from block: {self.current_block}")
        print(f"Small chunk size: {SMALL_CHUNK_SIZE}")
        print(f"Large chunk size: {LARGE_CHUNK_SIZE}")
        print(f"Switch to large chunks at block: {SWITCH_BLOCK}")

    def calculate_keccak256_topic(self, signature: str) -> str:
        """Calculate keccak256 hash for event signature"""
        k = keccak.new(digest_bits=256)
        k.update(signature.encode('utf-8'))
        return "0x" + k.hexdigest()

    def initialize_csv(self):
        """Initialize CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.csv_filename):
            headers = [
                "block_number", "transaction_hash", "log_index", 
                "voter", "proposal_id", "support", "votes",
                "raw_data", "raw_topics"
            ]
            
            with open(self.csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
            print(f"📄 Created new CSV file: {self.csv_filename}")
        else:
            # Count existing events
            with open(self.csv_filename, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                next(reader)  # Skip header
                existing_count = sum(1 for _ in reader)
            print(f"📊 Existing CSV file found with {existing_count} events")

    def save_checkpoint(self):
        """Save current progress to checkpoint file"""
        checkpoint_data = {
            'current_block': self.current_block,
            'total_events_found': self.total_events_found,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(self.checkpoint_filename, 'wb') as f:
            pickle.dump(checkpoint_data, f)

    def load_checkpoint(self):
        """Load progress from checkpoint file if it exists"""
        if os.path.exists(self.checkpoint_filename):
            try:
                with open(self.checkpoint_filename, 'rb') as f:
                    checkpoint_data = pickle.load(f)
                
                self.current_block = checkpoint_data.get('current_block', START_BLOCK)
                self.total_events_found = checkpoint_data.get('total_events_found', 0)
                
                print(f"📂 Loaded checkpoint: resuming from block {self.current_block}")
                print(f"📊 Previous events found: {self.total_events_found}")
            except Exception as e:
                print(f"⚠️  Error loading checkpoint: {e}")
                print("Starting from beginning...")

    def make_rpc_request(self, method: str, params: List[Any]) -> Optional[Dict[Any, Any]]:
        """Make RPC request with timeout and error handling"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        
        try:
            response = requests.post(
                self.rpc_url, 
                json=payload, 
                timeout=REQUEST_TIMEOUT,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            print(f"⏱️  Request timeout for {method}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"🌐 Network error: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error in RPC request: {e}")
            return None

    def get_latest_block(self) -> Optional[int]:
        """Get the latest block number"""
        response = self.make_rpc_request("eth_blockNumber", [])
        if response and "result" in response:
            return int(response["result"], 16)
        return None

    def decode_address_from_topic(self, topic: str) -> str:
        """Decode address from topic (simplified)"""
        if topic and len(topic) >= 42:
            return "0x" + topic[-40:]
        return ""

    def decode_uint256_from_data(self, data: str, offset: int) -> int:
        """Decode uint256 from data (simplified)"""
        try:
            if not data or data == "0x":
                return 0
            
            # Remove 0x prefix
            hex_data = data[2:] if data.startswith("0x") else data
            
            # Each uint256 is 64 hex characters (32 bytes)
            start_pos = offset * 64
            end_pos = start_pos + 64
            
            if len(hex_data) >= end_pos:
                hex_value = hex_data[start_pos:end_pos]
                return int(hex_value, 16)
            
            return 0
        except Exception:
            return 0

    def parse_votecast_event_fast(self, event: Dict) -> Dict:
        """Fast event parsing - skip complex string decoding"""
        voter = self.decode_address_from_topic(event["topics"][1]) if len(event["topics"]) > 1 else ""
        
        data = event["data"]
        proposal_id = self.decode_uint256_from_data(data, 0)
        support = self.decode_uint256_from_data(data, 1)
        votes = self.decode_uint256_from_data(data, 2)
        
        return {
            "block_number": int(event["blockNumber"], 16),
            "transaction_hash": event["transactionHash"],
            "log_index": int(event["logIndex"], 16),
            "voter": voter,
            "proposal_id": proposal_id,
            "support": support,
            "votes": votes,
            "raw_data": data,
            "raw_topics": json.dumps(event["topics"])
        }

    def append_events_to_csv(self, events: List[Dict]):
        """Append new events to CSV file"""
        if not events:
            return
        
        with open(self.csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            for event in events:
                writer.writerow([
                    event["block_number"],
                    event["transaction_hash"],
                    event["log_index"],
                    event["voter"],
                    event["proposal_id"],
                    event["support"],
                    event["votes"],
                    event["raw_data"],
                    event["raw_topics"]
                ])

    def fetch_chunk(self, from_block: int, to_block: int) -> List[Dict]:
        """Fetch events for a specific block range"""
        filter_params = {
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block),
            "address": self.contract_address,
            "topics": [self.topic_hash]
        }
        
        response = self.make_rpc_request("eth_getLogs", [filter_params])
        
        if response and "result" in response:
            return response["result"]
        else:
            return []

    def run_indexing(self):
        """Main indexing loop with adaptive chunk sizing"""
        try:
            # Get latest block
            self.latest_block = self.get_latest_block()
            if not self.latest_block:
                print("❌ Failed to get latest block number")
                return
            
            print(f"🎯 Target block: {self.latest_block}")
            print(f"📊 Blocks to process: {self.latest_block - self.current_block + 1}")
            
            chunk_count = 0
            start_time = time.time()
            
            while self.current_block <= self.latest_block:
                # Determine chunk size based on current block
                if self.current_block < SWITCH_BLOCK:
                    chunk_size = SMALL_CHUNK_SIZE
                    chunk_type = "small"
                else:
                    chunk_size = LARGE_CHUNK_SIZE
                    chunk_type = "large"
                
                chunk_end = min(self.current_block + chunk_size - 1, self.latest_block)
                chunk_count += 1
                
                print(f"🔄 {chunk_type.title()} chunk {chunk_count}: Blocks {self.current_block}-{chunk_end}", end=" ")
                
                # Fetch events for this chunk
                events = self.fetch_chunk(self.current_block, chunk_end)
                
                if events:
                    print(f"✅ Found {len(events)} events")
                    
                    # Parse events quickly
                    parsed_events = []
                    for event in events:
                        try:
                            parsed_event = self.parse_votecast_event_fast(event)
                            parsed_events.append(parsed_event)
                        except Exception as e:
                            print(f"⚠️  Error parsing event: {e}")
                    
                    # Append to CSV
                    self.append_events_to_csv(parsed_events)
                    self.total_events_found += len(parsed_events)
                    
                    # Show sample event
                    if parsed_events:
                        event = parsed_events[0]
                        support_text = {0: "Against", 1: "For", 2: "Abstain"}.get(event["support"], f"Unknown({event['support']})")
                        print(f"  📝 Sample: Block {event['block_number']}, Voter {event['voter'][:10]}..., Vote: {support_text}")
                
                else:
                    print("📭 No events")
                
                # Update progress
                self.current_block = chunk_end + 1
                
                # Save checkpoint every 50 chunks or when events are found
                if chunk_count % 50 == 0 or events:
                    self.save_checkpoint()
                    progress_pct = ((self.current_block - START_BLOCK) / (self.latest_block - START_BLOCK)) * 100
                    elapsed = time.time() - start_time
                    rate = chunk_count / elapsed if elapsed > 0 else 0
                    print(f"💾 Progress: {progress_pct:.1f}% | Rate: {rate:.1f} chunks/sec")
                
                # Very small delay
                time.sleep(0.05)
            
            # Final save
            self.save_checkpoint()
            
            elapsed = time.time() - start_time
            print(f"\n🎉 Indexing completed in {elapsed:.1f} seconds!")
            print(f"📊 Total events found: {self.total_events_found}")
            print(f"📁 Events saved to: {self.csv_filename}")
            
        except KeyboardInterrupt:
            print(f"\n⏸️  Indexing interrupted by user")
            self.save_checkpoint()
            print(f"💾 Progress saved. Resume by running the script again.")
            
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            self.save_checkpoint()
            print(f"💾 Progress saved. You can resume by running the script again.")
            raise

def main():
    """Main function"""
    indexer = FastVoteCastIndexer()
    indexer.run_indexing()

if __name__ == "__main__":
    main()