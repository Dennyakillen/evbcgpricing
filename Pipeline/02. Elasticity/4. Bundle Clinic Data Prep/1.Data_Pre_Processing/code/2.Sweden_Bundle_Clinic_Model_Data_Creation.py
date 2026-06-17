import os
import sys
import pandas as pd
import numpy as np
import yaml
from bundle_utils import *
from pathlib import Path

# Path to this config file
config_file = Path(__file__).resolve().parent /"src"/ "config.yml"

# Load YAML
with open(config_file, "r") as f:
    config = yaml.safe_load(f)

# Resolve module_path relative to config file location
module_path = (config_file.parent / config["module_path"]).resolve()

print("Module Path:", module_path)

if __name__ == '__main__':
    # Resolve module_path relative to config file location
    module_path = (config_file.parent / config["module_path"]).resolve()
    input_data = os.path.join(module_path, config['model_data_creation']['input_data'].lstrip("/\\"))
    sweden_bundles_data = os.path.join(module_path, config['model_data_creation']['sweden_bundles'].lstrip("/\\"))
    fte_data = os.path.join(module_path, config['model_data_creation']['fte_data'].lstrip("/\\"))
    output_data = os.path.join(module_path, config['model_data_creation']['output_data'].lstrip("/\\"))
    # output_model_data = os.path.join(model_module_path, config['model_data_creation']['model_output_data'].lstrip("/\\"))

    # 1. Load input data
    txn_data = load_and_clean_transactions(input_data)
    txn_data.rename(columns = {'SoldQuantity':'Qty',  "SalesTotal":"TotalNet", 'ID_Department':'SiteCode'}, inplace = True)
    sweden_bundles = load_data(sweden_bundles_data)
    sweden_bundles.rename(columns = {'Bundle':'Bundle_code', 'Bundle Revenue Sorted (Item Description)':'Bundle_description', "ProductCode":"Product Code"}, inplace = True)
    fte = pd.read_excel(fte_data)
    fte.rename(columns = {'ID_Department':'SiteCode'}, inplace = True)
    # --- Additiv normalisering 2026-06-17 (FD.36, Jens Palmo): gor FTE-data tolerant for kallformat.
    # BCG:s join/groupby-logik orord; sakerstaller bara att nycklar matchar oavsett ursprung.
    # (1) Cluster (BCG Alteryx, singular) -> aven Clusters (koden grupperar pa plural). Bevarar Cluster.
    if 'Cluster' in fte.columns and 'Clusters' not in fte.columns:
        fte['Clusters'] = fte['Cluster']
    # (2) week till str(YYYY-MM-DD) (koden konverterar bundle-datan sa fore FTE-merge; matcha det).
    fte['week_starting_monday'] = pd.to_datetime(fte['week_starting_monday'])  # datetime: matchar bundle-datans typ vid FTE-merge (koden to_datetime:ar bundle-datan fore merge, str efter).

    # 2. Create expected bundles
    expected_bundle_all = all_bundle_data_creation(sweden_bundles, txn_data)

    # 3. Apply elimination logic
    expected_bundle_all_final = apply_bundle_elimination(expected_bundle_all)

    # 4. Process bundles with FTE interpolation
    bundle_data_final_all, apt_data_basket_all = process_bundles_with_fte(
        sweden_bundles, txn_data, expected_bundle_all_final, fte
    )

    # 5. Save outputs
    bundle_data_final_all.to_csv(output_data, index=False)

    print("Pipeline completed. Results saved in /output folder.")