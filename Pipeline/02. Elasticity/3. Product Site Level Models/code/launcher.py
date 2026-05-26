# launcher.py
import os
import sys
import subprocess
import time

# Find current folder where launcher.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Adjust these paths to match your real structure
scripts = [
    os.path.join(BASE_DIR, "regular_price.py"),
    os.path.join(BASE_DIR, "data_prepration.py"),
    os.path.join(BASE_DIR, "feature_selection.py"),
    os.path.join(BASE_DIR, "model.py"),
    os.path.join(BASE_DIR, "data_prep_after_model_output.py")
]


def format_time(seconds):
    """Return formatted string: M min S sec if >= 60s, else S sec"""
    if seconds >= 60:
        mins, secs = divmod(seconds, 60)
        return f"{int(mins)} min {secs:.1f} sec"
    else:
        return f"{seconds:.2f} sec"


def run_pipeline():
    print("=" * 80)
    print(" Starting Elasticity Modeling Pipeline")
    print("=" * 80)

    python_exec = sys.executable
    total_start = time.time()
    timings = {}  # store per-script times

    for script_path in scripts:
        script_name = os.path.basename(script_path)
        print(f"\n Running {script_name} ...")
        if not os.path.exists(script_path):
            print(f" Script not found: {script_path}")
            break
        try:
            start = time.time()
            subprocess.run([python_exec, script_path], check=True)
            elapsed = time.time() - start
            timings[script_name] = elapsed
            print(f" Finished {script_name} in {format_time(elapsed)}")
        except subprocess.CalledProcessError:
            print(f" Error in {script_name}, stopping pipeline.")
            break

    total_elapsed = time.time() - total_start
    print("\n Pipeline completed.")

    # Print summary of timings
    if timings:
        print("\n Time Summary:")
        for script_name, t in timings.items():
            print(f"   • {script_name}: {format_time(t)}")
        print(f"\n Total time taken: {format_time(total_elapsed)}")


if __name__ == "__main__":
    run_pipeline()

