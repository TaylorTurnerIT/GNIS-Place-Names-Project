"""
Enhanced Matching Pipeline with Geographic Distance.

Extends the base matching pipeline with geolocation enhancement to:
- Calculate distances between matches
- Adjust confidence scores based on proximity
- Resolve ambiguous matches using geographic proximity
- Generate distance-based quality reports
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
from tqdm import tqdm
import json

from matching_algorithm import PlaceNameMatcher
from geolocation_matcher import GeoEnhancedMatcher, GeoDistanceCalculator


class EnhancedMatchingPipeline:
    """
    Complete matching pipeline with geographic distance enhancement.

    This pipeline integrates traditional fuzzy matching with geographic
    proximity analysis to improve match accuracy and disambiguation.
    """

    def __init__(
        self,
        place_names_df: pd.DataFrame,
        gnis_df: pd.DataFrame,
        county_centroids_file: Optional[Path] = None
    ) -> None:
        """
        Initialize the enhanced matching pipeline.

        Args:
            place_names_df: DataFrame with place name records.
            gnis_df: DataFrame with GNIS feature records.
            county_centroids_file: Path to county centroids CSV.
        """
        self.matcher = PlaceNameMatcher(place_names_df, gnis_df)
        self.geo_matcher = GeoEnhancedMatcher(
            place_names_df,
            gnis_df,
            county_centroids_file
        )
        self.results: Optional[pd.DataFrame] = None
        self.results_with_distance: Optional[pd.DataFrame] = None

    @staticmethod
    def _convert_to_native(obj: Any) -> Any:
        """
        Convert numpy types to native Python types for JSON serialization.

        Args:
            obj: Object to convert (can be dict, numpy type, etc.).

        Returns:
            Object with all numpy types converted to native Python types.
        """
        if isinstance(obj, dict):
            return {
                k: EnhancedMatchingPipeline._convert_to_native(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    def run_full_matching(
        self,
        confidence_threshold: float = 70,
        batch_size: int = 100,
        use_distance: bool = True
    ) -> pd.DataFrame:
        """
        Run complete matching pipeline with optional distance enhancement.

        Args:
            confidence_threshold: Minimum confidence score for matches.
            batch_size: Number of records to process per batch.
            use_distance: Whether to apply distance-based adjustments.

        Returns:
            DataFrame with match results, optionally with distance data.
        """
        total_records = len(self.matcher.place_names)
        all_results: List[Dict[str, Any]] = []

        print(f"Processing {total_records} place names...")
        print(f"Confidence threshold: {confidence_threshold}")
        print(f"Distance enhancement: {'enabled' if use_distance else 'disabled'}")

        for start_idx in tqdm(range(0, total_records, batch_size)):
            end_idx = min(start_idx + batch_size, total_records)
            batch = self.matcher.place_names.iloc[start_idx:end_idx]

            for idx, place in batch.iterrows():
                matches = self.matcher._find_matches_for_place(
                    place,
                    threshold=confidence_threshold
                )

                if matches:
                    best_score = matches[0]['confidence']
                    best_matches = [
                        m for m in matches
                        if m['confidence'] == best_score
                    ]

                    for match in best_matches[:3]:
                        all_results.append({
                            'place_idx': idx,
                            'place_name': place['Place_Name'],
                            'place_county': place['County'],
                            'place_po_start': place.get('PO_Start'),
                            'place_po_end': place.get('PO_End'),
                            'gnis_idx': match['gnis_idx'],
                            'gnis_id': match['gnis_id'],
                            'gnis_name': match['gnis_name'],
                            'gnis_county': match['gnis_county'],
                            'gnis_feature_class': match['feature_class'],
                            'confidence': match['confidence'],
                            'match_strategy': match['strategy'],
                            'notes': match['notes']
                        })
                else:
                    all_results.append({
                        'place_idx': idx,
                        'place_name': place['Place_Name'],
                        'place_county': place['County'],
                        'place_po_start': place.get('PO_Start'),
                        'place_po_end': place.get('PO_End'),
                        'gnis_idx': None,
                        'gnis_id': None,
                        'gnis_name': None,
                        'gnis_county': None,
                        'gnis_feature_class': None,
                        'confidence': 0,
                        'match_strategy': 'NO_MATCH',
                        'notes': 'No confident match found'
                    })

        self.results = pd.DataFrame(all_results)

        if use_distance:
            print("\nApplying distance-based enhancements...")
            self.results_with_distance = self._apply_distance_enhancement(
                self.results
            )
            return self.results_with_distance

        return self.results

    def _apply_distance_enhancement(
        self,
        matches_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Apply distance-based adjustments to match results.

        Args:
            matches_df: DataFrame with initial match results.

        Returns:
            DataFrame with distance calculations and adjusted confidence.
        """
        matches_with_dist = self.geo_matcher.add_distance_to_matches(
            matches_df
        )

        matches_with_dist = self.geo_matcher.adjust_confidence_by_distance(
            matches_with_dist
        )

        matches_with_dist = (
            self.geo_matcher.resolve_multiple_matches_by_distance(
                matches_with_dist
            )
        )

        return matches_with_dist

    def generate_quality_report(
        self,
        include_distance_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive quality metrics.

        Args:
            include_distance_analysis: Whether to include distance stats.

        Returns:
            Dictionary with detailed quality metrics.
        """
        if self.results is None:
            raise ValueError("Must run matching first")

        results_df = (
            self.results_with_distance
            if self.results_with_distance is not None
            else self.results
        )

        report: Dict[str, Any] = {
            'total_places': len(self.matcher.place_names),
            'total_gnis': len(self.matcher.gnis),
            'matches_found': int((results_df['confidence'] > 0).sum()),
            'no_matches': int((results_df['confidence'] == 0).sum()),
            'match_rate': float(
                (results_df['confidence'] > 0).sum() /
                len(results_df) * 100
            ),
        }

        report['confidence_distribution'] = {
            'high (90-100)': int(
                ((results_df['confidence'] >= 90) &
                 (results_df['confidence'] <= 100)).sum()
            ),
            'medium-high (80-89)': int(
                ((results_df['confidence'] >= 80) &
                 (results_df['confidence'] < 90)).sum()
            ),
            'medium (75-79)': int(
                ((results_df['confidence'] >= 75) &
                 (results_df['confidence'] < 80)).sum()
            ),
            'low (70-74)': int(
                ((results_df['confidence'] >= 70) &
                 (results_df['confidence'] < 75)).sum()
            ),
            'none (0)': int((results_df['confidence'] == 0).sum())
        }

        report['strategy_distribution'] = (
            results_df['match_strategy']
            .value_counts()
            .to_dict()
        )

        matched = results_df[results_df['confidence'] > 0]
        if len(matched) > 0:
            report['feature_class_distribution'] = (
                matched['gnis_feature_class']
                .value_counts()
                .head(10)
                .to_dict()
            )

        matched_with_county = matched[
            (matched['place_county'].notna()) &
            (matched['gnis_county'].notna())
        ]
        if len(matched_with_county) > 0:
            county_matches = (
                matched_with_county['place_county'].str.lower() ==
                matched_with_county['gnis_county'].str.lower()
            ).sum()
            report['county_match_rate'] = float(
                county_matches / len(matched_with_county) * 100
            )

        places_with_multiple = results_df.groupby('place_idx').size()
        report['places_with_multiple_matches'] = int(
            (places_with_multiple > 1).sum()
        )
        report['max_matches_per_place'] = int(places_with_multiple.max())

        if (
            include_distance_analysis and
            self.results_with_distance is not None and
            'distance_miles' in self.results_with_distance.columns
        ):
            dist_analysis = self.geo_matcher.analyze_distance_distribution(
                self.results_with_distance
            )
            report['distance_analysis'] = dist_analysis

        return self._convert_to_native(report)

    def export_for_review(self, output_dir: str = 'output') -> None:
        """
        Export results in different formats for review.

        Creates separate CSV files for different confidence levels and
        match scenarios to facilitate manual review.

        Args:
            output_dir: Directory path for output files.
        """
        if self.results is None:
            raise ValueError("Must run matching first")

        results_df = (
            self.results_with_distance
            if self.results_with_distance is not None
            else self.results
        )

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        high_confidence = results_df[results_df['confidence'] >= 90].copy()
        high_confidence.to_csv(
            output_path / 'high_confidence_matches.csv',
            index=False
        )

        medium_confidence = results_df[
            (results_df['confidence'] >= 75) &
            (results_df['confidence'] < 90)
        ].copy()
        medium_confidence.to_csv(
            output_path / 'medium_confidence_matches.csv',
            index=False
        )

        low_confidence = results_df[
            (results_df['confidence'] >= 70) &
            (results_df['confidence'] < 75)
        ].copy()
        low_confidence.to_csv(
            output_path / 'low_confidence_matches.csv',
            index=False
        )

        no_matches = results_df[results_df['confidence'] == 0].copy()
        no_matches.to_csv(
            output_path / 'no_matches.csv',
            index=False
        )

        multi_matches = results_df[
            results_df.duplicated(subset=['place_idx'], keep=False)
        ].sort_values(['place_idx', 'confidence'], ascending=[True, False])
        multi_matches.to_csv(
            output_path / 'multiple_matches.csv',
            index=False
        )

        results_df.to_csv(output_path / 'all_matches.csv', index=False)

        print(f"\nExported files to {output_dir}:")
        print(
            f"  - high_confidence_matches.csv "
            f"({len(high_confidence)} records)"
        )
        print(
            f"  - medium_confidence_matches.csv "
            f"({len(medium_confidence)} records)"
        )
        print(
            f"  - low_confidence_matches.csv "
            f"({len(low_confidence)} records)"
        )
        print(f"  - no_matches.csv ({len(no_matches)} records)")
        print(f"  - multiple_matches.csv ({len(multi_matches)} records)")
        print(f"  - all_matches.csv ({len(results_df)} records)")

    def export_distance_report(self, output_file: str = 'output/distance_analysis.txt') -> None:
        """
        Export a detailed distance analysis report.

        Args:
            output_file: Path for the output report file.
        """
        if self.results_with_distance is None:
            raise ValueError(
                "Must run matching with distance enhancement first"
            )

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("GEOGRAPHIC DISTANCE ANALYSIS REPORT\n")
            f.write("=" * 80 + "\n\n")

            dist_analysis = self.geo_matcher.analyze_distance_distribution(
                self.results_with_distance
            )

            if 'error' not in dist_analysis:
                f.write("OVERALL STATISTICS\n")
                f.write("-" * 80 + "\n")
                f.write(
                    f"Matches with distance data: "
                    f"{dist_analysis['total_matches_with_distance']}\n"
                )
                f.write(
                    f"Mean distance: "
                    f"{dist_analysis['mean_distance']:.2f} miles\n"
                )
                f.write(
                    f"Median distance: "
                    f"{dist_analysis['median_distance']:.2f} miles\n"
                )
                f.write(
                    f"Min distance: "
                    f"{dist_analysis['min_distance']:.2f} miles\n"
                )
                f.write(
                    f"Max distance: "
                    f"{dist_analysis['max_distance']:.2f} miles\n"
                )
                f.write(
                    f"Std deviation: "
                    f"{dist_analysis['std_distance']:.2f} miles\n"
                )

                f.write("\nDISTRIBUTION BY RANGE\n")
                f.write("-" * 80 + "\n")
                total = dist_analysis['total_matches_with_distance']
                for range_name, count in dist_analysis['distribution'].items():
                    pct = (count / total * 100) if total > 0 else 0
                    f.write(f"{range_name:20s}: {count:5d} ({pct:5.1f}%)\n")

            suspicious = self.results_with_distance[
                (self.results_with_distance['confidence'] >= 80) &
                (self.results_with_distance['distance_miles'] > 50)
            ].sort_values('distance_miles', ascending=False)

            if len(suspicious) > 0:
                f.write("\nSUSPICIOUS MATCHES (High confidence, far distance)\n")
                f.write("-" * 80 + "\n")
                f.write(
                    f"Found {len(suspicious)} matches with >=80% confidence "
                    f"but >50 miles apart\n\n"
                )

                for idx, row in suspicious.head(20).iterrows():
                    f.write(
                        f"{row['place_name']} ({row['place_county']}) -> "
                        f"{row['gnis_name']} ({row['gnis_county']})\n"
                    )
                    f.write(
                        f"  Distance: {row['distance_miles']:.1f} miles, "
                        f"Confidence: {row['confidence']:.0f}%\n"
                    )
                    f.write(f"  Notes: {row['notes']}\n\n")

        print(f"\nDistance analysis report saved to: {output_file}")


if __name__ == "__main__":
    """Example usage of the enhanced matching pipeline."""
    project_root = Path(__file__).parent.parent

    place_names = pd.read_csv(project_root / 'data' / 'PlaceNames.csv')
    gnis = pd.read_csv(project_root / 'data' / 'GNIS_250319.csv')

    print("=" * 80)
    print("ENHANCED MATCHING PIPELINE WITH DISTANCE")
    print("=" * 80)

    unmatched = place_names[place_names['Match'] == 'No'].copy()
    print(f"\nProcessing {len(unmatched)} unmatched records...")

    pipeline = EnhancedMatchingPipeline(
        unmatched.head(500),
        gnis
    )

    results = pipeline.run_full_matching(
        confidence_threshold=70,
        batch_size=50,
        use_distance=True
    )

    print("\n" + "=" * 80)
    print("QUALITY REPORT")
    print("=" * 80)
    report = pipeline.generate_quality_report(include_distance_analysis=True)
    print(json.dumps(report, indent=2))

    print("\n" + "=" * 80)
    print("EXPORTING RESULTS")
    print("=" * 80)
    pipeline.export_for_review()
    pipeline.export_distance_report()

    print("\n" + "=" * 80)
    print("PIPELINE COMPLETE")
    print("=" * 80)
