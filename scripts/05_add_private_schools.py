"""Extract Rhode Island private schools from the NCES Private School Universe Survey (PSS) 2021-22
public-use file (data/raw/pss/pss2122_pu.csv, from https://nces.ed.gov/surveys/pss/zip/pss2122_pu_csv.zip)."""
import os, urllib.request, zipfile, pandas as pd
if not os.path.exists("data/raw/pss/pss2122_pu.csv"):
    os.makedirs("data/raw/pss", exist_ok=True)
    urllib.request.urlretrieve("https://nces.ed.gov/surveys/pss/zip/pss2122_pu_csv.zip", "data/raw/pss/pss2122_pu_csv.zip")
    zipfile.ZipFile("data/raw/pss/pss2122_pu_csv.zip").extractall("data/raw/pss")
d = pd.read_csv("data/raw/pss/pss2122_pu.csv", encoding="latin1", low_memory=False)
r = d[d.PSTABB == "RI"].copy()
out = pd.DataFrame({
    "school_name": r.PINST.str.title(), "street": r.PADDRS.str.title(), "city": r.PCITY.str.title(),
    "zip": r.PZIP.astype(int).astype(str).str.zfill(5), "latitude": r.LATITUDE22, "longitude": r.LONGITUDE22,
    "enrollment": r.NUMSTUDS, "teachers_fte": r.NUMTEACH,
    "students_per_teacher": (r.NUMSTUDS / r.NUMTEACH).round(1),
    "pct_students_of_color": (100 - r.P_WHITE).round(1),
    "affiliation": r.RELIG.map({1: "Catholic", 2: "Other religious", 3: "Nonsectarian"}),
    "school_level": r.LEVEL.map({1: "Elementary", 2: "Secondary", 3: "Combined"}),
})
out = out[out.enrollment > 0].sort_values(["city", "school_name"])
out.to_csv("data/processed/ri_private_schools_2021.csv", index=False)
print(len(out), "private schools,", int(out.enrollment.sum()), "students; missing coords:", out.latitude.isna().sum())
print(out.affiliation.value_counts().to_dict(), out.school_level.value_counts(dropna=False).to_dict())
