import pandas as pd
import numpy as np
from collections import Counter
import re
from typing import List, Any

# Load datasets
print("Loading datasets...")
place_names: pd.DataFrame = pd.read_csv('/mnt/user-data/uploads/PlaceNames.csv')
gnis: pd.DataFrame = pd.read_csv('/mnt/user-data/uploads/GNIS_250319.csv')

print(f"\n=== DATASET OVERVIEW ===")
print(f"PlaceNames records: {len(place_names)}")
print(f"GNIS records: {len(gnis)}")

print(f"\n=== PLACENAMES STRUCTURE ===")
print(place_names.head(3))
print(f"\nColumns: {list(place_names.columns)}")
print(f"\nData types:\n{place_names.dtypes}")

print(f"\n=== GNIS STRUCTURE ===")
print(gnis.head(3))
print(f"\nColumns: {list(gnis.columns)}")
print(f"\nData types:\n{gnis.dtypes}")

# Check existing matches
print(f"\n=== EXISTING MATCHING STATUS ===")
print(f"PlaceNames with Match='Yes': {(place_names['Match'] == 'Yes').sum()}")
print(f"PlaceNames with Match='No': {(place_names['Match'] == 'No').sum()}")
print(f"PlaceNames with JoinID: {place_names['JoinID'].notna().sum()}")

# Analyze county information
print(f"\n=== COUNTY ANALYSIS ===")
place_counties: pd.Series = place_names['County'].value_counts().head(10)
gnis_counties: pd.Series = gnis['county_name'].value_counts().head(10)
print(f"\nTop 10 PlaceNames counties:\n{place_counties}")
print(f"\nTop 10 GNIS counties:\n{gnis_counties}")

# Analyze feature classes in GNIS
print(f"\n=== GNIS FEATURE CLASSES ===")
feature_classes: pd.Series = gnis['gaz_featureclass'].value_counts().head(20)
print(feature_classes)

# Check for (historical) markers
print(f"\n=== HISTORICAL MARKERS ===")
gnis_historical: int = gnis['gaz_name'].str.contains(r'\(historical\)', case=False, na=False).sum()
print(f"GNIS names with '(historical)': {gnis_historical}")

# Analyze name patterns
print(f"\n=== NAME PATTERN ANALYSIS ===")

# Extract base names (without historical marker)
def extract_base_name(name: Any) -> str:
    if pd.isna(name):
        return ''
    # Remove (historical) and similar markers
    clean_name: str = re.sub(r'\s*\([^)]*\)\s*', ' ', str(name))
    return clean_name.strip()

place_names['base_name'] = place_names['Place_Name'].apply(extract_base_name)
gnis['base_name'] = gnis['gaz_name'].apply(extract_base_name)

# Check for common suffixes/prefixes
def get_suffixes(names: pd.Series) -> List[tuple[str, int]]:
    """Extract common suffixes from place names"""
    suffixes: List[str] = []
    for name in names.dropna():
        words: List[str] = str(name).split()
        if len(words) > 1:
            suffixes.append(words[-1])
    return Counter(suffixes).most_common(20)

print("\nCommon suffixes in PlaceNames:")
place_suffixes: List[tuple[str, int]] = get_suffixes(place_names['Place_Name'])
for suffix, count in place_suffixes:
    print(f"  {suffix}: {count}")

print("\nCommon suffixes in GNIS:")
gnis_suffixes: List[tuple[str, int]] = get_suffixes(gnis['gaz_name'])
for suffix, count in gnis_suffixes:
    print(f"  {suffix}: {count}")

# Check for exact matches on base_name + county
print(f"\n=== POTENTIAL EXACT MATCHES ===")
exact_matches: int = 0
for idx, row in place_names.head(100).iterrows():
    if pd.notna(row['base_name']) and pd.notna(row['County']):
        match: pd.DataFrame = gnis[
            (gnis['base_name'].str.lower() == row['base_name'].lower()) &
            (gnis['county_name'].str.lower() == row['County'].lower())
        ]
        if len(match) > 0:
            exact_matches += 1

print(f"Exact matches found in first 100 PlaceNames: {exact_matches}")

# Analyze unmatched PlaceNames
unmatched: pd.DataFrame = place_names[place_names['Match'] == 'No']
print(f"\n=== UNMATCHED PLACENAMES SAMPLE ===")
print(unmatched[['Place_Name', 'County', 'PO_Start', 'PO_End']].head(20))

# Check for naming variations
print(f"\n=== NAMING VARIATION EXAMPLES ===")
# Look for cases where similar names exist
sample_names: List[str] = ['Aaron', 'Abbott', 'Abiff', 'Abernathy']
for name in sample_names:
    print(f"\n'{name}' variations in GNIS:")
    matches: pd.Series = gnis[gnis['gaz_name'].str.contains(name, case=False, na=False)]['gaz_name'].head(5)
    if len(matches) > 0:
        print(matches.tolist())
    else:
        print("  No matches found")

print(f"\n=== SUMMARY STATISTICS ===")
print(f"PlaceNames unique place names: {place_names['Place_Name'].nunique()}")
print(f"GNIS unique place names: {gnis['gaz_name'].nunique()}")
print(f"PlaceNames with empty names: {place_names['Place_Name'].isna().sum()}")
print(f"GNIS with empty names: {gnis['gaz_name'].isna().sum()}")
print(f"PlaceNames with empty county: {place_names['County'].isna().sum()}")
print(f"GNIS with empty county: {gnis['county_name'].isna().sum()}")
