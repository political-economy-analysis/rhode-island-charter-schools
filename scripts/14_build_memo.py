"""Build memo.pdf (reportlab) and memo.docx (python-docx) from one text source: memo, three exhibits,
technical appendix, references. Font: Charter. Page numbers "n/total". Checks the memo's 1,000-word limit
(header, headings, body, captions; the appendix and references are outside the limit).
Every number traces to a script: Exhibit 1 -> 08, Exhibit 2 -> 11 (needs 09), Exhibit 3 -> 02, other statistics -> 13.
Run order is in Appendix A. Usage (from the project root): python3 scripts/14_build_memo.py
"""
import re, sys
import pandas as pd
sys.path.insert(0, "scripts")
import style
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle,
                                HRFlowable, CondPageBreak)
from PIL import Image as PILImage
import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

P = "data/processed/"
# ====================================================================== MEMO TEXT
HEADER = [("TO:", "Governor-elect, State of Rhode Island"),
          ("FROM:", "Alexander McAllister, Policy Analyst"),
          ("DATE:", "November 9, 2026"),
          ("RE:", "Lifting the charter moratorium and doubling the cap from 28 to 56")]

SECTIONS = [
 ("Bottom line", [
  "Lifting the moratorium and doubling the cap would probably raise statewide proficiency, but only slightly and with real "
  "uncertainty. Rhode Island's charters serve mostly low-income students of color and score well above what their poverty "
  "levels predict, and rigorous studies elsewhere find large urban charter gains. But charters enroll only 10% of public-school "
  "students, so even large per-student gains move the statewide rate by about one point at most. Effects and budget strain would "
  "concentrate in Providence and nearby cities. The outcome depends on which operators expand."]),
 ("The proposal and the starting point", [
  "The June 18, 2026 law pauses charter approvals and expansion through 2028-29, limits new charter funding through fiscal 2029, "
  "and cut the cap from 35 to 28. The proposal would end the pause and raise the cap to 56. Rhode Island has 24 charters running "
  "42 school sites with 13,465 students, 10% of charter and district enrollment. They serve a needier population (Exhibit 1): "
  "79% of charter students are low-income (eligible for free or reduced-price lunch) versus 51% in district schools, and 81% are "
  "students of color versus 47%. Because families choose to apply, raw comparisons mislead; this memo leans on studies that "
  "account for that."]),
 ("Overall proficiency", [
  "<b>Raw scores are about equal.</b> In 2018-19, charter students were 31% proficient in math and 41% in reading, versus 31% and "
  "43% in district schools. But charters enroll poorer students, who score lower anywhere. Compared with district schools of "
  "similar poverty, charters score about 12 points higher in math and 14 in reading (Exhibit 2). That is suggestive, not proof: "
  "applicants may differ in ways lunch eligibility misses.",
  "<b>Lottery studies</b>, which compare students who narrowly won and lost admission, remove that problem. Boston charters "
  "produced large gains (Abdulkadiroğlu et al. 2011), and new campuses matched their parents after the sector's market share "
  "doubled (Cohodes, Setren and Walters 2021). Gains concentrate in urban “No Excuses” schools; Massachusetts charters "
  "outside cities lowered achievement (Angrist, Pathak and Walters 2013). Nationally, charter students gain 16 more days of "
  "learning in reading and 6 in math per year (CREDO 2023).",
  "<b>The statewide effect is diluted.</b> Doubling charter enrollment lifts the charter share to about 20%. If each switching "
  "student gained 5 percentage points in proficiency, the statewide rate would rise half a point; at 10 points, one point."]),
 ("Inequality", [
  "In 2018-19, charter students scored higher in math than district peers in every group: Black 35% proficient versus 16%, "
  "Hispanic 27% versus 13%, low-income 28% versus 14%, English learners 26% versus 8%, students with disabilities 23% versus 14%. "
  "The white-Black gap is 15 points at charters and 24 in district schools. These raw averages, from 18 to 32 charters per group, "
  "are not causal, and I did not test whether charters enroll and keep their share of students with disabilities or English "
  "learners. Lottery studies find the largest gains for low-income, non-white and lower-scoring urban students. If new charters "
  "resemble existing ones, expansion would modestly narrow gaps; because charters serve few students, the aggregate effect "
  "would be small."]),
 ("Geography", [
  "Charters cluster in the urban core: 36 of 42 sites and 87% of charter students are in six cities, and Providence alone hosts "
  "46% (Exhibit 3). Charter seats sited in Central Falls equal 53 per 100 district-school students there; Cumberland 32, "
  "Providence 30, Woonsocket 19, Cranston 11, Pawtucket 10. These show where seats are, not where students live. Per-pupil "
  "funding follows the student, so districts lose revenue at once while building, bus and staff costs fall slowly; Governor "
  "McKee cited about 10,000 students leaving public schools since 2021. Suburban and rural districts would feel little direct "
  "effect. Charter operators report lower spending per pupil ($15.6k versus $18.6k, fiscal 2020), though not like for like."]),
 ("Other constituencies", [
  "<b>Teachers:</b> charters employ about 1,000 teachers versus 9,300 in district schools. Moving 13,465 students would create "
  "roughly 1,000 charter jobs and cut district staffing needs by a similar number, through attrition or layoffs. A few charters, "
  "including Paul Cuffee, have recently unionized. <b>Taxpayers:</b> stranded costs fall on municipal budgets. <b>Families:</b> "
  "waitlist data were unavailable. <b>Operators:</b> a Providence dual-language charter blocked by the pause is suing."]),
 ("Risks, uncertainty and recommendation", [
  "Key uncertainties: new charters may underperform established ones; the best evidence is from Massachusetts, and I found no "
  "lottery study of Rhode Island charters; poverty is measured crudely; test data are from 2018-19. A neutral design could end "
  "the pause but condition approvals on operator track record, high-need locations, and enrollment of students with "
  "disabilities and English learners; phase the cap (say 28 to 40, then review); and give sending districts transition aid. "
  "Rhode Island lottery results, subgroup enrollment and attrition data, and early results from new schools would change this "
  "assessment."]),
]

EXHIBITS = [
 ("Exhibit 1. Charters serve a needier student body (math panel weighted by students tested)", "figures/memo/exhibit1_sector_comparison.png"),
 ("Exhibit 2. Charters sit above the poverty-adjusted line; raw averages are equal (averages weighted by enrollment)", "figures/memo/exhibit2_proficiency_vs_poverty.png"),
 ("Exhibit 3. Providence hosts nearly half of charter enrollment (42 sites, 2024-25; dot area proportional to enrollment)", "figures/memo/exhibit3_charter_map.png"),
]

# ====================================================================== APPENDIX CONTENT (blocks)
f1 = lambda v: f"{v:.1f}"
sc = pd.read_csv(P + "sector_comparison_summary.csv").set_index("sector")
bands = pd.read_csv(P + "sector_comparison_math_by_poverty.csv")
cent = pd.read_csv(P + "proficiency_vs_poverty_centroids.csv")
vline = pd.read_csv(P + "memo_statistics_charter_vs_line.csv").set_index("subject")
city = pd.read_csv(P + "memo_statistics_charter_by_city.csv").head(6)
sub = pd.read_csv(P + "memo_statistics_subgroups.csv"); sub = sub[sub.subject == "math"]
C, T = "Charter", "Traditional public"

band_rows = [[b, f1(bands[(bands.poverty_band == b) & (bands.sector == C)].math_proficiency_2018_19.iloc[0]),
              f1(bands[(bands.poverty_band == b) & (bands.sector == T)].math_proficiency_2018_19.iloc[0]),
              str(int(bands[(bands.poverty_band == b) & (bands.sector == C)].schools.iloc[0])),
              str(int(bands[(bands.poverty_band == b) & (bands.sector == T)].schools.iloc[0]))] for b in ("Under 60%", "60-80%", "Over 80%")]
cent_rows = []
for subj, name in (("math", "Math"), ("read", "Reading")):
    for sec in (C, T):
        r = cent[(cent.subject == subj) & (cent.sector == sec)].iloc[0]
        cent_rows.append([name, sec, str(int(r.schools)), f"{r.students_enrolled:,.0f}", f1(r.avg_low_income_pct), f1(r.avg_proficiency_pct)])
gap_rows = [[n, f1(vline.loc[s, "charter_avg_low_income"]), f1(vline.loc[s, "line_predicts"]), f1(vline.loc[s, "charter_avg_proficiency"]),
             f"+{vline.loc[s, 'charter_above_line_pts']:.1f}"] for s, n in (("math", "Math"), ("read", "Reading"))]
city_rows = [[r.city, str(int(r.sites)), f"{r.charter_students:,.0f}", f1(r.share_of_charter_students), f1(r.charter_seats_per_100_district_students)]
             for r in city.itertuples()]
order = ["Black", "Hispanic", "White", "Low-income", "English learners", "Students with disabilities"]
sub_rows = []
for g in order:
    a = sub[(sub.group == g) & (sub.sector == C)].iloc[0]; b = sub[(sub.group == g) & (sub.sector == T)].iloc[0]
    sub_rows.append([g, f1(a.proficient_pct), f1(b.proficient_pct), str(int(a.schools)), str(int(b.schools))])

APPENDIX = [
 ("p", "This appendix documents how each exhibit and number in the memo was produced, so a technical reader can rebuild them. "
       "All code is in the project's <i>scripts/</i> folder and runs from the project root. All data are public; no API keys or "
       "passwords are needed. Paths are relative to the project root."),
 ("h2", "A. Reproduction"),
 ("p", "<b>Environment.</b> Python 3.9.6 with pandas 2.3.3, numpy 2.0.2, matplotlib 3.9.4, pyshp 3.1.6, pillow 11.3.0, "
       "fonttools 4.60.2, reportlab 5.0.1 and python-docx. Figures and this document use the Charter font that ships with macOS "
       "(figure scripts fall back to DejaVu Sans if it is missing). Downloads are cached in <i>data/raw/</i> and reused."),
 ("table", ["Script", "Purpose", "Main output"], [
   ["01", "Charter school list (CCD directory, 2024)", "ri_charter_schools_2024.csv"],
   ["03", "Adds district finance (FY2020) to school lists", "*_enriched.csv"],
   ["05", "Private schools from the NCES Private School Survey", "ri_private_schools_2021.csv"],
   ["06", "Test-score, graduation and race-enrollment downloads", "ri_edfacts_*.csv; ri_ccd_enrollment_by_race.csv"],
   ["07", "Master list of charter, traditional public and private schools", "ri_school_master_list.csv"],
   ["08", "Exhibit 1 (sector comparison); --memo gives the memo version", "figures/memo/exhibit1_*.png"],
   ["09", "School-level scores and poverty, 2018-19", "proficiency_vs_poverty_schools.csv"],
   ["11", "Exhibit 2 (scores against poverty); --memo version", "figures/memo/exhibit2_*.png"],
   ["02", "Exhibit 3 (charter map); --memo version", "figures/memo/exhibit3_*.png"],
   ["13", "Other statistics quoted in the memo", "memo_statistics_*.csv"],
   ["14", "Builds this document", "memo.pdf, memo.docx"]], [0.55, 3.6, 2.15]),
 ("p", "Run order: 01, 03, 05, 06, 07; then 08, 09, 11 and 02; then 13; then 02, 08 and 11 again with <i>--memo</i>; then 14. "
       "Scripts 04 (interactive map), 10 and 12 (chart variants) are not used in the memo."),
 ("h2", "B. Data sources and conventions"),
 ("table", ["Source", "Used for", "Access"], [
   ["Urban Institute Education Data Portal: NCES Common Core of Data (CCD)",
    "School directory for 2018, 2020 and 2024 (charter flag, enrollment, lunch eligibility, teachers FTE, coordinates); enrollment by "
    "race (2020, 2024); district finance (2020)",
    "educationdata.urban.org/api/v1/ : schools/ccd/directory/{year}/?fips=44; schools/ccd/enrollment/{year}/grade-99/race/; "
    "school-districts/ccd/finance/2020/"],
   ["Urban Institute Education Data Portal: EDFacts assessments",
    "Share proficient in math and reading by school, grade (3-9), race and special-population group; 2015-18 and 2020",
    "schools/edfacts/assessments/{year}/grade-{g}/ with optional race/ or special-populations/"],
   ["NCES Private School Universe Survey, 2021-22", "Private school enrollment, teachers, percent White, affiliation, coordinates",
    "nces.ed.gov/surveys/pss/zip/pss2122_pu_csv.zip"],
   ["U.S. Census Bureau cartographic boundary file, 2022 county subdivisions", "Rhode Island town outlines for the map",
    "cb_2022_44_cousub_500k, stored in data/raw/ri_cousub/"],
   ["Flag of Rhode Island (public domain)", "Emblem on page 1", "Wikimedia Commons; data/raw/logo/flag.png"]], [1.75, 2.6, 1.95]),
 ("bullets", [
   "<b>Years.</b> The portal's year is read as the start of the school year (2018 = 2018-19; 2024 = 2024-25). This is an inference "
   "from the portal's conventions, not a documented fact, and should be confirmed.",
   "<b>Proficiency</b> is published as a range (low, high, midpoint). All results use the midpoint. Values coded -1 (missing), -2 "
   "(not applicable) or -3 (suppressed) are dropped; about 98% of school-grade rows in each year are usable.",
   "<b>Low-income</b> means eligible for free or reduced-price lunch, divided by enrollment. Schools that offer lunch to all "
   "students may report this inconsistently.",
   "<b>Students of color</b> is 100 minus the White share (CCD race file; for private schools, 100 minus the survey's percent White)."]),
 ("h2", "C. School universe"),
 ("p", "The master list (script 07) holds every school in the 2024 CCD directory with positive enrollment and status open or new: "
       "263 traditional public schools and 42 charter school sites, plus 86 private schools with positive enrollment in the survey "
       "(391 in all). Eleven directory entries were excluded because they report no enrollment (career-technical centers, annexes "
       "and two closed schools). “Charter” follows the CCD charter flag. The memo's 24 charters are the 24 operators "
       "running those 42 sites, matching a June 2026 Rhode Island Current count; the cap of 28 counts charters, not sites. "
       "In test-score tables, a school is a charter if it appears in the 2024 or 2020 charter lists (Exhibit 1) or is flagged in "
       "the 2018 directory (Exhibit 2)."),
 ("h2", "D. Exhibit 1: sector comparison (script 08)"),
 ("table", ["Panel", "Definition", "Weights and values"], [
   ["Low-income students", "Free or reduced-price lunch count ÷ enrollment, CCD 2024-25 (public sectors only)",
    "Enrollment-weighted mean over schools. Charter %s%%; traditional %s%%" % (f1(sc.loc[C, "frl"]), f1(sc.loc[T, "frl"]))],
   ["Students of color", "100 × (1 − White enrollment ÷ total), CCD 2024-25; private: survey percent White",
    "Enrollment-weighted. Charter %s%%; traditional %s%%; private %s%%" % (f1(sc.loc[C, "poc"]), f1(sc.loc[T, "poc"]), f1(sc.loc["Private", "poc"]))],
   ["Students per teacher", "Total enrollment ÷ total teacher FTE (private: 2021-22)",
    "Charter %s; traditional %s; private %s" % (f1(sc.loc[C, "spt"]), f1(sc.loc[T, "spt"]), f1(sc.loc["Private", "spt"]))],
   ["Spending per pupil", "Current spending on elementary-secondary education ÷ district enrollment, FY2020 (CCD finance); "
    "enrollment is the sum of 2020 school enrollments in the operator. Districts that merely contain a charter (Providence, Cranston) are "
    "excluded from the charter figure",
    "Weighted by operator enrollment: %d charter-only operators, $%s; %d districts, $%s" % (
        sc.loc[C, "spend_n"], f"{sc.loc[C, 'spend']:,.0f}", sc.loc[T, "spend_n"], f"{sc.loc[T, 'spend']:,.0f}")],
   ["Math proficiency, grades 3-9, 2018-19", "Midpoint share proficient, weighted by students tested. Poverty bands use each school's "
    "lunch eligibility in the 2020 directory",
    "All schools: charter %s%%; traditional %s%%. Bands below" % (f1(sc.loc[C, "math_2018_19"]), f1(sc.loc[T, "math_2018_19"]))],
   ["Students enrolled", "Sum of enrollment, CCD 2024-25 and survey 2021-22",
    "Charter %s; traditional %s; private %s" % (f"{sc.loc[C, 'students']:,.0f}", f"{sc.loc[T, 'students']:,.0f}", f"{sc.loc['Private', 'students']:,.0f}")]],
  [1.35, 2.85, 2.1]),
 ("table", ["Poverty band", "Charter % proficient", "Traditional % proficient", "Charter schools", "Traditional schools"], band_rows,
  [1.2, 1.3, 1.5, 1.1, 1.2]),
 ("h2", "E. Exhibit 2: scores against poverty (scripts 09 and 11)"),
 ("bullets", [
   "<b>Unit:</b> the school. Poverty is free or reduced-price lunch ÷ enrollment from the 2018 directory, capped at 100%. "
   "Proficiency is the midpoint share proficient averaged over grades 3-9, weighted by students tested. Schools missing either "
   "value are dropped: 33 charters and 257 traditional public schools (math and reading alike). Marker area grows with the "
   "square root of students tested.",
   "<b>Dashed line:</b> least squares fit of proficiency on poverty for traditional schools only (numpy.polyfit, degree 1, weights "
   "equal to the square root of students tested, so each school counts in proportion to students tested). Math: intercept 53.9, "
   "slope −0.51 points per percentage point of poverty. Reading: intercept 68.4, slope −0.61.",
   "<b>Diamonds:</b> sector averages of poverty and proficiency, weighted by school enrollment. The gap is the charter average "
   "minus the line's prediction at the charter average poverty level.",
   "Exhibit 1's math panel weights by students tested (charters 33.8%) and Exhibit 2 by enrollment (30.5%), which includes grades "
   "not tested; the memo's text quotes Exhibit 2."]),
 ("table", ["Subject", "Sector", "Schools", "Students enrolled", "Avg. low-income %", "Avg. proficient %"], cent_rows,
  [0.8, 1.5, 0.8, 1.2, 1.0, 1.0]),
 ("table", ["Subject", "Charter avg. low-income %", "Line predicts %", "Charter avg. proficient %", "Charter above line (points)"], gap_rows,
  [0.9, 1.5, 1.2, 1.4, 1.3]),
 ("h2", "F. Exhibit 3 and geography (scripts 02 and 13)"),
 ("p", "Each dot is a charter site at its 2024 CCD coordinates; area is proportional to enrollment (largest: RISE Prep Mayoral "
       "Academy, 573 students). Town outlines come from the Census file above; the inset zooms on Providence, Central Falls and "
       "Pawtucket. Each site is assigned to its listed city. Charter seats per 100 students divides charter enrollment in a city by "
       "enrollment of traditional public schools located in that city. Charters draw students from several towns, so the ratio shows "
       "where seats are, not where students live. The six cities below hold 36 of 42 sites and 87.4% of charter students."),
 ("table", ["City", "Charter sites", "Charter students", "% of charter students", "Seats per 100 district students"], city_rows,
  [1.4, 1.0, 1.3, 1.3, 1.3]),
 ("h2", "G. Other memo statistics (script 13)"),
 ("p", "Math proficiency by group, 2018-19 (midpoint share proficient, weighted by students tested; school counts are schools with "
       "scores for the group):"),
 ("table", ["Group", "Charter %", "Traditional %", "Charter schools", "Traditional schools"], sub_rows, [2.0, 1.0, 1.2, 1.1, 1.0]),
 ("bullets", [
   "<b>Gap by race:</b> white minus Black proficiency is 49.3 − 34.6 = 14.7 points at charters and 39.1 − 15.5 = 23.6 in "
   "traditional schools.",
   "<b>Scenario:</b> charters enroll 13,465 of 133,879 charter and district students (10.1%). If charter enrollment doubled with "
   "students moving from districts, the share would be 20.1%. Statewide change = 13,465 × g ÷ 133,879, where g is the "
   "proficiency gain per switching student: g = 2.5 gives 0.25 points, g = 5 gives 0.50, g = 10 gives 1.01. The gain g is an "
   "assumption for illustration, not an estimate.",
   "<b>Teachers:</b> teacher FTE is 995 at charters and 9,298 at traditional schools. Students moved ÷ students per teacher: "
   "13,465 ÷ 13.0 ≈ 1,040 district FTE and 13,465 ÷ 13.5 ≈ 995 charter FTE, assuming staffing scales with enrollment.",
   "<b>Cap:</b> 24 charters operate under a cap of 28, leaving 4 slots; the proposal would allow 56."]),
 ("h2", "H. Limitations"),
 ("bullets", [
   "Descriptive comparisons do not separate school effects from who enrolls. The memo's causal evidence rests on the cited lottery "
   "studies; none is from Rhode Island, and I did not read CREDO's Rhode Island report.",
   "Test data are from 2018-19. Results the portal labels 2020 show charters lower (math 15.9% versus 21.7%); they appear to be 2020-21, "
   "when far fewer students were tested, and are not used.",
   "Lunch eligibility is a crude poverty measure; Exhibit 1's bands use 2020 data and Exhibit 2 uses 2018.",
   "Spending compares charter-only operators with whole districts for FY2020 and is not like for like.",
   "Subgroup results rest on 18 to 32 charters per group and on midpoints of reported ranges; no significance tests were run.",
   "The staffing and fiscal scenarios assume proportional staffing and unchanged per-pupil funding."]),
]

REFS = [
 ("Research", [
  "Abdulkadiroğlu, A., Angrist, J. D., Dynarski, S. M., Kane, T. J., and Pathak, P. A. (2011). Accountability and flexibility in "
  "public schools: Evidence from Boston's charters and pilots. <i>Quarterly Journal of Economics</i>, 126(2), 699–748. "
  "https://doi.org/10.1093/qje/qjr017",
  "Angrist, J. D., Pathak, P. A., and Walters, C. R. (2013). Explaining charter school effectiveness. <i>American Economic Journal: "
  "Applied Economics</i>, 5(4), 1–27. https://doi.org/10.1257/app.5.4.1",
  "Cohodes, S., Setren, E., and Walters, C. R. (2021). Can successful schools replicate? Scaling up Boston's charter school sector. "
  "<i>American Economic Journal: Economic Policy</i>, 13(1), 138–167. "
  "https://econpapers.repec.org/RePEc:aea:aejpol:v:13:y:2021:i:1:p:138-67",
  "Center for Research on Education Outcomes (CREDO) (2023). <i>National Charter School Study III</i>. Stanford University. "
  "Figures cited (16 days in reading, 6 in math) are from the press release: "
  "https://credo.stanford.edu/wp-content/uploads/2023/06/NCSS3-Press-Release-.pdf"]),
 ("Law, policy and news", [
  "Ballotpedia (July 15, 2026). Rhode Island enacts three-year charter school moratorium. "
  "https://news.ballotpedia.org/2026/07/15/rhode-island-enacts-three-year-charter-school-moratorium/",
  "Rhode Island Current (June 18, 2026). McKee signs charter school moratorium bills with five days to spare, ending uncertainty. "
  "https://rhodeislandcurrent.com/2026/06/18/mckee-signs-charter-school-moratorium-bills-with-five-days-to-spare-ending-uncertainty/",
  "Providence Business News. Paul Cuffee becomes first fully unionized charter school in R.I. "
  "https://pbn.com/paul-cuffee-becomes-first-fully-unionized-charter-school-in-r-i/",
  "Rhode Island Department of Education, Funding Formula Working Group, charter school funding presentation (the statement that "
  "state and local per-pupil funding follows the student; not read in full, so confirm against current law, R.I. Gen. Laws title 16, "
  "chapter 77). https://ride.ri.gov/Portals/0/Uploads/Documents/Funding-and-Finance-Wise-Investments/Funding-Sources/"
  "State-Education-Aid-Funding-Formula/FundingFormulaWorkingGroup/Mtg2-Charter_Schools_presentation.pdf",
  "Debate #3 preparation sheet (course materials): background on the June 18, 2026 law."]),
 ("Data", [
  "Urban Institute, Education Data Portal (NCES Common Core of Data; EDFacts). https://educationdata.urban.org/",
  "National Center for Education Statistics, Private School Universe Survey, 2021-22. https://nces.ed.gov/surveys/pss/",
  "U.S. Census Bureau, cartographic boundary files, 2022 county subdivisions (Rhode Island, 1:500,000).",
  "Flag of Rhode Island, Wikimedia Commons (public domain), used for the emblem on page 1."]),
]

# ====================================================================== word count (memo only)
strip = lambda s: re.sub(r"<[^>]+>", "", s)
memo_text = [f"{k} {v}" for k, v in HEADER] + ["MEMORANDUM"] + [t for t, _ in SECTIONS] + [strip(p) for _, ps in SECTIONS for p in ps] \
            + [c for c, _ in EXHIBITS]
words = sum(len(t.split()) for t in memo_text)
print(f"memo word count: {words} (header, headings, body, exhibit captions)")
assert words <= 1000, "over the 1,000-word limit"

# ====================================================================== PDF
for name, idx in (("Charter", 0), ("Charter-Italic", 1), ("Charter-BoldItalic", 2), ("Charter-Bold", 3)):
    pdfmetrics.registerFont(TTFont(name, style.TTC, subfontIndex=idx))
pdfmetrics.registerFontFamily("Charter", normal="Charter", bold="Charter-Bold", italic="Charter-Italic", boldItalic="Charter-BoldItalic")
K = colors.black
body = ParagraphStyle("body", fontName="Charter", fontSize=10, leading=13.4, textColor=K, spaceAfter=5)
h = ParagraphStyle("h", fontName="Charter-Bold", fontSize=10.5, leading=13, textColor=K, spaceBefore=7, spaceAfter=2.5)
title = ParagraphStyle("title", fontName="Charter-Bold", fontSize=17, leading=20, textColor=K)
hdr = ParagraphStyle("hdr", fontName="Charter", fontSize=10, leading=13, textColor=K)
hdrb = ParagraphStyle("hdrb", parent=hdr, fontName="Charter-Bold")
cap = ParagraphStyle("cap", fontName="Charter-Bold", fontSize=10.5, leading=13, textColor=K, spaceAfter=6)
tcell = ParagraphStyle("tcell", fontName="Charter", fontSize=8, leading=10, textColor=K)
tcellb = ParagraphStyle("tcellb", parent=tcell, fontName="Charter-Bold")
bullet = ParagraphStyle("bullet", parent=body, leftIndent=12, bulletIndent=2, spaceAfter=3.5)
ref = ParagraphStyle("ref", parent=body, fontSize=9, leading=11.8, leftIndent=14, firstLineIndent=-14, spaceAfter=4)
esc = lambda s: s.replace("&", "&amp;")

class NumberedCanvas(canvas.Canvas):
    """Page numbers in the form n/total."""
    def __init__(self, *a, **k):
        super().__init__(*a, **k); self._saved = []
    def showPage(self):
        self._saved.append(dict(self.__dict__)); self._startPage()
    def save(self):
        n = len(self._saved)
        for st in self._saved:
            self.__dict__.update(st)
            self.setFont("Charter", 8.5); self.setFillColor(K)
            self.drawCentredString(letter[0] / 2, 0.5 * inch, f"{self._pageNumber}/{n}")
            super().showPage()
        super().save()

def pdf_table(header, rows, widths):
    data = [[Paragraph(esc(c), tcellb) for c in header]] + [[Paragraph(esc(c), tcell) for c in r] for r in rows]
    t = Table(data, colWidths=[w * inch for w in widths], hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                           ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                           ("LINEABOVE", (0, 0), (-1, 0), 0.8, K), ("LINEBELOW", (0, 0), (-1, 0), 0.5, K),
                           ("LINEBELOW", (0, -1), (-1, -1), 0.8, K)]))
    return [Spacer(1, 3), t, Spacer(1, 7)]

doc = SimpleDocTemplate("memo.pdf", pagesize=letter, leftMargin=1 * inch, rightMargin=1 * inch, topMargin=0.85 * inch,
                        bottomMargin=0.85 * inch, title="Lifting the charter moratorium and doubling the cap from 28 to 56",
                        author="Alexander McAllister")
style.emblem()
story = []
logo_w = 0.72 * inch
lw, lh = PILImage.open(style.LOGO_OUT).size
top = Table([[Image(style.LOGO_OUT, width=logo_w, height=logo_w * lh / lw), Paragraph("MEMORANDUM", title)]],
            colWidths=[0.95 * inch, 5.35 * inch], hAlign="LEFT")
top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
story += [top, Spacer(1, 7)]
t = Table([[Paragraph(a, hdrb), Paragraph(b, hdr)] for a, b in HEADER], colWidths=[0.75 * inch, 5.55 * inch], hAlign="LEFT")
t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
                       ("TOPPADDING", (0, 0), (-1, -1), 0)]))
story += [t, Spacer(1, 4), HRFlowable(width="100%", thickness=0.8, color=K, spaceBefore=2, spaceAfter=2)]
for i, (head, paras) in enumerate(SECTIONS, 1):
    story += [CondPageBreak(0.9 * inch), Paragraph(f"{i}. {head}", h)] + [Paragraph(esc(p), body) for p in paras]
for c, path in EXHIBITS:
    w, hh = PILImage.open(path).size
    s = min(6.5 * inch / w, 8.4 * inch / hh)
    story += [PageBreak(), Paragraph(esc(c), cap), Image(path, width=w * s, height=hh * s, hAlign="CENTER")]
story += [PageBreak(), Paragraph("TECHNICAL APPENDIX", title), Spacer(1, 4), HRFlowable(width="100%", thickness=0.8, color=K, spaceAfter=3)]
for blk in APPENDIX:
    kind = blk[0]
    if kind == "p": story.append(Paragraph(esc(blk[1]), body))
    elif kind == "h2": story += [CondPageBreak(1.1 * inch), Paragraph(blk[1], h)]
    elif kind == "bullets": story += [Paragraph(esc(b), bullet, bulletText="•") for b in blk[1]]
    elif kind == "table": story += pdf_table(blk[1], blk[2], blk[3])
story += [PageBreak(), Paragraph("REFERENCES", title), Spacer(1, 4), HRFlowable(width="100%", thickness=0.8, color=K, spaceAfter=3)]
for grp, items in REFS:
    story += [CondPageBreak(1.0 * inch), Paragraph(grp, h)] + [Paragraph(esc(x), ref) for x in items]
doc.build(story, canvasmaker=NumberedCanvas)

# ====================================================================== DOCX
d = docx.Document()
sec = d.sections[0]; sec.left_margin = sec.right_margin = Inches(1); sec.top_margin = sec.bottom_margin = Inches(0.85)
st = d.styles["Normal"]; st.font.name = "Charter"; st.font.size = Pt(10); st.font.color.rgb = RGBColor(0, 0, 0)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Charter")
st.paragraph_format.space_after = Pt(4); st.paragraph_format.line_spacing = 1.12

def runs(par, text, size=None, bold=None):
    for tok in re.split(r"(<b>.*?</b>|<i>.*?</i>)", text):
        if not tok: continue
        b, i = tok.startswith("<b>"), tok.startswith("<i>")
        r = par.add_run(strip(tok)); r.bold = True if (b or bold) else None; r.italic = True if i else None
        r.font.name = "Charter"; r.font.color.rgb = RGBColor(0, 0, 0)
        if size: r.font.size = Pt(size)

def rule(par):
    pPr = par._p.get_or_add_pPr(); bd = OxmlElement("w:pBdr"); bt = OxmlElement("w:bottom")
    for k, v in (("val", "single"), ("sz", "8"), ("space", "1"), ("color", "000000")): bt.set(qn(f"w:{k}"), v)
    bd.append(bt); pPr.append(bd)

def field(par, code):
    for kind, txt in (("begin", None), (None, code), ("end", None)):
        r = par.add_run(); r.font.name = "Charter"; r.font.size = Pt(8.5)
        if kind:
            fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), kind); r._r.append(fc)
        else:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = txt; r._r.append(it)

fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
field(fp, "PAGE"); r = fp.add_run("/"); r.font.name = "Charter"; r.font.size = Pt(8.5); field(fp, "NUMPAGES")

def cell_borders(table):
    b = OxmlElement("w:tblBorders")
    for edge in ("top", "bottom"):
        e = OxmlElement(f"w:{edge}"); e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "8"); e.set(qn("w:color"), "000000"); b.append(e)
    table._tbl.tblPr.append(b)

def docx_table(header, rows, widths):
    t = d.add_table(rows=1 + len(rows), cols=len(header)); t.alignment = WD_TABLE_ALIGNMENT.LEFT; cell_borders(t); t.autofit = False
    for ri, rowvals in enumerate([header] + rows):
        for ci, val in enumerate(rowvals):
            c = t.cell(ri, ci); c.width = Inches(widths[ci]); p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(1)
            runs(p, val, size=8, bold=(ri == 0))
    d.add_paragraph().paragraph_format.space_after = Pt(2)

def heading(text, size=10.5):
    p = d.add_paragraph(); p.paragraph_format.space_before = Pt(6); p.paragraph_format.keep_with_next = True
    runs(p, text, size=size, bold=True)

tb = d.add_table(rows=1, cols=2); tb.autofit = False
tb.cell(0, 0).width = Inches(0.95); tb.cell(0, 1).width = Inches(5.5)
tb.cell(0, 0).paragraphs[0].add_run().add_picture(style.LOGO_OUT, width=Inches(0.72))
runs(tb.cell(0, 1).paragraphs[0], "MEMORANDUM", size=17, bold=True)
tb.cell(0, 1).vertical_alignment = WD_ALIGN_VERTICAL.CENTER
for a, b in HEADER:
    p = d.add_paragraph(); p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.tab_stops.add_tab_stop(Inches(0.8)); runs(p, a, bold=True); runs(p, "\t" + b)
rule(d.add_paragraph())
for i, (head, paras) in enumerate(SECTIONS, 1):
    heading(f"{i}. {head}")
    for para in paras: runs(d.add_paragraph(), para)
for c, path in EXHIBITS:
    d.add_page_break(); p = d.add_paragraph(); runs(p, c, size=10.5, bold=True)
    w, hh = PILImage.open(path).size
    d.add_picture(path, width=Inches(min(6.5, 8.4 * w / hh))); d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
d.add_page_break(); runs(d.add_paragraph(), "TECHNICAL APPENDIX", size=17, bold=True); rule(d.add_paragraph())
for blk in APPENDIX:
    kind = blk[0]
    if kind == "p": runs(d.add_paragraph(), blk[1])
    elif kind == "h2": heading(blk[1])
    elif kind == "bullets":
        for b in blk[1]:
            p = d.add_paragraph(); p.paragraph_format.left_indent = Inches(0.18); p.paragraph_format.first_line_indent = Inches(-0.14)
            runs(p, "• " + b)
    elif kind == "table": docx_table(blk[1], blk[2], blk[3])
d.add_page_break(); runs(d.add_paragraph(), "REFERENCES", size=17, bold=True); rule(d.add_paragraph())
for grp, items in REFS:
    heading(grp)
    for x in items:
        p = d.add_paragraph(); p.paragraph_format.left_indent = Inches(0.2); p.paragraph_format.first_line_indent = Inches(-0.2)
        runs(p, x, size=9)
d.save("memo.docx")
print("wrote memo.pdf and memo.docx")
