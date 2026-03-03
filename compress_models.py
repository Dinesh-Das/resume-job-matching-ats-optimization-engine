import os
import joblib
import glob

# Try output directory in current folder
output_dir = os.path.join(os.getcwd(), "output")
if not os.path.exists(output_dir):
    print(f"Error: {output_dir} not found. Are you running this in the deploy root folder?")
    exit(1)

joblib_files = glob.glob(os.path.join(output_dir, "*.joblib"))
print(f"Found {len(joblib_files)} model files to compress in {output_dir}...")

for file in joblib_files:
    print(f"Compressing {os.path.basename(file)}... ", end="", flush=True)
    try:
        data = joblib.load(file)
        joblib.dump(data, file, compress=3)
        size_mb = os.path.getsize(file) / (1024 * 1024)
        print(f"Done! New size: {size_mb:.1f} MB")
    except Exception as e:
        print(f"Error: {e}")

print("All models successfully compressed! You can now run git commit and git push again.")
