"""
Enhanced Example Usage: GNIS Matching with Geographic Distance.

This script demonstrates the geolocation-enhanced matching pipeline
that uses both fuzzy matching and geographic proximity for improved
accuracy and disambiguation.
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any

if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, 'src')

import pandas as pd
from enhanced_matching_pipeline import EnhancedMatchingPipeline
from geolocation_matcher import (
    CountyCentroidGeocoder,
    GeoDistanceCalculator
)


def main() -> None:
    """
    Main function demonstrating enhanced matching with distance.
    """
    print("=" * 80)
    print("ENHANCED PLACE NAME MATCHING WITH GEOGRAPHIC DISTANCE")
    print("=" * 80)

    print("\n1. Loading datasets...")
    place_names: pd.DataFrame = pd.read_csv('data/PlaceNames.csv')
    gnis: pd.DataFrame = pd.read_csv('data/GNIS_250319.csv')

    print(f"   ✅ Loaded {len(place_names):,} place names")
    print(f"   ✅ Loaded {len(gnis):,} GNIS features")

    print("\n2. Initializing geocoder...")
    geocoder: CountyCentroidGeocoder = CountyCentroidGeocoder()
    print(f"   ✅ Loaded {len(geocoder.centroids)} county centroids")

    example_coords = geocoder.get_coordinates("Davidson")
    if example_coords:
        print(
            f"   📍 Example: Davidson County center at "
            f"{example_coords[0]:.4f}, {example_coords[1]:.4f}"
        )

    print("\n3. Testing distance calculation...")
    nashville_lat, nashville_lon = 36.1667, -86.7844
    chattanooga_lat, chattanooga_lon = 35.1245, -85.2972

    distance: float = GeoDistanceCalculator.haversine_distance(
        nashville_lat,
        nashville_lon,
        chattanooga_lat,
        chattanooga_lon
    )
    print(
        f"   📏 Distance Nashville → Chattanooga: {distance:.2f} miles"
    )

    print("\n4. Filtering to unmatched records...")
    unmatched: pd.DataFrame = place_names[place_names['Match'] == 'No']
    sample_size = min(200, len(unmatched))
    sample: pd.DataFrame = unmatched.head(sample_size)
    print(f"   ✅ Processing sample of {sample_size} unmatched records")

    print("\n5. Creating enhanced matching pipeline...")
    pipeline: EnhancedMatchingPipeline = EnhancedMatchingPipeline(
        sample,
        gnis
    )
    print("   ✅ Pipeline initialized with distance enhancement")

    print("\n6. Running matching with distance enhancement...")
    results: pd.DataFrame = pipeline.run_full_matching(
        confidence_threshold=70,
        batch_size=50,
        use_distance=True
    )

    print("\n7. Analyzing results...")
    print(f"   📊 Total matches processed: {len(results)}")
    print(f"   ✅ Matches found: {(results['confidence'] > 0).sum()}")
    print(
        f"   🎯 High confidence (≥90): "
        f"{(results['confidence'] >= 90).sum()}"
    )
    print(
        f"   📈 Medium confidence (75-89): "
        f"{((results['confidence'] >= 75) & (results['confidence'] < 90)).sum()}"
    )

    if 'distance_miles' in results.columns:
        valid_dist = results['distance_miles'].notna().sum()
        print(f"   📍 Matches with distance data: {valid_dist}")
        if valid_dist > 0:
            mean_dist = results['distance_miles'].mean()
            median_dist = results['distance_miles'].median()
            print(f"   📏 Average distance: {mean_dist:.1f} miles")
            print(f"   📏 Median distance: {median_dist:.1f} miles")

    print("\n8. Generating quality report...")
    report: Dict[str, Any] = pipeline.generate_quality_report(
        include_distance_analysis=True
    )

    print("\n   Key Metrics:")
    print(f"   • Match rate: {report['match_rate']:.1f}%")
    if 'county_match_rate' in report:
        print(f"   • County match rate: {report['county_match_rate']:.1f}%")

    if 'distance_analysis' in report:
        dist_stats = report['distance_analysis']
        print("\n   Distance Statistics:")
        print(f"   • Mean: {dist_stats['mean_distance']:.1f} miles")
        print(f"   • Median: {dist_stats['median_distance']:.1f} miles")
        print(
            f"   • Range: {dist_stats['min_distance']:.1f} - "
            f"{dist_stats['max_distance']:.1f} miles"
        )

        print("\n   Distance Distribution:")
        dist_dist = dist_stats['distribution']
        total = dist_stats['total_matches_with_distance']
        for range_name, count in dist_dist.items():
            pct = (count / total * 100) if total > 0 else 0
            print(f"   • {range_name:20s}: {count:4d} ({pct:5.1f}%)")

    print("\n9. Exporting results...")
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    pipeline.export_for_review(str(output_dir))

    if 'distance_miles' in results.columns:
        pipeline.export_distance_report(
            str(output_dir / 'distance_analysis.txt')
        )
        print("   ✅ Distance analysis report saved")

    print("\n10. Sample matches with distance:")
    sample_matches = results[
        (results['confidence'] > 0) &
        (results['distance_miles'].notna())
    ].head(5)

    for idx, row in sample_matches.iterrows():
        print(f"\n   📍 {row['place_name']} ({row['place_county']}) →")
        print(f"      {row['gnis_name']} ({row['gnis_county']})")
        print(
            f"      Confidence: {row['confidence']:.0f}%, "
            f"Distance: {row['distance_miles']:.1f} miles"
        )
        if 'distance_note' in row and pd.notna(row['distance_note']):
            print(f"      Note: {row['distance_note']}")

    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print(f"\n📁 Results saved to: {output_dir}")
    print("\n📖 Generated Files:")
    print("  • high_confidence_matches.csv")
    print("  • medium_confidence_matches.csv")
    print("  • low_confidence_matches.csv")
    print("  • no_matches.csv")
    print("  • multiple_matches.csv")
    print("  • all_matches.csv")
    print("  • distance_analysis.txt")

    print("\n📖 Next Steps:")
    print("  1. Review distance_analysis.txt for suspicious matches")
    print("  2. Check high-confidence matches (likely accurate)")
    print("  3. Manually review medium-confidence matches")
    print("  4. Consider adjusting distance thresholds if needed")
    print("  5. Run on full dataset when satisfied with results")

    print("\n✨ Enhanced matching complete! ✨\n")


if __name__ == "__main__":
    main()
