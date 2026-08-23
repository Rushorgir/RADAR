from __future__ import annotations

import pandas as pd
import numpy as np
import os

DEFAULT_SATCAT_PATH = os.getenv(
    "SATCAT_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "satcat.csv")),
)

class SatcatEnricher:
    def __init__(self, satcat_path: str | None = None):
        self.satcat_path = satcat_path or DEFAULT_SATCAT_PATH
        self.satcat_df = None

    def load(self):
        """
        Loads the SATCAT dataset and derives orbital regimes.
        """
        if not os.path.exists(self.satcat_path):
            print(f"INFO: SATCAT file not found at {self.satcat_path}, using default mappings.")
            self.satcat_df = pd.DataFrame(columns=['NORAD_CAT_ID', 'orbital_regime', 'APOGEE', 'PERIGEE', 'INCLINATION'])
            return
            
        self.satcat_df = pd.read_csv(self.satcat_path)
        
        # Validate uniqueness of NORAD_CAT_ID
        total_rows = len(self.satcat_df)
        unique_norad = self.satcat_df['NORAD_CAT_ID'].nunique()
        if total_rows != unique_norad:
            print(f"WARNING: Found {total_rows - unique_norad} duplicate NORAD_CAT_ID entries. Dropping duplicates.")
        
        # Drop duplicates based on NORAD_CAT_ID safely
        self.satcat_df = self.satcat_df.drop_duplicates(subset=['NORAD_CAT_ID']).copy()
        
        # Normalize identifiers
        self.satcat_df['NORAD_CAT_ID'] = pd.to_numeric(self.satcat_df['NORAD_CAT_ID'], errors='coerce')
        
        self.satcat_df['orbital_regime'] = self.satcat_df.apply(self._derive_regime, axis=1)

    def _derive_regime(self, row) -> str:
        """
        Derives the orbital regime using physical rules in deterministic order.
        1. LEO: APOGEE <= 2000
        2. HEO: eccentricity > 0.25 AND APOGEE > 30000
        3. GEO: 35000 < mean_altitude < 37000 AND INCLINATION < 25
        4. MEO: 2000 < mean_altitude <= 35000
        5. UNKNOWN: insufficient or invalid data
        """
        apogee = row.get('APOGEE')
        perigee = row.get('PERIGEE')
        inc = row.get('INCLINATION')
        
        if pd.isna(apogee) or pd.isna(perigee):
            return 'UNKNOWN'
            
        mean_altitude = (apogee + perigee) / 2.0
        # Earth radius = 6378.137 km
        sma = (apogee + perigee) / 2.0 + 6378.137
        if sma <= 0:
            return 'UNKNOWN'
            
        eccentricity = (apogee - perigee) / (apogee + perigee + 2 * 6378.137)
        
        # 1. LEO
        if apogee <= 2000:
            return 'LEO'
        
        # 2. HEO
        if eccentricity > 0.25 and apogee > 30000:
            return 'HEO'
            
        # 3. GEO
        # If inclination is missing, we cannot verify GEO strictly, but usually it's < 25
        if 35000 < mean_altitude < 37000:
            if not pd.isna(inc) and inc < 25:
                return 'GEO'
                
        # 4. MEO
        if 2000 < mean_altitude <= 35000:
            return 'MEO'
            
        # 5. UNKNOWN
        return 'UNKNOWN'

    def enrich_training_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Joins SATCAT data to the training dataset.
        Primary object is identified by `mission_id` == `NORAD_CAT_ID`.
        Secondary object ID is unavailable, so secondary features remain NaN.
        """
        if self.satcat_df is None:
            self.load()
            
        satcat_df = (
            self.satcat_df[['NORAD_CAT_ID', 'orbital_regime']]
            if self.satcat_df is not None
            else pd.DataFrame(columns=['NORAD_CAT_ID', 'orbital_regime'])
        )
            
        # Join primary object
        df['mission_id_numeric'] = pd.to_numeric(df['mission_id'], errors='coerce')
        
        merged = df.merge(
            satcat_df,
            left_on='mission_id_numeric',
            right_on='NORAD_CAT_ID',
            how='left'
        )
        
        from src.ml.features.extractor import ORBITAL_REGIME_MAPPING
        df['orbital_regime_encoded'] = merged['orbital_regime'].map(ORBITAL_REGIME_MAPPING).fillna(4).astype(int)
        
        # explicitly populate physical cross sectional area features as np.nan
        df['primary_cross_section_area_m2'] = np.nan
        df['secondary_cross_section_area_m2'] = np.nan
        df['combined_cross_section_area_m2'] = np.nan
        df['log_combined_cross_section_area'] = np.nan
        
        # Drop temporary column
        df = df.drop(columns=['mission_id_numeric'])
        
        return df
