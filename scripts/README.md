# Utility Scripts

## Usage Order

### One-Time Setup (Already Done)
1. `create_labeled_dataset.py` - Merge inventory + Reddit results
   - **Only run if you collect new Reddit data**
   - Creates `data/validation/labeled_features.csv`

### Every Analysis Run
2. `apply_outcomes.py` - Apply known business outcomes
```bash
   python scripts/apply_outcomes.py
```

3. Run analysis
```bash
   python src/analysis/statistical_analysis.py
```

4. Generate charts
```bash
   python scripts/generate_visualizations.py
```

## Quick Run (All at Once)
```bash
./run_analysis.sh
```