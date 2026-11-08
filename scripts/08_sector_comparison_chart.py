"""Compare Rhode Island charter, traditional public and private schools; writes
figures/sector_comparison.png and data/processed/sector_comparison_summary.csv.
Inputs (all from earlier scripts): ri_school_master_list.csv (07), ri_ccd_enrollment_by_race.csv (06),
ri_edfacts_assessments_all.csv (06), ri_private_schools_2021.csv (05), the charter / non-charter enriched
CSVs (03), and the raw CCD 2020 directory (school poverty bands for the test-score panel).
Requires: pandas, numpy, matplotlib. Usage: python3 scripts/08_sector_comparison_chart.py
"""
import json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

P = "data/processed/"
m = pd.read_csv(P + "ri_school_master_list.csv", dtype={"school_id": str})
race = pd.read_csv(P + "ri_ccd_enrollment_by_race.csv", dtype={"ncessch": str})
white = race[(race.year == 2024) & (race.race == 1)].set_index("ncessch").enrollment
priv_raw = pd.read_csv(P + "ri_private_schools_2021.csv")
pub = m[m.sector != "Private"].copy()
pub["poc"] = 100 * (1 - pub.school_id.map(white) / pub.enrollment)

SECT = ["Charter", "Traditional public", "Private"]
wavg = lambda v, w: float((v * w).sum() / w[v.notna()].sum())

# ---- sector-level descriptives (student-weighted) ----
S = {}
for s in SECT:
    g = m[m.sector == s]
    d = dict(schools=len(g), students=int(g.enrollment.sum()), spt=g.enrollment.sum() / g.teachers_fte.sum())
    if s == "Private":
        d["frl"] = np.nan
        d["poc"] = wavg(priv_raw.pct_students_of_color, priv_raw.enrollment)
    else:
        p = pub[pub.sector == s]
        d["frl"] = wavg(p.pct_free_reduced_lunch, p.enrollment)
        d["poc"] = wavg(p.poc, p.enrollment)
    S[s] = d

# ---- spending: FY2020 current spending per pupil; charter-only operators vs whole districts ----
ch = pd.read_csv(P + "ri_charter_schools_2024_enriched.csv", dtype={"ncessch": str})
nc = pd.read_csv(P + "ri_noncharter_schools_2024_enriched.csv", dtype={"ncessch": str})
def spend(d, key):
    x = d.drop_duplicates(key).dropna(subset=["per_pupil_current_spending_2020"])
    return wavg(x.per_pupil_current_spending_2020, x.lea_enrollment_2020), len(x)
S["Charter"]["spend"], S["Charter"]["spend_n"] = spend(ch, "leaid")
S["Traditional public"]["spend"], S["Traditional public"]["spend_n"] = spend(nc, "lea_name")
S["Private"]["spend"] = np.nan

# ---- test scores: grade 3-9 math, student-weighted; "2018" = 2018-19, "2020" = 2020-21 (pandemic year) ----
a = pd.read_csv(P + "ri_edfacts_assessments_all.csv", dtype={"ncessch": str})
c20 = pd.DataFrame(json.load(open("data/raw/urban_ccd_ri_charters_2020.json"))["results"])
charter_ids = set(m[m.sector == "Charter"].school_id) | set(c20.ncessch.astype(str))  # incl. since-closed charters
a["sector"] = np.where(a.ncessch.isin(charter_ids), "Charter", "Traditional public")
a = a[(a.math_test_pct_prof_midpt >= 0) & (a.math_test_num_valid > 0)]
d20 = pd.DataFrame(json.load(open("data/raw/urban_ccd_ri_all_schools_2020.json"))["results"])
d20["frl"] = 100 * d20.free_or_reduced_price_lunch / d20.enrollment
a = a.merge(d20[["ncessch", "frl"]].assign(ncessch=lambda x: x.ncessch.astype(str)), on="ncessch", how="left")
a["band"] = pd.cut(a.frl, [-1, 60, 80, 101], labels=["Under 60%", "60-80%", "Over 80%"])
prof = lambda g: wavg(g.math_test_pct_prof_midpt, g.math_test_num_valid.astype(float))
def by(y, band=None):
    b = a[a.year == y]
    if band: b = b[b.band == band]
    return {s: (prof(b[b.sector == s]) if (b.sector == s).any() else np.nan) for s in SECT[:2]}, \
           {s: b[b.sector == s].ncessch.nunique() for s in SECT[:2]}
ALL18, N18 = by(2018); ALL20, _ = by(2020)
BANDS = ["Under 60%", "60-80%", "Over 80%"]
BAND18 = {b: by(2018, b) for b in BANDS}

rows = [dict(sector=s, **S[s], math_2018_19=ALL18.get(s, np.nan), math_2020_21=ALL20.get(s, np.nan)) for s in SECT]
pd.DataFrame(rows).round(1).to_csv(P + "sector_comparison_summary.csv", index=False)
pd.DataFrame([dict(poverty_band=b, sector=s, math_proficiency_2018_19=BAND18[b][0][s], schools=BAND18[b][1][s])
              for b in BANDS for s in SECT[:2]]).round(1).to_csv(P + "sector_comparison_math_by_poverty.csv", index=False)

# ---- chart: portrait US Letter (8.5 x 11 in) so it drops onto a PDF page 1:1 ----
import sys, textwrap
sys.path.insert(0, "scripts")
import style as rist
from style import COL, INK, SRC, BG
rist.setup_fonts()
MEMO = "--memo" in sys.argv   # memo version: no in-figure title or logo (the memo supplies caption and logo)
fig, axes = plt.subplots(3, 2, figsize=(8.5, 11), facecolor=BG)
fig.subplots_adjust(left=.16, right=.95, top=.955 if MEMO else .86, bottom=.07, hspace=.55, wspace=.62)
LAB = {"Charter": "Charter", "Traditional public": "Traditional\npublic", "Private": "Private"}

def style(ax, title, source, yt, ylab, ylim):
    ax.set_facecolor(BG); ax.set_ylim(*ylim)
    ax.set_yticks(yt); ax.set_yticklabels(ylab, fontsize=9, color=INK)
    ax.set_xticks([]); [ax.spines[k].set_visible(False) for k in ("top", "right", "bottom")]
    ax.tick_params(axis="y", length=0)
    ax.set_title(title, loc="left", fontsize=10.5, fontweight="bold", pad=7, color=INK)
    ax.text(0, -.05, source, transform=ax.transAxes, fontsize=7.5, color=SRC, va="top")

def bars(ax, title, key, fmt, source, xmax):
    for i, s in enumerate(SECT):
        y, v = 2 - i, S[s][key]
        if np.isnan(v):
            ax.text(xmax * .02, y, "no data in public file", va="center", fontsize=8.5, color=INK, style="italic")
        else:
            ax.barh(y, v, height=.52, color=COL[s])
            ax.text(v + xmax * .02, y, fmt(v), va="center", fontsize=10, fontweight="bold", color=INK)
    ax.set_xlim(0, xmax)
    style(ax, title, source, [2, 1, 0], [LAB[s] for s in SECT], (-.6, 2.6))

CCD, BOTH = "Source: NCES CCD, 2024-25", "Source: NCES CCD 2024-25; PSS 2021-22"
bars(axes[0, 0], "Low-income students", "frl", lambda v: f"{v:.0f}%", CCD, 100)
bars(axes[0, 1], "Students of color", "poc", lambda v: f"{v:.0f}%", BOTH, 100)
bars(axes[1, 0], "Students per teacher", "spt", lambda v: f"{v:.1f}", BOTH, 20)
bars(axes[1, 1], "Spending per pupil, FY2020", "spend", lambda v: f"${v/1000:.1f}k", "Source: NCES CCD finance, FY2020", 24000)

# math proficiency: overall + by school poverty band (first group is labeled by sector, so no legend is needed)
ax = axes[2, 0]
groups = [ALL18] + [BAND18[b][0] for b in BANDS]
for gi, v in enumerate(groups):
    for k, s in enumerate(SECT[:2]):
        y = (3 - gi) + (.17 if k == 0 else -.17)
        ax.barh(y, v[s], height=.3, color=COL[s])
        ax.text(v[s] + 1.2, y, f"{v[s]:.0f}%" + (f"  {s}" if gi == 0 else ""), va="center",
                fontsize=8 if gi == 0 else 8.5, fontweight="bold", color=INK)
ax.set_xlim(0, 100)
style(ax, "Math proficiency, grades 3-9, 2018-19", "Source: EDFacts, 2018-19", [3, 2, 1, 0],
      ["All schools"] + [f"{b}\nlow-income" for b in BANDS], (-.55, 3.6))

# size of each sector
ax = axes[2, 1]; tot = sum(S[s]["students"] for s in SECT)
for i, s in enumerate(SECT):
    y, st = 2 - i, S[s]["students"]
    ax.barh(y, st, height=.52, color=COL[s])
    ax.text(st + 5000, y + .06, f"{st:,}", va="center", fontsize=10, fontweight="bold", color=INK)
    ax.text(st + 5000, y - .3, f"{S[s]['schools']} schools, {100*st/tot:.0f}%", va="center", fontsize=8, color=INK)
ax.set_xlim(0, 230000)
style(ax, "Students enrolled", BOTH, [2, 1, 0], [LAB[s] for s in SECT], (-.75, 2.6))

# header: flag emblem to the left of the centered title (standalone version only)
if not MEMO:
    title = fig.text(.5, .955, "Rhode Island Charter\nSchool Comparison", fontsize=19, fontweight="bold", ha="center", va="top",
                     linespacing=1.15, color=INK)
    fig.canvas.draw()
    bb = title.get_window_extent().transformed(fig.transFigure.inverted())
    logo = rist.emblem()
    h = bb.height * 1.05; w = h * logo.width / logo.height * (11 / 8.5)
    lax = fig.add_axes([bb.x0 - w - .02, bb.y0 + (bb.height - h) / 2, w, h]); lax.imshow(logo); lax.axis("off")
fig.text(.5, .035, "Descriptive comparison, not a causal estimate. Data: Urban Institute Education Data Portal; NCES.",
         fontsize=7.5, color=SRC, ha="center", va="top")
if MEMO:
    fig.savefig("figures/memo/exhibit1_sector_comparison.png", dpi=220, facecolor=BG)
else:
    fig.savefig("figures/sector_comparison.png", dpi=220, facecolor=BG)
    fig.savefig("figures/sector_comparison.pdf", facecolor=BG)
print(pd.DataFrame(rows).round(1).to_string())
