"""
Advanced Place Name Matching Algorithm
Handles multiple matching strategies with confidence scoring
"""

import pandas as pd
import numpy as np
import re
from rapidfuzz import fuzz, process
from collections import defaultdict
from typing import List, Tuple, Dict, Optional, Any, DefaultDict
from pathlib import Path

class PlaceNameMatcher:
    """
    Multi-strategy place name matching system with confidence scoring.
    
    Key Challenges Addressed:
    1. Different naming conventions (e.g., "Aaron" vs "Aaron Branch")
    2. Historical markers in GNIS
    3. Different feature types (post offices vs geographic features)
    4. Missing county information
    5. Multiple potential matches per place name
    """
    
    def __init__(self, place_names_df: pd.DataFrame, gnis_df: pd.DataFrame) -> None:
        self.place_names: pd.DataFrame = place_names_df.copy()
        self.gnis: pd.DataFrame = gnis_df.copy()
        self.gnis_by_county: Dict[Any, Any] = {}
        self.gnis_by_name: Dict[Any, Any] = {}
        self.gnis_by_first_word: DefaultDict[str, List[Any]] = defaultdict(list)

        # Preprocess data
        self._preprocess_data()

        # Build indexes for efficient lookup
        self._build_indexes()
        
    def _preprocess_data(self) -> None:
        """Clean and standardize data"""
        # Extract base names (remove parenthetical notes)
        self.place_names['base_name'] = self.place_names['Place_Name'].apply(self._extract_base_name)
        self.gnis['base_name'] = self.gnis['gaz_name'].apply(self._extract_base_name)
        
        # Normalize for comparison
        self.place_names['normalized_name'] = self.place_names['base_name'].str.lower().str.strip()
        self.gnis['normalized_name'] = self.gnis['base_name'].str.lower().str.strip()
        
        # Normalize counties
        self.place_names['normalized_county'] = self.place_names['County'].str.lower().str.strip()
        self.gnis['normalized_county'] = self.gnis['county_name'].str.lower().str.strip()
        
        # Extract name components (first word, last word, etc.)
        self.place_names['first_word'] = self.place_names['normalized_name'].str.split().str[0]
        self.place_names['last_word'] = self.place_names['normalized_name'].str.split().str[-1]
        
        self.gnis['first_word'] = self.gnis['normalized_name'].str.split().str[0]
        self.gnis['last_word'] = self.gnis['normalized_name'].str.split().str[-1]
        
        # Identify historical markers
        self.gnis['is_historical'] = self.gnis['gaz_name'].str.contains(
            r'\(historical\)', case=False, na=False
        )
        
    def _extract_base_name(self, name: Any) -> str:
        """Remove parenthetical notes and extra whitespace"""
        if pd.isna(name):
            return ''
        # Remove content in parentheses
        clean_name: str = re.sub(r'\s*\([^)]*\)\s*', ' ', str(name))
        return clean_name.strip()
    
    def _build_indexes(self) -> None:
        """Build lookup indexes for fast matching"""
        # Index by county and name
        self.gnis_by_county = self.gnis.groupby('normalized_county').groups
        self.gnis_by_name = self.gnis.groupby('normalized_name').groups

        # Index by first word for partial matching
        self.gnis_by_first_word = defaultdict(list)
        for idx, row in self.gnis.iterrows():
            if pd.notna(row['first_word']) and row['first_word']:
                self.gnis_by_first_word[row['first_word']].append(idx)
    
    def match_all(self, confidence_threshold: float = 70) -> pd.DataFrame:
        """
        Run all matching strategies and return results

        Strategies (in order of confidence):
        1. Exact match (name + county)
        2. Exact name match with fuzzy county
        3. Name variation match (handles suffixes/prefixes)
        4. Fuzzy name match with exact county
        5. Fuzzy name and county match
        6. Historical name matching
        7. First word matching (for cases like "Aaron" vs "Aaron Branch")
        """
        results: List[Dict[str, Any]] = []
        
        for idx, place in self.place_names.iterrows():
            matches = self._find_matches_for_place(place, confidence_threshold)
            
            if matches:
                # Take the best match(es)
                best_score = matches[0]['confidence']
                best_matches = [m for m in matches if m['confidence'] == best_score]
                
                for match in best_matches[:3]:  # Top 3 if tied
                    results.append({
                        'place_idx': idx,
                        'place_name': place['Place_Name'],
                        'place_county': place['County'],
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
                # No match found
                results.append({
                    'place_idx': idx,
                    'place_name': place['Place_Name'],
                    'place_county': place['County'],
                    'gnis_idx': None,
                    'gnis_id': None,
                    'gnis_name': None,
                    'gnis_county': None,
                    'gnis_feature_class': None,
                    'confidence': 0,
                    'match_strategy': 'NO_MATCH',
                    'notes': 'No confident match found'
                })
        
        return pd.DataFrame(results)
    
    def _find_matches_for_place(self, place: pd.Series, threshold: float = 70) -> List[Dict[str, Any]]:
        """Find all potential matches for a single place"""
        matches: List[Dict[str, Any]] = []

        place_name: str = place['normalized_name']
        place_county: str = place['normalized_county']
        
        if not place_name:
            return matches
        
        # Strategy 1: Exact match (name + county)
        if pd.notna(place_county) and place_county:
            exact_matches = self._exact_match(place_name, place_county)
            if exact_matches:
                matches.extend(exact_matches)
                return matches  # High confidence, return immediately
        
        # Strategy 2: Exact name, any county (or missing county)
        exact_name_matches = self._exact_name_match(place_name, place_county)
        matches.extend(exact_name_matches)
        
        # Strategy 3: Name variations (suffix/prefix matching)
        variation_matches = self._name_variation_match(place_name, place_county, place)
        matches.extend(variation_matches)
        
        # Strategy 4: Fuzzy name with exact county
        if pd.notna(place_county) and place_county:
            fuzzy_matches = self._fuzzy_match_with_county(place_name, place_county, threshold)
            matches.extend(fuzzy_matches)
        
        # Strategy 5: Fuzzy match without county requirement
        general_fuzzy = self._fuzzy_match_general(place_name, place_county, threshold)
        matches.extend(general_fuzzy)
        
        # Strategy 6: First word matching (for partial names)
        first_word_matches = self._first_word_match(place, threshold)
        matches.extend(first_word_matches)
        
        # Sort by confidence and remove duplicates
        matches = self._deduplicate_matches(matches)
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        return matches
    
    def _exact_match(self, place_name: str, place_county: str) -> List[Dict[str, Any]]:
        """Strategy 1: Exact name and county match"""
        matches: List[Dict[str, Any]] = []
        
        mask = (
            (self.gnis['normalized_name'] == place_name) &
            (self.gnis['normalized_county'] == place_county)
        )
        
        for idx, row in self.gnis[mask].iterrows():
            matches.append({
                'gnis_idx': idx,
                'gnis_id': row['gaz_id'],
                'gnis_name': row['gaz_name'],
                'gnis_county': row['county_name'],
                'feature_class': row['gaz_featureclass'],
                'confidence': 100,
                'strategy': 'EXACT_MATCH',
                'notes': 'Exact name and county match'
            })
        
        return matches
    
    def _exact_name_match(self, place_name: str, place_county: str) -> List[Dict[str, Any]]:
        """Strategy 2: Exact name match, any county"""
        matches: List[Dict[str, Any]] = []
        
        mask = self.gnis['normalized_name'] == place_name
        
        for idx, row in self.gnis[mask].iterrows():
            # Higher confidence if counties match
            confidence: float = 95
            notes: str = 'Exact name match'
            
            if pd.notna(place_county) and place_county:
                if row['normalized_county'] == place_county:
                    continue  # Already covered by exact match
                else:
                    confidence = 85
                    notes = 'Exact name, different county'
            else:
                notes = 'Exact name, no county to verify'
            
            matches.append({
                'gnis_idx': idx,
                'gnis_id': row['gaz_id'],
                'gnis_name': row['gaz_name'],
                'gnis_county': row['county_name'],
                'feature_class': row['gaz_featureclass'],
                'confidence': confidence,
                'strategy': 'EXACT_NAME',
                'notes': notes
            })
        
        return matches
    
    def _name_variation_match(self, place_name: str, place_county: str, place: pd.Series) -> List[Dict[str, Any]]:
        """Strategy 3: Handle name variations with suffixes/prefixes"""
        matches: List[Dict[str, Any]] = []

        # Common variations to check
        variations: List[str] = self._generate_name_variations(place_name)
        
        for variation in variations:
            mask = self.gnis['normalized_name'] == variation

            for idx, row in self.gnis[mask].iterrows():
                confidence: float = 90

                # Adjust confidence based on county match
                if pd.notna(place_county) and place_county:
                    if row['normalized_county'] == place_county:
                        confidence = 95
                    else:
                        confidence = 80
                
                matches.append({
                    'gnis_idx': idx,
                    'gnis_id': row['gaz_id'],
                    'gnis_name': row['gaz_name'],
                    'gnis_county': row['county_name'],
                    'feature_class': row['gaz_featureclass'],
                    'confidence': confidence,
                    'strategy': 'NAME_VARIATION',
                    'notes': f'Name variation: {variation}'
                })
        
        return matches
    
    def _generate_name_variations(self, name: str) -> List[str]:
        """Generate common name variations"""
        variations: List[str] = []

        # Common suffixes that might be added/removed
        suffixes: List[str] = [
            'branch', 'creek', 'hollow', 'ridge', 'spring', 'hill',
            'station', 'mill', 'chapel', 'store', 'landing', 'gap',
            'grove', 'valley', 'point', 'springs', 'crossroads', 'depot'
        ]

        words: List[str] = name.split()

        # Try adding common suffixes
        for suffix in suffixes:
            variations.append(f"{name} {suffix}")

        # Try removing last word if it's a common suffix
        if len(words) > 1 and words[-1] in suffixes:
            variations.append(' '.join(words[:-1]))

        # Try possessive variations
        if words:
            first_word: str = words[0]
            if not first_word.endswith('s'):
                variations.append(first_word + 's ' + ' '.join(words[1:]) if len(words) > 1 else first_word + 's')
            if first_word.endswith('s') and len(first_word) > 1:
                variations.append(first_word[:-1] + ' '.join(words[1:]) if len(words) > 1 else first_word[:-1])

        return list(set(variations))
    
    def _fuzzy_match_with_county(self, place_name: str, place_county: str, threshold: float) -> List[Dict[str, Any]]:
        """Strategy 4: Fuzzy name match with exact county"""
        matches: List[Dict[str, Any]] = []

        # Get all GNIS entries in the same county
        if place_county in self.gnis_by_county:
            county_gnis: pd.DataFrame = self.gnis.iloc[list(self.gnis_by_county[place_county])]

            # Use fuzzy matching on names
            names_to_match: List[str] = county_gnis['normalized_name'].tolist()
            fuzzy_results = process.extract(
                place_name, 
                names_to_match, 
                scorer=fuzz.token_sort_ratio,
                limit=5
            )
            
            for match_name, score, idx_in_list in fuzzy_results:
                if score >= threshold:
                    gnis_idx = county_gnis.index[idx_in_list]
                    row = self.gnis.loc[gnis_idx]
                    
                    matches.append({
                        'gnis_idx': gnis_idx,
                        'gnis_id': row['gaz_id'],
                        'gnis_name': row['gaz_name'],
                        'gnis_county': row['county_name'],
                        'feature_class': row['gaz_featureclass'],
                        'confidence': score,
                        'strategy': 'FUZZY_WITH_COUNTY',
                        'notes': f'Fuzzy match in same county (score: {score})'
                    })
        
        return matches
    
    def _fuzzy_match_general(self, place_name: str, place_county: str, threshold: float) -> List[Dict[str, Any]]:
        """Strategy 5: General fuzzy matching"""
        matches: List[Dict[str, Any]] = []

        # Fuzzy match against all GNIS names
        names_to_match: List[str] = self.gnis['normalized_name'].tolist()
        fuzzy_results = process.extract(
            place_name,
            names_to_match,
            scorer=fuzz.token_sort_ratio,
            limit=10
        )
        
        for match_name, score, idx_in_list in fuzzy_results:
            if score >= threshold:
                row = self.gnis.iloc[idx_in_list]

                # Adjust confidence based on county match
                confidence: float = score
                notes: str = f'Fuzzy match (score: {score})'
                
                if pd.notna(place_county) and place_county:
                    if row['normalized_county'] == place_county:
                        confidence = min(score + 5, 100)  # Boost for county match
                        notes += ', same county'
                    else:
                        confidence = max(score - 10, threshold)  # Penalty for different county
                        notes += ', different county'
                
                if confidence >= threshold:
                    matches.append({
                        'gnis_idx': row.name,
                        'gnis_id': row['gaz_id'],
                        'gnis_name': row['gaz_name'],
                        'gnis_county': row['county_name'],
                        'feature_class': row['gaz_featureclass'],
                        'confidence': confidence,
                        'strategy': 'FUZZY_GENERAL',
                        'notes': notes
                    })
        
        return matches
    
    def _first_word_match(self, place: pd.Series, threshold: float) -> List[Dict[str, Any]]:
        """Strategy 6: Match on first word (for cases like 'Aaron' vs 'Aaron Branch')"""
        matches: List[Dict[str, Any]] = []

        first_word: str = place['first_word']
        place_name: str = place['normalized_name']
        place_county: str = place['normalized_county']
        
        if not first_word or len(first_word) < 3:  # Avoid matching very short words
            return matches
        
        # Only use if place name is relatively short (1-2 words)
        if len(place_name.split()) > 2:
            return matches
        
        # Get GNIS entries that start with the same word
        if first_word in self.gnis_by_first_word:
            for gnis_idx in self.gnis_by_first_word[first_word]:
                row = self.gnis.loc[gnis_idx]

                # Calculate confidence based on name similarity and county match
                confidence: float = 70  # Base confidence for first word match

                # Check if it's just adding a suffix
                gnis_words: List[str] = row['normalized_name'].split()
                if len(gnis_words) == 2 and gnis_words[0] == first_word:
                    confidence = 80  # Higher confidence for simple suffix addition

                # County match bonus
                notes: str
                if pd.notna(place_county) and place_county:
                    if row['normalized_county'] == place_county:
                        confidence = min(confidence + 10, 95)
                        notes = f"First word match with suffix '{gnis_words[-1] if len(gnis_words) > 1 else ''}', same county"
                    else:
                        confidence = max(confidence - 5, threshold)
                        notes = f"First word match, different county"
                else:
                    notes = f"First word match with suffix '{gnis_words[-1] if len(gnis_words) > 1 else ''}'"
                
                if confidence >= threshold:
                    matches.append({
                        'gnis_idx': gnis_idx,
                        'gnis_id': row['gaz_id'],
                        'gnis_name': row['gaz_name'],
                        'gnis_county': row['county_name'],
                        'feature_class': row['gaz_featureclass'],
                        'confidence': confidence,
                        'strategy': 'FIRST_WORD',
                        'notes': notes
                    })
        
        return matches
    
    def _deduplicate_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate matches, keeping highest confidence"""
        seen: Dict[Any, Dict[str, Any]] = {}
        for match in matches:
            key: Any = match['gnis_idx']
            if key not in seen or match['confidence'] > seen[key]['confidence']:
                seen[key] = match

        return list(seen.values())
    
    def evaluate_existing_matches(self) -> pd.DataFrame:
        """Evaluate the quality of existing matches in the data"""
        matched: pd.DataFrame = self.place_names[self.place_names['Match'] == 'Yes'].copy()

        evaluation: List[Dict[str, Any]] = []
        for idx, place in matched.iterrows():
            if pd.notna(place['JoinID']):
                gnis_match: pd.DataFrame = self.gnis[self.gnis['JoinID'] == place['JoinID']]

                if len(gnis_match) > 0:
                    gnis_row: pd.Series = gnis_match.iloc[0]

                    # Calculate similarity scores
                    name_similarity: float = fuzz.ratio(
                        place['normalized_name'],
                        gnis_row['normalized_name']
                    )

                    county_match: Optional[bool] = (
                        place['normalized_county'] == gnis_row['normalized_county']
                    ) if pd.notna(place['County']) else None

                    evaluation.append({
                        'place_name': place['Place_Name'],
                        'gnis_name': gnis_row['gaz_name'],
                        'name_similarity': name_similarity,
                        'county_match': county_match,
                        'feature_class': gnis_row['gaz_featureclass']
                    })

        return pd.DataFrame(evaluation)


# Example usage
if __name__ == "__main__":
    # Get project root directory (parent of src)
    PROJECT_ROOT = Path(__file__).parent.parent

    # Load data
    place_names = pd.read_csv(PROJECT_ROOT / 'data' / 'PlaceNames.csv')
    gnis = pd.read_csv(PROJECT_ROOT / 'data' / 'GNIS_250319.csv')
    
    # Create matcher
    print("Initializing matcher...")
    matcher = PlaceNameMatcher(place_names, gnis)
    
    # Evaluate existing matches
    print("\n=== EVALUATING EXISTING MATCHES ===")
    eval_df = matcher.evaluate_existing_matches()
    print(f"Existing matches evaluated: {len(eval_df)}")
    print(f"Average name similarity: {eval_df['name_similarity'].mean():.2f}")
    print(f"County matches: {eval_df['county_match'].sum()} / {eval_df['county_match'].notna().sum()}")
    
    # Test on unmatched records
    print("\n=== TESTING ON SAMPLE UNMATCHED RECORDS ===")
    unmatched_mask = place_names['Match'] == 'No'
    unmatched_indices = matcher.place_names[unmatched_mask].head(20).index
    
    for idx in unmatched_indices:
        place = matcher.place_names.loc[idx]
        matches = matcher._find_matches_for_place(place)
        
        print(f"\n{place['Place_Name']} ({place['County']})")
        if matches:
            for i, match in enumerate(matches[:3], 1):
                print(f"  {i}. {match['gnis_name']} ({match['gnis_county']}) - "
                      f"{match['confidence']}% - {match['strategy']}")
        else:
            print("  No matches found")
    
    print("\n=== RUNNING FULL MATCHING (this may take a minute...) ===")
    # Run full matching on a subset
    sample_unmatched = place_names[place_names['Match'] == 'No'].head(100)
    matcher_sample = PlaceNameMatcher(sample_unmatched, gnis)
    results = matcher_sample.match_all(confidence_threshold=75)
    
    # Analyze results
    print(f"\nProcessed: {len(sample_unmatched)} unmatched places")
    print(f"Found matches: {(results['confidence'] > 0).sum()}")
    print(f"High confidence (>90): {(results['confidence'] > 90).sum()}")
    print(f"Medium confidence (75-90): {((results['confidence'] >= 75) & (results['confidence'] <= 90)).sum()}")
    
    print("\n=== MATCH STRATEGY BREAKDOWN ===")
    print(results['match_strategy'].value_counts())
    
    # Save sample results
    import os
    os.makedirs(PROJECT_ROOT / 'output', exist_ok=True)
    results.to_csv(PROJECT_ROOT / 'output' / 'sample_matches.csv', index=False)
    print(f"\nSample results saved to {PROJECT_ROOT / 'output' / 'sample_matches.csv'}")
