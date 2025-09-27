import pandas as pd

# Load the fixed CSV file
df = pd.read_csv('VoteCast_events_fixed_20250924_180037.csv')

print('Support value distribution:')
print(df['support'].value_counts().sort_index())

print('\nSample of different support values:')
for val in sorted(df['support'].unique()):
    print(f'Support {val}: {len(df[df["support"] == val])} votes')

print('\nFirst few rows with different support values:')
for val in sorted(df['support'].unique())[:3]:
    sample = df[df['support'] == val].head(2)
    print(f'\nSupport {val} examples:')
    print(sample[['block_number', 'voter', 'proposal_id', 'support', 'votes']].to_string())