# GNIS Place Names Matching Project

Advanced place name matching system with **strict mode** enabled by default for high-quality results.

## Quick Start

### Run with Default Settings (Recommended)

```bash
python run.py
```

This will:
- Process all unmatched place names
- Use strict matching (80% confidence threshold)
- Export results to `output/` directory
- Generate interactive review interface

### Command Line Options

```bash
# Run on sample of 100 records
python run.py --sample 100

# Use custom threshold (70% = looser, 85% = stricter)
python run.py --threshold 85

# Process all records (not just unmatched)
python run.py --all

# Specify output directory
python run.py --output results/

# Combine options
python run.py --sample 50 --threshold 75 --output test_output/
```

## What's New - Strict Mode

✅ **Default threshold increased:** 70% → **80%**
✅ **County mismatch penalties:** -5 to -10 → **-20 to -30**
✅ **Fuzzy matching thresholds:** 70% → **85-90%**
✅ **First word matching:** Much stricter (4-char min, lower confidence)
✅ **Better code quality:** PEP 8 compliant, improved type hints

**Result:** Fewer matches, but much higher quality and confidence.

## Project Structure

```
GNISPlaceNames/
├── run.py                    # Main entry point (run this!)
├── data/                     # Data files
│   ├── PlaceNames.csv
│   └── GNIS_250319.csv
├── src/                      # Source code
│   ├── matching_algorithm.py          # Core matching logic
│   ├── matching_pipeline.py           # Batch processing pipeline
│   ├── enhanced_matching_pipeline.py  # With geolocation
│   ├── geolocation_matcher.py         # Distance calculations
│   └── analyze_datasets.py            # Dataset analysis
├── docs/                     # Documentation
│   ├── QUICK_REFERENCE.md             # Quick reference card
│   ├── QUALITY_IMPROVEMENTS_SUMMARY.md # Complete summary
│   ├── STRICT_MODE_CHANGES.md         # Detailed changes
│   ├── ISSUES_FOUND.md                # Issues identified
│   ├── BUGFIXES.md                    # Previous bug fixes
│   └── README.md                      # Detailed guide
├── output/                   # Results (created on first run)
│   ├── all_matches.csv
│   ├── high_confidence_matches.csv
│   ├── medium_confidence_matches.csv
│   ├── low_confidence_matches.csv
│   ├── no_matches.csv
│   ├── multiple_matches.csv
│   └── review.html
└── tests/                    # Test files
    ├── test_run.py
    └── test_comprehensive.py
```

## Output Files

| File | Records | Purpose |
|------|---------|---------|
| `high_confidence_matches.csv` | ≥90% | Ready for approval |
| `medium_confidence_matches.csv` | 75-89% | Needs review |
| `low_confidence_matches.csv` | 70-74% | Expert review required |
| `no_matches.csv` | 0% | Requires manual research |
| `multiple_matches.csv` | Multiple | Needs disambiguation |
| `review.html` | Sample | Interactive review interface |

## Confidence Levels Explained

### Strict Mode (Default: 80%)

| Score | Meaning | Action |
|-------|---------|--------|
| 100% | Exact name + county match | Auto-approve |
| 90-99% | Very high confidence | Quick review |
| 80-89% | High confidence | Standard review |
| 75-79% | Medium confidence | Careful review |
| 70-74% | Low confidence | Expert review |
| <70% | Too uncertain | Rejected |

### County Mismatches

**In strict mode, wrong county is heavily penalized:**
- Exact name, different county: 85% → **65%** (-20 points)
- Fuzzy match, different county: -10 → **-30 penalty**
- First word match, different county: -5 → **-20 penalty**

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) | One-page quick reference |
| [docs/QUALITY_IMPROVEMENTS_SUMMARY.md](docs/QUALITY_IMPROVEMENTS_SUMMARY.md) | Complete improvement summary |
| [docs/STRICT_MODE_CHANGES.md](docs/STRICT_MODE_CHANGES.md) | Detailed change log |
| [docs/ISSUES_FOUND.md](docs/ISSUES_FOUND.md) | All 13 issues identified |
| [docs/README.md](docs/README.md) | Comprehensive usage guide |

## Python API Usage

### Basic Usage

```python
from src.matching_algorithm import PlaceNameMatcher
import pandas as pd

# Load data
place_names = pd.read_csv('data/PlaceNames.csv')
gnis = pd.read_csv('data/GNIS_250319.csv')

# Create matcher
matcher = PlaceNameMatcher(place_names, gnis)

# Run with strict defaults (80% threshold)
results = matcher.match_all()

# Or use custom threshold
results = matcher.match_all(confidence_threshold=85)
```

### Using the Pipeline

```python
from src.matching_pipeline import MatchingPipeline

pipeline = MatchingPipeline(place_names, gnis)

# Run matching
results = pipeline.run_full_matching(
    confidence_threshold=80,
    batch_size=100
)

# Generate report
report = pipeline.generate_quality_report()

# Export results
pipeline.export_for_review('output')
pipeline.create_review_html('output/review.html')
```

### With Distance Enhancement

```python
from src.enhanced_matching_pipeline import EnhancedMatchingPipeline

pipeline = EnhancedMatchingPipeline(place_names, gnis)

# Run with distance enhancement
results = pipeline.run_full_matching(
    confidence_threshold=80,
    use_distance=True
)

# Export with distance analysis
pipeline.export_for_review('output')
pipeline.export_distance_report('output/distance_analysis.txt')
```

## Expected Results

### Before Strict Mode
- Match rate: ~96%
- High confidence: 27%
- Many county mismatches still marked high confidence ⚠️

### After Strict Mode (Current)
- Match rate: ~70-80%
- High confidence: 40-50%
- County mismatches properly penalized ✅
- **Quality over quantity**

## Customizing Thresholds

### More Lenient (Old Behavior)

```python
# Use 70% threshold (previous default)
results = matcher.match_all(confidence_threshold=70)
```

```bash
# Via command line
python run.py --threshold 70
```

### More Strict

```python
# Use 85% threshold (very strict)
results = matcher.match_all(confidence_threshold=85)

# Use 90% threshold (extremely strict)
results = matcher.match_all(confidence_threshold=90)
```

```bash
# Via command line
python run.py --threshold 85
python run.py --threshold 90
```

## Testing

### Syntax Validation

```bash
python3 -m py_compile src/matching_algorithm.py
python3 -m py_compile src/matching_pipeline.py
```

### Run Tests (if dependencies installed)

```bash
python test_run.py
python test_comprehensive.py
```

### Quick Sample Test

```bash
# Test on 10 records
python run.py --sample 10
```

## Requirements

- Python 3.7+
- pandas
- numpy
- rapidfuzz
- tqdm

### Installation

```bash
pip install -r requirements.txt
```

## Key Features

✅ **Multi-Strategy Matching**
- Exact match (name + county)
- Name variations (suffixes/prefixes)
- Fuzzy matching (with and without county)
- First word matching

✅ **Strict Mode (Default)**
- Conservative thresholds (80%)
- Heavy county mismatch penalties (-20 to -30)
- High-quality results prioritized

✅ **Quality Analysis**
- Confidence scoring for all matches
- Multiple match detection
- County validation
- Strategy tracking

✅ **Export Capabilities**
- CSV files by confidence level
- Interactive HTML review interface
- Quality reports with statistics
- Distance analysis (enhanced mode)

## Support

For detailed information, see:
- [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) - Quick start guide
- [docs/QUALITY_IMPROVEMENTS_SUMMARY.md](docs/QUALITY_IMPROVEMENTS_SUMMARY.md) - What changed
- [docs/README.md](docs/README.md) - Comprehensive guide

## License

See project documentation for license information.

---

**Made with strict quality standards - prioritizing accuracy over quantity.**
