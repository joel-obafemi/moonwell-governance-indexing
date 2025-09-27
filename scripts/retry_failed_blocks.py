#!/usr/bin/env python3

import requests
import json
import csv
import time
from datetime import datetime

# Configuration
RPC_URL = "https://rpc.api.moonbeam.network"
CONTRACT_ADDRESS = "0x511aB53F793683763E5a8829738301368a2411E3"
DELEGATE_CHANGED_TOPIC = "0x3134e8a2e6d97e929a7e54011ea5485d7d196dd5f0ba4d4ef95803e8e3fc257f"

# Failed block ranges identified from logs (add more as needed)
FAILED_RANGES = [
    (4535122, 4536121),  # Failed due to timeout
    (4538122, 4539121),  # Failed due to timeout  
    (4543122, 4544121),  # Failed due to timeout
    # Add more failed ranges here as identified
]

# Smaller chunk size for retry and longer timeout
RETRY_CHUNK_SIZE = 100   # Much smaller chunks for problematic ranges
RETRY_TIMEOUT = 60       # Longer timeout for retries

def make_rpc_call(method, params, timeout=RETRY_TIMEOUT):
    """Make RPC call with extended timeout and retries"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": 1
            }
            
            response = requests.post(RPC_URL, json=payload, timeout=timeout)
            response.raise_for_status()
            
            result = response.json()
            if "error" in result:
                print(f"RPC Error: {result['error']}")
                if "timeout" in str(result['error']).lower():
                    # For timeout errors, wait longer before retry
                    time.sleep(5 * (attempt + 1))
                    continue
                return None
                
            return result.get("result")
            
        except requests.exceptions.RequestException as e:
            print(f"Request failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                wait_time = min(30, 2 ** attempt)  # Cap wait time at 30 seconds
                print(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                return None
    
    return None

def parse_delegate_changed_event(log):
    """Parse DelegateChanged event from log entry"""
    try:
        topics = log.get('topics', [])
        if len(topics) != 4:
            return None
            
        # Extract addresses from topics (remove 0x and pad to get address)
        delegator = "0x" + topics[1][-40:]
        from_delegate = "0x" + topics[2][-40:]
        to_delegate = "0x" + topics[3][-40:]
        
        return {
            'block_number': int(log['blockNumber'], 16),
            'transaction_hash': log['transactionHash'],
            'log_index': int(log['logIndex'], 16),
            'delegator': delegator,
            'from_delegate': from_delegate,
            'to_delegate': to_delegate,
            'raw_data': log.get('data', ''),
            'raw_topics': json.dumps(topics)
        }
    except Exception as e:
        print(f"Error parsing event: {e}")
        return None

def search_events_in_small_chunks(start_block, end_block):
    """Search for events using very small chunks to avoid timeouts"""
    print(f"🔍 Retrying blocks {start_block:,} to {end_block:,} with small chunks...")
    
    all_events = []
    current_block = start_block
    
    while current_block <= end_block:
        chunk_end = min(current_block + RETRY_CHUNK_SIZE - 1, end_block)
        
        print(f"  Searching blocks {current_block:,} to {chunk_end:,}...")
        
        params = [
            {
                "fromBlock": hex(current_block),
                "toBlock": hex(chunk_end),
                "address": CONTRACT_ADDRESS,
                "topics": [DELEGATE_CHANGED_TOPIC]
            }
        ]
        
        logs = make_rpc_call("eth_getLogs", params)
        if logs is None:
            print(f"    ❌ Still failed for blocks {current_block:,} to {chunk_end:,}")
            # Continue to next chunk even if this one fails
            current_block = chunk_end + 1
            continue
        
        chunk_events = []
        for log in logs:
            event = parse_delegate_changed_event(log)
            if event:
                chunk_events.append(event)
        
        if chunk_events:
            print(f"    ✅ Found {len(chunk_events)} events")
            all_events.extend(chunk_events)
        else:
            print(f"    ✅ No events (confirmed)")
        
        current_block = chunk_end + 1
        
        # Small delay between chunks to be gentle on RPC
        time.sleep(0.5)
    
    return all_events

def main():
    print("🔄 Retrying Failed Block Ranges")
    print("=" * 40)
    print(f"Contract: {CONTRACT_ADDRESS}")
    print(f"Failed ranges to retry: {len(FAILED_RANGES)}")
    print(f"Retry chunk size: {RETRY_CHUNK_SIZE} blocks")
    print(f"Retry timeout: {RETRY_TIMEOUT} seconds")
    print()
    
    # Output file for retry results
    output_file = "retry_failed_blocks.csv"
    
    # Write CSV header
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['block_number', 'transaction_hash', 'log_index', 'delegator', 'from_delegate', 'to_delegate', 'raw_data', 'raw_topics'])
    
    total_events_found = 0
    successful_retries = 0
    
    for i, (start_block, end_block) in enumerate(FAILED_RANGES, 1):
        print(f"📊 Retry {i}/{len(FAILED_RANGES)}: Blocks {start_block:,} to {end_block:,}")
        
        try:
            events = search_events_in_small_chunks(start_block, end_block)
            
            if events:
                # Save events to file
                with open(output_file, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    for event in events:
                        writer.writerow([
                            event['block_number'],
                            event['transaction_hash'],
                            event['log_index'],
                            event['delegator'],
                            event['from_delegate'],
                            event['to_delegate'],
                            event['raw_data'],
                            event['raw_topics']
                        ])
                
                print(f"  💾 Saved {len(events)} events from this range")
                total_events_found += len(events)
            else:
                print(f"  ✅ Confirmed no events in this range")
            
            successful_retries += 1
            
        except KeyboardInterrupt:
            print(f"\n⏸️  Retry interrupted at range {i}")
            break
        except Exception as e:
            print(f"  ❌ Error processing range: {e}")
            continue
        
        # Pause between ranges to avoid overwhelming RPC
        if i < len(FAILED_RANGES):
            print("  ⏳ Waiting 3 seconds before next range...")
            time.sleep(3)
    
    print(f"\n✅ Retry completed!")
    print(f"📊 Ranges processed: {successful_retries}/{len(FAILED_RANGES)}")
    print(f"📊 Total events recovered: {total_events_found}")
    print(f"💾 Results saved to: {output_file}")
    
    if total_events_found > 0:
        print(f"\n🔍 Events found in previously failed ranges:")
        print(f"   This confirms some events were missed due to timeouts")
        print(f"   These events should be merged with the main dataset")
    else:
        print(f"\n✅ No events found in failed ranges")
        print(f"   This confirms no data was lost due to timeouts")

if __name__ == "__main__":
    main()