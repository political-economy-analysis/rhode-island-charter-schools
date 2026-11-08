"""Shared look for every exhibit and the memo: Charter font, Rhode Island flag palette, emblem.
Used by 02, 08, 11 (figures) and 14 (memo). Charter ships with macOS (Charter.ttc); its four faces are extracted
to a temp folder so matplotlib can use regular/bold/italic. Falls back to DejaVu Sans if Charter is missing."""
import os, tempfile
import numpy as np
import matplotlib
from matplotlib import font_manager as fm
from PIL import Image

TTC = "/System/Library/Fonts/Supplemental/Charter.ttc"
NAVY, GOLD, GOLD_D, SLATE = "#003478", "#F2B600", "#B58500", "#8A94A6"   # RI flag navy and gold, plus slate
INK, SRC, BG, GRID, LAND = "#000000", "#6b6a66", "#ffffff", "#e6e5e1", "#ececec"  # text black except sources
COL = {"Charter": NAVY, "Traditional public": GOLD, "Private": SLATE}
LOGO_SRC = "data/raw/logo/flag.png"      # RI flag emblem, public domain (Wikimedia Commons: Flag_of_Rhode_Island.svg)
LOGO_OUT = "data/raw/logo/ri_emblem.png"

def setup_fonts():
    family = "DejaVu Sans"
    try:
        from fontTools.ttLib import TTCollection
        d = os.path.join(tempfile.gettempdir(), "charter_fonts"); os.makedirs(d, exist_ok=True)
        for i, f in enumerate(TTCollection(TTC).fonts[:4]):
            p = os.path.join(d, f"Charter-{i}.ttf")
            if not os.path.exists(p): f.save(p)
            fm.fontManager.addfont(p)
        family = "Charter"
    except Exception as e:
        print("Charter font unavailable, using DejaVu Sans:", e)
    matplotlib.rcParams.update({"font.family": family, "text.color": INK, "axes.edgecolor": "#d9d8d4",
                                "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK})
    return family

def emblem():
    """Flag emblem with the white background made transparent and cropped to its content (also saved as PNG)."""
    im = Image.open(LOGO_SRC).convert("RGBA"); px = np.array(im)
    px[(px[..., :3] > 235).all(axis=2), 3] = 0
    im = Image.fromarray(px); im = im.crop(im.getchannel("A").getbbox())
    im.save(LOGO_OUT)
    return im
