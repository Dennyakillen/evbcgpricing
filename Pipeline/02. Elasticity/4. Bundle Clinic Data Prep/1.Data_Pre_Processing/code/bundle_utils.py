import os
import pandas as pd
import warnings
from tqdm import tqdm
import ray

warnings.filterwarnings("ignore")

# Init Ray safely
if not ray.is_initialized():
    ray.init(
        ignore_reinit_error=True,
        num_cpus=12,
        object_store_memory=2 * 1024**3,  # 2 GB
        include_dashboard=False
    )


def load_and_clean_transactions(filepath: str) -> pd.DataFrame:
    """
    Load transactions from a CSV file and filter invalid rows.

    Args:
        filepath (str): Path to the CSV file containing transaction data.

    Returns:
        pd.DataFrame: Cleaned transaction data with only positive SalesTotal and SoldQuantity.
    """
    txn_data = pd.read_csv(filepath, encoding="cp1252")
    txn_data = txn_data[txn_data["SalesTotal"] > 0]
    txn_data = txn_data[txn_data["SoldQuantity"] > 0]
    return txn_data


def load_data(filename: str) -> pd.DataFrame:
    """
    Load sweden data from a CSV file.

    Args:
        filename (str): CSV filename.

    Returns:
        pd.DataFrame: Sweden dataset.
    """
    return pd.read_csv(filename, encoding="cp1252")


def load_mapping(path: str, filename: str, filetype: str = "excel",
                 key_cols: tuple[str, str] | None = None) -> pd.DataFrame:
    """
    Load mapping data from Excel or CSV, optionally creating a composite key.

    Args:
        path (str): Directory path.
        filename (str): File name.
        filetype (str, optional): File format ("excel" or "csv"). Defaults to "excel".
        key_cols (tuple[str, str], optional): Columns to combine into a composite key.

    Returns:
        pd.DataFrame: Processed mapping data.
    """
    if filetype == "excel":
        mapping = pd.read_excel(os.path.join(path, filename))
    else:
        mapping = pd.read_csv(os.path.join(path, filename))

    if "week" in mapping.columns:
        mapping = mapping.rename(columns={"week": "week_starting_monday"})
        mapping["week_starting_monday"] = mapping["week_starting_monday"].astype(str).str[:10]

    if key_cols:
        mapping["KEY"] = mapping[key_cols[0]].astype(str) + "-" + mapping[key_cols[1]].astype(str)

    return mapping

def merge_fte_mapping(bundle_data: pd.DataFrame, fte_mapping: pd.DataFrame) -> pd.DataFrame:
    """
    Merge FTE mapping into bundle data using a composite key.

    Args:
        bundle_data (pd.DataFrame): Bundle dataset.
        fte_mapping (pd.DataFrame): FTE mapping with clusters and weeks.

    Returns:
        pd.DataFrame: Bundle dataset with FTE merged.
    """
    bundle_data["KEY"] = (
        bundle_data["Clusters"].astype(str) + "-" +
        bundle_data["week_starting_monday"].astype(str)
    )
    fte_mapping["KEY"] = (
        fte_mapping["Clusters"].astype(str) + "-" +
        fte_mapping["week_starting_monday"].astype(str)
    )
    merged = bundle_data.merge(fte_mapping[["KEY", "FTE"]], on="KEY", how="left")
    print(f"FTE merged. Missing FTE values: {merged['FTE'].isna().sum()}")
    return merged


@ray.remote
def build_bundle_for_type(bundle_type, uk_bundles, txn_data):
    """
    Build expected bundles for a given bundle type.

    Args:
        bundle_type (str): Bundle code.
        uk_bundles (pd.DataFrame): UK bundles dataset.
        txn_data (pd.DataFrame): Transaction dataset.

    Returns:
        pd.DataFrame: Expected bundles for the specified type.
    """
    uk_bundles_filtered = uk_bundles[uk_bundles["Bundle_code"] == bundle_type]
    txn_data_filtered = txn_data.merge(
        uk_bundles_filtered[["Bundle_description", "Bundle_code", "Product Code"]],
        how="inner", left_on="ProductCode", right_on="Product Code"
    )
    if txn_data_filtered.empty:
        return pd.DataFrame()

    txn_data_agg = (
        txn_data_filtered.groupby(["VisitIdPatient", "ProductCode"])
        .agg({"Qty": "sum", "TotalNet": "sum"}).reset_index()
    )

    bundle = txn_data_agg.groupby("VisitIdPatient").agg({
        "ProductCode": lambda x: ",".join(x.astype(str)),
        "Qty": "sum",
        "TotalNet": "sum"
    }).reset_index().rename(columns={"ProductCode": "Bundle_code"})

    unique_bundle_codes = uk_bundles_filtered["Bundle_code"].dropna().unique()
    expected_bundle = bundle[bundle["Bundle_code"].isin(unique_bundle_codes)]
    expected_bundle = expected_bundle[["VisitIdPatient", "TotalNet"]].copy()
    expected_bundle["Bundle_name"] = bundle_type
    return expected_bundle


def all_bundle_data_creation(uk_bundles: pd.DataFrame, txn_data: pd.DataFrame) -> pd.DataFrame:
    """
    Build expected bundles for all bundle types in parallel.

    Args:
        uk_bundles (pd.DataFrame): UK bundles dataset.
        txn_data (pd.DataFrame): Transaction dataset.

    Returns:
        pd.DataFrame: Combined expected bundle dataset.
    """
    tasks = [build_bundle_for_type.remote(b, uk_bundles, txn_data) for b in uk_bundles.Bundle_code.unique()]
    results = ray.get(tasks)
    return pd.concat(results, ignore_index=True)


def eliminate_subsets_optimized(bundle_names: list[str]) -> dict[str, int]:
    """
    Eliminate bundles that are strict subsets of other bundles.

    Args:
        bundle_names (list[str]): List of bundle names.

    Returns:
        dict[str, int]: Dictionary of bundles with elimination flag (0 or 1).
    """
    bundle_sets = {b: set(b.split(",")) for b in bundle_names}
    output = dict.fromkeys(bundle_names, 0)
    bundle_list = list(bundle_sets.items())

    for i, (key_i, set_i) in enumerate(bundle_list):
        for j in range(i + 1, len(bundle_list)):
            key_j, set_j = bundle_list[j]
            if set_i < set_j:
                output[key_i] = 1
            elif set_j < set_i:
                output[key_j] = 1
    return output


@ray.remote
def eliminate_for_visit(visitid, group_df):
    """
    Apply subset elimination for bundles in a single visit.

    Args:
        visitid (str or int): Visit ID.
        group_df (pd.DataFrame): Bundles for the visit.

    Returns:
        pd.DataFrame: Elimination results for bundles.
    """
    bundle_names = group_df["Bundle_name"].unique()
    if len(bundle_names) <= 1:
        return pd.DataFrame()
    elim_dict = eliminate_subsets_optimized(bundle_names)
    rows = [
        {"VisitIdPatient": visitid, "Bundle_name": bname, "Bundle_Elimination": elim}
        for bname, elim in elim_dict.items() if elim == 1
    ]
    return pd.DataFrame(rows)


def apply_bundle_elimination(expected_bundle_all: pd.DataFrame) -> pd.DataFrame:
    """
    Apply subset elimination across all visits.

    Args:
        expected_bundle_all (pd.DataFrame): Expected bundle dataset.

    Returns:
        pd.DataFrame: Dataset with elimination flags applied.
    """
    tasks = [eliminate_for_visit.remote(vid, g) for vid, g in expected_bundle_all.groupby("VisitIdPatient")]
    results = ray.get(tasks)
    elimination_df = pd.concat(results, ignore_index=True)

    return (
        expected_bundle_all[["VisitIdPatient", "TotalNet", "Bundle_name"]]
        .merge(elimination_df, on=["VisitIdPatient", "Bundle_name"], how="left")
        .assign(Bundle_Elimination=lambda df: df["Bundle_Elimination"].fillna(0).astype(int))
    )


def process_bundles_with_fte(
    uk_bundles: pd.DataFrame,
    txn_data: pd.DataFrame,
    expected_bundle_all_final: pd.DataFrame,
    fte_data: pd.DataFrame,
    level: str = "Clusters"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Process all bundles: APT analysis, elasticity, bundle metrics, and FTE interpolation.

    Args:
        uk_bundles (pd.DataFrame): UK bundles dataset.
        txn_data (pd.DataFrame): Transaction data.
        expected_bundle_all_final (pd.DataFrame): Bundles with elimination applied.
        fte_data (pd.DataFrame): Site-week FTE interpolation data.
        level (str, optional): Grouping level. Defaults to "Clusters".

    Returns:
        tuple:
            pd.DataFrame: Final bundle metrics with FTE included.
            pd.DataFrame: APT product-level data.
    """
    bundle_data_final_all = pd.DataFrame()
    apt_data_basket_all = pd.DataFrame()

    for bundle_type in tqdm(uk_bundles.Bundle_code.unique(), desc="Processing bundles"):
        # Filter bundle definition
        uk_bundles_filtered = uk_bundles[uk_bundles["Bundle_code"] == bundle_type]
        txn_data_filtered = txn_data.merge(
            uk_bundles_filtered[["Bundle_description", "Bundle_code", "Product Code"]],
            how="inner", left_on="ProductCode", right_on="Product Code"
        )

        # Expected bundle
        expected_bundle = expected_bundle_all_final[
            (expected_bundle_all_final["Bundle_name"] == bundle_type)
            & (expected_bundle_all_final["Bundle_Elimination"] == 0)
        ][["VisitIdPatient", "Bundle_name", "Bundle_Elimination"]]

        txn_data_expected = txn_data_filtered.merge(expected_bundle, on="VisitIdPatient")

        # APT quantities
        txn_data_apt = txn_data_expected.groupby(
            ["Bundle_description", "VisitIdPatient", "ProductCode"]
        ).agg({"Qty": "sum", "TotalNet": "sum"}).reset_index()

        txn_data_prod = txn_data_apt.groupby(
            ["Bundle_description", "ProductCode", "Qty"]
        ).agg({"VisitIdPatient": "nunique", "TotalNet": "sum"}
        ).rename(columns={"VisitIdPatient": "visits_by_qty", "TotalNet": "rev_by_qty"}).reset_index()

        product_visit_total = txn_data_apt.groupby("ProductCode").agg(
            {"VisitIdPatient": "nunique", "TotalNet": "sum"}
        ).rename(columns={"VisitIdPatient": "Total_visits", "TotalNet": "Total_revenue"}).reset_index()

        txn_data_prod = txn_data_prod.merge(product_visit_total, on="ProductCode")
        txn_data_prod["visits_perc"] = txn_data_prod["visits_by_qty"] / txn_data_prod["Total_visits"]
        txn_data_prod["revenue_perc"] = txn_data_prod["rev_by_qty"] / txn_data_prod["Total_revenue"]

        txn_data_prod.sort_values(
            by=["ProductCode", "visits_perc", "revenue_perc"],
            ascending=[True, False, False],
            inplace=True
        )
        txn_data_prod["apt_flag"] = txn_data_prod.groupby("ProductCode").cumcount().apply(
            lambda x: "Apt" if x == 0 else "Not apt"
        )

        apt_qty = txn_data_prod[txn_data_prod["apt_flag"] == "Apt"].rename(columns={"Qty": "Apt_quantity"})
        apt_qty = apt_qty[["ProductCode", "Apt_quantity"]]

        # Elasticity
        txn_data_elasticity = txn_data_expected.merge(apt_qty, on="ProductCode")
        txn_data_elasticity = txn_data_elasticity.groupby(
            [level, "week_starting_monday", "ProductCode", "Apt_quantity"]
        ).agg({"Qty": "sum", "TotalNet": "sum"}).reset_index()

        txn_data_elasticity["product_price"] = (
            (txn_data_elasticity["TotalNet"] / txn_data_elasticity["Qty"])
            * txn_data_elasticity["Apt_quantity"]
        )

        txn_elasticity = txn_data_elasticity.groupby([level, "week_starting_monday"]).agg(
            {"product_price": "sum", "TotalNet": "sum"}
        ).reset_index().rename(columns={"product_price": "basket_price", "TotalNet": "basket_revenue"})

        # Add FTE interpolation
        txn_data_expected["week_starting_monday"] = pd.to_datetime(txn_data_expected["week_starting_monday"])
        txn_data_expected = pd.merge(
            txn_data_expected,
            fte_data[["SiteCode", "week_starting_monday", "FTE_Interpolated"]],
            on=["SiteCode", "week_starting_monday"],
            how="left"
        )
        txn_data_expected["week_starting_monday"] = txn_data_expected["week_starting_monday"].astype(str)

        fte_interpolated = txn_data_expected.groupby(
            ["SiteCode", level, "week_starting_monday", "Bundle_description", "Bundle_code"]
        ).agg(FTE_Interpolated=("FTE_Interpolated", "mean")).reset_index()

        fte_interpolated_cluster = fte_interpolated.groupby(
            [level, "week_starting_monday", "Bundle_description", "Bundle_code"]
        ).agg(FTE_Interpolated=("FTE_Interpolated", "sum")).reset_index()

        # Visits + FTE
        bundle_visits = txn_data_expected.groupby(
            [level, "week_starting_monday", "Bundle_description", "Bundle_code"]
        ).agg(Bundle_visits=("VisitIdPatient", "nunique"),
              num_of_sites=("SiteCode", "nunique")).reset_index()

        bundle_visits = pd.merge(
            bundle_visits, fte_interpolated_cluster,
            on=[level, "week_starting_monday", "Bundle_description", "Bundle_code"],
            how="left"
        )

        bundle_data_final = txn_elasticity.merge(bundle_visits, on=[level, "week_starting_monday"])
        bundle_data_final["bundle_visits_per_site"] = (
            bundle_data_final["Bundle_visits"] / bundle_data_final["num_of_sites"]
        )

        bundle_data_final = bundle_data_final[
            [level, "week_starting_monday", "Bundle_description", "Bundle_code",
             "Bundle_visits", "basket_price", "basket_revenue",
             "bundle_visits_per_site", "num_of_sites", "FTE_Interpolated"]
        ]

        # Append results
        bundle_data_final_all = pd.concat([bundle_data_final_all, bundle_data_final], ignore_index=True)
        apt_data_basket_all = pd.concat([apt_data_basket_all, txn_data_prod], ignore_index=True)

    return bundle_data_final_all, apt_data_basket_all
