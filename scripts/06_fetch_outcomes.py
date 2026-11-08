"""Fetch Rhode Island school-level outcome and demographic data from the Urban Institute
Education Data Portal (EDFacts state assessments, graduation rates, CCD enrollment by race).
Raw JSON goes to data/raw/urban/, combined tidy CSVs to data/processed/.
Usage: python3 scripts/06_fetch_outcomes.py
Missing-value codes in the API: -1 missing, -2 not applicable, -3 suppressed.
"""
import json, os, time, urllib.request
import pandas as pd

BASE = "https://educationdata.urban.org/api/v1"
RAW = "data/raw/urban"
os.makedirs(RAW, exist_ok=True)


def fetch(path):
    """Fetch one endpoint (following pagination), cached on disk."""
    cache = f"{RAW}/{path.strip('/').replace('/', '_')}.json"
    if os.path.exists(cache):
        return json.load(open(cache))
    url, rows = f"{BASE}/{path}?fips=44", []
    while url:
        for attempt in range(4):
            try:
                d = json.load(urllib.request.urlopen(url, timeout=90))
                break
            except Exception as e:
                if attempt == 3:
                    print("FAILED", url, e)
                    return []
                time.sleep(2 * (attempt + 1))
        rows += d["results"]
        url = d.get("next")
    json.dump(rows, open(cache, "w"))
    return rows


# 1. Proficiency by grade x (all students | race | special populations)
# RI switched tests (PARCC 2015-17 -> RICAS 2018), so levels are not comparable across the break.
YEARS = [2015, 2016, 2017, 2018, 2020]
GRADES = [3, 4, 5, 6, 7, 8, 9]
for sub, label in [("", "all"), ("race/", "race"), ("special-populations/", "special_pops")]:
    rows = []
    for y in YEARS:
        for g in GRADES:
            rows += fetch(f"schools/edfacts/assessments/{y}/grade-{g}/{sub}")
    df = pd.DataFrame(rows)
    if len(df):
        df.to_csv(f"data/processed/ri_edfacts_assessments_{label}.csv", index=False)
    print("assessments", label, df.shape)

# 2. Graduation rates (school level)
rows = []
for y in range(2015, 2020):
    rows += fetch(f"schools/edfacts/grad-rates/{y}/")
df = pd.DataFrame(rows)
if len(df):
    df.to_csv("data/processed/ri_edfacts_grad_rates.csv", index=False)
print("grad rates", df.shape)

# 3. CCD enrollment by race (all RI schools) for 2020 and 2024
rows = []
for y in (2020, 2024):
    rows += fetch(f"schools/ccd/enrollment/{y}/grade-99/race/")
df = pd.DataFrame(rows)
RACE = {1: "White", 2: "Black", 3: "Hispanic", 4: "Asian", 5: "American Indian/Alaska Native",
        6: "Native Hawaiian/Pacific Islander", 7: "Two or more races", 8: "Nonresident alien",
        9: "Unknown", 20: "Other", 99: "Total"}
df["race_label"] = df["race"].map(RACE)
df.to_csv("data/processed/ri_ccd_enrollment_by_race.csv", index=False)
print("enrollment by race", df.shape)
