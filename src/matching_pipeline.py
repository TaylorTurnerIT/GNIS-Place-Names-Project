"""
Additional utilities for place name matching:
- Batch processing with progress tracking
- Match quality analysis
- Export functions for review
"""

import pandas as pd
import numpy as np
from matching_algorithm import PlaceNameMatcher
from tqdm import tqdm
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

class MatchingPipeline:
    """Complete matching pipeline with quality metrics"""

    def __init__(self, place_names_df: pd.DataFrame, gnis_df: pd.DataFrame) -> None:
        self.matcher: PlaceNameMatcher = PlaceNameMatcher(place_names_df, gnis_df)
        self.results: Optional[pd.DataFrame] = None

    @staticmethod
    def _convert_to_native(obj: Any) -> Any:
        """Convert numpy types to native Python types for JSON serialization"""
        if isinstance(obj, dict):
            return {k: MatchingPipeline._convert_to_native(v) for k, v in obj.items()}
        elif isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj
        
    def run_full_matching(
        self,
        confidence_threshold: float = 80,
        batch_size: int = 100
    ) -> pd.DataFrame:
        """
        Run matching on all records with progress tracking.

        Args:
            confidence_threshold: Minimum confidence (default: 80, strict).
            batch_size: Records per batch (default: 100).

        Returns:
            DataFrame with all match results.
        """
        total_records: int = len(self.matcher.place_names)
        all_results: List[Dict[str, Any]] = []

        print(f"Processing {total_records} place names...")
        print(f"Confidence threshold: {confidence_threshold} (strict mode)")
        
        # Process in batches for memory efficiency
        for start_idx in tqdm(range(0, total_records, batch_size)):
            end_idx: int = min(start_idx + batch_size, total_records)
            batch: pd.DataFrame = self.matcher.place_names.iloc[start_idx:end_idx]

            for idx, place in batch.iterrows():
                matches: List[Dict[str, Any]] = (
                    self.matcher._find_matches_for_place(
                        place,
                        threshold=confidence_threshold
                    )
                )

                if matches:
                    best_score: float = matches[0]['confidence']
                    best_matches: List[Dict[str, Any]] = [
                        m for m in matches
                        if m['confidence'] == best_score
                    ]

                    for match in best_matches[:3]:
                        all_results.append({
                            'place_idx': idx,
                            'place_name': place['Place_Name'],
                            'place_county': place['County'],
                            'place_po_start': place['PO_Start'],
                            'place_po_end': place['PO_End'],
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
                        'place_po_start': place['PO_Start'],
                        'place_po_end': place['PO_End'],
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
        return self.results
    
    def generate_quality_report(self) -> Dict[str, Any]:
        """Generate comprehensive quality metrics"""
        if self.results is None:
            raise ValueError("Must run matching first")

        report: Dict[str, Any] = {
            'total_places': len(self.matcher.place_names),
            'total_gnis': len(self.matcher.gnis),
            'matches_found': (self.results['confidence'] > 0).sum(),
            'no_matches': (self.results['confidence'] == 0).sum(),
            'match_rate': (self.results['confidence'] > 0).sum() / len(self.results) * 100,
        }
        
        # Confidence distribution
        report['confidence_distribution'] = {
            'high (90-100)': ((self.results['confidence'] >= 90) & (self.results['confidence'] <= 100)).sum(),
            'medium-high (80-89)': ((self.results['confidence'] >= 80) & (self.results['confidence'] < 90)).sum(),
            'medium (75-79)': ((self.results['confidence'] >= 75) & (self.results['confidence'] < 80)).sum(),
            'low (70-74)': ((self.results['confidence'] >= 70) & (self.results['confidence'] < 75)).sum(),
            'none (0)': (self.results['confidence'] == 0).sum()
        }
        
        # Strategy distribution
        report['strategy_distribution'] = self.results['match_strategy'].value_counts().to_dict()
        
        # Feature class distribution
        matched: pd.DataFrame = self.results[self.results['confidence'] > 0]
        if len(matched) > 0:
            report['feature_class_distribution'] = matched['gnis_feature_class'].value_counts().head(10).to_dict()

        # County match analysis
        matched_with_county: pd.DataFrame = matched[
            (matched['place_county'].notna()) & 
            (matched['gnis_county'].notna())
        ]
        if len(matched_with_county) > 0:
            county_matches: int = (
                matched_with_county['place_county'].str.lower() ==
                matched_with_county['gnis_county'].str.lower()
            ).sum()
            report['county_match_rate'] = county_matches / len(matched_with_county) * 100

        # Multiple matches analysis
        places_with_multiple: pd.Series = self.results.groupby('place_idx').size()
        report['places_with_multiple_matches'] = (places_with_multiple > 1).sum()
        report['max_matches_per_place'] = places_with_multiple.max()

        # Convert numpy types to native Python types
        return self._convert_to_native(report)
    
    def export_for_review(self, output_dir: str = 'output') -> None:
        """Export results in different formats for review"""
        if self.results is None:
            raise ValueError("Must run matching first")

        # 1. High confidence matches - ready for auto-approval
        high_confidence: pd.DataFrame = self.results[self.results['confidence'] >= 90].copy()
        high_confidence.to_csv(f'{output_dir}/high_confidence_matches.csv', index=False)
        
        # 2. Medium confidence - needs review
        medium_confidence: pd.DataFrame = self.results[
            (self.results['confidence'] >= 75) &
            (self.results['confidence'] < 90)
        ].copy()
        medium_confidence.to_csv(f'{output_dir}/medium_confidence_matches.csv', index=False)

        # 3. Low confidence - needs expert review
        low_confidence: pd.DataFrame = self.results[
            (self.results['confidence'] >= 70) &
            (self.results['confidence'] < 75)
        ].copy()
        low_confidence.to_csv(f'{output_dir}/low_confidence_matches.csv', index=False)

        # 4. No matches - requires research
        no_matches: pd.DataFrame = self.results[self.results['confidence'] == 0].copy()
        no_matches.to_csv(f'{output_dir}/no_matches.csv', index=False)

        # 5. Multiple matches - needs disambiguation
        multi_matches: pd.DataFrame = self.results[
            self.results.duplicated(subset=['place_idx'], keep=False)
        ].sort_values(['place_idx', 'confidence'], ascending=[True, False])
        multi_matches.to_csv(f'{output_dir}/multiple_matches.csv', index=False)
        
        # 6. Full results
        self.results.to_csv(f'{output_dir}/all_matches.csv', index=False)
        
        print(f"\nExported files to {output_dir}:")
        print(f"  - high_confidence_matches.csv ({len(high_confidence)} records)")
        print(f"  - medium_confidence_matches.csv ({len(medium_confidence)} records)")
        print(f"  - low_confidence_matches.csv ({len(low_confidence)} records)")
        print(f"  - no_matches.csv ({len(no_matches)} records)")
        print(f"  - multiple_matches.csv ({len(multi_matches)} records)")
        print(f"  - all_matches.csv ({len(self.results)} records)")
    
    def create_review_html(self, output_file: str = 'output/review.html', max_records: int = 100) -> None:
        """Create an HTML interface for reviewing matches"""
        if self.results is None:
            raise ValueError("Must run matching first")

        # Sample records for review (prioritize medium confidence)
        sample: pd.DataFrame = self.results[
            (self.results['confidence'] >= 75) & 
            (self.results['confidence'] < 90)
        ].head(max_records)

        html: str = """
<!DOCTYPE html>
<html>
<head>
    <title>Place Name Match Review</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .match-card {
            border: 1px solid #ddd;
            margin: 10px 0;
            padding: 15px;
            border-radius: 5px;
        }
        .high-confidence { border-left: 5px solid green; }
        .medium-confidence { border-left: 5px solid orange; }
        .low-confidence { border-left: 5px solid red; }
        .match-header { font-weight: bold; margin-bottom: 10px; }
        .confidence { 
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            color: white;
            font-weight: bold;
        }
        .conf-high { background-color: green; }
        .conf-medium { background-color: orange; }
        .conf-low { background-color: red; }
        .details { margin: 5px 0; }
        .label { font-weight: bold; color: #555; }
        button { 
            padding: 5px 15px;
            margin: 5px 5px 0 0;
            cursor: pointer;
        }
        .approve { background-color: #4CAF50; color: white; border: none; }
        .reject { background-color: #f44336; color: white; border: none; }
        .skip { background-color: #999; color: white; border: none; }
    </style>
</head>
<body>
    <h1>Place Name Match Review</h1>
    <p>Review matches and approve or reject. Medium confidence matches shown below.</p>
"""
        
        for idx, row in sample.iterrows():
            confidence_class = 'high' if row['confidence'] >= 90 else 'medium' if row['confidence'] >= 75 else 'low'
            conf_label_class = 'conf-high' if row['confidence'] >= 90 else 'conf-medium' if row['confidence'] >= 75 else 'conf-low'
            
            html += f"""
    <div class="match-card {confidence_class}-confidence">
        <div class="match-header">
            Match #{idx + 1}
            <span class="confidence {conf_label_class}">{row['confidence']:.1f}%</span>
        </div>
        <div class="details">
            <span class="label">PlaceNames:</span> {row['place_name']} 
            ({row['place_county'] if pd.notna(row['place_county']) else 'No County'})
        </div>
        <div class="details">
            <span class="label">GNIS:</span> {row['gnis_name']} 
            ({row['gnis_county']} - {row['gnis_feature_class']})
        </div>
        <div class="details">
            <span class="label">Strategy:</span> {row['match_strategy']}
        </div>
        <div class="details">
            <span class="label">Notes:</span> {row['notes']}
        </div>
        <button class="approve" onclick="approve({idx})">✓ Approve</button>
        <button class="reject" onclick="reject({idx})">✗ Reject</button>
        <button class="skip" onclick="skip({idx})">→ Skip</button>
    </div>
"""
        
        html += """
    <script>
        function approve(id) {
            alert('Match ' + id + ' approved (this is a demo - implement backend to save)');
            // In production, send to backend to update database
        }
        function reject(id) {
            alert('Match ' + id + ' rejected (this is a demo - implement backend to save)');
        }
        function skip(id) {
            alert('Match ' + id + ' skipped (this is a demo - implement backend to save)');
        }
    </script>
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\nReview interface created: {output_file}")
        print(f"Open in a web browser to review {len(sample)} matches")


class MatchAnalyzer:
    """Analyze patterns in matching results"""

    @staticmethod
    def analyze_unmatched(place_names: pd.DataFrame, results: pd.DataFrame) -> Dict[str, Any]:
        """Analyze characteristics of unmatched places"""
        unmatched_idx: np.ndarray = results[results['confidence'] == 0]['place_idx'].unique()
        unmatched_places: pd.DataFrame = place_names.loc[unmatched_idx]

        analysis: Dict[str, Any] = {
            'total_unmatched': len(unmatched_places),
            'with_county': unmatched_places['County'].notna().sum(),
            'without_county': unmatched_places['County'].isna().sum(),
        }
        
        # PO duration analysis
        unmatched_with_dates: pd.DataFrame = unmatched_places[
            unmatched_places['PO_Start'].notna() &
            unmatched_places['PO_End'].notna()
        ]
        if len(unmatched_with_dates) > 0:
            durations: pd.Series = unmatched_with_dates['PO_End'] - unmatched_with_dates['PO_Start']
            analysis['avg_po_duration'] = durations.mean()
            analysis['median_po_duration'] = durations.median()
            analysis['short_lived_pos'] = (durations <= 5).sum()  # <= 5 years

        # Name length analysis
        name_lengths: pd.Series = unmatched_places['Place_Name'].str.split().str.len()
        analysis['avg_name_length_words'] = name_lengths.mean()
        analysis['single_word_names'] = (name_lengths == 1).sum()

        # Common patterns
        analysis['most_common_counties'] = unmatched_places['County'].value_counts().head(10).to_dict()
        
        return analysis
    
    @staticmethod
    def suggest_improvements(results: pd.DataFrame) -> List[str]:
        """Suggest algorithm improvements based on results"""
        suggestions: List[str] = []

        # Analyze fuzzy match scores
        fuzzy_matches: pd.DataFrame = results[results['match_strategy'].str.contains('FUZZY')]
        if len(fuzzy_matches) > 0:
            avg_confidence: float = fuzzy_matches['confidence'].mean()
            if avg_confidence < 75:
                suggestions.append(
                    f"Fuzzy matches have low average confidence ({avg_confidence:.1f}%). "
                    "Consider adjusting fuzzy matching parameters or adding more preprocessing."
                )
        
        # Check for systematic county mismatches
        mismatches: pd.DataFrame = results[
            (results['place_county'].notna()) &
            (results['gnis_county'].notna()) &
            (results['place_county'].str.lower() != results['gnis_county'].str.lower())
        ]
        if len(mismatches) > len(results) * 0.3:
            suggestions.append(
                f"{len(mismatches)} matches ({len(mismatches)/len(results)*100:.1f}%) "
                "have county mismatches. Consider historical county boundary changes."
            )
        
        # Multiple matches analysis
        multi_match_places: int = results[results.duplicated(subset=['place_idx'], keep=False)]['place_idx'].nunique()
        if multi_match_places > 0:
            suggestions.append(
                f"{multi_match_places} places have multiple potential matches. "
                "Consider adding geographic proximity or additional context for disambiguation."
            )
        
        return suggestions


# Example usage
if __name__ == "__main__":
    # Get project root directory (parent of src)
    PROJECT_ROOT = Path(__file__).parent.parent

    # Load data
    place_names = pd.read_csv(PROJECT_ROOT / 'data' / 'PlaceNames.csv')
    gnis = pd.read_csv(PROJECT_ROOT / 'data' / 'GNIS_250319.csv')
    
    print("=" * 80)
    print("PLACE NAME MATCHING PIPELINE")
    print("=" * 80)
    
    # Create pipeline
    pipeline = MatchingPipeline(place_names, gnis)
    
    # Run matching (on a sample for demo)
    print("\nRunning matching on unmatched records...")
    unmatched = place_names[place_names['Match'] == 'No'].copy()
    pipeline_sample = MatchingPipeline(unmatched.head(500), gnis)
    results = pipeline_sample.run_full_matching(confidence_threshold=70, batch_size=50)
    
    # Generate quality report
    print("\n" + "=" * 80)
    print("QUALITY REPORT")
    print("=" * 80)
    report = pipeline_sample.generate_quality_report()
    
    # Convert numpy types to native Python types for JSON serialization
    def convert_to_native(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: convert_to_native(v) for k, v in obj.items()}
        elif isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    report = convert_to_native(report)
    print(json.dumps(report, indent=2))
    
    # Analyze unmatched
    print("\n" + "=" * 80)
    print("UNMATCHED ANALYSIS")
    print("=" * 80)
    unmatched_analysis = MatchAnalyzer.analyze_unmatched(
        unmatched.head(500), 
        results
    )
    print(json.dumps(unmatched_analysis, indent=2, default=str))
    
    # Get improvement suggestions
    print("\n" + "=" * 80)
    print("IMPROVEMENT SUGGESTIONS")
    print("=" * 80)
    suggestions = MatchAnalyzer.suggest_improvements(results)
    for i, suggestion in enumerate(suggestions, 1):
        print(f"{i}. {suggestion}")
    
    # Export results
    print("\n" + "=" * 80)
    print("EXPORTING RESULTS")
    print("=" * 80)
    pipeline_sample.export_for_review()
    
    # Create review interface
    pipeline_sample.create_review_html(max_records=50)
    
    print("\n" + "=" * 80)
    print("PIPELINE COMPLETE")
    print("=" * 80)
