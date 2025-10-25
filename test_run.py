"""
Test script to run the matching pipeline on a small sample
"""

import sys
sys.path.insert(0, 'src')

from matching_pipeline import MatchingPipeline
import pandas as pd

# Load data
print("Loading datasets...")
place_names = pd.read_csv('data/PlaceNames.csv')
gnis = pd.read_csv('data/GNIS_250319.csv')

print(f"Loaded {len(place_names)} place names and {len(gnis)} GNIS records")

# Test on a small sample first
print("\nTesting on first 10 unmatched records...")
unmatched = place_names[place_names['Match'] == 'No'].head(10)

# Create pipeline
pipeline = MatchingPipeline(unmatched, gnis)

# Run matching
results = pipeline.run_full_matching(confidence_threshold=70, batch_size=5)

# Display results
print("\n" + "="*80)
print("RESULTS")
print("="*80)
print(results[['place_name', 'gnis_name', 'confidence', 'match_strategy']])

# Generate quality report
print("\n" + "="*80)
print("QUALITY REPORT")
print("="*80)
report = pipeline.generate_quality_report()
for key, value in report.items():
    print(f"{key}: {value}")

print("\nTest completed successfully!")
