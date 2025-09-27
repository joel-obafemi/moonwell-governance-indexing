#!/usr/bin/env python3
"""
Fix votes column formatting in Moonriver VoteCast data to prevent scientific notation
The issue is that large numbers get converted to scientific notation when uploaded to Dune
We need to ensure the votes column is properly formatted as strings with quotes
"""

import pandas as pd
import csv
from datetime import datetime

def fix_votes_formatting():
    """Fix the votes column formatting to prevent scientific notation"""
    
    input_file = "Moonriver_VoteCast_events_fixed_20250925_152315.csv"
    output_file = f"Moonriver_VoteCast_events_votes_fixed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    print(f"Reading input file: {input_file}")
    
    # Read the CSV file
    df = pd.read_csv(input_file)
    
    print(f"Original data shape: {df.shape}")
    print(f"Votes column dtype: {df['votes'].dtype}")
    
    # Sample of original votes values
    print("\nSample original votes values:")
    for i in range(5):
        print(f"  Row {i}: {df.iloc[i]['votes']}")
    
    # Ensure votes column is treated as string to prevent scientific notation
    # Convert to string and ensure no scientific notation
    df['votes'] = df['votes'].astype(str)
    
    # Check for any scientific notation and convert back to full numbers
    def fix_scientific_notation(value):
        if 'e+' in str(value).lower() or 'e-' in str(value).lower():
            # Convert scientific notation back to full number
            return f"{float(value):.0f}"
        return str(value)
    
    df['votes'] = df['votes'].apply(fix_scientific_notation)
    
    print("\nSample fixed votes values:")
    for i in range(5):
        print(f"  Row {i}: {df.iloc[i]['votes']}")
    
    # Write to CSV with proper formatting
    # Use quoting to ensure large numbers are treated as strings
    print(f"\nWriting to output file: {output_file}")
    
    df.to_csv(output_file, index=False, quoting=csv.QUOTE_NONNUMERIC)
    
    print(f"✅ Successfully created {output_file}")
    print(f"Total events: {len(df)}")
    
    # Verify the output file
    print("\nVerifying output file...")
    with open(output_file, 'r') as f:
        lines = f.readlines()
        print("First few lines of output:")
        for i, line in enumerate(lines[:3]):
            print(f"  Line {i}: {line.strip()}")
    
    return output_file

def main():
    print("=== Fixing Votes Column Formatting for Moonriver VoteCast Data ===\n")
    
    output_file = fix_votes_formatting()
    
    print(f"\n🎉 Votes formatting fixed successfully!")
    print(f"Output file: {output_file}")
    print("\nThe votes column is now properly formatted to prevent scientific notation in Dune.")

if __name__ == "__main__":
    main()