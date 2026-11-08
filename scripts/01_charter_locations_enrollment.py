"""Fetch RI charter schools (location + enrollment) from the Urban Institute
Education Data Portal (CCD school directory) and write a CSV.
Usage: python3 scripts/01_charter_locations_enrollment.py [YEAR]
"""
import csv, json, sys, urllib.request

YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
URL = f"https://educationdata.urban.org/api/v1/schools/ccd/directory/{YEAR}/?fips=44&charter=1"
raw = json.load(urllib.request.urlopen(URL, timeout=60))
json.dump(raw, open(f"data/raw/urban_ccd_ri_charters_{YEAR}.json", "w"))

LEVEL = {1: "Primary", 2: "Middle", 3: "High", 4: "Other", 0: "Not applicable", -1: "Missing"}
STATUS = {1: "Open", 2: "Closed", 3: "New", 4: "Added", 5: "Changed agency", 6: "Inactive", 7: "Future", 8: "Reopened"}
cols = ["year", "ncessch", "school_name", "lea_name", "street_location", "city_location", "zip_location",
        "county_code", "latitude", "longitude", "school_level", "school_status", "lowest_grade_offered",
        "highest_grade_offered", "virtual", "enrollment", "free_or_reduced_price_lunch", "teachers_fte"]
rows = []
for r in raw["results"]:
    row = {c: r.get(c) for c in cols}
    row["school_level"] = LEVEL.get(r.get("school_level"), r.get("school_level"))
    row["school_status"] = STATUS.get(r.get("school_status"), r.get("school_status"))
    rows.append(row)
rows.sort(key=lambda x: (x["city_location"] or "", x["school_name"]))
out = f"data/processed/ri_charter_schools_{YEAR}.csv"
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)

open_rows = [r for r in rows if r["school_status"] in ("Open", "New", "Added", "Reopened")]
tot = lambda rs: sum(r["enrollment"] or 0 for r in rs if (r["enrollment"] or 0) > 0)
print(f"{out}: {len(rows)} records, {len(open_rows)} open; enrollment (all) {tot(rows):,}")
by = {}
for r in rows:
    by.setdefault(r["city_location"], []).append(r)
for c, rs in sorted(by.items(), key=lambda kv: -tot(kv[1])):
    print(f"  {c:15s} {len(rs):2d} schools  {tot(rs):6,d}")
print("missing enrollment:", [r["school_name"] for r in rows if (r["enrollment"] or 0) <= 0])
print("non-open:", [(r["school_name"], r["school_status"]) for r in rows if r not in open_rows])
