"""
Split feature inventory into batches for rate-limit-friendly collection.
Creates 5 batch CSV files (10 features each) to avoid Google Trends 429 errors.

Usage: python src/data_collection/create_batches.py
"""

import pandas as pd
from pathlib import Path


def create_batches(input_file: str = 'data/raw/feature_inventory.csv', batch_size: int = 10):
    """Split feature inventory into batches."""
    df = pd.read_csv(input_file)
    print(f"📂 Loaded {len(df)} features from {input_file}")
    
    batch_dir = Path('data/raw/batches')
    batch_dir.mkdir(parents=True, exist_ok=True)
    
    num_batches = (len(df) + batch_size - 1) // batch_size
    
    for i in range(num_batches):
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, len(df))
        
        batch = df.iloc[start_idx:end_idx]
        batch_file = batch_dir / f'batch_{i+1}_of_{num_batches}.csv'
        
        batch.to_csv(batch_file, index=False)
        print(f"✓ Created {batch_file.name}: Features {start_idx+1}-{end_idx}")
        print(f"   Companies: {', '.join(batch['company'].unique())}")
    
    print(f"\n🎯 Created {num_batches} batches in {batch_dir}/")
    print("\nTo collect:")
    for i in range(num_batches):
        print(f"   python src/data/collect_trends_data.py --full --input data/raw/batches/batch_{i+1}_of_{num_batches}.csv")
        if i < num_batches - 1:
            print(f"   # Wait 30-60 minutes before next batch")


if __name__ == "__main__":
    create_batches()
