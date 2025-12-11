# src/analysis/create_labeled_dataset.py

from pathlib import Path
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
VALIDATION_DIR = DATA_DIR / "validation"


def map_outcome(classification: str) -> str:
    """
    Map Reddit classification to a coarse outcome label.

    - ADOPTION / SUSTAINED_INTEREST → success
    - ABANDONMENT / LOW_AWARENESS   → failure
    - NO_DECAY_DATA                 → no_decay_data
    - Everything else               → inconclusive
    """
    if classification in ("ADOPTION", "SUSTAINED_INTEREST"):
        return "success"
    if classification in ("ABANDONMENT", "LOW_AWARENESS"):
        return "failure"
    if classification == "NO_DECAY_DATA":
        return "no_decay_data"
    return "inconclusive"


def main() -> None:
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)

    inventory_path = RAW_DIR / "feature_inventory.csv"
    reddit_path = VALIDATION_DIR / "reddit_validation_results.csv"

    inv = pd.read_csv(inventory_path)
    reddit = pd.read_csv(reddit_path)

    # Safe merge on (feature_name, company, launch_date)
    df = inv.merge(
        reddit,
        on=["feature_name", "company", "launch_date"],
        how="inner",
        validate="one_to_one",
    )

    # Derive outcome labels
    df["outcome_label"] = df["classification"].map(map_outcome)
    df["is_success"] = df["outcome_label"].eq("success").astype("Int64")
    df["is_failure"] = df["outcome_label"].eq("failure").astype("Int64")

    out_path = VALIDATION_DIR / "labeled_features.csv"
    df.to_csv(out_path, index=False)

    print(f"✅ Saved labeled dataset: {out_path}")
    print("\nOutcome label counts:")
    print(df["outcome_label"].value_counts(dropna=False))


if __name__ == "__main__":
    main()