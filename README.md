# Moonwell Governance Event Indexer

A comprehensive blockchain event indexing system for Moonwell governance events on Moonriver and Moonbeam networks. This project extracts, processes, and uploads governance-related events to Dune Analytics for data analysis and visualization.

## 🚀 Features

- **Multi-Chain Support**: Indexes events from both Moonriver and Moonbeam networks
- **Fault-Tolerant**: Network interruption resistance with automatic retry mechanisms
- **Incremental Processing**: Checkpoint-based progress tracking and resume capability
- **Data Export**: Automatic CSV generation and Dune Analytics integration
- **Event Types Supported**:
  - `DelegateChanged` events
  - `DelegateVotesChanged` events
  - `VoteCast` events

## 📊 Data Coverage

### Moonriver Network
- **Contract Address**: `0x8568A675384d761f36eC269D695d6Ce4423cfaB1`
- **Starting Block**: `2,676,660`
- **Events Indexed**: 
  - DelegateVotesChanged: ~71 events
  - VoteCast: Comprehensive historical data

### Moonbeam Network
- **Contract Address**: `0x511aB53F793683763E5a8829738301368a2411E3`
- **Starting Block**: `1,005,779`
- **Events Indexed**:
  - DelegateVotesChanged: ~188,691 events

## 🛠️ Technology Stack

- **Python 3.8+**
- **Web3.py** for blockchain interaction
- **Requests** for HTTP API calls
- **CSV** for data export
- **Pickle** for checkpoint persistence

## 📁 Project Structure

```
moonwell-csv/
├── indexers/
│   ├── moonriver_delegatevotes_changed_indexer.py
│   ├── moonbeam_delegatevotes_changed_indexer.py
│   ├── moonriver_delegate_changed_indexer_enhanced.py
│   └── moonriver_votecast_indexer_enhanced.py
├── uploaders/
│   ├── upload_moonriver_delegatevotes_to_dune.py
│   ├── upload_moonbeam_delegatevotes_to_dune.py
│   └── upload_moonbeam_votecast_to_dune.py
├── data/
│   ├── *.csv (generated event data)
│   ├── *.pkl (checkpoint files)
│   └── *.txt (progress tracking)
└── README.md
```

## 🚀 Quick Start

### Prerequisites

```bash
pip install web3 requests
```

### Running the Indexers

1. **Index Moonriver DelegateVotesChanged Events**:
```bash
python moonriver_delegatevotes_changed_indexer.py
```

2. **Index Moonbeam DelegateVotesChanged Events**:
```bash
python moonbeam_delegatevotes_changed_indexer.py
```

3. **Upload to Dune Analytics**:
```bash
python upload_moonriver_delegatevotes_to_dune.py
python upload_moonbeam_delegatevotes_to_dune.py
```

## 📈 Dune Analytics Integration

The project automatically uploads indexed data to Dune Analytics with the following table names:

- `moonriver_delegatevotes_changed_events`
- `moonbeam_delegatevotes_changed_events`

### Sample Queries

**Basic Event Query**:
```sql
SELECT * FROM moonriver_delegatevotes_changed_events
ORDER BY block_number DESC
LIMIT 10;
```

**Readable Balance Format**:
```sql
SELECT
    delegate,
    CAST(previous_balance AS DECIMAL(38,0)) / 1e18 as previous_balance_readable,
    CAST(new_balance AS DECIMAL(38,0)) / 1e18 as new_balance_readable,
    block_number,
    transaction_hash
FROM moonriver_delegatevotes_changed_events
ORDER BY block_number DESC;
```

## 🔧 Configuration

### RPC Endpoints
- **Moonriver**: `https://rpc.api.moonriver.moonbeam.network`
- **Moonbeam**: `https://rpc.api.moonbeam.network`

### Event Signatures
- **DelegateVotesChanged**: `0xdec2bacdd2f05b59de34da9b523dff8be42e5e38e818c82fdb0bae774387a724`
- **DelegateChanged**: `0x3134e8a2e6d97e929a7e54011ea5485d7d196dd5f0ba4d4ef95803e8e3fc257f`

## 🛡️ Error Handling

The indexers include robust error handling for:
- Network timeouts and connection issues
- RPC rate limiting
- Invalid block ranges
- Data parsing errors

## 📊 Data Schema

### DelegateVotesChanged Events
```
- block_number: Block number where event occurred
- transaction_hash: Transaction hash
- delegate: Address of the delegate
- previous_balance: Previous voting power (wei)
- new_balance: New voting power (wei)
- timestamp: Block timestamp
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🔗 Links

- [Moonwell Protocol](https://moonwell.fi/)
- [Dune Analytics](https://dune.com/)
- [Moonriver Network](https://moonriver.moonscan.io/)
- [Moonbeam Network](https://moonscan.io/)

## 📞 Contact

For questions or support, please open an issue in this repository.

---

*This project is part of a blockchain data analysis portfolio demonstrating expertise in Web3 development, data indexing, and analytics integration.*