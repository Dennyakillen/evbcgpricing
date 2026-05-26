# main.py
from pathlib import Path
import sys
import subprocess

BASE_DIR = Path(__file__).resolve().parent
def main():
    # Run Data Preparation
    
    subprocess.run([sys.executable, str(BASE_DIR / "Data_Preparation.py")], check=True)
    print("Data Preparation completed")

    # Run Clustering
    
    subprocess.run([sys.executable, str(BASE_DIR / "Clustering.py")], check=True)
    print("Clustering completed")

if __name__ == "__main__":
    main()