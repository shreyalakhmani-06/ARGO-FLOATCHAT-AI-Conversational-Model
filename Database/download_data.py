from ftplib import FTP
import os

# Connect to Argo FTP
ftp = FTP("ftp.ifremer.fr")
ftp.login()

# INCOIS DAC only
dac_centers = ["incois"]

# Where to save data locally
base_dir = "data"
os.makedirs(os.path.join(base_dir, "profiles"), exist_ok=True)
os.makedirs(os.path.join(base_dir, "metadata"), exist_ok=True)

# Counters to stop after 60 files each
prof_count, meta_count = 0, 0
limit = 60 

# Helper to download a single file
def download(remote_file, local_file):
    if not os.path.exists(local_file):  # avoid re-downloading
        with open(local_file, "wb") as f:
            ftp.retrbinary("RETR " + remote_file, f.write)
        print("Downloaded:", remote_file)

# Loop through DAC centers
for dac in dac_centers:
    ftp.cwd(f"/ifremer/argo/dac/{dac}")
    floats = ftp.nlst()  # list of float IDs
    
    for fl in floats:
        ftp.cwd(f"/ifremer/argo/dac/{dac}/{fl}")
        files = ftp.nlst()

        # Look for profile and metadata files
        for f in files:
            if f.endswith("_prof.nc") and prof_count < limit:
                download(f, os.path.join(base_dir, "profiles", f"{dac}_{f}"))
                prof_count += 1

            if f.endswith("_meta.nc") and meta_count < limit:
                download(f, os.path.join(base_dir, "metadata", f"{dac}_{f}"))
                meta_count += 1

        # Go back up one level
        ftp.cwd("..")

        # Stop when limits reached
        if prof_count >= limit and meta_count >= limit:
            break
    if prof_count >= limit and meta_count >= limit:
        break

ftp.quit()
print(f"✅ Done: {prof_count} profiles and {meta_count} metadata files saved in /data")
