#!/bin/bash

# Complete analysis runner for public-signals-mislead project
# Usage: ./run_analysis.sh

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "================================================================================"
echo "  Public Signals Mislead: Complete Analysis"
echo "================================================================================"
echo ""

# Check Python version
echo -e "${BLUE}Checking Python version...${NC}"
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "  Python version: $python_version"
echo ""

# Check required packages
echo -e "${BLUE}Checking required packages...${NC}"
missing_packages=""

if ! python -c "import pandas" 2>/dev/null; then
    missing_packages="$missing_packages pandas"
fi

if ! python -c "import scipy" 2>/dev/null; then
    missing_packages="$missing_packages scipy"
fi

if ! python -c "import plotly" 2>/dev/null; then
    missing_packages="$missing_packages plotly"
fi

if [ -n "$missing_packages" ]; then
    echo -e "${YELLOW}⚠️  Missing packages:$missing_packages${NC}"
    echo "Installing..."
    pip install $missing_packages
    echo ""
fi

echo -e "${GREEN}✅ All packages installed${NC}"
echo ""

# Step 1: Apply outcomes
echo "================================================================================"
echo "  Step 1/3: Applying Business Outcomes"
echo "================================================================================"
echo ""
python scripts/apply_outcomes.py
echo ""

# Step 2: Statistical analysis
echo "================================================================================"
echo "  Step 2/3: Running Statistical Tests"
echo "================================================================================"
echo ""
python src/analysis/statistical_analysis.py
echo ""

# Step 3: Generate visualizations
echo "================================================================================"
echo "  Step 3/3: Generating Interactive Charts"
echo "================================================================================"
echo ""
python scripts/generate_visualizations.py
echo ""

# Summary
echo "================================================================================"
echo -e "  ${GREEN}✅ ANALYSIS COMPLETE${NC}"
echo "================================================================================"
echo ""
echo "Results saved to:"
echo "  📊 Statistical results: data/validation/statistical_results.csv"
echo "  📈 Interactive charts:  results/figures/*.html"
echo ""
echo "View main chart:"
echo "  open results/figures/decay_vs_outcome.html"
echo ""
echo "Or browse all charts:"
echo "  open results/figures/"
echo ""