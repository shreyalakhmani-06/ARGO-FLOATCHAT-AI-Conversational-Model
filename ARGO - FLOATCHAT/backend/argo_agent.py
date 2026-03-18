import pandas as pd
import plotly.express as px
from datetime import datetime
from typing import Dict, Any, List
from db import get_profile_measurements, juld_to_datetime
from nlp_to_sql import parse_query_to_filters

class ArgoDataVisualizer:
    def prepare_data(self, data: List[Dict], filters: Dict[str, Any]) -> pd.DataFrame:
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        if "JULD" in df.columns:
            df["datetime"] = df["JULD"].apply(lambda x: juld_to_datetime(x) if pd.notnull(x) else pd.NaT)
        return df

    def create_depth_profile(self, df: pd.DataFrame, filters: Dict[str, Any], param: str) -> dict:
        if df.empty or "PRES" not in df.columns or param not in df.columns:
            return {"error": f"No data for {param} vs depth"}
        valid_data = df.dropna(subset=[param, "PRES"])
        fig = px.line(valid_data, x=param, y="PRES", title=f"{param} vs Depth")
        fig.update_yaxes(autorange="reversed", title_text="Pressure (dbar)")
        return {"type": "plotly", "figure": fig.to_dict()}

    def create_scatter_plot(self, df: pd.DataFrame, x_param: str, y_param: str) -> dict:
        if df.empty or x_param not in df.columns or y_param not in df.columns:
            return {"error": f"No data for {y_param} vs {x_param}"}
        valid_data = df.dropna(subset=[x_param, y_param])
        fig = px.scatter(valid_data, x=x_param, y=y_param,
                         color="PRES" if "PRES" in df.columns else None,
                         title=f"{y_param} vs {x_param}", color_continuous_scale="viridis")
        return {"type": "plotly", "figure": fig.to_dict()}

    def generate_visualizations(self, data: List[Dict], filters: Dict[str, Any]) -> dict:
        df = self.prepare_data(data, filters)
        visualizations = {}
        for viz_type in filters.get("_visualization_type", []):
            if viz_type == "temp_vs_depth":
                visualizations[viz_type] = self.create_depth_profile(df, filters, "TEMP")
            elif viz_type == "salinity_vs_depth":
                visualizations[viz_type] = self.create_depth_profile(df, filters, "PSAL")
            elif viz_type == "temp_vs_salinity":
                visualizations[viz_type] = self.create_scatter_plot(df, "TEMP", "PSAL")
        # Remove plots with errors
        visualizations = {k: v for k, v in visualizations.items() if "error" not in v}
        return visualizations

class ArgoAgenticAI:
    def __init__(self):
        self.visualizer = ArgoDataVisualizer()
        self.conversation_history = []

    def process_query(self, platform_number: str, user_query: str) -> Dict[str, Any]:
        self.conversation_history.append({"time": datetime.now(), "platform": platform_number, "query": user_query})

        try:
            filters = parse_query_to_filters(platform_number, user_query)
            platform_number = filters.get("platform_number") or platform_number
            data = get_profile_measurements(platform_number, filters)

            visualizations = self.visualizer.generate_visualizations(data, filters)

            response = {"success": True, "platform_number": platform_number, "count": len(data)}

            if visualizations:
                # Return single visualization for backward compatibility
                if len(visualizations) == 1:
                    response["visualization"] = list(visualizations.values())[0]
                else:
                    response["visualizations"] = visualizations
            else:
                # Handle closest-depth queries if no visualization
                if 'pres' in filters and any(p in filters.get("_detected_parameters", []) for p in ["TEMP", "PSAL"]):
                    requested_depth = filters['pres']
                    if data:
                        closest_row = min(
                            [row for row in data if row.get("PRES") is not None],
                            key=lambda x: abs(x.get("PRES", float('inf')) - requested_depth),
                            default=None
                        )
                        if closest_row:
                            result_values = {p: closest_row.get(p) for p in filters["_detected_parameters"] if p in closest_row}
                            return {
                                "success": True,
                                "platform_number": platform_number,
                                "requested_depth": requested_depth,
                                "closest_depth": closest_row.get("PRES"),
                                "values": result_values
                            }
                    return {
                        "success": False,
                        "platform_number": platform_number,
                        "message": f"No data available for float {platform_number} at depth {requested_depth}."
                    }
                response["message"] = "No visualization could be generated."

            return response

        except Exception as e:
            return {"success": False, "message": str(e)}
