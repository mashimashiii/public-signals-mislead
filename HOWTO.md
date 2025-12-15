# How to Run This Analysis

**Time:** 5-10 minutes  
**Difficulty:** Easy (if you have Python)

## Setup (One-Time, 2 minutes)

### 1. Clone or Download

```bash
# Option A: Clone with git
git clone https://github.com/yourusername/public-signals-mislead.git
cd public-signals-mislead

# Option B: Download ZIP and extract
# Navigate to folder in terminal
```

### 2. Install Packages

```bash
pip install -r requirements.txt
```

Wait time: 30 seconds - 2 minutes

### 3. Verify Data Files

```bash
ls data/validation/labeled_features.csv
ls data/trends/
```

Should see `labeled_features.csv` and several CSV files in `data/trends/`.

If missing, you didn't clone everything - the data is in the repo.

## Run the Analysis (5 minutes)

### Step 1: Apply Business Outcomes

What this does: Labels 20 features with verified outcomes from earnings calls.

```bash
python scripts/apply_outcomes.py
```

Wait time: Instant

Expected output:
```
✓ 16 successes (Tier 1: 7, Tier 2: 9)
✗ 4 failures
? 16 unknown (need research)
```

### Step 2: Run Statistical Tests

What this does: Tests if search decay predicts success. Spoiler: it doesn't.

```bash
python src/analysis/statistical_analysis.py
```

Wait time: Instant

Expected output:
```
STATISTICAL ANALYSIS: Search Decay vs Success
✓ 16 successes, ✗ 4 failures

TEST 1: Search Decay - Success vs Failure
  Successes:  83.7% (±16.4%)
  Failures:   88.2% (±13.7%)
  p-value: 0.5943
  ✓ No significant difference

KEY FINDING: 11 successes with >80% decay (69%)
```

Saved to: `data/validation/statistical_results.csv`

### Step 3: Generate Charts

What this does: Creates 5 interactive HTML visualizations.

```bash
python scripts/generate_visualizations.py
```

Wait time: 2-3 seconds

Expected output:
```
GENERATING VISUALIZATIONS

1️⃣ Creating decay vs outcome scatter...
   ✓ Saved: results/figures/decay_vs_outcome.html
2️⃣ Creating divergence comparison...
   ✓ Saved: results/figures/divergence_examples.html
...
```

### Step 4: View Results

Open charts in browser:

```bash
# Mac
open results/figures/decay_vs_outcome.html

# Windows
start results/figures/decay_vs_outcome.html

# Linux
xdg-open results/figures/decay_vs_outcome.html
```

All 5 charts:
1. `decay_vs_outcome.html` - Main finding
2. `divergence_examples.html` - Netflix vs Disney+
3. `decision_matrix.html` - Interpretation guide
4. `success_by_type.html` - Category analysis
5. `statistical_comparison.html` - Metrics comparison

Charts are interactive - click, zoom, hover.

## One-Command Script (Optional)

Run everything at once:

```bash
chmod +x run_analysis.sh
./run_analysis.sh
```

Total time: 5 seconds

## Troubleshooting

### Error: ModuleNotFoundError

```bash
pip install pandas scipy plotly
```

### Error: FileNotFoundError

You're in the wrong directory. Navigate to project root:

```bash
cd /path/to/public-signals-mislead
```

### Error: ImportError: No module named 'config'

Run from project root, not from inside subdirectories:

```bash
# Wrong
cd src/analysis
python statistical_analysis.py

# Right
cd /path/to/public-signals-mislead
python src/analysis/statistical_analysis.py
```

### Charts won't open

Open manually:
- Navigate to `results/figures/` in file browser
- Double-click any `.html` file
- Opens in default browser

## Data Collection (Optional - Already Done)

You don't need to collect data - it's in the repo.

But if you want to re-collect:

### Google Trends (Time-Intensive)

```bash
# Create batches
python src/data_collection/create_batches.py

# Collect batch 1
python src/data_collection/collect_trends_data.py --input data/raw/batches/batch_1_of_5.csv

# Wait 30-60 minutes (rate limit cooldown)

# Collect batch 2
python src/data_collection/collect_trends_data.py --input data/raw/batches/batch_2_of_5.csv

# Wait 30-60 minutes

# Repeat for batches 3-5

# Merge all batches
python src/data_collection/merge_batches.py
```

Total time: ~4 hours (mostly waiting)

Why so slow? Google Trends limits: ~10 features per hour max.

### Reddit Collection (Also Time-Intensive)

```bash
# Collect Netflix features
python src/data_collection/reddit/validate_features.py --companies "Netflix"

# Wait 10-15 minutes (rate limits)

# Collect Spotify
python src/data_collection/reddit/validate_features.py --companies "Spotify"

# Repeat for other companies
```

Total time: 1-2 hours

Why so slow? Reddit API limits: 60 req/min with auth, 30 req/min without.

### Business Verification (Manual)

Most time-consuming:
- Read earnings call transcripts
- Check press releases
- Find credible reports
- Verify metrics

Time: Several days (already done for you)

**Bottom line:** Use the provided data. Focus on analysis.
