"""Build one reference list of Rhode Island schools (charter / traditional public / private)
and run consistency checks against the raw downloads.
Outputs: data/processed/ri_school_master_list.csv, data/processed/ri_school_master_excluded.csv
Public + charter: CCD 2024 directory (data/raw/urban_ccd_ri_all_schools_2024.json).
Private: NCES PSS 2021-22 (data/processed/ri_private_schools_2021.csv, built by 05)."""
import json, pandas as pd
LEVEL = {1: "Primary", 2: "Middle", 3: "High", 4: "Other"}
raw = pd.DataFrame(json.load(open("data/raw/urban_ccd_ri_all_schools_2024.json"))["results"])
raw["ncessch"] = raw.ncessch.astype(str)
raw["sector"] = raw.charter.map({1: "Charter", 0: "Traditional public"})
keep = raw[raw.enrollment.notna() & (raw.enrollment > 0) & raw.school_status.isin([1, 3])]
pub = pd.DataFrame({
    "sector": keep.sector, "school_id": keep.ncessch, "school_name": keep.school_name,
    "district_or_lea": keep.lea_name, "city": keep.city_location, "zip": keep.zip_location.astype(str).str.zfill(5),
    "latitude": keep.latitude, "longitude": keep.longitude, "school_level": keep.school_level.map(LEVEL),
    "lowest_grade": keep.lowest_grade_offered, "highest_grade": keep.highest_grade_offered,
    "enrollment": keep.enrollment, "teachers_fte": keep.teachers_fte,
    "pct_free_reduced_lunch": (100 * keep.free_or_reduced_price_lunch / keep.enrollment).round(1),
    "status": keep.school_status.map({1: "Open", 3: "New"}), "source": "CCD 2024",
})
priv = pd.read_csv("data/processed/ri_private_schools_2021.csv", dtype={"zip": str})
priv = pd.DataFrame({
    "sector": "Private", "school_id": ["PSS_%03d" % i for i in range(1, len(priv) + 1)],
    "school_name": priv.school_name, "district_or_lea": priv.affiliation, "city": priv.city, "zip": priv.zip,
    "latitude": priv.latitude, "longitude": priv.longitude, "school_level": priv.school_level,
    "enrollment": priv.enrollment, "teachers_fte": priv.teachers_fte, "status": "Open", "source": "PSS 2021-22"})
m = pd.concat([pub, priv], ignore_index=True).sort_values(["sector", "city", "school_name"])
m.to_csv("data/processed/ri_school_master_list.csv", index=False)
ex = raw[~raw.ncessch.isin(keep.ncessch)][["ncessch", "school_name", "lea_name", "charter", "school_status", "enrollment"]]
ex.to_csv("data/processed/ri_school_master_excluded.csv", index=False)
print(m.groupby("sector").agg(schools=("school_id", "size"), students=("enrollment", "sum")))
