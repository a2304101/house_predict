import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
#POI_CSV = r"F:/桃竹苗/final/m/taiwan_comprehensive_pois.csv"
POI_CSV = BASE_DIR / "m" / "taiwan_comprehensive_pois.csv"
#STATION_PICKLE = r"F:/桃竹苗/final/m/taiwan_stations_t2.pkl"
STATION_PICKLE = BASE_DIR / "m" / "taiwan_stations_t2.pkl"
RADIUS_500M = 0.0045
RADIUS_300M = 0.0027
DEGREE_TO_METER = 110000


class GeoFeatureService:
    def __init__(self):
        poi_df = pd.read_csv(POI_CSV)
        station_df = pd.read_pickle(STATION_PICKLE)

        self.conv_tree = self._tree(poi_df, ["shop_convenience"])
        self.bank_tree = self._tree(poi_df, ["amenity_bank"])
        self.food_tree = self._tree(poi_df, [
            "amenity_restaurant",
            "amenity_cafe",
            "amenity_fast_food",
            "amenity_food_court",
        ])
        self.med_tree = self._tree(poi_df, [
            "amenity_clinic",
            "amenity_hospital",
            "amenity_pharmacy",
        ])
        self.worship_tree = self._tree(poi_df, ["amenity_place_of_worship"])
        self.parking_tree = self._tree(poi_df, ["amenity_parking"])

        self.thsr_tree = self._station_tree(station_df, "THSR_station")
        self.tra_tree = self._station_tree(station_df, "TRA_station")
        self.mrt_tree = self._station_tree(station_df, "MRT_station")

    def _tree(self, poi_df, types):
        df = poi_df[poi_df["poi_type"].isin(types)]
        if df.empty:
            return None
        return KDTree(df[["lat", "lon"]].to_numpy())

    def _station_tree(self, station_df, station_type):
        df = station_df[station_df["station_type"] == station_type]
        if df.empty:
            return None
        return KDTree(df[["lat", "lon"]].to_numpy())

    def _count(self, tree, coord, radius):
        if tree is None:
            return 0
        return len(tree.query_ball_point(coord, r=radius))

    def _distance(self, tree, coord, default_value):
        if tree is None:
            return default_value
        dist, _ = tree.query(coord, k=1)
        return int(round(dist * DEGREE_TO_METER))

    def build_features(self, lat, lon):
        coord = np.array([lat, lon])

        return {
            "poi_convenience_count_300m": self._count(self.conv_tree, coord, RADIUS_300M),
            "poi_convenience_count_500m": self._count(self.conv_tree, coord, RADIUS_500M),
            "poi_bank_count_500m": self._count(self.bank_tree, coord, RADIUS_500M),
            "poi_food_count_300m": self._count(self.food_tree, coord, RADIUS_300M),
            "poi_food_count_500m": self._count(self.food_tree, coord, RADIUS_500M),
            "poi_medical_count_500m": self._count(self.med_tree, coord, RADIUS_500M),
            "poi_parking_count_500m": self._count(self.parking_tree, coord, RADIUS_500M),

            "distance_to_nearest_worship_m": self._distance(self.worship_tree, coord, 99999),
            "distance_to_thsr_m": self._distance(self.thsr_tree, coord, 99999),
            "distance_to_tra_m": self._distance(self.tra_tree, coord, 99999),
            "distance_to_mrt_m": min(self._distance(self.mrt_tree, coord, 5000), 5000),
        }


GEO_SERVICE = GeoFeatureService()
