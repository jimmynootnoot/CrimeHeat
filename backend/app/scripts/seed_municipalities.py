"""Load the filtered PPALMA boundary GeoJSON into the municipalities table.

Source of truth: data/boundaries/ppalma_municipalities.geojson, itself filtered
from the real PSGC-sourced province file (see README for provenance). Run with:

    python -m app.scripts.seed_municipalities

Names are canonicalized on read via app.core.taxonomy — the PSGC file spells
one municipality "Pigkawayan" while the study's display form is "Pigcawayan".
The sourced GeoJSON is deliberately left unedited so its provenance stays
verifiable and re-downloadable.
"""
from pathlib import Path

import geopandas as gpd
from geoalchemy2.shape import from_shape
from shapely.geometry import MultiPolygon, Polygon

from app.core.taxonomy import normalize_municipality
from app.db.session import SessionLocal
from app.models.municipality import Municipality

BOUNDARY_PATH = Path(__file__).resolve().parents[3] / "data" / "boundaries" / "ppalma_municipalities.geojson"


def to_multipolygon(geom):
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    return geom


def run() -> None:
    gdf = gpd.read_file(BOUNDARY_PATH)
    db = SessionLocal()
    try:
        for _, row in gdf.iterrows():
            psgc_code = str(row["adm3_psgc"])
            source_name = row["adm3_en"]
            name, standardized = normalize_municipality(source_name)
            if name is None:
                raise ValueError(
                    f"Boundary file contains municipality '{source_name}' which is not a "
                    f"recognized PPALMA municipality. Check data/boundaries/ppalma_municipalities.geojson."
                )
            if standardized:
                print(f"  standardized '{source_name}' -> '{name}'")
            geom = to_multipolygon(row.geometry)

            existing = db.query(Municipality).filter_by(psgc_code=psgc_code).first()
            if existing:
                existing.name = name
                existing.geom = from_shape(geom, srid=4326)
            else:
                db.add(
                    Municipality(
                        psgc_code=psgc_code,
                        name=name,
                        geom=from_shape(geom, srid=4326),
                    )
                )
        db.commit()
        count = db.query(Municipality).count()
        print(f"Seeded {count} municipalities.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
