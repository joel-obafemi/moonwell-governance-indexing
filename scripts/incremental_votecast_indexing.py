#!/usr/bin/env python3
"""
Resilient VoteCast Events Indexing Script for Moonbeam blockchain
Features:
- Checkpoint/resume functionality
- Automatic CSV appending
- Network interruption resistance
- Progress tracking and state persistence
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

# Configuration
MOONBEAM_RPC_URL = "https://rpc.api.moonbeam.network"
# Try multiple potential contract addresses
POTENTIAL_CONTRACTS = [
    "0x9A8464C4C11CeA17e191653Deb7CdC1bE30F1Af4",  # Original address
    "0x511aB53F793683763E5a8829738301368a2411E3",  # DelegateChanged contract
    None  # No contract filter - search all contracts
]
START_BLOCK = 5803712
CHUNK_SIZE = 1000  # Testing larger chunk size with official Moonbeam RPC

# File paths
CSV_FILENAME = "VoteCast_events_incremental.csv"
CHECKPOINT_FILENAME = "votecast_indexing_checkpoint.pkl"
PROGRESS_FILENAME = "votecast_indexing_progress.txt"

# Try multiple VoteCast event signatures
POTENTIAL_SIGNATURES = [
    "VoteCast(address,uint256,uint8,uint256,string)",  # With reason
    "VoteCast(address,uint256,uint8,uint256)",         # Without reason
    "VoteCast(address,uint256,uint256,uint256)",       # Alternative format
]

class VoteCastIndexer:
    def __init__(self):
        """Initialize the VoteCast indexer with multiple potential configurations"""
        self.rpc_url = MOONBEAM_RPC_URL
        self.potential_contracts = POTENTIAL_CONTRACTS
        self.potential_signatures = POTENTIAL_SIGNATURES
        self.start_block = START_BLOCK
        self.chunk_size = CHUNK_SIZE
        self.csv_filename = CSV_FILENAME
        self.checkpoint_filename = CHECKPOINT_FILENAME
        self.progress_filename = PROGRESS_FILENAME
        
        # Will be set after finding the correct configuration
        self.contract_address = None
        self.votecast_signature = None
        self.topic_hash = None
        self.total_events_found = 0
        self.current_block = START_BLOCK
        self.latest_block = None
        
        # Initialize CSV file with headers if it doesn't exist
        self.initialize_csv()
        
        # Load checkpoint if exists
        self.load_checkpoint()
        
        print(f"🗳️  VoteCast Events Incremental Indexer")
        print("=" * 50)
        print(f"CSV File: {self.csv_filename}")
        print(f"Checkpoint File: {self.checkpoint_filename}")
        print(f"Resume from block: {self.current_block}")
        print(f"Will test multiple contract addresses and signatures to find correct configuration")

    def find_correct_configuration(self, test_block: int = None) -> bool:
        """
        Test different contract addresses and signatures to find the correct configuration
        """
        if test_block is None:
            test_block = self.start_block
            
        print(f"\n🔍 Testing configurations on block {test_block}...")
        
        for contract_addr in self.potential_contracts:
            for signature in self.potential_signatures:
                print(f"\nTesting: Contract={contract_addr}, Signature={signature}")
                
                topic_hash = self.calculate_keccak256_topic(signature)
                print(f"Topic hash: {topic_hash}")
                
                # Build filter parameters
                filter_params = {
                    "fromBlock": hex(test_block),
                    "toBlock": hex(test_block),
                    "topics": [topic_hash]
                }
                
                # Add contract address if specified
                if contract_addr:
                    filter_params["address"] = contract_addr
                
                try:
                    response = self.make_rpc_request("eth_getLogs", [filter_params])
                    
                    if "result" in response and len(response["result"]) > 0:
                        print(f"✅ Found {len(response['result'])} events with this configuration!")
                        print(f"Setting contract address: {contract_addr}")
                        print(f"Setting signature: {signature}")
                        
                        self.contract_address = contract_addr
                        self.votecast_signature = signature
                        self.topic_hash = topic_hash
                        return True
                    else:
                        print(f"❌ No events found with this configuration")
                        
                except Exception as e:
                    print(f"❌ Error testing configuration: {e}")
                    continue
        
        print(f"\n❌ Could not find correct configuration for block {test_block}")
        return False

    def calculate_keccak256_topic(self, signature: str) -> str:
        """Calculate the keccak256 hash of an event signature"""
        k = keccak.new(digest_bits=256)
        k.update(signature.encode('utf-8'))
        return "0x" + k.hexdigest()

    def initialize_csv(self):
        """Initialize CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.csv_filename):
            headers = [
                "block_number", "transaction_hash", "log_index", 
                "voter", "proposal_id", "support", "votes", "reason",
                "raw_data", "raw_topics"
            ]
            with open(self.csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
            print(f"✅ Created new CSV file: {self.csv_filename}")
        else:
            # Count existing events
            with open(self.csv_filename, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                existing_count = sum(1 for row in reader) - 1  # Subtract header
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
        
        # Also save human-readable progress
        with open(self.progress_filename, 'w') as f:
            f.write(f"Last processed block: {self.current_block}\n")
            f.write(f"Total events found: {self.total_events_found}\n")
            f.write(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if self.latest_block:
                progress_pct = ((self.current_block - START_BLOCK) / (self.latest_block - START_BLOCK)) * 100
                f.write(f"Progress: {progress_pct:.2f}%\n")

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
                self.current_block = START_BLOCK

    def make_rpc_request(self, method: str, params: List[Any], timeout: int = 30) -> Optional[Dict[Any, Any]]:
        """Make a JSON-RPC request with retry logic"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        
        headers = {"Content-Type": "application/json"}
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = requests.post(MOONBEAM_RPC_URL, json=payload, headers=headers, timeout=timeout)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"HTTP error {response.status_code}: {response.text}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        return None
                        
            except requests.exceptions.Timeout:
                print(f"Request timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    return None
            except Exception as e:
                print(f"Request error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    return None
        
        return None

    def get_latest_block(self) -> Optional[int]:
        """Get the latest block number"""
        response = self.make_rpc_request("eth_blockNumber", [])
        if response and "result" in response:
            return int(response["result"], 16)
        return None

    def decode_address_from_topic(self, topic: str) -> str:
        """Decode an address from a topic"""
        address_hex = topic[2:][-40:]
        return "0x" + address_hex

    def decode_uint256_from_data(self, data: str, offset: int) -> int:
        """Decode a uint256 value from event data"""
        start_pos = 2 + (offset * 64)
        end_pos = start_pos + 64
        hex_value = data[start_pos:end_pos]
        return int(hex_value, 16)

    def decode_string_from_data(self, data: str, offset: int) -> str:
        """Decode a string value from event data"""
        try:
            string_offset = self.decode_uint256_from_data(data, offset)
            length_offset = string_offset // 32
            string_length = self.decode_uint256_from_data(data, length_offset)
            
            data_offset = length_offset + 1
            start_pos = 2 + (data_offset * 64)
            
            chunks_needed = (string_length + 31) // 32
            hex_string = ""
            
            for i in range(chunks_needed):
                chunk_start = start_pos + (i * 64)
                chunk_end = chunk_start + 64
                hex_string += data[chunk_start:chunk_end]
            
            string_bytes = bytes.fromhex(hex_string)[:string_length]
            return string_bytes.decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"Error decoding string: {e}")
            return ""

    def parse_votecast_event(self, event: Dict) -> Dict:
        """Parse a VoteCast event"""
        voter = self.decode_address_from_topic(event["topics"][1]) if len(event["topics"]) > 1 else ""
        
        data = event["data"]
        proposal_id = self.decode_uint256_from_data(data, 0)
        support = self.decode_uint256_from_data(data, 1)
        votes = self.decode_uint256_from_data(data, 2)
        reason = self.decode_string_from_data(data, 3)
        
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

    def append_events_to_csv(self, events: List[Dict]):
        """Append new events to CSV file immediately"""
        if not events:
            return
        
        headers = [
            "block_number", "transaction_hash", "log_index", 
            "voter", "proposal_id", "support", "votes", "reason",
            "raw_data", "raw_topics"
        ]
        
        with open(self.csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            for event in events:
                writer.writerow(event)
        
        print(f"💾 Appended {len(events)} events to CSV")

    def fetch_chunk(self, from_block: int, to_block: int) -> List[Dict]:
        """Fetch events for a specific block range"""
        if not self.topic_hash:
            raise Exception("Configuration not set. Call find_correct_configuration() first.")
            
        filter_params = {
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block),
            "topics": [self.topic_hash]
        }
        
        # Add contract address if specified
        if self.contract_address:
            filter_params["address"] = self.contract_address
        
        response = self.make_rpc_request("eth_getLogs", [filter_params])
        
        if response and "result" in response:
            return response["result"]
        else:
            print(f"❌ Error fetching events for blocks {from_block}-{to_block}")
            return []

    def run_indexing(self):
        """Main indexing loop with configuration discovery and resilience features"""
        # First, find the correct configuration
        if not self.find_correct_configuration():
            print("❌ Could not determine correct contract configuration. Exiting.")
            return
        
        print(f"\n✅ Configuration found:")
        print(f"Contract address: {self.contract_address}")
        print(f"Event signature: {self.votecast_signature}")
        print(f"Topic hash: {self.topic_hash}")
        
        try:
            # Get latest block
            self.latest_block = self.get_latest_block()
            if not self.latest_block:
                print("❌ Failed to get latest block number")
                return
            
            print(f"🎯 Target block: {self.latest_block}")
            print(f"📊 Blocks to process: {self.latest_block - self.current_block + 1}")
            
            chunk_count = 0
            
            while self.current_block <= self.latest_block:
                chunk_end = min(self.current_block + CHUNK_SIZE - 1, self.latest_block)
                chunk_count += 1
                
                print(f"\n🔄 Chunk {chunk_count}: Processing blocks {self.current_block} to {chunk_end}")
                
                # Fetch events for this chunk
                events = self.fetch_chunk(self.current_block, chunk_end)
                
                if events:
                    print(f"✅ Found {len(events)} VoteCast events")
                    
                    # Parse events
                    parsed_events = []
                    for event in events:
                        try:
                            parsed_event = self.parse_votecast_event(event)
                            parsed_events.append(parsed_event)
                        except Exception as e:
                            print(f"⚠️  Error parsing event: {e}")
                    
                    # Sort by block number and log index
                    parsed_events.sort(key=lambda x: (x["block_number"], x["log_index"]))
                    
                    # Immediately append to CSV
                    self.append_events_to_csv(parsed_events)
                    self.total_events_found += len(parsed_events)
                    
                    # Show some event details
                    for event in parsed_events[:3]:  # Show first 3 events
                        support_text = {0: "Against", 1: "For", 2: "Abstain"}.get(event["support"], f"Unknown({event['support']})")
                        print(f"  📝 Block {event['block_number']}: {event['voter']} voted {support_text} on proposal {event['proposal_id']}")
                
                else:
                    print(f"📭 No events found in blocks {self.current_block}-{chunk_end}")
                
                # Update progress
                self.current_block = chunk_end + 1
                
                # Save checkpoint every 10 chunks or when events are found
                if chunk_count % 10 == 0 or events:
                    self.save_checkpoint()
                    progress_pct = ((self.current_block - START_BLOCK) / (self.latest_block - START_BLOCK)) * 100
                    print(f"💾 Checkpoint saved. Progress: {progress_pct:.2f}%")
                
                # Small delay to avoid rate limiting
                time.sleep(0.1)
            
            # Final checkpoint save
            self.save_checkpoint()
            
            print(f"\n🎉 Indexing completed!")
            print(f"📊 Total events found: {self.total_events_found}")
            print(f"📁 Events saved to: {self.csv_filename}")
            
            # Print final statistics
            self.print_final_statistics()
            
        except KeyboardInterrupt:
            print(f"\n⏸️  Indexing interrupted by user")
            self.save_checkpoint()
            print(f"💾 Progress saved. Resume by running the script again.")
            
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            self.save_checkpoint()
            print(f"💾 Progress saved. You can resume by running the script again.")
            raise

    def print_final_statistics(self):
        """Print final statistics about the indexed data"""
        if not os.path.exists(self.csv_filename):
            return
        
        try:
            events = []
            with open(self.csv_filename, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                events = list(reader)
            
            if not events:
                print("📊 No events to analyze")
                return
            
            print(f"\n📊 Final Statistics:")
            print(f"   Total events: {len(events)}")
            
            # Block range
            block_numbers = [int(event['block_number']) for event in events]
            print(f"   Block range: {min(block_numbers)} to {max(block_numbers)}")
            
            # Unique voters and proposals
            unique_voters = len(set(event['voter'] for event in events))
            unique_proposals = len(set(event['proposal_id'] for event in events))
            print(f"   Unique voters: {unique_voters}")
            print(f"   Unique proposals: {unique_proposals}")
            
            # Support distribution
            support_counts = {}
            for event in events:
                support = int(event['support'])
                support_counts[support] = support_counts.get(support, 0) + 1
            
            print(f"   Vote distribution:")
            for support, count in sorted(support_counts.items()):
                support_text = {0: "Against", 1: "For", 2: "Abstain"}.get(support, f"Unknown({support})")
                print(f"     {support_text}: {count}")
                
        except Exception as e:
            print(f"Error generating statistics: {e}")

def main():
    """Main function"""
    indexer = VoteCastIndexer()
    indexer.run_indexing()

if __name__ == "__main__":
    main()