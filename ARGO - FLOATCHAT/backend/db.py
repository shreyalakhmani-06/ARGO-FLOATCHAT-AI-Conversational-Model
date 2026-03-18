import os
from sqlalchemy import create_engine, MetaData, Table, select, and_
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from typing import Dict, List, Any
from sqlalchemy import func


# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:root@localhost:5432/argo_db"
)
engine = create_engine(DATABASE_URL)
metadata = MetaData()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Tables
floats_metadata = Table("floats_metadata", metadata, autoload_with=engine)

# Base date for JULD (Argo convention: days since 1950-01-01)
BASE_JULD_DATE = datetime(1950, 1, 1)


def juld_to_datetime(juld):
    """Convert JULD field into datetime."""
    if juld is None:
        return None
    try:
        return BASE_JULD_DATE + timedelta(days=float(juld))
    except Exception:
        pass
    try:
        return datetime.fromisoformat(str(juld))
    except Exception:
        return None


def get_float_metadata(platform_number: str) -> Dict[str, Any]:
    """Retrieve metadata for a given float platform."""
    with engine.connect() as conn:
        query = select(floats_metadata).where(
            floats_metadata.c.platform_number == str(platform_number)
        )
        row = conn.execute(query).fetchone()
        return dict(row._mapping) if row else {}


def get_profile_measurements(platform_number: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch profile measurements for a given platform with optional filters."""
    with engine.connect() as conn:
        # Get metadata (profile table name for the float)
        meta_query = select(floats_metadata).where(
            floats_metadata.c.platform_number == str(platform_number)
        )
        meta_row = conn.execute(meta_query).fetchone()
        if not meta_row:
            return []

        profile_table_name = meta_row._mapping['profile_table']
        profile_table = Table(profile_table_name, metadata, autoload_with=engine)

        query = select(profile_table)
        conditions = []

        # ----------------- Filters -----------------
        # PRES / depth
        # Remove exact 'pres' filtering to let ArgoAgent pick closest
        if "min_pres" in filters:
            conditions.append(profile_table.c.PRES >= filters["min_pres"])
        if "max_pres" in filters:
            conditions.append(profile_table.c.PRES <= filters["max_pres"])

        # Temperature
        if "temp" in filters:
            conditions.append(profile_table.c.TEMP == filters["temp"])
        if "min_temp" in filters:
            conditions.append(profile_table.c.TEMP >= filters["min_temp"])
        if "max_temp" in filters:
            conditions.append(profile_table.c.TEMP <= filters["max_temp"])

        # Salinity
        if "psal" in filters:
            conditions.append(profile_table.c.PSAL == filters["psal"])
        if "min_psal" in filters:
            conditions.append(profile_table.c.PSAL >= filters["min_psal"])
        if "max_psal" in filters:
            conditions.append(profile_table.c.PSAL <= filters["max_psal"])

        # Latitude/Longitude
        if "min_lat" in filters:
            conditions.append(profile_table.c.LATITUDE >= filters["min_lat"])
        if "max_lat" in filters:
            conditions.append(profile_table.c.LATITUDE <= filters["max_lat"])
        if "min_lon" in filters:
            conditions.append(profile_table.c.LONGITUDE >= filters["min_lon"])
        if "max_lon" in filters:
            conditions.append(profile_table.c.LONGITUDE <= filters["max_lon"])

        # Date range
        if "start" in filters:
            start_date = juld_to_datetime(filters["start"])
            if start_date:
                conditions.append(profile_table.c.JULD >= start_date)
        if "end" in filters:
            end_date = juld_to_datetime(filters["end"])
            if end_date:
                conditions.append(profile_table.c.JULD <= end_date)

        if conditions:
            query = query.where(and_(*conditions))

        # ----------------- Fetch rows -----------------
        rows = conn.execute(query).fetchall()
        result = []
        for row in rows:
            r = dict(row._mapping)
            if "JULD" in r and isinstance(r["JULD"], datetime):
                r["JULD"] = r["JULD"].isoformat()
            result.append(r)

        return result
