#!/usr/bin/env python3
"""
Fix Moonriver VoteCast CSV data formatting issues:
1. Extract voter addresses from raw_data
2. Convert proposal IDs from large numbers to simple integers
3. Ensure proper data formatting for Dune upload
"""

import pandas as pd
import json
from datetime import datetime
import os

def extract_voter_from_raw_data(raw_data):
    """Extract voter address from raw_data hex string"""
    try:
        if not raw_data or raw_data == '':
            return ''
        
        # Remove 0x prefix if present
        if raw_data.startswith('0x'):
            raw_data = raw_data[2:]
        
        # The voter address is in the first 32 bytes (64 hex characters)
        # But we need to extract the actual 20-byte address from bytes 12-32
        if len(raw_data) >= 64:
            # Extract address from bytes 12-32 (characters 24-64)
            address_hex = raw_data[24:64]
            # Add 0x prefix and return
            return '0x' + address_hex
        
        return ''
    except Exception as e:
        print(f"Error extracting voter from raw_data: {e}")
        return ''

def decode_proposal_id(raw_data):
    """Extract and decode proposal ID from raw_data"""
    try:
        if not raw_data or raw_data == '':
            return 0
        
        # Remove 0x prefix if present
        if raw_data.startswith('0x'):
            raw_data = raw_data[2:]
        
        # The proposal ID is in the second 32 bytes (characters 64-128)
        if len(raw_data) >= 128:
            proposal_id_hex = raw_data[64:128]
            # Convert hex to integer
            proposal_id = int(proposal_id_hex, 16)
            return proposal_id
        
        return 0
    except Exception as e:
        print(f"Error decoding proposal ID from raw_data: {e}")
        return 0

def extract_support_from_raw_data(raw_data):
    """Extract support value from raw_data"""
    try:
        if not raw_data or raw_data == '':
            return 0
        
        # Remove 0x prefix if present
        if raw_data.startswith('0x'):
            raw_data = raw_data[2:]
        
        # The support value is in the third 32 bytes (characters 128-192)
        if len(raw_data) >= 192:
            support_hex = raw_data[128:192]
            # Convert hex to integer
            support = int(support_hex, 16)
            return support
        
        return 0
    except Exception as e:
        print(f"Error extracting support from raw_data: {e}")
        return 0

def extract_votes_from_raw_data(raw_data):
    """Extract votes value from raw_data"""
    try:
        if not raw_data or raw_data == '':
            return 0
        
        # Remove 0x prefix if present
        if raw_data.startswith('0x'):
            raw_data = raw_data[2:]
        
        # The votes value is in the fourth 32 bytes (characters 192-256)
        if len(raw_data) >= 256:
            votes_hex = raw_data[192:256]
            # Convert hex to integer
            votes = int(votes_hex, 16)
            return votes
        
        return 0
    except Exception as e:
        print(f"Error extracting votes from raw_data: {e}")
        return 0

def fix_moonriver_votecast_data():
    """Fix the Moonriver VoteCast CSV data formatting issues"""
    
    # Find the latest complete VoteCast file
    csv_files = []
    for file in os.listdir('.'):
        if file.startswith('Moonriver_VoteCast_events_complete_') and file.endswith('.csv'):
            csv_files.append(file)
    
    if not csv_files:
        print("No Moonriver VoteCast complete CSV files found!")
        return
    
    # Use the most recent file
    latest_file = sorted(csv_files)[-1]
    print(f"Processing file: {latest_file}")
    
    # Read the CSV file
    df = pd.read_csv(latest_file)
    print(f"Loaded {len(df)} events from {latest_file}")
    
    # Fix the data
    print("Fixing voter addresses...")
    df['voter'] = df['raw_data'].apply(extract_voter_from_raw_data)
    
    print("Fixing proposal IDs...")
    df['proposal_id'] = df['raw_data'].apply(decode_proposal_id)
    
    print("Fixing support values...")
    df['support'] = df['raw_data'].apply(extract_support_from_raw_data)
    
    print("Fixing votes values...")
    df['votes'] = df['raw_data'].apply(extract_votes_from_raw_data)
    
    # Create output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"Moonriver_VoteCast_events_fixed_{timestamp}.csv"
    
    # Save the fixed data
    df.to_csv(output_file, index=False)
    print(f"Fixed data saved to: {output_file}")
    
    # Show sample of fixed data
    print("\nSample of fixed data:")
    print(df[['block_number', 'voter', 'proposal_id', 'support', 'votes']].head(10))
    
    # Show statistics
    print(f"\nData statistics:")
    print(f"Total events: {len(df)}")
    print(f"Events with voter addresses: {len(df[df['voter'] != ''])}")
    print(f"Unique voters: {df['voter'].nunique()}")
    print(f"Unique proposal IDs: {df['proposal_id'].nunique()}")
    print(f"Proposal ID range: {df['proposal_id'].min()} - {df['proposal_id'].max()}")
    
    return output_file

if __name__ == "__main__":
    print("Starting Moonriver VoteCast data fix...")
    output_file = fix_moonriver_votecast_data()
    print(f"Data fix completed! Output file: {output_file}")