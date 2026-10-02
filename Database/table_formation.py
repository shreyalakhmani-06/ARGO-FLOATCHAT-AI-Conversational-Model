import pandas as pd
import numpy as np

# 1) Read CSV
src = "merged_profiles.csv"
df = pd.read_csv(src, dtype=str, low_memory=False)

# 2) Normalize column names for case-insensitive selection
df.columns = [c.strip() for c in df.columns]  # trim whitespace
lower_map = {c.lower(): c for c in df.columns}  # map lowercase -> original

# Desired columns (lowercase keys)
wanted = [
    "platform_number",
    "cycle_number",
    "pres",
    "temp",
    "psal",
    "juld",
    "latitude",
    "longitude",
    "direction",
]

# Resolve available columns case-insensitively
have_cols = {k: lower_map[k] for k in wanted if k in lower_map}

# Warn if anything is missing (optional: not raising to be resilient)
missing = [k for k in wanted if k not in have_cols]
if missing:
    print("Warning: missing columns (case-insensitive):", missing)

# 3) Subset to available requested columns
df = df[ list(have_cols.values()) ].copy()

# 4) Clean byte-string-like fields such as b'ARGOS   ' -> ARGOS
def debytes(x):
    if isinstance(x, str) and x.startswith("b'") and x.endswith("'"):
        try:
            # Drop leading b' and trailing ', then strip
            inner = x[2:-1]
            return inner.strip()
        except Exception:
            return x
    if isinstance(x, str) and x.startswith('b"') and x.endswith('"'):
        try:
            inner = x[2:-1]
            return inner.strip()
        except Exception:
            return x
    return x.strip() if isinstance(x, str) else x

for col in df.columns:
    df[col] = df[col].apply(debytes)

# 5) Rename columns: pres->pressure, temp->temperature, psal->salinity
rename_map = {}
if "pres" in lower_map and lower_map["pres"] in df.columns:
    rename_map[ lower_map["pres"] ] = "pressure"
if "temp" in lower_map and lower_map["temp"] in df.columns:
    rename_map[ lower_map["temp"] ] = "temperature"
if "psal" in lower_map and lower_map["psal"] in df.columns:
    rename_map[ lower_map["psal"] ] = "salinity"

df.rename(columns=rename_map, inplace=True)

# 6) Convert measurement columns to numeric (errors='coerce' -> NaN on bad strings)
for mcol in ["pressure", "temperature", "salinity"]:
    if mcol in df.columns:
        df[mcol] = pd.to_numeric(df[mcol], errors="coerce")

# 7) Drop rows where ALL three measurements are missing
measure_cols_present = [c for c in ["pressure", "temperature", "salinity"] if c in df.columns]
if measure_cols_present:
    df = df.dropna(subset=measure_cols_present, how="all")

# 8) Optionally coerce lat/lon to numeric
for gcol in ["latitude", "longitude"]:
    if gcol in lower_map and lower_map[gcol] in df.columns:
        df[ lower_map[gcol] ] = pd.to_numeric(df[ lower_map[gcol] ], errors="coerce")

# 9) Save cleaned result
out = "cleaned_measurements.csv"
df.to_csv(out, index=False)

print(f"File '{out}' created successfully with {len(df)} rows and {df.shape[1]} columns.")
