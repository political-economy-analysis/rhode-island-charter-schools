"""Map RI charter schools as dots sized by enrollment (area proportional to enrollment,
anchored to the largest school). Inputs: data/processed/ri_charter_schools_2024.csv,
Census cartographic-boundary town shapefile in data/raw/ri_cousub/. Output: figures/ri_charter_map.png (standalone) or, with --memo, figures/memo/exhibit3_charter_map.png
(no title: the memo supplies the caption). Requires: matplotlib, pandas, pyshp."""
import math, os, sys
sys.path.insert(0, "scripts")
import style
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon
from matplotlib.lines import Line2D
import pandas as pd, shapefile

os.makedirs("figures", exist_ok=True)
df = pd.read_csv("data/processed/ri_charter_schools_2024.csv")
sf = shapefile.Reader("data/raw/ri_cousub/cb_2022_44_cousub_500k.shp")

def polys():
    out = []
    for s in sf.shapes():
        parts = list(s.parts) + [len(s.points)]
        for a, b in zip(parts[:-1], parts[1:]):
            out.append(Polygon(s.points[a:b], closed=True))
    return out

style.setup_fonts()
MEMO = "--memo" in sys.argv
FW, FH = (8.2, 6.3) if MEMO else (11, 8.2)
SURF, LAND, EDGE, INK, MUTED, DOT = style.BG, style.LAND, "#c9c9c9", style.INK, style.SRC, style.NAVY
MAXE = df.enrollment.max()
S_MAX = 330 * (FW / 11) ** 2  # marker area (pt^2) for the largest school; others scale linearly with enrollment
size = lambda e: S_MAX * e / MAXE

def draw(ax, xlim=None, ylim=None, ring=0.8):
    ax.add_collection(PatchCollection(polys(), facecolor=LAND, edgecolor=EDGE, linewidth=0.5))
    d = df.sort_values("enrollment", ascending=False)  # big first, small on top
    ax.scatter(d.longitude, d.latitude, s=size(d.enrollment), c=DOT, alpha=0.8,
               edgecolors=SURF, linewidths=ring, zorder=3)
    ax.set_aspect(1 / math.cos(math.radians(41.7)))
    ax.set_xlim(xlim or (-71.92, -71.08)); ax.set_ylim(ylim or (41.13, 42.03))
    ax.axis("off")

fig = plt.figure(figsize=(FW, FH), facecolor=SURF)
top = 0.95 if MEMO else 0.86
ax = fig.add_axes([0.0, 0.02, 0.55, top - 0.02]); draw(ax)
ax2 = fig.add_axes([0.52, 0.22, 0.46, top - 0.24])
box = ((-71.50, -71.33), (41.79, 41.93))
draw(ax2, *box, ring=0.8)
for sp in ax2.spines.values(): sp.set_visible(False)
ax2.set_title("Zoom: Providence, Central Falls, Pawtucket", fontsize=10, color=INK, fontweight="bold", loc="left")
# zoom box on main map
ax.plot([box[0][0], box[0][1], box[0][1], box[0][0], box[0][0]],
        [box[1][0], box[1][0], box[1][1], box[1][1], box[1][0]], color=MUTED, lw=0.8, zorder=4)

# label the five largest schools on the zoom or main map
OFFS = {"Iluminar": (12, -16, "left"), "Promesa": (12, 8, "left")}   # keep the two Achievement First labels apart
for _, r in df.nlargest(5, "enrollment").iterrows():
    in_box = box[0][0] < r.longitude < box[0][1] and box[1][0] < r.latitude < box[1][1]
    a = ax2 if in_box else ax
    dx, dy, ha = next((v for k, v in OFFS.items() if k in r.school_name), ((-10, 10, "right") if r.longitude > -71.40 else (10, 10, "left")))
    a.annotate(f"{r.school_name} ({int(r.enrollment):,})", (r.longitude, r.latitude), xytext=(dx, dy), ha=ha,
               textcoords="offset points", fontsize=8, color=INK, zorder=5,
               bbox=dict(boxstyle="round,pad=0.15", fc=SURF, ec="none", alpha=0.8))

# size legend
leg = [Line2D([0], [0], marker="o", ls="", markerfacecolor=DOT, markeredgecolor=SURF, alpha=0.8,
              markersize=math.sqrt(size(v)), label=f"{v:,}") for v in (100, 300, int(MAXE))]
fig.legend(handles=leg, title="Students enrolled", loc="lower right", bbox_to_anchor=(0.97, 0.03),
           frameon=False, labelspacing=1.4, borderpad=0.5, fontsize=9, title_fontsize=9, labelcolor=INK)
if not MEMO:
    fig.text(0.02, 0.945, "Providence hosts nearly half of Rhode Island's charter enrollment", fontsize=15,
             fontweight="bold", color=INK)
if not MEMO:
    fig.text(0.02, 0.905, f"{len(df)} charter school sites, 2024-25; dot area is proportional to enrollment "
         f"(largest: {df.loc[df.enrollment.idxmax(), 'school_name']}, {int(MAXE):,} students)", fontsize=10, color=INK)
fig.text(0.02, 0.025 if MEMO else 0.012, "Source: Urban Institute Education Data Portal (NCES Common Core of Data); "
         "town boundaries: U.S. Census Bureau cartographic boundary file.", fontsize=8, color=MUTED)
fig.savefig("figures/memo/exhibit3_charter_map.png" if MEMO else "figures/ri_charter_map.png", dpi=220, facecolor=SURF)
print(df.nlargest(5, "enrollment")[["school_name", "city_location", "enrollment"]])
