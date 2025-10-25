"""
Example Usage: GNIS Place Name Matching Pipeline
Demonstrates proper type-hinted usage of the matching pipeline
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

# Add src to path if running from project root
sys.path.insert(0, 'src')

import pandas as pd
from matching_pipeline import MatchingPipeline, MatchAnalyzer


def main() -> None:
    """
    Main function demonstrating the complete matching pipeline workflow
    """

    # Load datasets
    print("="*80)
    print("GNIS PLACE NAME MATCHING PIPELINE")
    print("="*80)
    print("\nLoading datasets...")

    place_names: pd.DataFrame = pd.read_csv('data/PlaceNames.csv')
    gnis: pd.DataFrame = pd.read_csv('data/GNIS_250319.csv')

    print(f"✅ Loaded {len(place_names):,} place names")
    print(f"✅ Loaded {len(gnis):,} GNIS records")

    # Filter to unmatched records only (optional)
    print("\nFiltering to unmatched records...")
    unmatched: pd.DataFrame = place_names[place_names['Match'] == 'No']
    print(f"✅ Found {len(unmatched):,} unmatched place names to process")

    # For this example, process a sample (remove .head(100) to process all)
    sample: pd.DataFrame = unmatched.head(100)
    print(f"✅ Processing sample of {len(sample)} records")

    # Create pipeline
    print("\n" + "="*80)
    print("STEP 1: Initialize Pipeline")
    print("="*80)
    pipeline: MatchingPipeline = MatchingPipeline(sample, gnis)
    print("✅ Pipeline initialized")

    # Run matching
    print("\n" + "="*80)
    print("STEP 2: Run Matching Algorithm")
    print("="*80)
    print("Running matching with confidence threshold of 70%...")
    results: pd.DataFrame = pipeline.run_full_matching(
        confidence_threshold=70,
        batch_size=25
    )
    print(f"✅ Matching complete! Processed {len(results)} result records")

    # Generate quality report
    print("\n" + "="*80)
    print("STEP 3: Generate Quality Report")
    print("="*80)
    report: Dict[str, Any] = pipeline.generate_quality_report()

    print(f"\n📊 Match Statistics:")
    print(f"  Total places:     {report['total_places']}")
    print(f"  Matches found:    {report['matches_found']}")
    print(f"  No matches:       {report['no_matches']}")
    print(f"  Match rate:       {report['match_rate']:.1f}%")

    print(f"\n📈 Confidence Distribution:")
    conf_dist: Dict[str, int] = report['confidence_distribution']
    for category, count in conf_dist.items():
        percentage: float = (count / len(results) * 100) if len(results) > 0 else 0
        print(f"  {category:20s}: {count:4d} ({percentage:5.1f}%)")

    print(f"\n🎯 Top Matching Strategies:")
    strategy_dist: Dict[str, int] = report['strategy_distribution']
    for strategy, count in list(strategy_dist.items())[:5]:
        percentage: float = (count / len(results) * 100) if len(results) > 0 else 0
        print(f"  {strategy:20s}: {count:4d} ({percentage:5.1f}%)")

    # Export results
    print("\n" + "="*80)
    print("STEP 4: Export Results for Review")
    print("="*80)
    pipeline.export_for_review(output_dir='output')
    print("✅ Results exported to output/ directory")

    # Create HTML review interface
    print("\n" + "="*80)
    print("STEP 5: Create Interactive Review Interface")
    print("="*80)
    pipeline.create_review_html(
        output_file='output/review.html',
        max_records=50
    )
    print("✅ Review interface created: output/review.html")

    # Analyze unmatched places
    print("\n" + "="*80)
    print("STEP 6: Analyze Unmatched Places")
    print("="*80)
    unmatched_analysis: Dict[str, Any] = MatchAnalyzer.analyze_unmatched(
        sample,
        results
    )
    print(f"\n📊 Unmatched Analysis:")
    print(f"  Total unmatched:  {unmatched_analysis['total_unmatched']}")
    print(f"  With county:      {unmatched_analysis['with_county']}")
    print(f"  Without county:   {unmatched_analysis['without_county']}")

    # Get improvement suggestions
    print("\n" + "="*80)
    print("STEP 7: Generate Improvement Suggestions")
    print("="*80)
    suggestions: List[str] = MatchAnalyzer.suggest_improvements(results)
    if suggestions:
        print("\n💡 Suggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
    else:
        print("✅ No issues detected!")

    # Summary
    print("\n" + "="*80)
    print("PIPELINE COMPLETE!")
    print("="*80)
    print("\n📁 Generated Files:")
    print("  • output/high_confidence_matches.csv")
    print("  • output/medium_confidence_matches.csv")
    print("  • output/low_confidence_matches.csv")
    print("  • output/no_matches.csv")
    print("  • output/multiple_matches.csv")
    print("  • output/all_matches.csv")
    print("  • output/review.html")

    print("\n📖 Next Steps:")
    print("  1. Open output/review.html in a web browser")
    print("  2. Review high confidence matches first")
    print("  3. Work through medium confidence matches")
    print("  4. Research low confidence and no matches")

    print("\n✨ Happy matching! ✨\n")


if __name__ == "__main__":
    main()
