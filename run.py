#!/usr/bin/env python3
"""
GNIS Place Names Matching - Default Run Script

This script runs the place name matching algorithm with strict mode enabled
(default confidence threshold: 80%).

Usage:
    python run.py                    # Run on all unmatched records
    python run.py --sample 100       # Run on sample of 100 records
    python run.py --threshold 85     # Use custom threshold
    python run.py --all              # Run on ALL records (matched + unmatched)
"""

import sys
import argparse
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from matching_pipeline import MatchingPipeline


def main():
    """Run the place name matching pipeline."""
    parser = argparse.ArgumentParser(
        description='GNIS Place Names Matching (Strict Mode)'
    )
    parser.add_argument(
        '--sample',
        type=int,
        help='Run on sample of N records (default: all unmatched)'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=80,
        help='Confidence threshold (default: 80, strict mode)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Run on all records (not just unmatched)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='output',
        help='Output directory (default: output/)'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("GNIS PLACE NAMES MATCHING - STRICT MODE")
    print("=" * 80)
    print()

    # Load data
    print("Loading data...")
    project_root = Path(__file__).parent
    data_dir = project_root / 'data'

    try:
        place_names = pd.read_csv(data_dir / 'PlaceNames.csv')
        gnis = pd.read_csv(data_dir / 'GNIS_250319.csv')
    except FileNotFoundError as e:
        print(f"Error: Data file not found: {e}")
        print(f"Expected files in: {data_dir}/")
        return 1

    print(f"  PlaceNames: {len(place_names):,} records")
    print(f"  GNIS: {len(gnis):,} records")
    print()

    # Select records to process
    if args.all:
        records_to_process = place_names
        print("Processing: ALL records")
    else:
        unmatched = place_names[place_names['Match'] == 'No']
        print(f"Processing: Unmatched records only ({len(unmatched):,})")
        records_to_process = unmatched

    if args.sample:
        records_to_process = records_to_process.head(args.sample)
        print(f"Sample size: {args.sample} records")

    print(f"Total to process: {len(records_to_process):,} records")
    print(f"Confidence threshold: {args.threshold}% (strict mode)")
    print()

    # Create output directory
    output_dir = project_root / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run matching
    print("=" * 80)
    print("RUNNING MATCHING PIPELINE")
    print("=" * 80)
    print()

    pipeline = MatchingPipeline(records_to_process, gnis)
    results = pipeline.run_full_matching(
        confidence_threshold=args.threshold,
        batch_size=100
    )

    # Generate quality report
    print()
    print("=" * 80)
    print("QUALITY REPORT")
    print("=" * 80)
    print()

    report = pipeline.generate_quality_report()

    print(f"Total places: {report['total_places']:,}")
    print(f"Matches found: {report['matches_found']:,}")
    print(f"No matches: {report['no_matches']:,}")
    print(f"Match rate: {report['match_rate']:.1f}%")
    print()

    print("Confidence Distribution:")
    for level, count in report['confidence_distribution'].items():
        pct = (count / report['total_places'] * 100)
        print(f"  {level:20s}: {count:5,} ({pct:5.1f}%)")
    print()

    if 'county_match_rate' in report:
        print(f"County match rate: {report['county_match_rate']:.1f}%")
        print()

    if report['places_with_multiple_matches'] > 0:
        print(
            f"Places with multiple matches: "
            f"{report['places_with_multiple_matches']:,}"
        )
        print()

    # Export results
    print("=" * 80)
    print("EXPORTING RESULTS")
    print("=" * 80)
    print()

    pipeline.export_for_review(str(output_dir))
    print()

    # Create review interface
    print("Creating review HTML interface...")
    pipeline.create_review_html(
        str(output_dir / 'review.html'),
        max_records=100
    )
    print()

    print("=" * 80)
    print("COMPLETE")
    print("=" * 80)
    print()
    print(f"Results exported to: {output_dir}/")
    print()
    print("Output files:")
    print("  - all_matches.csv - All results")
    print("  - high_confidence_matches.csv - Ready for approval (≥90%)")
    print("  - medium_confidence_matches.csv - Needs review (75-89%)")
    print("  - low_confidence_matches.csv - Expert review (70-74%)")
    print("  - no_matches.csv - Requires research")
    print("  - multiple_matches.csv - Needs disambiguation")
    print("  - review.html - Interactive review interface")
    print()
    print("Next steps:")
    print(f"  1. Review high confidence matches in {output_dir}/")
    print("  2. Open review.html in web browser for interactive review")
    print("  3. Validate results and adjust threshold if needed")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
