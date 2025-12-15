# Data Documentation

This document explains data sources, collection methodology, and reproducibility.

## Data Sources

### Feature Inventory (`data/raw/feature_inventory.csv`)

**Source:** Manually compiled from company press releases
- Spotify Newsroom, Netflix About, YouTube Blog, Disney Newsroom
- Earnings call transcripts (public)

**Coverage:** 50 features from Nov 2021 to Dec 2024

**Columns:**
- `feature_id`: Unique identifier (1-50)
- `feature_name`: Human-readable name
- `company`: Platform (Spotify, Netflix, YouTube, etc.)
- `launch_date`: Official launch date (YYYY-MM-DD)
- `feature_type`: Category (AI, Monetization, Content, etc.)
- `google_trends_keyword`: Search term for collection
- `announcement_source`: URL to official announcement
- `expected_stickiness`: Initial hypothesis
- `notes`: Additional context

### Google Trends Data (`data/trends/`)

**Tool:** `pytrends` library (unofficial Google Trends API)

**Collection Window:**
- 14 days before launch
- 98 days (14 weeks) after launch
- Total: 112 days per feature

Why extended window? Some features peaked 55 days after launch.

**Rate Limiting:**
- Batch size: 10 features
- Delay between requests: 10 seconds
- Delay between batches: 24 hours
- Total collection: ~5 days

**Geography:** Global (not US-only)

Why global? Netflix, Spotify, Disney+ are international. Password sharing was worldwide news. We're measuring relative patterns, not absolute volumes.

### Reddit Data (`data/validation/`)

**Tool:** PRAW (Python Reddit API Wrapper) with public JSON fallback

**Collection:**
- Company subreddits (r/netflix, r/spotify, etc.)
- 30-90 day post-launch window
- Keyword-based sentiment analysis

**Rate Limiting:**
- PRAW: ~60 requests/minute
- Public JSON: ~30 requests/minute
- Total time: 1-2 hours for all companies

## Data Processing

### Raw → Cleaned

**1. Merge batches** (`merge_batches.py`)
- Combines 5 batch collections
- Removes duplicates
- Output: `MERGED_trends_data.csv`

**2. Peak-based recalculation** (`recalculate_with_peaks.py`)
- Finds actual peak date (not launch date)
- Calculates decay from peak
- Output: `MERGED_trends_data_PEAK_metrics.csv`

### Why Peak-Based?

Features don't peak on launch day.

**Examples:**
- Paramount+ Live Sports: Launched Mar 1, peaked Mar 25 (24 days later)
- Apple Music Family: Launched Oct 15, peaked Nov 29 (45 days later)

**Reason:** Users search when they have a problem (key game, pricing question), not when feature launches.

**Impact:** Launch-based calculation shows 0.7% decay (false "sticky"). Peak-based shows 73% decay (correct "novelty").

## Final Metrics

**Stickiness Metrics:**
- `days_to_peak`: Days between launch and peak
- `peak_interest`: Google Trends score (0-100, normalized)
- `week_4_interest`: Average interest 21-28 days after peak
- `week_8_interest`: Average interest 56-63 days after peak
- `decay_rate_w4`: (peak - week_4) / peak
- `decay_rate_w8`: (peak - week_8) / peak

**Classification:**
- `sticky`: <30% decay
- `mixed`: 30-70% decay
- `novelty`: >70% decay
- `unknown`: Insufficient data

## Limitations

### 1. Search Volume ≠ Usage

Declining search could mean:
- Adoption (users learned feature, use habitually)
- Abandonment (curiosity wore off)

Validation: Cross-reference with company metrics and Reddit sentiment.

### 2. Google Trends Normalization

All features normalized to peak=100 within their timeframe.

Impact:
- Can compare decay patterns between features
- Cannot compare absolute volumes between features

Example: "Netflix password sharing" and "Disney+ Parental Controls" both peak at 100, but Netflix likely has 1000x higher volume.

### 3. Sampling Bias (Mitigated)

Initial issue: Rate limiting blocked high-volume features while allowing low-volume ones.

Solution: Batch collection with 24-hour delays captured full dataset.

Remaining: Features with very low volume show "no data" (5-8 features excluded).

### 4. Global vs Regional

Features may have different patterns in other markets. This captures global behavior.

### 5. Time Period

Features launched Nov 2021 - Dec 2024. Recent features may still be in awareness phase.

## Reproducibility

### To Reproduce

```bash
# 1. Clone
git clone https://github.com/tomasz-solis/public-signals-mislead
cd public-signals-mislead

# 2. Install
pip install -r requirements.txt

# 3. Create batches
python src/data_collection/create_batches.py

# 4. Collect (5 days, one batch per day)
python src/data_collection/collect_trends_data.py --full --input data/raw/batches/batch_1_of_5.csv
# Wait 24 hours
python src/data_collection/collect_trends_data.py --full --input data/raw/batches/batch_2_of_5.csv
# Repeat for batches 3-5

# 5. Merge and analyze
python src/data_collection/merge_batches.py
python src/data_collection/recalculate_with_peaks.py --input data/trends/MERGED_trends_data.csv
```

Note: Trends data may vary slightly on different dates due to updated volumes and Google's sampling.

Core patterns (sticky vs novelty) should remain consistent.

## Data Sharing

**Included in repo:**
- Feature inventory
- Final metrics
- Sample trends data (5 features)
- All code

**Not included:**
- Full raw trends data (~2-5 MB)
- Intermediate batch files

Rationale: Raw data is reproducible via scripts. GitHub best practice: keep data <1 MB.

**To access full dataset:** Contact me or run collection scripts (5 days due to rate limits).

## Quality Checks

**Validation:**
- Launch dates verified against official sources
- Keywords tested manually on trends.google.com
- Duplicates removed after batch merging
- Peak dates inspected visually
- Decay calculations spot-checked

**Known issues:**
- Netflix Extra Member: No search volume (keyword too specific)
- [Other features with low volume excluded]

## References

**Google Trends:**
- Official: trends.google.com
- API: github.com/GeneralMills/pytrends
- Methodology: support.google.com/trends/answer/4365533

**Company sources:** See feature_inventory.csv

**Last updated:** December 2024
**Geographic coverage:** Global
**Feature period:** November 2021 - December 2024

## Contact

Tomasz Solis
- Email: tomasz.solis@gmail.com
- LinkedIn: linkedin.com/in/tomaszsolis
- GitHub: github.com/tomasz-solis
