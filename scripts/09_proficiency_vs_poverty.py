"""Scatter of school test proficiency vs. school poverty, charters highlighted.
Outputs: figures/proficiency_vs_poverty.png/.pdf, data/processed/proficiency_vs_poverty_schools.csv,
data/processed/proficiency_vs_poverty_summary.csv
Inputs: data/processed/ri_edfacts_assessments_all.csv (06), data/raw/urban_ccd_ri_all_schools_2018.json
(school directory 2018-19: charter flag, lunch eligibility; fetched below if missing).
Year labels: Urban's EDFacts/CCD "2018" = school year 2018-19.
Requires: pandas, numpy, matplotlib, pillow. Usage: python3 scripts/09_proficiency_vs_poverty.py
"""
import json, os, urllib.request
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

P = "data/processed/"
dp = "data/raw/urban_ccd_ri_all_schools_2018.json"
if not os.path.exists(dp):
    open(dp, "wb").write(urllib.request.urlopen(
        "https://educationdata.urban.org/api/v1/schools/ccd/directory/2018/?fips=44", timeout=90).read())
d = pd.DataFrame(json.load(open(dp))["results"])
d["ncessch"] = d.ncessch.astype(str)
d = d[(d.enrollment > 0) & (d.free_or_reduced_price_lunch >= 0)]
d["frl"] = (100 * d.free_or_reduced_price_lunch / d.enrollment).clip(upper=100)

a = pd.read_csv(P + "ri_edfacts_assessments_all.csv", dtype={"ncessch": str})
a = a[a.year == 2018]

def school_scores(subj):
    b = a[(a[f"{subj}_test_pct_prof_midpt"] >= 0) & (a[f"{subj}_test_num_valid"] > 0)].copy()
    b["w"] = b[f"{subj}_test_num_valid"].astype(float)
    b["x"] = b[f"{subj}_test_pct_prof_midpt"] * b.w
    g = b.groupby("ncessch").agg(x=("x", "sum"), tested=("w", "sum"))
    g[f"{subj}_prof"] = g.x / g.tested
    return g[[f"{subj}_prof", "tested"]].rename(columns={"tested": f"{subj}_tested"})

df = d[["ncessch", "school_name", "lea_name", "charter", "frl", "enrollment"]].merge(
    school_scores("math"), on="ncessch", how="inner").merge(school_scores("read"), on="ncessch", how="left")
df["sector"] = np.where(df.charter == 1, "Charter", "Traditional public")

# Fit prediction line on traditional public schools only (weighted by tested students), then
# measure how far charters sit from it.
summ = []
for subj in ("math", "read"):
    t = df[(df.sector == "Traditional public") & df[f"{subj}_prof"].notna()]
    c = df[(df.sector == "Charter") & df[f"{subj}_prof"].notna()]
    slope, icpt = np.polyfit(t.frl, t[f"{subj}_prof"], 1, w=np.sqrt(t[f"{subj}_tested"]))
    df.loc[df[f"{subj}_prof"].notna(), f"{subj}_resid"] = df[f"{subj}_prof"] - (icpt + slope * df.frl)
    r = df.loc[c.index, f"{subj}_resid"]
    wres = float((r * c[f"{subj}_tested"]).sum() / c[f"{subj}_tested"].sum())
    summ.append(dict(subject=subj, charter_schools=len(c), traditional_schools=len(t), slope_pts_per_10pct_frl=10 * slope,
                     intercept=icpt, charter_avg_gap_vs_line_pts=wres, charters_above_line=int((r > 0).sum())))
df.round(2).to_csv(P + "proficiency_vs_poverty_schools.csv", index=False)
pd.DataFrame(summ).round(2).to_csv(P + "proficiency_vs_poverty_summary.csv", index=False)

# ---- chart ----
NAVY, GOLD = "#003478", "#F2B600"
INK, SRC, BG = "#000000", "#6b6a66", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK, "axes.edgecolor": "#d9d8d4"})
fig, axes = plt.subplots(1, 2, figsize=(8.5, 5.8), facecolor=BG)
fig.subplots_adjust(left=.085, right=.97, top=.83, bottom=.17, wspace=.22)
xs = np.array([0, 100])
for ax, subj, name, s in zip(axes, ("math", "read"), ("Math", "Reading"), summ):
    ax.set_facecolor(BG)
    for sec, color, alpha, z, edge in (("Traditional public", GOLD, .55, 2, "#b58500"), ("Charter", NAVY, .95, 4, "white")):
        g = df[(df.sector == sec) & df[f"{subj}_prof"].notna()]
        ax.scatter(g.frl, g[f"{subj}_prof"], s=np.sqrt(g[f"{subj}_tested"]) * 3.2, c=color, alpha=alpha,
                   edgecolors=edge, linewidths=.5, zorder=z)
    ax.plot(xs, s["intercept"] + s["slope_pts_per_10pct_frl"] / 10 * xs, color=INK, lw=1.3, ls=(0, (4, 3)), zorder=3)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100]); ax.set_xticklabels([f"{v}%" for v in (0, 25, 50, 75, 100)], fontsize=8.5)
    ax.set_yticks([0, 25, 50, 75, 100]); ax.set_yticklabels([f"{v}%" for v in (0, 25, 50, 75, 100)], fontsize=8.5)
    ax.grid(color="#e6e5e1", lw=.6, zorder=0); ax.set_axisbelow(True)
    [ax.spines[k].set_visible(False) for k in ("top", "right")]
    ax.tick_params(length=0)
    ax.set_xlabel("Students eligible for free/reduced lunch", fontsize=8.5, labelpad=6)
    ax.set_title(f"{name} proficiency", loc="left", fontsize=10.5, fontweight="bold", pad=8)
    ax.text(97, 94, f"Charters average {s['charter_avg_gap_vs_line_pts']:+.0f} points\nvs. the line for similar schools",
            ha="right", va="top", fontsize=8.2, fontweight="bold", bbox=dict(fc=BG, ec="none", pad=2), zorder=6)
    ax.text(4, 3, "Dot size = students tested", fontsize=7.2, color=SRC, va="bottom")
axes[0].set_ylabel("Students proficient", fontsize=8.5, labelpad=6)
# direct labels (no legend box): navy = charter, gold = traditional, dashed = trend line
axes[0].text(99, 79, "Charter schools", color=NAVY, fontsize=8.5, fontweight="bold", ha="right")
axes[0].text(99, 73, "Traditional public schools", color="#8a6500", fontsize=8.5, fontweight="bold", ha="right")
axes[0].text(99, 67, "- - -  Line fit to traditional schools", color=INK, fontsize=7.8, ha="right")

title = fig.text(.5, .95, "Test Scores and Poverty in Rhode Island Schools", fontsize=15, fontweight="bold",
                 ha="center", va="top")
fig.text(.5, .045, f"Source: EDFacts 2018-19; NCES CCD 2018-19. Schools: {summ[0]['charter_schools']} charter, "
         f"{summ[0]['traditional_schools']} traditional public (math). Descriptive, not a causal estimate.",
         fontsize=7.5, color=SRC, ha="center", va="top")
fig.canvas.draw()
bb = title.get_window_extent().transformed(fig.transFigure.inverted())
logo = Image.open("data/raw/logo/flag.png").convert("RGBA")
px = np.array(logo); px[(px[..., :3] > 235).all(axis=2), 3] = 0
logo = Image.fromarray(px); logo = logo.crop(logo.getchannel("A").getbbox())
h = bb.height * 1.9; w = h * logo.width / logo.height * (5.8 / 8.5)
lax = fig.add_axes([bb.x0 - w - .015, bb.y0 + (bb.height - h) / 2, w, h]); lax.imshow(logo); lax.axis("off")
fig.savefig("figures/proficiency_vs_poverty.png", dpi=220, facecolor=BG)
fig.savefig("figures/proficiency_vs_poverty.pdf", facecolor=BG)
print(pd.DataFrame(summ).round(2).to_string())
