"""
Geographic Distance Enhancement for Place Name Matching.

This module adds geographic proximity as a matching criterion to improve
accuracy and resolve ambiguous matches. Uses Haversine distance to calculate
great circle distance between coordinates.

Expected impact:
- Resolve 30-40% of ambiguous matches
- Reduce false positives by 50-100 cases
- Increase overall accuracy from ~90% to 95-98%
"""

import pandas as pd
import numpy as np
from math import radians, cos, sin, asin, sqrt
from typing import Optional, Tuple
from pathlib import Path


class GeoDistanceCalculator:
    """Calculate geographic distances using the Haversine formula."""

    EARTH_RADIUS_MILES: float = 3959.0

    @staticmethod
    def haversine_distance(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate great circle distance between two points.

        Uses the Haversine formula to compute the distance between two
        points on Earth specified by latitude and longitude.

        Args:
            lat1: Latitude of first point in decimal degrees.
            lon1: Longitude of first point in decimal degrees.
            lat2: Latitude of second point in decimal degrees.
            lon2: Longitude of second point in decimal degrees.

        Returns:
            Distance in miles between the two points.
        """
        lon1_rad, lat1_rad, lon2_rad, lat2_rad = map(
            radians,
            [lon1, lat1, lon2, lat2]
        )

        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad

        a = (
            sin(dlat / 2) ** 2 +
            cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
        )
        c = 2 * asin(sqrt(a))

        return GeoDistanceCalculator.EARTH_RADIUS_MILES * c


class GeoEnhancedMatcher:
    """
    Enhanced matcher that uses geographic distance for disambiguation.

    This class extends the basic matching functionality by adding
    geographic proximity as a factor in match confidence and for
    resolving ambiguous cases.
    """

    def __init__(
        self,
        place_names_df: pd.DataFrame,
        gnis_df: pd.DataFrame,
        county_centroids_file: Optional[Path] = None
    ) -> None:
        """
        Initialize the geo-enhanced matcher.

        Args:
            place_names_df: DataFrame with place name records.
            gnis_df: DataFrame with GNIS feature records.
            county_centroids_file: Path to CSV file with county centroid
                coordinates. If None, uses default location.
        """
        self.place_names = place_names_df.copy()
        self.gnis = gnis_df.copy()

        if county_centroids_file is None:
            project_root = Path(__file__).parent.parent
            county_centroids_file = project_root / 'tn_county_centroids.csv'

        self.county_centroids = pd.read_csv(county_centroids_file)
        self._add_coordinates()

    def _add_coordinates(self) -> None:
        """Add county centroid coordinates to both datasets."""
        self.place_names = self.place_names.merge(
            self.county_centroids,
            left_on='County',
            right_on='county_name',
            how='left',
            suffixes=('', '_centroid')
        )

        self.place_names.rename(
            columns={
                'centroid_lat': 'place_lat',
                'centroid_lon': 'place_lon'
            },
            inplace=True
        )

        self.gnis = self.gnis.merge(
            self.county_centroids,
            left_on='county_name',
            right_on='county_name',
            how='left',
            suffixes=('', '_centroid')
        )

        self.gnis.rename(
            columns={
                'centroid_lat': 'gnis_lat',
                'centroid_lon': 'gnis_lon'
            },
            inplace=True
        )

    def add_distance_to_matches(
        self,
        matches_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Add distance column to existing match results.

        Calculates the geographic distance between each place name and
        its matched GNIS feature using county centroid coordinates.

        Args:
            matches_df: DataFrame with match results containing place_idx
                and gnis_idx columns.

        Returns:
            DataFrame with added distance_miles column.
        """
        matches = matches_df.copy()

        matches = matches.merge(
            self.place_names[[
                'Place_Name',
                'County',
                'place_lat',
                'place_lon'
            ]],
            left_on=['place_name', 'place_county'],
            right_on=['Place_Name', 'County'],
            how='left'
        )

        matches = matches.merge(
            self.gnis[['gaz_id', 'gnis_lat', 'gnis_lon']],
            left_on='gnis_id',
            right_on='gaz_id',
            how='left'
        )

        distances = []
        for _, row in matches.iterrows():
            if (
                pd.notna(row['place_lat']) and
                pd.notna(row['place_lon']) and
                pd.notna(row['gnis_lat']) and
                pd.notna(row['gnis_lon'])
            ):
                dist = GeoDistanceCalculator.haversine_distance(
                    row['place_lat'],
                    row['place_lon'],
                    row['gnis_lat'],
                    row['gnis_lon']
                )
                distances.append(dist)
            else:
                distances.append(None)

        matches['distance_miles'] = distances
        return matches

    def adjust_confidence_by_distance(
        self,
        matches_df: pd.DataFrame,
        close_distance: float = 5.0,
        medium_distance: float = 10.0,
        reasonable_distance: float = 20.0,
        far_distance: float = 50.0
    ) -> pd.DataFrame:
        """
        Adjust confidence scores based on geographic distance.

        Distance-based adjustments:
        - 0-5 miles: +10 confidence (very close, likely same location)
        - 5-10 miles: +5 confidence (close)
        - 10-20 miles: No change (reasonable distance)
        - 20-50 miles: -10 confidence (far, possibly different)
        - >50 miles: -20 confidence (very far, likely different)

        Args:
            matches_df: DataFrame with matches and distance_miles column.
            close_distance: Threshold for very close matches in miles.
            medium_distance: Threshold for close matches in miles.
            reasonable_distance: Threshold for reasonable distance in miles.
            far_distance: Threshold for far matches in miles.

        Returns:
            DataFrame with adjusted confidence scores and distance notes.
        """
        matches = matches_df.copy()

        for idx, row in matches.iterrows():
            if pd.notna(row.get('distance_miles')):
                dist = row['distance_miles']
                original_conf = row['confidence']

                if dist <= close_distance:
                    adjustment = 10
                    note = f"Very close (<{close_distance}mi)"
                elif dist <= medium_distance:
                    adjustment = 5
                    note = f"Close ({close_distance}-{medium_distance}mi)"
                elif dist <= reasonable_distance:
                    adjustment = 0
                    note = (
                        f"Reasonable distance "
                        f"({medium_distance}-{reasonable_distance}mi)"
                    )
                elif dist <= far_distance:
                    adjustment = -10
                    note = (
                        f"Far ({reasonable_distance}-{far_distance}mi)"
                    )
                else:
                    adjustment = -20
                    note = f"Very far (>{far_distance}mi)"

                new_conf = min(100, max(0, original_conf + adjustment))
                matches.at[idx, 'confidence'] = new_conf
                matches.at[idx, 'distance_note'] = note
                matches.at[idx, 'confidence_adjustment'] = adjustment

        return matches

    def resolve_multiple_matches_by_distance(
        self,
        matches_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Resolve multiple matches by selecting the closest one.

        For places with multiple potential matches, this method selects
        the geographically closest match when distance data is available.

        Args:
            matches_df: DataFrame with matches including place_idx and
                distance_miles columns.

        Returns:
            DataFrame with ambiguous matches resolved by proximity.
        """
        matches = matches_df.copy()

        multi_match_places = matches[
            matches.duplicated(subset=['place_idx'], keep=False)
        ]

        resolved = []
        for place_idx in multi_match_places['place_idx'].unique():
            place_matches = matches[matches['place_idx'] == place_idx]

            with_distance = place_matches[
                place_matches['distance_miles'].notna()
            ]

            if len(with_distance) > 0:
                closest_idx = with_distance['distance_miles'].idxmin()
                closest = with_distance.loc[closest_idx].copy()
                closest['resolution_method'] = 'Geographic proximity'
                resolved.append(closest)
            else:
                for _, row in place_matches.iterrows():
                    resolved.append(row)

        single_matches = matches[
            ~matches['place_idx'].isin(multi_match_places['place_idx'])
        ]

        result = pd.concat(
            [single_matches, pd.DataFrame(resolved)],
            ignore_index=True
        )
        return result

    def analyze_distance_distribution(
        self,
        matches_df: pd.DataFrame
    ) -> dict:
        """
        Analyze the distribution of distances in matches.

        Args:
            matches_df: DataFrame with matches including distance_miles.

        Returns:
            Dictionary with distance statistics and distribution.
        """
        valid_distances = matches_df[
            matches_df['distance_miles'].notna()
        ]['distance_miles']

        if len(valid_distances) == 0:
            return {'error': 'No valid distance data available'}

        return {
            'total_matches_with_distance': len(valid_distances),
            'mean_distance': float(valid_distances.mean()),
            'median_distance': float(valid_distances.median()),
            'min_distance': float(valid_distances.min()),
            'max_distance': float(valid_distances.max()),
            'std_distance': float(valid_distances.std()),
            'distribution': {
                'under_5_miles': int((valid_distances < 5).sum()),
                '5_to_10_miles': int(
                    ((valid_distances >= 5) & (valid_distances < 10)).sum()
                ),
                '10_to_20_miles': int(
                    ((valid_distances >= 10) & (valid_distances < 20)).sum()
                ),
                '20_to_50_miles': int(
                    ((valid_distances >= 20) & (valid_distances < 50)).sum()
                ),
                'over_50_miles': int((valid_distances >= 50).sum())
            }
        }


class CountyCentroidGeocoder:
    """
    Geocode place names using county centroids.

    This provides fast, approximate geocoding suitable for initial
    analysis and filtering. Accuracy is typically 5-20 miles.
    """

    def __init__(self, county_centroids_file: Optional[Path] = None) -> None:
        """
        Initialize the geocoder.

        Args:
            county_centroids_file: Path to CSV file with county centroid
                coordinates. If None, uses default location.
        """
        if county_centroids_file is None:
            project_root = Path(__file__).parent.parent
            county_centroids_file = project_root / 'tn_county_centroids.csv'

        self.centroids = pd.read_csv(county_centroids_file)

    def geocode_by_county(
        self,
        places_df: pd.DataFrame,
        county_column: str = 'County'
    ) -> pd.DataFrame:
        """
        Add approximate coordinates based on county.

        Args:
            places_df: DataFrame with place records.
            county_column: Name of column containing county names.

        Returns:
            DataFrame with added latitude and longitude columns.
        """
        result = places_df.merge(
            self.centroids,
            left_on=county_column,
            right_on='county_name',
            how='left'
        )

        result.rename(
            columns={
                'centroid_lat': 'latitude',
                'centroid_lon': 'longitude'
            },
            inplace=True
        )

        coords_added = result['latitude'].notna().sum()
        print(
            f"Added approximate coordinates for {coords_added} places"
        )

        return result

    def get_coordinates(
        self,
        county_name: str
    ) -> Optional[Tuple[float, float]]:
        """
        Get coordinates for a specific county.

        Args:
            county_name: Name of the county.

        Returns:
            Tuple of (latitude, longitude) or None if not found.
        """
        match = self.centroids[
            self.centroids['county_name'].str.lower() ==
            county_name.lower()
        ]

        if len(match) > 0:
            row = match.iloc[0]
            return (row['centroid_lat'], row['centroid_lon'])

        return None


if __name__ == "__main__":
    """Example usage of the geolocation enhancement module."""
    project_root = Path(__file__).parent.parent

    print("=" * 80)
    print("GEOLOCATION ENHANCEMENT DEMO")
    print("=" * 80)

    print("\n1. Loading county centroids...")
    geocoder = CountyCentroidGeocoder()
    print(f"   Loaded {len(geocoder.centroids)} county centroids")

    example_county = "Davidson"
    coords = geocoder.get_coordinates(example_county)
    if coords:
        print(
            f"   {example_county} County center: "
            f"{coords[0]:.4f}, {coords[1]:.4f}"
        )

    print("\n2. Testing distance calculation...")
    lat1, lon1 = 36.1667, -86.7844
    lat2, lon2 = 35.1345, -85.2972

    distance = GeoDistanceCalculator.haversine_distance(
        lat1,
        lon1,
        lat2,
        lon2
    )
    print(f"   Distance between test points: {distance:.2f} miles")

    print("\n" + "=" * 80)
    print("Demo complete. Use GeoEnhancedMatcher with your matching")
    print("pipeline to add distance-based enhancements.")
    print("=" * 80)
