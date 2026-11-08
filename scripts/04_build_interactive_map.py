"""Build figures/ri_charter_map.html: zoomable Leaflet map, hover tooltips per school.
Inputs: data/processed/ri_charter_schools_2024_enriched.csv, ri_noncharter_schools_2024_enriched.csv, ri_private_schools_2021.csv, data/raw/ri_cousub shapefile.
Requires: pandas, pyshp. The HTML loads Leaflet 1.9.4 from cdnjs (internet needed to view)."""
import json, pandas as pd, shapefile
df = pd.read_csv("data/processed/ri_charter_schools_2024_enriched.csv", dtype={"ncessch": str, "zip_location": str})
df["zip_location"] = df.zip_location.str.zfill(5)
def grade(g): return "PK" if g == -1 else "K" if g == 0 else str(int(g))
def build(df, kind):
    out = []
    nn = lambda v: None if pd.isna(v) else float(v)
    for r in df.itertuples():
        out.append(dict(kind=kind, name=r.school_name, lea=r.lea_name, addr=f"{r.street_location}, {str(r.city_location).title()} {r.zip_location}",
            lat=r.latitude, lon=r.longitude, grades=f"{grade(r.lowest_grade_offered)}-{grade(r.highest_grade_offered)}",
            enroll=int(r.enrollment), frl=nn(r.pct_free_reduced_lunch), spt=nn(r.students_per_teacher),
            pp=nn(r.per_pupil_current_spending_2020), ppi=nn(r.per_pupil_instruction_2020), pps=nn(r.per_pupil_state_rev_2020),
            ppl=nn(r.per_pupil_local_rev_2020), virtual=bool(r.virtual) if not pd.isna(r.virtual) else False))
    return out
schools = build(df, "charter")
dd = pd.read_csv("data/processed/ri_noncharter_schools_2024_enriched.csv", dtype={"ncessch": str, "zip_location": str})
dd["zip_location"] = dd.zip_location.str.zfill(5)
others = build(dd, "district")
pv = pd.read_csv("data/processed/ri_private_schools_2021.csv", dtype={"zip": str})
nz = lambda v: None if pd.isna(v) else v
privates = [dict(kind="private", name=r.school_name, addr=f"{r.street}, {r.city} {r.zip}", lat=r.latitude, lon=r.longitude,
                 enroll=int(r.enrollment), spt=nz(r.students_per_teacher), poc=nz(r.pct_students_of_color),
                 aff=nz(r.affiliation), level=nz(r.school_level)) for r in pv.itertuples()]
# Town polygons: Census cartographic boundary file (1:500k, clipped to shoreline).
towns = []
for sr in shapefile.Reader("data/raw/ri_cousub/cb_2022_44_cousub_500k.shp").shapeRecords():
    s_ = sr.shape; parts = list(s_.parts) + [len(s_.points)]
    rings = [[[round(x, 5), round(y, 5)] for x, y in s_.points[a:b]] for a, b in zip(parts[:-1], parts[1:])]
    towns.append({"type": "Feature", "properties": {"name": sr.record["NAME"]},
                  "geometry": {"type": "MultiPolygon", "coordinates": [[r] for r in rings]}})
geo = {"type": "FeatureCollection", "features": towns}
html = open("scripts/map_template.html").read().replace("__SCHOOLS__", json.dumps(schools, separators=(",", ":"))).replace("__OTHERS__", json.dumps(others, separators=(",", ":"))).replace("__PRIVATES__", json.dumps(privates, separators=(",", ":"))).replace("__TOWNS__", json.dumps(geo, separators=(",", ":")))
open("figures/ri_charter_map.html", "w").write(html)
print("wrote figures/ri_charter_map.html", len(html) // 1024, "KB")
