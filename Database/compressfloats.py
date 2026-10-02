import pandas as pd
import os
import glob

# Path where your 60 CSV files are stored
folder_path = r"csv_data\floats"

# Get all CSV files
all_files = glob.glob(os.path.join(folder_path, "*.csv"))

# Columns we want to keep
columns_to_keep = [
    "platform_number", "project_name", "pi_name", 
    "launch_date", "launch_latitude", "launch_longitude", "dac"
]

df_list = []
for file in all_files:
    df = pd.read_csv(file)
    
    # Keep only the selected columns
    df = df.reindex(columns=columns_to_keep)
    
    df_list.append(df)

# Merge all into one DataFrame
merged_df = pd.concat(df_list, ignore_index=True)

# Save to single CSV
merged_df.to_csv("merged_floats.csv", index=False)

print("✅ Merged 60 CSV files into merged_floats.csv with only the 7 required columns")
