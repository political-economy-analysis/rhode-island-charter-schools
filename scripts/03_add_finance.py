"""Add per-pupil finance (FY2020, latest year with data in the Urban API) to the charter CSV.
Per-pupil = LEA total / LEA enrollment summed over the LEA's schools in the 2020 CCD directory.
Uses data/raw/urban_ccd_ri_finance_2020.json and urban_ccd_ri_charters_2020.json (see README)."""
import json, urllib.request, pandas as pd, os
for name, url in {
  "urban_ccd_ri_finance_2020.json": "https://educationdata.urban.org/api/v1/school-districts/ccd/finance/2020/?fips=44",
  "urban_ccd_ri_all_schools_2020.json": "https://educationdata.urban.org/api/v1/schools/ccd/directory/2020/?fips=44",
  "urban_ccd_ri_all_schools_2024.json": "https://educationdata.urban.org/api/v1/schools/ccd/directory/2024/?fips=44",
  "urban_ccd_ri_charters_2020.json": "https://educationdata.urban.org/api/v1/schools/ccd/directory/2020/?fips=44&charter=1"}.items():
    p = f"data/raw/{name}"
    if not os.path.exists(p): open(p, "wb").write(urllib.request.urlopen(url, timeout=60).read())
fin = pd.DataFrame(json.load(open("data/raw/urban_ccd_ri_finance_2020.json"))["results"])
c20 = pd.DataFrame(json.load(open("data/raw/urban_ccd_ri_charters_2020.json"))["results"])
# Finance is only meaningful for charter-only LEAs; district LEAs that merely contain a charter
# school (e.g. Providence, Cranston) report whole-district spending, so we drop them.
al = pd.DataFrame(json.load(open("data/raw/urban_ccd_ri_all_schools_2020.json"))["results"])
mixed = set(al.loc[al.charter != 1, "leaid"])
enr = c20[~c20.leaid.isin(mixed)].groupby("leaid").enrollment.sum().rename("lea_enrollment_2020").reset_index()
fin = fin.merge(enr, on="leaid")
fin["per_pupil_current_spending_2020"] = fin.exp_current_elsec_total / fin.lea_enrollment_2020
fin["per_pupil_instruction_2020"] = fin.exp_current_instruction_total / fin.lea_enrollment_2020
fin["per_pupil_state_rev_2020"] = fin.rev_state_total / fin.lea_enrollment_2020
fin["per_pupil_local_rev_2020"] = fin.rev_local_total / fin.lea_enrollment_2020
keep = ["leaid", "lea_enrollment_2020", "per_pupil_current_spending_2020", "per_pupil_instruction_2020",
        "per_pupil_state_rev_2020", "per_pupil_local_rev_2020"]
df = pd.read_csv("data/processed/ri_charter_schools_2024.csv", dtype={"ncessch": str})
df["leaid"] = df.ncessch.str[:7]
df = df.merge(fin[keep], on="leaid", how="left")
df["pct_free_reduced_lunch"] = (100 * df.free_or_reduced_price_lunch / df.enrollment).round(1)
df["students_per_teacher"] = (df.enrollment / df.teachers_fte).round(1)
df.to_csv("data/processed/ri_charter_schools_2024_enriched.csv", index=False)
print(df[["school_name","enrollment","pct_free_reduced_lunch","students_per_teacher","per_pupil_current_spending_2020"]].describe())
print("no finance:", df.per_pupil_current_spending_2020.isna().sum(), "schools")
print(df.sort_values("per_pupil_current_spending_2020")[["lea_name","per_pupil_current_spending_2020"]].drop_duplicates().to_string())

# ---- Non-charter (district and other public) schools, 2024, with district-level FY2020 finance ----
a24 = pd.DataFrame(json.load(open("data/raw/urban_ccd_ri_all_schools_2024.json"))["results"])
d = a24[(a24.charter != 1) & a24.school_status.isin([1, 3]) & (a24.enrollment > 0)].copy()
enr_all = al.groupby("leaid").enrollment.sum().rename("lea_enrollment_2020").reset_index()
f2 = pd.DataFrame(json.load(open("data/raw/urban_ccd_ri_finance_2020.json"))["results"]).merge(enr_all, on="leaid")
f2["per_pupil_current_spending_2020"] = f2.exp_current_elsec_total / f2.lea_enrollment_2020
f2["per_pupil_instruction_2020"] = f2.exp_current_instruction_total / f2.lea_enrollment_2020
f2["per_pupil_state_rev_2020"] = f2.rev_state_total / f2.lea_enrollment_2020
f2["per_pupil_local_rev_2020"] = f2.rev_local_total / f2.lea_enrollment_2020
d = d.merge(f2[keep], on="leaid", how="left")
d["pct_free_reduced_lunch"] = (100 * d.free_or_reduced_price_lunch / d.enrollment).round(1)
d["students_per_teacher"] = (d.enrollment / d.teachers_fte).round(1)
d["city_location"] = d.city_location.str.title()
cols = ["year","ncessch","school_name","lea_name","street_location","city_location","zip_location","latitude","longitude",
        "lowest_grade_offered","highest_grade_offered","virtual","enrollment","free_or_reduced_price_lunch","teachers_fte",
        "school_status","pct_free_reduced_lunch","students_per_teacher"] + keep[1:]
d[cols].to_csv("data/processed/ri_noncharter_schools_2024_enriched.csv", index=False)
print("non-charter schools:", len(d), "enrollment", int(d.enrollment.sum()), "no finance:", d.per_pupil_current_spending_2020.isna().sum())
print(d.per_pupil_current_spending_2020.describe())
