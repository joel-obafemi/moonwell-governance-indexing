#!/usr/bin/env python3
"""
Fix VoteCast CSV data by properly extracting voter addresses from raw_data
and ensuring correct column formatting for Dune Analytics upload.
"""

import pandas as pd
import json
from datetime import datetime
import os

def extract_voter_from_raw_data(raw_data):
    """
    Extract voter address from raw_data hex string.
    The voter address is the first 32 bytes (64 hex characters) after 0x.
    """
    if not raw_data or raw_data == '' or pd.isna(raw_data):
        return ''
    
    try:
        # Remove 0x prefix
        hex_data = raw_data[2:] if raw_data.startswith('0x') else raw_data
        
        # Extract first 32 bytes (64 hex chars) and convert to address
        # Skip the first 24 bytes (48 hex chars) to get the 20-byte address
        if len(hex_data) >= 64:
            voter_hex = hex_data[24:64]  # Extract the 20-byte address part
            voter_address = '0x' + voter_hex
            return voter_address
        else:
            return ''
    except Exception as e:
        print(f"Error extracting voter from raw_data: {e}")
        return ''

def extract_proposal_id_from_raw_data(raw_data):
    """
    Extract proposal_id from raw_data hex string.
    The proposal_id is in bytes 32-63 (second 32-byte chunk).
    """
    if not raw_data or raw_data == '' or pd.isna(raw_data):
        return ''
    
    try:
        # Remove 0x prefix
        hex_data = raw_data[2:] if raw_data.startswith('0x') else raw_data
        
        # Extract bytes 32-63 (64 hex chars starting from position 64)
        if len(hex_data) >= 128:
            proposal_id_hex = hex_data[64:128]  # Second 32-byte chunk
            proposal_id_int = int(proposal_id_hex, 16)
            return str(proposal_id_int)  # Return as string to avoid scientific notation
        else:
            return ''
    except Exception as e:
        print(f"Error extracting proposal_id from raw_data: {e}")
        return ''

def extract_support_from_raw_data(raw_data):
    """
    Extract support value from raw_data hex string.
    The support value is in bytes 64-95 (third 32-byte chunk).
    Should be 0 (Against), 1 (For), or 2 (Abstain).
    """
    if not raw_data or raw_data == '' or pd.isna(raw_data):
        return 0
    
    try:
        # Remove 0x prefix
        hex_data = raw_data[2:] if raw_data.startswith('0x') else raw_data
        
        # Extract bytes 64-95 (64 hex chars starting from position 128)
        if len(hex_data) >= 192:
            support_hex = hex_data[128:192]  # Third 32-byte chunk
            support_int = int(support_hex, 16)
            # Ensure it's a valid support value (0, 1, or 2)
            if support_int in [0, 1, 2]:
                return support_int
            else:
                return 1  # Default to "For" if invalid
        else:
            return 1  # Default to "For" if data is too short
    except Exception as e:
        print(f"Error extracting support from raw_data: {e}")
        return 1  # Default to "For" on error

def extract_votes_from_raw_data(raw_data):
    """
    Extract vote weight from raw_data hex string.
    The vote weight is in the last 32 bytes of the raw_data.
    """
    if not raw_data or raw_data == '' or pd.isna(raw_data):
        return 0
    
    try:
        # Remove 0x prefix
        hex_data = raw_data[2:] if raw_data.startswith('0x') else raw_data
        
        # Extract last 32 bytes (64 hex chars) for vote weight
        if len(hex_data) >= 64:
            votes_hex = hex_data[-64:]  # Last 64 hex characters
            votes_int = int(votes_hex, 16)
            return votes_int
        else:
            return 0
    except Exception as e:
        print(f"Error extracting votes from raw_data: {e}")
        return 0

def fix_votecast_csv():
    """
    Fix the VoteCast CSV by properly extracting voter addresses and vote weights.
    """
    
    # Find the most recent clean CSV file
    csv_files = [f for f in os.listdir('.') if f.startswith('VoteCast_events_clean_') and f.endswith('.csv')]
    if not csv_files:
        # Fallback to merged file
        csv_files = [f for f in os.listdir('.') if f.startswith('VoteCast_events_merged_') and f.endswith('.csv')]
    
    if not csv_files:
        print("No VoteCast CSV files found!")
        return
    
    # Sort by modification time and get the most recent
    csv_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    input_file = csv_files[0]
    
    print(f"Processing file: {input_file}")
    
    # Read the CSV file
    try:
        df = pd.read_csv(input_file)
        print(f"Loaded {len(df)} events from {input_file}")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    # Extract voter addresses from raw_data
    print("Extracting voter addresses from raw_data...")
    df['voter_extracted'] = df['raw_data'].apply(extract_voter_from_raw_data)
    
    # Extract proposal IDs from raw_data
    print("Extracting proposal IDs from raw_data...")
    df['proposal_id_extracted'] = df['raw_data'].apply(extract_proposal_id_from_raw_data)
    
    # Extract support values from raw_data
    print("Extracting support values from raw_data...")
    df['support_extracted'] = df['raw_data'].apply(extract_support_from_raw_data)
    
    # Extract vote weights from raw_data
    print("Extracting vote weights from raw_data...")
    df['votes_extracted'] = df['raw_data'].apply(extract_votes_from_raw_data)
    
    # Update the voter column with extracted addresses
    df['voter'] = df['voter_extracted']
    
    # Update the proposal_id column with extracted IDs
    df['proposal_id'] = df['proposal_id_extracted']
    
    # Update the support column with extracted values
    df['support'] = df['support_extracted']
    
    # Update the votes column with extracted weights (convert to readable format)
    df['votes'] = df['votes_extracted'] / 1e18  # Convert from wei to readable format
    
    # Clean up temporary columns
    df = df.drop(['voter_extracted', 'proposal_id_extracted', 'support_extracted', 'votes_extracted'], axis=1)
    
    # Ensure proper column order and types
    expected_columns = ['block_number', 'transaction_hash', 'log_index', 'voter', 'proposal_id', 'support', 'votes', 'raw_data', 'raw_topics']
    
    # Keep only expected columns that exist
    available_columns = [col for col in expected_columns if col in df.columns]
    df = df[available_columns]
    
    # Convert data types
    df['block_number'] = df['block_number'].astype(int)
    df['log_index'] = df['log_index'].astype(int)
    df['support'] = df['support'].astype(int)
    df['votes'] = df['votes'].astype(float)
    
    # Format proposal_id as string to prevent scientific notation in CSV/Dune
    df['proposal_id'] = df['proposal_id'].astype(str)
    
    # Clean up raw_topics formatting
    def clean_raw_topics(topics):
        if pd.isna(topics) or topics == '':
            return ''
        try:
            # If it's already a JSON string, parse and reformat
            if isinstance(topics, str) and topics.startswith('['):
                parsed = json.loads(topics.replace('""', '"'))
                return json.dumps(parsed)
            return str(topics)
        except:
            return str(topics)
    
    df['raw_topics'] = df['raw_topics'].apply(clean_raw_topics)
    
    # Generate output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"VoteCast_events_fixed_{timestamp}.csv"
    
    # Save the fixed CSV
    df.to_csv(output_file, index=False)
    
    # Print summary
    print(f"\n✅ Fixed VoteCast CSV saved as: {output_file}")
    print(f"📊 Total events: {len(df)}")
    print(f"🗳️  Events with voter addresses: {len(df[df['voter'] != ''])}")
    print(f"📈 Block range: {df['block_number'].min()} → {df['block_number'].max()}")
    
    # Show sample of fixed data
    print(f"\n📋 Sample of fixed data:")
    print(df[['block_number', 'voter', 'proposal_id', 'support', 'votes']].head())
    
    return output_file

if __name__ == "__main__":
    fix_votecast_csv()