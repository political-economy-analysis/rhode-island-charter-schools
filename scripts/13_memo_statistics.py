"""Extra statistics quoted in the memo. Writes data/processed/memo_statistics_*.csv and prints a summary.
Uses: ri_school_master_list.csv (07), EDFacts files (06), 2018 CCD directory (09)."""
import json
import numpy as np, pandas as pd
P = "data/processed/"
d = pd.DataFrame(json.load(open("data/raw/urban_ccd_ri_all_schools_2018.json"))["results"]); d["ncessch"] = d.ncessch.astype(str)
charter18 = set(d[d.charter == 1].ncessch)
wm = lambda g, v, w: float((g[v] * g[w]).sum() / g[w].sum())

# 1. Subgroup proficiency, 2018-19, math and reading (students-tested weighted), charter vs traditional
rows = []
race = pd.read_csv(P + "ri_edfacts_assessments_race.csv", dtype={"ncessch": str})
sp = pd.read_csv(P + "ri_edfacts_assessments_special_pops.csv", dtype={"ncessch": str})
def grp(df, mask, label):
    b = df[(df.year == 2018) & mask].copy()
    b["sector"] = np.where(b.ncessch.isin(charter18), "Charter", "Traditional public")
    for subj in ("math", "read"):
        x = b[(b[f"{subj}_test_pct_prof_midpt"] >= 0) & (b[f"{subj}_test_num_valid"] > 0)]
        for sec, g in x.groupby("sector"):
            rows.append(dict(group=label, subject=subj, sector=sec, schools=g.ncessch.nunique(),
                             students_tested=int(g[f"{subj}_test_num_valid"].sum()),
                             proficient_pct=wm(g, f"{subj}_test_pct_prof_midpt", f"{subj}_test_num_valid")))
for code, lab in ((2, "Black"), (3, "Hispanic"), (1, "White")):
    grp(race, (race.race == code), lab)
for col, lab in (("econ_disadvantaged", "Low-income"), ("disability", "Students with disabilities"), ("lep", "English learners")):
    grp(sp, (sp[col] == 1), lab)
sub = pd.DataFrame(rows).round(1); sub.to_csv(P + "memo_statistics_subgroups.csv", index=False)
print(sub[sub.subject == "math"].pivot(index="group", columns="sector", values=["proficient_pct", "schools"]).to_string())

# 2. Where charter enrollment is (2024-25 master list)
m = pd.read_csv(P + "ri_school_master_list.csv", dtype={"school_id": str})
c = m[m.sector == "Charter"]
city = c.groupby("city").agg(sites=("school_id", "size"), charter_students=("enrollment", "sum")).sort_values("charter_students", ascending=False)
city["share_of_charter_students"] = (100 * city.charter_students / city.charter_students.sum()).round(1)
t = m[m.sector == "Traditional public"].groupby("city").enrollment.sum().rename("district_school_students_in_city")
city = city.join(t); city["charter_seats_per_100_district_students"] = (100 * city.charter_students / city.district_school_students_in_city).round(1)
city.to_csv(P + "memo_statistics_charter_by_city.csv"); print(city.head(8).to_string())
north = ["Providence", "Central Falls", "Pawtucket", "Cranston", "Cumberland", "Woonsocket"]
print("share of charter sites in 6 cities:", int(c.city.isin(north).sum()), "of", len(c), "| students share:", round(100 * c[c.city.isin(north)].enrollment.sum() / c.enrollment.sum(), 1))
print("operators:", c.district_or_lea.nunique())

# 3. Scenario arithmetic
ch_n, tr_n = c.enrollment.sum(), m[m.sector == "Traditional public"].enrollment.sum()
tot = ch_n + tr_n
print("charter share now:", round(100 * ch_n / tot, 1), "% of", int(tot), "public students")
print("if charter enrollment doubles (students move from districts):", round(100 * 2 * ch_n / tot, 1), "%")
for eff in (0, 2.5, 5, 10):
    print(f"per-student proficiency gain {eff} pts -> statewide change {ch_n * eff / tot:.2f} pts")
# teachers: staffing implied by moving ch_n students
spt_c = c.enrollment.sum() / c.teachers_fte.sum(); spt_t = m[m.sector == "Traditional public"].enrollment.sum() / m[m.sector == "Traditional public"].teachers_fte.sum()
print("teacher FTE shifted per 13,465 students: district", round(ch_n / spt_t), "charter", round(ch_n / spt_c), "| total teachers charter/trad:", round(c.teachers_fte.sum()), round(m[m.sector == "Traditional public"].teachers_fte.sum()))

# 4. Charter average vs. line fit to traditional schools, evaluated at the charter average poverty level
# (same method as scripts/11: line weighted by sqrt(students tested); averages weighted by enrollment)
s = pd.read_csv(P + "proficiency_vs_poverty_schools.csv", dtype={"ncessch": str})
s["sector"] = np.where(s.charter == 1, "Charter", "Traditional public")
out = []
for subj in ("math", "read"):
    t = s[(s.sector == "Traditional public") & s[f"{subj}_prof"].notna()]
    c_ = s[(s.sector == "Charter") & s[f"{subj}_prof"].notna()]
    sl, ic = np.polyfit(t.frl, t[f"{subj}_prof"], 1, w=np.sqrt(t[f"{subj}_tested"]))
    cx, cy = wm(c_, "frl", "enrollment"), wm(c_, f"{subj}_prof", "enrollment")
    out.append(dict(subject=subj, charter_avg_low_income=cx, charter_avg_proficiency=cy,
                    line_predicts=ic + sl * cx, charter_above_line_pts=cy - (ic + sl * cx)))
adj = pd.DataFrame(out).round(1); adj.to_csv(P + "memo_statistics_charter_vs_line.csv", index=False); print(adj.to_string())
