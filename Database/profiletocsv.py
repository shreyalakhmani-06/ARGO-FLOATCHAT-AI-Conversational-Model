import xarray as xr
import pandas as pd
import os
import glob

# Folder containing your .nc profile files
nc_folder = r"data\profiles"  # change this to your folder path
output_folder = "profiles_csv"
os.makedirs(output_folder, exist_ok=True)

# Variables to keep
variables_to_keep = [
    'PLATFORM_NUMBER', 'PROJECT_NAME', 'PI_NAME', 'CYCLE_NUMBER', 'DIRECTION',
    'JULD', 'JULD_QC', 'LATITUDE', 'LONGITUDE', 'POSITION_QC', 'POSITIONING_SYSTEM',
    'PRES', 'TEMP', 'PSAL'
]

# Get all .nc files in the folder
nc_files = glob.glob(os.path.join(nc_folder, "*.nc"))

for nc_file in nc_files:
    # Open the .nc file
    ds = xr.open_dataset(nc_file)
    
    # Check which variables are present
    present_vars = [var for var in variables_to_keep if var in ds.variables]
    
    # Convert selected variables to a pandas DataFrame
    df = ds[present_vars].to_dataframe().reset_index()
    
    # Output CSV file name
    base_name = os.path.basename(nc_file).replace(".nc", ".csv")
    output_path = os.path.join(output_folder, base_name)
    
    # Save to CSV
    df.to_csv(output_path, index=False)
    print(f"Converted {nc_file} → {output_path}")
    
    # Close the dataset
    ds.close()

print("All .nc files have been converted to CSV!")
