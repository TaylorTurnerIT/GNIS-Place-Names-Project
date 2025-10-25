"""
Comprehensive test of all matching pipeline functionality
"""

import sys
import os
sys.path.insert(0, 'src')

from matching_pipeline import MatchingPipeline, MatchAnalyzer
import pandas as pd
import json

# Create output directory if it doesn't exist
os.makedirs('output', exist_ok=True)

# Load data
print("Loading datasets...")
place_names = pd.read_csv('data/PlaceNames.csv')
gnis = pd.read_csv('data/GNIS_250319.csv')

print(f"Loaded {len(place_names)} place names and {len(gnis)} GNIS records")

# Test on a larger sample
print("\n" + "="*80)
print("Testing on 50 unmatched records...")
print("="*80)
unmatched = place_names[place_names['Match'] == 'No'].head(50)

# Create pipeline
pipeline = MatchingPipeline(unmatched, gnis)

# Run matching
print("\nRunning full matching pipeline...")
results = pipeline.run_full_matching(confidence_threshold=70, batch_size=10)

# Generate quality report
print("\n" + "="*80)
print("QUALITY REPORT")
print("="*80)
report = pipeline.generate_quality_report()
print(json.dumps(report, indent=2))

# Test export functionality
print("\n" + "="*80)
print("EXPORTING RESULTS")
print("="*80)
pipeline.export_for_review(output_dir='output')

# Create review HTML
print("\n" + "="*80)
print("CREATING REVIEW INTERFACE")
print("="*80)
pipeline.create_review_html(output_file='output/review.html', max_records=20)

# Test MatchAnalyzer
print("\n" + "="*80)
print("ANALYZING UNMATCHED PLACES")
print("="*80)
unmatched_analysis = MatchAnalyzer.analyze_unmatched(unmatched, results)
print(json.dumps(unmatched_analysis, indent=2, default=str))

print("\n" + "="*80)
print("IMPROVEMENT SUGGESTIONS")
print("="*80)
suggestions = MatchAnalyzer.suggest_improvements(results)
for i, suggestion in enumerate(suggestions, 1):
    print(f"{i}. {suggestion}")

print("\n" + "="*80)
print("ALL TESTS COMPLETED SUCCESSFULLY!")
print("="*80)
print("\nGenerated files:")
print("  - output/high_confidence_matches.csv")
print("  - output/medium_confidence_matches.csv")
print("  - output/low_confidence_matches.csv")
print("  - output/no_matches.csv")
print("  - output/multiple_matches.csv")
print("  - output/all_matches.csv")
print("  - output/review.html")
