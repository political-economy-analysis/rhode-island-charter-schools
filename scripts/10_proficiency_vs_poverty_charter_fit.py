"""Variant of 09: same scatter, stacked vertically, with a separate fitted line for charter schools too.
Outputs: figures/proficiency_vs_poverty_charter_fit.png/.pdf, data/processed/proficiency_vs_poverty_line_fits.csv
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

# Fit one weighted line per sector (weights = sqrt of students tested), plus bootstrap 95% intervals over schools.
rng = np.random.default_rng(0)
def fit(g, subj):
    return np.polyfit(g.frl, g[f"{subj}_prof"], 1, w=np.sqrt(g[f"{subj}_tested"]))  # slope, intercept
fits, rows = {}, []
for subj in ("math", "read"):
    for sec in ("Traditional public", "Charter"):
        g = df[(df.sector == sec) & df[f"{subj}_prof"].notna()]
        sl, ic = fit(g, subj)
        bs = np.array([fit(g.iloc[rng.integers(0, len(g), len(g))], subj) for _ in range(2000)])
        fits[(subj, sec)] = (sl, ic, g.frl.min(), g.frl.max())
        rows.append(dict(subject=subj, sector=sec, schools=len(g), slope_pts_per_10pct_frl=10 * sl,
                         slope_ci_low=10 * np.percentile(bs[:, 0], 2.5), slope_ci_high=10 * np.percentile(bs[:, 0], 97.5),
                         predicted_at_25=ic + 25 * sl, predicted_at_50=ic + 50 * sl, predicted_at_75=ic + 75 * sl,
                         frl_min=g.frl.min(), frl_max=g.frl.max()))
out = pd.DataFrame(rows).round(2)
out.to_csv(P + "proficiency_vs_poverty_line_fits.csv", index=False)

# ---- chart: two panels stacked vertically ----
NAVY, GOLD, GOLD_D = "#003478", "#F2B600", "#B58500"
INK, SRC, BG = "#000000", "#6b6a66", "#fcfcfb"      # all text black except the source line
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK, "axes.edgecolor": "#d9d8d4"})
fig, axes = plt.subplots(2, 1, figsize=(8.5, 11), facecolor=BG)
fig.subplots_adjust(left=.10, right=.90, top=.885, bottom=.09, hspace=.30)
xs = np.linspace(0, 100, 50)
for ax, subj, name in zip(axes, ("math", "read"), ("Math proficiency", "Reading proficiency")):
    ax.set_facecolor(BG)
    for sec, color, alpha, z, edge in (("Traditional public", GOLD, .55, 2, GOLD_D), ("Charter", NAVY, .95, 4, "white")):
        g = df[(df.sector == sec) & df[f"{subj}_prof"].notna()]
        ax.scatter(g.frl, g[f"{subj}_prof"], s=np.sqrt(g[f"{subj}_tested"]) * 4.5, c=color, alpha=alpha,
                   edgecolors=edge, linewidths=.5, zorder=z)
    sl, ic, _, _ = fits[(subj, "Traditional public")]
    ax.plot(xs, ic + sl * xs, color=GOLD_D, lw=2.2, ls=(0, (5, 3)), zorder=3)
    sl, ic, lo, hi = fits[(subj, "Charter")]
    xc = np.linspace(lo, hi, 30)                       # drawn only over the range of charter data
    ax.plot(xc, ic + sl * xc, color=NAVY, lw=2.4, zorder=5)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ticks = [0, 25, 50, 75, 100]
    ax.set_xticks(ticks); ax.set_xticklabels([f"{v}%" for v in ticks], fontsize=9)
    ax.set_yticks(ticks); ax.set_yticklabels([f"{v}%" for v in ticks], fontsize=9)
    ax.grid(color="#e6e5e1", lw=.6, zorder=0); ax.set_axisbelow(True)
    [ax.spines[k].set_visible(False) for k in ("top", "right")]; ax.tick_params(length=0)
    ax.set_xlabel("Students eligible for free/reduced lunch", fontsize=9.5, labelpad=7)
    ax.set_ylabel("Students proficient", fontsize=9.5, labelpad=7)
    ax.set_title(name, loc="left", fontsize=12, fontweight="bold", pad=10)
    ft, fc = fits[(subj, "Traditional public")], fits[(subj, "Charter")]
    gap = lambda x: (fc[1] + fc[0] * x) - (ft[1] + ft[0] * x)
    ax.text(98, 97, "Charter line vs. traditional line:\n" + "   ".join(f"{x}% low-income: {gap(x):+.0f} pts" for x in (25, 50, 75))
            .replace("   ", "\n"), ha="right", va="top", fontsize=8.8, fontweight="bold",
            bbox=dict(fc=BG, ec="none", pad=3), zorder=7, linespacing=1.5)
    ax.text(2, 3, "Dot size = students tested", fontsize=8, color=INK, va="bottom", ha="left")
# direct labels at the line ends, in the right margin (text stays black; line color carries identity)
for ax, subj in zip(axes, ("math", "read")):
    for sec, x_end in (("Charter", None), ("Traditional public", 100)):
        sl, ic, lo, hi = fits[(subj, sec)]
        x = hi if x_end is None else x_end
        ax.text(x + 1.5, ic + sl * x, "Charter\nline" if sec == "Charter" else "Traditional\nline", fontsize=8.5,
                fontweight="bold", va="center", ha="left", clip_on=False, linespacing=1.1)
title = fig.text(.5, .965, "Test Scores and Poverty in\nRhode Island Schools", fontsize=18, fontweight="bold",
                 ha="center", va="top", linespacing=1.15)
fig.text(.5, .022, f"Source: EDFacts 2018-19; NCES CCD 2018-19. Schools: {out.schools.iloc[1]} charter, "
         f"{out.schools.iloc[0]} traditional public (math). Descriptive, not a causal estimate.",
         fontsize=7.5, color=SRC, ha="center", va="top")
fig.canvas.draw()
bb = title.get_window_extent().transformed(fig.transFigure.inverted())
logo = Image.open("data/raw/logo/flag.png").convert("RGBA")
px = np.array(logo); px[(px[..., :3] > 235).all(axis=2), 3] = 0
logo = Image.fromarray(px); logo = logo.crop(logo.getchannel("A").getbbox())
h = bb.height * 1.05; w = h * logo.width / logo.height * (11 / 8.5)
lax = fig.add_axes([bb.x0 - w - .02, bb.y0 + (bb.height - h) / 2, w, h]); lax.imshow(logo); lax.axis("off")
fig.savefig("figures/proficiency_vs_poverty_charter_fit.png", dpi=220, facecolor=BG)
fig.savefig("figures/proficiency_vs_poverty_charter_fit.pdf", facecolor=BG)
print(out.to_string())
