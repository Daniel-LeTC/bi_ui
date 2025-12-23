import duckdb
import pandas as pd
import numpy as np
import os
import time

# Config
SOURCE_FILE = "../scrape_tool/exports/Master_PPC_Data.parquet"
TARGET_FILE = "../scrape_tool/exports/Big_Master_PPC_Data.parquet"
TARGET_ROWS = 1_000_000

def generate_big_data():
    print(f"🚀 Loading original data from {SOURCE_FILE}...")
    
    # Load original data
    con = duckdb.connect()
    original_df = con.execute(f"SELECT * FROM read_parquet('{SOURCE_FILE}')").df()
    original_rows = len(original_df)
    
    print(f"✅ Loaded {original_rows} rows.")
    
    if original_rows == 0:
        print("❌ Source file is empty!")
        return

    # Calculate multiplier
    multiplier = (TARGET_ROWS // original_rows) + 1
    print(f"🔄 Need to replicate {multiplier} times to reach {TARGET_ROWS} rows...")
    
    dfs = []
    
    for i in range(multiplier):
        batch = original_df.copy()
        
        # Masking / Randomization
        # 1. Modify SKU & ASIN to look unique
        suffix = f"_FAKE_{i}"
        if "SKU" in batch.columns:
            batch["SKU"] = batch["SKU"].astype(str) + suffix
        if "ASIN" in batch.columns:
            batch["ASIN"] = batch["ASIN"].astype(str) + suffix
            
        # 2. Jitter Metrics (Revenue, Spend) +/- 10%
        if "Revenue (Actual)" in batch.columns:
            jitter = np.random.uniform(0.9, 1.1, size=len(batch))
            batch["Revenue (Actual)"] = batch["Revenue (Actual)"] * jitter
            
        if "Ads Spend (Actual)" in batch.columns:
            jitter = np.random.uniform(0.9, 1.1, size=len(batch))
            batch["Ads Spend (Actual)"] = batch["Ads Spend (Actual)"] * jitter

        dfs.append(batch)
    
    print("🧩 Concatenating batches...")
    big_df = pd.concat(dfs, ignore_index=True)
    
    # Trim to exact target
    big_df = big_df.head(TARGET_ROWS)
    print(f"📊 Final DataFrame shape: {big_df.shape}")
    
    print(f"💾 Saving to {TARGET_FILE}...")
    start_time = time.time()
    big_df.to_parquet(TARGET_FILE, compression='snappy')
    end_time = time.time()
    
    print(f"✅ DONE! Saved 1M rows in {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    generate_big_data()