import re
from typing import Dict, Any, List

class ArgoQueryParser:
    def __init__(self):
        # Parameter mapping
        self.parameter_mappings = {
            'temperature': 'TEMP', 'temp': 'TEMP',
            'pressure': 'PRES', 'depth': 'PRES', 'pres': 'PRES',
            'salinity': 'PSAL', 'psal': 'PSAL',
            'latitude': 'LATITUDE', 'lat': 'LATITUDE',
            'longitude': 'LONGITUDE', 'lon': 'LONGITUDE',
            'time': 'JULD', 'date': 'JULD', 'juld': 'JULD'
        }

    def detect_parameters(self, query: str) -> List[str]:
        ql = query.lower()
        return list({p for k, p in self.parameter_mappings.items() if k in ql})

    def extract_conditions(self, query: str, params: List[str]) -> Dict[str, Any]:
        ql = query.lower()
        filters = {}

        # 'at depth X' or 'pressure X'
        depth_match = re.search(r'(?:depth|pressure|pres)\s*(?:of)?\s*(-?\d+\.?\d*)', ql)
        if depth_match:
            filters['pres'] = float(depth_match.group(1))

        # Temperature / Salinity conditions
        temp_match = re.search(r'(?:temperature|temp)\s*(?:above|over|greater than)\s*(-?\d+\.?\d*)', ql)
        if temp_match:
            filters['min_temp'] = float(temp_match.group(1))
        temp_match2 = re.search(r'(?:temperature|temp)\s*(?:below|under|less than)\s*(-?\d+\.?\d*)', ql)
        if temp_match2:
            filters['max_temp'] = float(temp_match2.group(1))

        psal_match = re.search(r'(?:salinity|psal)\s*(?:above|over|greater than)\s*(-?\d+\.?\d*)', ql)
        if psal_match:
            filters['min_psal'] = float(psal_match.group(1))
        psal_match2 = re.search(r'(?:salinity|psal)\s*(?:below|under|less than)\s*(-?\d+\.?\d*)', ql)
        if psal_match2:
            filters['max_psal'] = float(psal_match2.group(1))

        # Latitude / Longitude conditions
        lat_match = re.search(r'lat(?:itude)?\s*(?:>=|>|above|north of)\s*(-?\d+\.?\d*)', ql)
        if lat_match:
            filters['min_lat'] = float(lat_match.group(1))
        lat_match2 = re.search(r'lat(?:itude)?\s*(?:<=|<|below|south of)\s*(-?\d+\.?\d*)', ql)
        if lat_match2:
            filters['max_lat'] = float(lat_match2.group(1))

        lon_match = re.search(r'lon(?:gitude)?\s*(?:>=|>|east of)\s*(-?\d+\.?\d*)', ql)
        if lon_match:
            filters['min_lon'] = float(lon_match.group(1))
        lon_match2 = re.search(r'lon(?:gitude)?\s*(?:<=|<|west of)\s*(-?\d+\.?\d*)', ql)
        if lon_match2:
            filters['max_lon'] = float(lon_match2.group(1))

        return filters

    def determine_visualization_type(self, query: str, filters: Dict[str, Any]) -> List[str]:
        ql = query.lower()
        viz_types = []

        if "temp vs depth" in ql or "temperature vs depth" in ql:
            viz_types.append("temp_vs_depth")
        if "salinity vs depth" in ql or "psal vs depth" in ql:
            viz_types.append("salinity_vs_depth")
        if ("temp vs salinity" in ql or "temperature vs salinity" in ql or
            "salinity vs temp" in ql):
            viz_types.append("temp_vs_salinity")
        if "time series" in ql or "over time" in ql:
            viz_types.append("time_series")
        if "scatter" in ql or "vs" in ql:
            viz_types.append("scatter")

        return viz_types

_PARSER = ArgoQueryParser()

def parse_query_to_filters(platform_number: str, user_query: str) -> Dict[str, Any]:
    parser = _PARSER
    params = parser.detect_parameters(user_query)
    filters = parser.extract_conditions(user_query, params)
    viz_types = parser.determine_visualization_type(user_query, filters)

    filters['_detected_parameters'] = params
    filters['_visualization_type'] = viz_types

    # Detect platform number
    match = re.search(r"\b\d{7}\b", user_query)
    if match:
        filters['platform_number'] = match.group(0)
    else:
        filters['platform_number'] = platform_number

    return filters
