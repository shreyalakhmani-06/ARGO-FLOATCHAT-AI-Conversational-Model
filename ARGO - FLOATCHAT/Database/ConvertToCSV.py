from netCDF4 import Dataset
import pandas as pd
import numpy as np
import os
import glob

profile_dir = "data/profiles"
metadata_dir = "data/metadata"
output_dir = "csv_data"
os.makedirs(output_dir, exist_ok=True)

def safe_extract(nc, var, idx=None):
    """Return variable if exists, else None"""
    if var in nc.variables:
        arr = nc.variables[var][:]
        if idx is not None and arr.shape:  # single value per profile
            return arr[idx]
        return arr
    return None

# -------- Convert Profiles --------
print("🔹 Converting Profile files...")
for file in glob.glob(os.path.join(profile_dir, "**/*.nc"), recursive=True):
    nc = Dataset(file, "r")

    n_profiles = len(nc.dimensions.get("N_PROF", [])) or 1
    rows = []

    for i in range(n_profiles):
        lat = safe_extract(nc, "LATITUDE", i)
        lon = safe_extract(nc, "LONGITUDE", i)

        pres = safe_extract(nc, "PRES")
        temp = safe_extract(nc, "TEMP")
        psal = safe_extract(nc, "PSAL")

        if pres is not None and temp is not None and psal is not None:
            for j in range(len(pres[i])):
                rows.append({
                    "latitude": float(lat) if lat is not None else None,
                    "longitude": float(lon) if lon is not None else None,
                    "pressure": float(pres[i][j]) if pres[i][j] < 1e30 else None,
                    "temperature": float(temp[i][j]) if temp[i][j] < 1e30 else None,
                    "salinity": float(psal[i][j]) if psal[i][j] < 1e30 else None
                })

    df = pd.DataFrame(rows)
    csv_file = os.path.join(output_dir, os.path.basename(file).replace(".nc", ".csv"))
    df.to_csv(csv_file, index=False)
    print("✅ Saved:", csv_file)
    nc.close()

# -------- Convert Metadata --------
print("\n🔹 Converting Metadata files...")
for file in glob.glob(os.path.join(metadata_dir, "**/*.nc"), recursive=True):
    nc = Dataset(file, "r")

    df = pd.DataFrame({
        "platform_number": [safe_extract(nc, "PLATFORM_NUMBER")],
        "project_name": [safe_extract(nc, "PROJECT_NAME")],
        "pi_name": [safe_extract(nc, "PI_NAME")],
        "launch_date": [safe_extract(nc, "LAUNCH_DATE")],
        "launch_latitude": [safe_extract(nc, "LAUNCH_LATITUDE")],
        "launch_longitude": [safe_extract(nc, "LAUNCH_LONGITUDE")],
        "dac": [safe_extract(nc, "DATA_CENTRE")]
    })

    csv_file = os.path.join(output_dir, os.path.basename(file).replace(".nc", ".csv"))
    df.to_csv(csv_file, index=False)
    print("✅ Saved:", csv_file)
    nc.close()
