# When Search Trends Lie About Product Success

**TL;DR:** Analyzed 36 subscription features. Found 69% of successes show massive search decay - same pattern as failures. External signals mislead without context.

## The Problem

You launch a feature. Google Trends shows huge initial interest, then drops 90% in a month. Is your feature failing?

**Maybe. Or maybe it's working perfectly.**

Netflix Password Sharing:
- 93% search decay
- Added 9.3 million subscribers

Disney+ GroupWatch:
- 88% search decay
- Discontinued for low usage

Same signal. Opposite outcomes. Search patterns alone tell you nothing.

## Main Finding

Tested 20 features with verified business outcomes from earnings calls:

**Statistical Result:**
- Successes: 83.7% average decay
- Failures: 88.2% average decay
- p-value: 0.59 (not significant)
- Effect size: Negligible (Cohen's d = -0.30)

**Translation:** Search decay alone cannot predict feature success.

**But:** Combining search decay + Reddit sentiment + engagement reveals patterns:
- High decay + positive sentiment + lots of mentions = Adoption (users learned it)
- High decay + negative sentiment = Abandonment (users gave up)
- Low decay + positive sentiment = Sustained interest (rare)

## Why This Matters

**For Product Teams:** Don't panic when trends drop. Don't cancel features based on declining buzz.

**For Data Teams:** Multi-signal validation beats single metrics. Context matters.

**For Hiring Managers:** This demonstrates decision science thinking, not just running tests.

## Quick Start

**Prerequisites:** Python 3.9+

```bash
pip install -r requirements.txt

# Apply verified business outcomes
python scripts/apply_outcomes.py

# Run statistical tests
python src/analysis/statistical_analysis.py

# Generate interactive charts
python scripts/generate_visualizations.py

# Open results
open results/figures/decay_vs_outcome.html
```

**Total time:** 5 minutes

## The Numbers

**Dataset:**
- 36 subscription features analyzed
- 20 with verified business outcomes
- 9 companies (Netflix, Spotify, Disney+, YouTube, etc.)
- 2021-2024 data

**Key Stats:**
- 16 successes, 4 failures verified
- 69% of successes show >80% decay
- Reddit mentions DO predict success (p=0.02)
- Negative sentiment alone doesn't (p=0.68)

## Project Structure

```
public-signals-mislead/
├── config/
│   └── outcomes.py              # 20 verified business outcomes
├── src/
│   ├── data_collection/         # Google Trends + Reddit
│   ├── analysis/                # Statistical tests
│   └── visualization/           # Charts
├── data/
│   ├── trends/                  # Collected data
│   └── validation/              # Labeled features
└── results/
    └── figures/                 # 5 interactive HTML charts
```

## Data Collection (Already Done)

I spent several days collecting this data:

**Google Trends:**
- Split into batches (rate limit: ~10 features/hour)
- Collected daily search interest
- Calculated peak-based decay

**Reddit Sentiment:**
- Searched company subreddits
- 30-90 day post-launch window
- Keyword-based sentiment analysis

**Business Outcomes:**
- Verified from earnings calls and press releases
- Only included features with hard metrics

You can use the provided data - no need to re-collect.

## Visualizations

5 interactive Plotly charts:

1. **Decay vs Outcome** - Shows overlap between success/failure
2. **Divergence Examples** - Netflix vs Disney+ case studies
3. **Decision Matrix** - How to interpret mixed signals
4. **Success by Type** - Which feature categories work
5. **Statistical Comparison** - Success vs failure metrics

All saved as HTML - open in any browser.

## Tech Stack

- Python for everything
- pandas for data wrangling
- scipy for statistical tests
- plotly for visualizations
- PRAW for Reddit API (data already collected)

## Skills Demonstrated

**Decision Science:**
- Understanding when correlation doesn't mean causation
- Building validation frameworks
- Knowing metric limitations

**Statistical Rigor:**
- Effect sizes matter more than p-values
- Sample size awareness
- Conservative interpretation

**Data Engineering:**
- API rate limit handling
- Incremental data collection
- Data validation

**Product Thinking:**
- User behavior patterns
- Feature lifecycle understanding
- Stakeholder communication

## The Real Insight

High search decay is ambiguous:

**Could mean success (adoption):**
- Users learned the feature, stopped searching
- Netflix Password Sharing: Everyone knows about it
- Spotify AI DJ: Integrated into usage

**Could mean failure (abandonment):**
- Users tried it, gave up
- Netflix Games: Initial curiosity, then nothing
- Disney+ GroupWatch: Tried once, never again

You need additional signals:
- Sentiment: Praising or complaining?
- Engagement: High or low mentions?
- Context: What type of feature?

**External signals measure public discussion, not product adoption.**

## Contact

Tomasz Solis
- Email: tomasz.solis@gmail.com
- LinkedIn: linkedin.com/in/tomaszsolis
- GitHub: github.com/tomasz-solis

## License

MIT - Use this however you want.
