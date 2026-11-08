"""Variant of 09: scatter stacked vertically; trend line for traditional schools only, plus one "center of gravity"
point per sector = average low-income share and proficiency, weighted by school enrollment.
Outputs: figures/proficiency_vs_poverty_centroids.png/.pdf, data/processed/proficiency_vs_poverty_centroids.csv
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

# Traditional-school line (weighted by students tested) and enrollment-weighted sector centroids.
fits, rows = {}, []
for subj in ("math", "read"):
    t = df[(df.sector == "Traditional public") & df[f"{subj}_prof"].notna()]
    fits[subj] = np.polyfit(t.frl, t[f"{subj}_prof"], 1, w=np.sqrt(t[f"{subj}_tested"]))
    for sec in ("Charter", "Traditional public"):
        g = df[(df.sector == sec) & df[f"{subj}_prof"].notna()]
        w = g.enrollment
        rows.append(dict(subject=subj, sector=sec, schools=len(g), students_enrolled=int(w.sum()),
                         avg_low_income_pct=float((g.frl * w).sum() / w.sum()),
                         avg_proficiency_pct=float((g[f"{subj}_prof"] * w).sum() / w.sum())))
cent = pd.DataFrame(rows)
cent.round(2).to_csv(P + "proficiency_vs_poverty_centroids.csv", index=False)

# ---- chart: two panels stacked vertically ----
import sys
sys.path.insert(0, "scripts")
import style
from style import NAVY, GOLD, GOLD_D, INK, SRC, BG
style.setup_fonts()
MEMO = "--memo" in sys.argv   # memo version: no in-figure title or logo
fig, axes = plt.subplots(2, 1, figsize=(8.5, 11), facecolor=BG)
fig.subplots_adjust(left=.10, right=.95, top=.955 if MEMO else .885, bottom=.10, hspace=.30)
xs = np.linspace(0, 100, 50)
for ax, subj, name in zip(axes, ("math", "read"), ("Math proficiency", "Reading proficiency")):
    ax.set_facecolor(BG)
    for sec, color, alpha, z, edge in (("Traditional public", GOLD, .45, 2, GOLD_D), ("Charter", NAVY, .55, 3, "white")):
        g = df[(df.sector == sec) & df[f"{subj}_prof"].notna()]
        ax.scatter(g.frl, g[f"{subj}_prof"], s=np.sqrt(g[f"{subj}_tested"]) * 4.5, c=color, alpha=alpha,
                   edgecolors=edge, linewidths=.5, zorder=z)
    sl, ic = fits[subj]
    ax.plot(xs, ic + sl * xs, color=GOLD_D, lw=2.2, ls=(0, (5, 3)), zorder=4)
    # centers of gravity: large diamonds outlined in black
    cs = cent[cent.subject == subj].set_index("sector")
    for sec, color in (("Traditional public", GOLD), ("Charter", NAVY)):
        ax.scatter(cs.loc[sec, "avg_low_income_pct"], cs.loc[sec, "avg_proficiency_pct"], s=300, marker="D", c=color,
                   edgecolors=INK, linewidths=2, zorder=8)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ticks = [0, 25, 50, 75, 100]
    ax.set_xticks(ticks); ax.set_xticklabels([f"{v}%" for v in ticks], fontsize=9)
    ax.set_yticks(ticks); ax.set_yticklabels([f"{v}%" for v in ticks], fontsize=9)
    ax.grid(color="#e6e5e1", lw=.6, zorder=0); ax.set_axisbelow(True)
    [ax.spines[k].set_visible(False) for k in ("top", "right")]; ax.tick_params(length=0)
    ax.set_xlabel("Students eligible for free/reduced lunch", fontsize=9.5, labelpad=7)
    ax.set_ylabel("Students proficient", fontsize=9.5, labelpad=7)
    ax.set_title(name, loc="left", fontsize=12, fontweight="bold", pad=10)
    lines = ["Averages (diamonds):"] + [
        f"{sec.replace(' public', '')}: {cs.loc[sec, 'avg_low_income_pct']:.0f}% low-income, {cs.loc[sec, 'avg_proficiency_pct']:.0f}% proficient"
        for sec in ("Charter", "Traditional public")]
    ax.text(98, 97, "\n".join(lines), ha="right", va="top", fontsize=8.8, fontweight="bold",
            bbox=dict(fc=BG, ec="none", pad=3), zorder=9, linespacing=1.5)
    ax.text(2, 3, "Dot size = students tested", fontsize=8, color=INK, va="bottom", ha="left")
    # direct labels on the diamonds
    for sec, lab, dy in (("Charter", "Charter\naverage", 9), ("Traditional public", "Traditional\naverage", -9)):
        x, y = cs.loc[sec, "avg_low_income_pct"], cs.loc[sec, "avg_proficiency_pct"]
        ax.annotate(lab, (x, y), xytext=(0, dy * 2.3), textcoords="offset points", ha="center",
                    va="bottom" if dy > 0 else "top", fontsize=8.5, fontweight="bold", zorder=10,
                    bbox=dict(fc=BG, ec="none", pad=1.5, alpha=.85))
    # label for the dashed line
    ax.text(101.5, ic + sl * 100, "Traditional\nline", fontsize=8.5, fontweight="bold", va="center", ha="left",
            clip_on=False, linespacing=1.1)
if not MEMO:
    title = fig.text(.5, .965, "Test Scores and Poverty in\nRhode Island Schools", fontsize=18, fontweight="bold",
                     ha="center", va="top", linespacing=1.15)
    fig.canvas.draw()
    bb = title.get_window_extent().transformed(fig.transFigure.inverted())
    logo = style.emblem()
    h = bb.height * 1.05; w = h * logo.width / logo.height * (11 / 8.5)
    lax = fig.add_axes([bb.x0 - w - .02, bb.y0 + (bb.height - h) / 2, w, h]); lax.imshow(logo); lax.axis("off")
fig.text(.5, .052, "Diamonds show each sector's average low-income share and proficiency, weighted by school enrollment.\n"
         "Dashed line is fit to traditional public schools only. Descriptive, not a causal estimate.",
         fontsize=7.5, color=SRC, ha="center", va="top", linespacing=1.5)
fig.text(.5, .022, f"Source: EDFacts 2018-19; NCES CCD 2018-19. Schools: {cent.schools.iloc[0]} charter, "
         f"{cent.schools.iloc[1]} traditional public (math).", fontsize=7.5, color=SRC, ha="center", va="top")
if MEMO:
    fig.savefig("figures/memo/exhibit2_proficiency_vs_poverty.png", dpi=220, facecolor=BG)
else:
    fig.savefig("figures/proficiency_vs_poverty_centroids.png", dpi=220, facecolor=BG)
    fig.savefig("figures/proficiency_vs_poverty_centroids.pdf", facecolor=BG)
print(cent.round(1).to_string())
