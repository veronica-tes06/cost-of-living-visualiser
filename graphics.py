"""Static charts (PNG and SVG) for the Cost of Living Visualizer reports.

Minimum wage is the main income measure, with the average net salary (chart 8) shown alongside it,
because the average salary mixes all jobs and does not represent students or low earners.
Chart 9 compares city-centre and outside rent, which answers the group's question of how to
represent rent when it depends on location.

The following function remains available but is skipped by the command below:
 13  Coverage by salary (the data is a single snapshot)

Run python graphics.py to save PNGs and the HTML map in ./graphics/ and SVGs in ./graphics/svg/.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, PercentFormatter

from costs import (
    BASKET_CATEGORIES,
    BASKET_COLUMNS,
    BASKET_GROUP,
    BASKET_ITEM,
    BASKET_QUANTITY,
    DEFAULT_BASKET,
    HOUSEHOLD_BILLS,
    LEISURE,
    MIN_WAGE,
    NET_SALARY,
    RENT,
    RENT_IN,
    RENT_OUT,
    TRANSPORT,
    load_prices,
)

HERE = Path(__file__).parent
OUT = HERE / "graphics"
SVG = OUT / "svg"
PRICES = HERE / "data" / "europe_allyouneed.csv"

# The five categories in the project plan, in the report's display order.
CATS = [RENT, "Food", TRANSPORT, HOUSEHOLD_BILLS, LEISURE]
REGIONS = {
    "Western": ["Austria", "Belgium", "France", "Germany", "Ireland", "Netherlands",
                "Switzerland", "United Kingdom"],
    "Northern &\nBaltic": ["Denmark", "Finland", "Iceland", "Norway", "Sweden",
                           "Estonia", "Latvia", "Lithuania"],
    "Southern": ["Croatia", "Greece", "Italy", "Malta", "Portugal", "Slovenia", "Spain", "Turkey"],
    "Central &\nEastern": ["Bulgaria", "Czech Republic", "Hungary", "Poland", "Romania",
                           "Russia", "Slovakia"],
    "Western\nBalkans": ["Albania", "Bosnia and Herzegovina", "Kosovo", "Montenegro",
                         "North Macedonia", "Serbia"],
}
REGION_OF = {c: r for r, cs in REGIONS.items() for c in cs}

# Categorical palette validated by validate_palette.js in this fixed five-colour order.
CAT_COLORS = dict(zip(CATS, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]))
WAGE_C, COST_C = "#2a78d6", "#eb6834"
POS_C, NEG_C = "#2a78d6", "#e34948"          # Blue and red diverging pair.
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
BLUES = LinearSegmentedColormap.from_list("blues", ["#f0efec", "#cde2fb", "#6da7ec", "#2a78d6", "#104281"])
SOURCE = "Source: Numbeo prices (europe_allyouneed.csv). Rent = 1-bed apartment outside city centre."

# Shared chart styles for every figure.
plt.rcParams.update({
    "figure.dpi": 110, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "axes.labelsize": 11, "axes.titlesize": 14,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlepad": 26,
    "xtick.color": INK2, "ytick.color": INK2, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
    "axes.spines.top": False, "axes.spines.right": False,
    "grid.color": GRID, "grid.linewidth": 0.8, "legend.frameon": False,
})
EUR = FuncFormatter(lambda v, _: f"{'−' if v < 0 else ''}€{abs(v):,.0f}")


def money(v, sign=False):
    return f"{'−' if v < 0 else ('+' if sign else '')}€{abs(v):,.0f}"


# ------------------------------------------------------------------ Data
def build_table() -> pd.DataFrame:
    """Return monthly costs by category, total cost, wages and metrics for each country."""
    _, wide = load_prices(PRICES)
    basket = pd.DataFrame(DEFAULT_BASKET, columns=BASKET_COLUMNS)
    basket["category"] = basket[BASKET_GROUP].map(BASKET_CATEGORIES)
    t = pd.DataFrame({RENT: wide[RENT_OUT]})
    for cat, g in basket.groupby("category"):
        t[cat] = (wide[g[BASKET_ITEM]] * g[BASKET_QUANTITY].values).sum(axis=1)
    t = t[CATS].round(2)
    t["Total cost"] = t[CATS].sum(axis=1)
    t["Minimum wage"] = wide[MIN_WAGE]
    t["Average net salary"] = wide[NET_SALARY]
    t["Remaining (min wage)"] = t["Minimum wage"] - t["Total cost"]
    t["Rent % of min wage"] = t["Rent"] / t["Minimum wage"] * 100
    t["Remaining (avg salary)"] = t["Average net salary"] - t["Total cost"]
    t["Affordability ratio"] = t["Average net salary"] / t["Total cost"]
    t["Rent city centre"] = wide[RENT_IN]
    t["Rent share %"] = t["Rent"] / t["Total cost"] * 100
    t["Region"] = t.index.map(REGION_OF)
    return t.sort_values("Total cost")


def finish(fig, ax, name, subtitle, note=SOURCE):
    """Add the subtitle and source, then save a 180 dpi PNG and a tightly cropped SVG."""
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=INK2, fontsize=10, va="bottom")
    fig.text(0.01, 0.005, note, color=MUTED, fontsize=8, va="bottom")
    fig.tight_layout(rect=(0, 0.025, 1, 1))
    fig.savefig(OUT / name, dpi=180, bbox_inches="tight")
    fig.savefig(SVG / name.replace(".png", ".svg"), bbox_inches="tight")
    plt.close(fig)
    print("  ✓", name)


def style_bars(ax, axis="x"):
    """Draw a light grid behind the bars."""
    ax.grid(axis=axis, alpha=0.6)
    ax.set_axisbelow(True)


# ------------------------------------------------------------------ 1-9
def g1_wage_vs_cost(t):
    d = t.dropna(subset=["Minimum wage"]).sort_values("Minimum wage")
    y = np.arange(len(d))          # Place the two bars for each country at ± h/2.
    h = 0.38
    fig, ax = plt.subplots(figsize=(10, 9))
    ax.barh(y + h / 2, d["Minimum wage"], height=h, color=WAGE_C, label="Monthly minimum wage")
    cost = ax.barh(y - h / 2, d["Total cost"], height=h, color=COST_C, label="Monthly cost of living")
    ax.bar_label(cost, labels=["cost > wage" if c > w else "" for c, w in zip(d["Total cost"], d["Minimum wage"])],
                 padding=4, fontsize=8, color=INK2)
    ax.set_yticks(y, labels=d.index)
    ax.set_xlim(left=0)
    ax.xaxis.set_major_formatter(EUR)
    ax.set_xlabel("€ per month")
    style_bars(ax)
    ax.set_title("Can the minimum wage cover the cost of living?")
    ax.legend(loc="lower right")
    finish(fig, ax, "1_minimum_wage_vs_cost.png",
           f"{len(d)} European countries with minimum-wage data in the source · single person, monthly, €",
           SOURCE + " Minimum wage is gross.")


def g2_breakdown(t):
    fig, ax = plt.subplots(figsize=(10, 11))
    left = np.zeros(len(t))
    for cat in CATS:                     # Stack bars using left=.
        bars = ax.barh(t.index, t[cat], left=left, color=CAT_COLORS[cat], label=cat,
                       height=0.72, edgecolor=SURFACE, linewidth=1.5)
        left += t[cat].values
    ax.bar_label(bars, labels=[money(v) for v in t["Total cost"]], padding=4, fontsize=8, color=INK2)
    ax.xaxis.set_major_formatter(EUR)
    ax.set_xlim(0, t["Total cost"].max() * 1.1)
    ax.set_xlabel("€ per month")
    style_bars(ax)
    ax.set_title("What drives the cost of living?")
    ax.legend(ncol=5, loc="upper left", bbox_to_anchor=(0, 1.035), fontsize=9)
    finish(fig, ax, "2_cost_breakdown.png",
           "Monthly cost for a single person, € · basket: rent, groceries, transport pass, bills, eating out & leisure")


def g3_remaining(t):
    d = t.dropna(subset=["Minimum wage"]).sort_values("Remaining (min wage)")
    v = d["Remaining (min wage)"]
    fig, ax = plt.subplots(figsize=(10, 9))
    bars = ax.barh(d.index, v, color=[POS_C if x >= 0 else NEG_C for x in v], height=0.7)
    ax.bar_label(bars, labels=[money(x, True) for x in v], padding=4, fontsize=8, color=INK2)
    ax.axvline(0, color=INK2, linewidth=1)
    ax.set_xlim(min(v.min(), 0) * 1.35 - 50, v.max() * 1.15)
    ax.xaxis.set_major_formatter(EUR)
    ax.set_xlabel("€ left per month")
    style_bars(ax)
    ax.set_title("Which countries leave minimum-wage workers money at month end?")
    ax.legend(handles=[Patch(color=POS_C, label="Surplus"), Patch(color=NEG_C, label="Deficit")],
              loc="lower right")
    finish(fig, ax, "3_remaining_income.png",
           "Remaining income = minimum wage − monthly cost of living (€)",
           SOURCE + " Minimum wage is gross, so real remaining income is lower.")


def g4_scatter(t):
    """Answer the planning question about whether countries with higher minimum wages cost more to live in."""
    t = t.dropna(subset=["Minimum wage"])
    fig, ax = plt.subplots(figsize=(10, 7))
    # Colour shows a third variable (rent share), explained by the colour bar.
    points = ax.scatter(t["Total cost"], t["Minimum wage"], c=t["Rent share %"], cmap=BLUES,
                        s=70, alpha=0.95, edgecolors=INK2, linewidths=0.4, zorder=3)
    fig.colorbar(points, ax=ax, label="Rent as % of the monthly cost", format=PercentFormatter(decimals=0))
    top = max(t["Total cost"].max(), t["Minimum wage"].max()) * 1.05
    ax.plot([0, top], [0, top], color=MUTED, linestyle="--", linewidth=1)
    xt = t["Total cost"].max() * 0.98          # Keep the label visible beside the line.
    ax.text(xt, xt * 0.93, "wage = cost", color=MUTED, fontsize=8, ha="right", va="top")
    label = {"Ireland": (8, 0), "Germany": (-8, 8), "Netherlands": (8, 0), "Belgium": (-8, 6),
             "France": (8, -4), "Spain": (8, 4), "Malta": (8, -4), "Portugal": (8, -10),
             "Czech Republic": (8, -8), "Albania": (8, -8), "Bulgaria": (-8, 6), "Slovenia": (8, 2)}
    for c, (dx, dy) in label.items():
        if c in t.index:
            ax.annotate(c, (t.at[c, "Total cost"], t.at[c, "Minimum wage"]),
                        xytext=(dx, dy), textcoords="offset points", fontsize=8, color=INK2,
                        ha="left" if dx > 0 else "right")
    r = t["Total cost"].corr(t["Minimum wage"])
    ax.set_xlim(0, t["Total cost"].max() * 1.1)
    ax.set_ylim(0, t["Minimum wage"].max() * 1.1)
    ax.xaxis.set_major_formatter(EUR); ax.yaxis.set_major_formatter(EUR)
    ax.set_xlabel("Monthly cost of living (€)"); ax.set_ylabel("Monthly minimum wage, gross (€)")
    ax.grid(alpha=0.6); ax.set_axisbelow(True)
    ax.set_title("Are countries with higher minimum wages also more expensive?")
    finish(fig, ax, "4_minimum_wage_vs_cost_scatter.png",
           f"{len(t)} countries with minimum-wage data · Pearson r = {r:.2f} · below the dashed line = the wage does not cover the basket")


def g5_heatmap(t):
    share = t[CATS].div(t["Total cost"], axis=0).sort_values("Rent", ascending=False) * 100
    fig, ax = plt.subplots(figsize=(8, 11))
    im = ax.imshow(share.values, cmap=BLUES, aspect="auto", vmin=0)     # Darker = larger share.
    ax.set_xticks(range(len(CATS)), labels=CATS)
    ax.set_yticks(range(len(share)), labels=share.index)
    ax.xaxis.tick_top(); ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    vmax = share.values.max()
    for i in range(share.shape[0]):
        for j in range(share.shape[1]):
            v = share.iat[i, j]
            ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=8,
                    color="white" if v > vmax * 0.55 else INK)
    ax.set_xticks([x - 0.5 for x in range(1, len(CATS))], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(share))], minor=True)
    ax.grid(which="minor", color=SURFACE, linewidth=2); ax.tick_params(which="minor", length=0)
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02, label="% of monthly cost",
                      format=PercentFormatter(decimals=0))
    cb.outline.set_visible(False)
    ax.set_title("Where does the monthly budget go?", pad=58)
    ax.text(0, 1.055, "Share of each category in the monthly cost of living · sorted by rent share",
            transform=ax.transAxes, color=INK2, fontsize=10, va="bottom")
    finish(fig, ax, "5_budget_share_heatmap.png", "",
           "Malta: public transport is free for residents, so its transport share is 0%.")


def g6_rent_burden(t):
    d = t.dropna(subset=["Minimum wage"]).sort_values("Rent % of min wage")
    v = d["Rent % of min wage"]
    fig, ax = plt.subplots(figsize=(10, 9))
    bars = ax.barh(d.index, v, color=[NEG_C if x > 40 else WAGE_C for x in v], height=0.7)
    ax.bar_label(bars, labels=[f"{x:.0f}%" for x in v], padding=4, fontsize=8, color=INK2)
    ax.axvline(40, color=INK2, linestyle="--", linewidth=1)
    ax.set_ylim(-0.6, len(d) + 0.4)
    ax.text(40.5, len(d) - 0.1, "40% housing-cost overburden threshold (Eurostat)",
            fontsize=8, color=INK2, va="center")
    ax.xaxis.set_major_formatter(PercentFormatter(decimals=0))
    ax.set_xlim(0, v.max() * 1.12)
    ax.set_xlabel("Rent as % of the gross minimum wage")
    style_bars(ax)
    ax.set_title("How much of the minimum wage goes on rent?")
    finish(fig, ax, "6_rent_burden.png",
           "Rent of a 1-bed apartment outside the city centre as % of the gross monthly minimum wage",
           "Source: Numbeo (europe_allyouneed.csv). Eurostat's 40% threshold uses disposable household income: indicative only.")


def g7b_map_html(t):
    """Build an interactive map of the affordability ratio and save it as an HTML file."""
    import plotly.express as px
    d = t.reset_index().rename(columns={"index": "country"})
    fig = px.choropleth(d, locations="country", locationmode="country names",
                        color="Affordability ratio", color_continuous_scale="Blues",
                        hover_name="country",
                        hover_data={"country": False, "Total cost": ":,.0f",
                                    "Average net salary": ":,.0f", "Affordability ratio": ":.2f"},
                        title="Average net salary ÷ monthly cost of living (×2 = covers the basket twice)")
    fig.update_geos(scope="europe", projection_type="natural earth", showcountries=True,
                    lataxis_range=[34, 71], lonaxis_range=[-25, 45])
    fig.update_traces(marker_line_color="white", marker_line_width=0.6)
    fig.update_layout(margin=dict(l=0, r=0, t=50, b=0), coloraxis_colorbar_title="Salary ÷ cost")
    fig.write_html(OUT / "7b_affordability_map_interactive.html", include_plotlyjs="cdn")
    print("  ✓ 7b_affordability_map_interactive.html")


def g8_remaining_avg(t):
    d = t.sort_values("Remaining (avg salary)")
    v = d["Remaining (avg salary)"]
    fig, ax = plt.subplots(figsize=(10, 11))
    bars = ax.barh(d.index, v, color=[POS_C if x >= 0 else NEG_C for x in v], height=0.7)
    ax.bar_label(bars, labels=[money(x, True) for x in v], padding=4, fontsize=8, color=INK2)
    ax.axvline(0, color=INK2, linewidth=1)
    ax.set_xlim(min(v.min(), 0) * 1.3 - 150, v.max() * 1.12)
    ax.xaxis.set_major_formatter(EUR)
    ax.set_xlabel("€ left per month")
    style_bars(ax)
    nomw = set(t.index[t["Minimum wage"].isna()])
    for lbl in ax.get_yticklabels():
        if lbl.get_text() in nomw:
            lbl.set_fontweight("bold")
    ax.set_title("How much is left for an average earner?")
    finish(fig, ax, "8_remaining_average_salary.png",
           "Average monthly net salary − monthly cost of living (€) · bold = no minimum-wage data",
           SOURCE + " Net salary is after tax. Bold countries are missing from charts 1, 3 and 6.")


def g9_rent_centre(t):
    d = t.sort_values("Rent city centre")
    y = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(10, 11))
    ax.hlines(y, d["Rent"], d["Rent city centre"], color=GRID, linewidth=3, zorder=1)
    ax.scatter(d["Rent"], y, s=55, color="#8dbdf3", zorder=3, label="Outside city centre",
               edgecolors=SURFACE, linewidths=1.5)
    ax.scatter(d["Rent city centre"], y, s=55, color="#104281", zorder=3, label="City centre",
               edgecolors=SURFACE, linewidths=1.5)
    prem = (d["Rent city centre"] / d["Rent"] - 1) * 100
    for i, (c, p) in enumerate(prem.items()):
        ax.annotate(f"+{p:.0f}%", xy=(d.at[c, "Rent city centre"], i), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=8, color=INK2)
    ax.set_yticks(y, labels=d.index)
    ax.xaxis.set_major_formatter(EUR)
    ax.set_xlim(0, d["Rent city centre"].max() * 1.12)
    ax.set_xlabel("€ per month")
    style_bars(ax)
    ax.legend(loc="lower right")
    ax.set_title("How much more does living in the city centre cost?")
    finish(fig, ax, "9_rent_centre_vs_outside.png",
           "Monthly rent of a 1-bed apartment, € · label = city-centre premium over outside the centre",
           "Source: Numbeo prices (europe_allyouneed.csv).")


# ------------------------------------------------------------------ 10-14 (other chart types)
def g10_pie(t, country="Ireland"):
    """Pie charts work here because the five categories add up to the whole budget."""
    median_basket = t[CATS].median()
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.4))
    for ax, values, title in ((axes[0], t.loc[country, CATS], f"{country} · {money(t.at[country, 'Total cost'])}/month"),
                              (axes[1], median_basket, f"European median · {money(median_basket.sum())}/month")):
        ax.pie(values, labels=CATS, colors=[CAT_COLORS[c] for c in CATS],
               autopct="%1.1f%%", startangle=90, counterclock=False, pctdistance=0.75,
               wedgeprops={"edgecolor": "white", "linewidth": 1},
               textprops={"fontsize": 9, "color": INK})
        ax.set_title(title, fontsize=11, loc="center", pad=10)
    fig.suptitle("Where does the monthly budget go?", fontsize=14, fontweight="bold", x=0.02, ha="left")
    fig.text(0.02, 0.9, "Share of each category in the monthly cost of a single person",
             color=INK2, fontsize=10)
    fig.text(0.01, 0.005, SOURCE, color=MUTED, fontsize=8, va="bottom")
    fig.tight_layout(rect=(0, 0.03, 1, 0.9))
    fig.savefig(OUT / "10_budget_pie.png", dpi=180, bbox_inches="tight")
    fig.savefig(SVG / "10_budget_pie.svg", bbox_inches="tight")
    plt.close(fig)
    print("  ✓ 10_budget_pie.png")


def g11_histogram(t):
    """Show the same data with fewer and more bins and mark the median, since bin width changes the shape."""
    med = t["Total cost"].median()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=False)
    for ax, bins, title in ((axes[0], 5, "Few bins: coarse summary"), (axes[1], 15, "More bins: more detail")):
        ax.hist(t["Total cost"], bins=bins, color="#6da7ec", edgecolor="white")
        ax.axvline(med, color=NEG_C, linestyle="--", linewidth=1.5, label=f"Median {money(med)}")
        ax.set_title(title, fontsize=11, pad=8)
        ax.set_xlabel("Monthly cost of living (€)")
        ax.set_ylabel("Number of countries")
        ax.xaxis.set_major_formatter(EUR)
        ax.grid(axis="y", alpha=0.6); ax.set_axisbelow(True)
        ax.legend(loc="upper right", fontsize=9)
    fig.suptitle("How is the monthly cost distributed across 37 countries?", fontsize=14,
                 fontweight="bold", x=0.02, ha="left")
    fig.text(0.01, 0.005, SOURCE + " Bin width is a modelling choice.", color=MUTED, fontsize=8, va="bottom")
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(OUT / "11_cost_histogram.png", dpi=180, bbox_inches="tight")
    fig.savefig(SVG / "11_cost_histogram.svg", bbox_inches="tight")
    plt.close(fig)
    print("  ✓ 11_cost_histogram.png")


def g12_boxplot(t):
    """Compare the spread of monthly cost between regions."""
    order = list(REGIONS)
    data_by_region = [t.loc[t["Region"] == r, "Total cost"] for r in order]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.boxplot(data_by_region, tick_labels=order, patch_artist=True,
               boxprops={"facecolor": "#cde2fb", "edgecolor": "#2a78d6"},
               medianprops={"color": "#104281", "linewidth": 2},
               whiskerprops={"color": INK2}, capprops={"color": INK2},
               flierprops={"markeredgecolor": INK2})
    rng = np.random.default_rng(0)
    for i, vals in enumerate(data_by_region, start=1):        # Show each country as a point.
        ax.scatter(i + rng.uniform(-0.12, 0.12, len(vals)), vals, s=18, color=INK2, alpha=0.6, zorder=3)
    ax.yaxis.set_major_formatter(EUR)
    ax.set_xlabel("Region")
    ax.set_ylabel("Monthly cost of living (€)")
    ax.grid(axis="y", alpha=0.6); ax.set_axisbelow(True)
    ax.set_title("Does the cost of living differ between regions?")
    finish(fig, ax, "12_cost_by_region_boxplot.png",
           "Box = middle 50% of countries, line = median, whiskers = 1.5 × IQR · dots = individual countries")


def g13_line(t):
    """Share of countries where each salary covers the monthly cost, with the median salary marked."""
    salaries = np.arange(400, 4001, 100)
    covered = np.array([(t["Total cost"] <= s).mean() * 100 for s in salaries])
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(salaries, covered, marker="o", markersize=4, linewidth=2, color=WAGE_C)
    ref = t["Average net salary"].median()
    ref_cov = (t["Total cost"] <= ref).mean() * 100
    ax.scatter([ref], [ref_cov], color=NEG_C, s=65, zorder=5)
    ax.annotate(f"Median average net salary ({money(ref)})\ncovers the basket in {ref_cov:.0f}% of countries",
                xy=(ref, ref_cov), xytext=(40, -70), textcoords="offset points", fontsize=9,
                arrowprops={"arrowstyle": "->", "color": NEG_C})
    ax.set_xlabel("Monthly net salary (€)")
    ax.set_ylabel("% of countries where it covers the basket")
    ax.xaxis.set_major_formatter(EUR)
    ax.yaxis.set_major_formatter(PercentFormatter(decimals=0))
    ax.set_ylim(0, 105)
    ax.grid(alpha=0.6); ax.set_axisbelow(True)
    ax.set_title("How much do you need to earn to live in most of Europe?")
    finish(fig, ax, "13_salary_coverage_line.png",
           "Share of the 37 countries whose monthly cost of living is at or below each salary")


def g14_dashboard(t):
    """Three panels for three questions (compare, relate, distribute), each with a different chart type."""
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    mw = t.dropna(subset=["Minimum wage"])
    top = mw.sort_values("Remaining (min wage)").tail(10)
    axes[0].barh(top.index, top["Remaining (min wage)"], color=WAGE_C)
    axes[0].bar_label(axes[0].containers[0], labels=[money(v, True) for v in top["Remaining (min wage)"]],
                      padding=3, fontsize=8)
    axes[0].set_title("Compare | € left on the minimum wage (top 10)", fontsize=11, pad=8)
    axes[0].set_xlim(0, top["Remaining (min wage)"].max() * 1.25)

    axes[1].scatter(mw["Total cost"], mw["Minimum wage"], color=WAGE_C, s=25, alpha=0.8)
    axes[1].set_title("Relate | minimum wage vs cost", fontsize=11, pad=8)
    axes[1].set_xlabel("Monthly cost (€)"); axes[1].set_ylabel("Minimum wage (€)")

    axes[2].hist(t["Total cost"], bins=10, color="#6da7ec", edgecolor="white")
    axes[2].set_title("Distribute | monthly cost", fontsize=11, pad=8)
    axes[2].set_xlabel("Monthly cost (€)"); axes[2].set_ylabel("Countries")
    for ax in axes:
        ax.grid(axis="x" if ax is axes[0] else "y", alpha=0.6); ax.set_axisbelow(True)
    fig.suptitle("Three questions, three encodings", fontsize=14, fontweight="bold", x=0.02, ha="left")
    fig.text(0.01, 0.005, SOURCE, color=MUTED, fontsize=8, va="bottom")
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(OUT / "14_three_questions_dashboard.png", dpi=180, bbox_inches="tight")
    fig.savefig(SVG / "14_three_questions_dashboard.svg", bbox_inches="tight")
    plt.close(fig)
    print("  ✓ 14_three_questions_dashboard.png")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    SVG.mkdir(exist_ok=True)
    table = build_table()
    table.round(2).to_csv(OUT / "cost_of_living_table.csv", encoding="utf-8-sig")
    print("Table:", OUT / "cost_of_living_table.csv")
    for g in (g1_wage_vs_cost, g2_breakdown, g3_remaining, g4_scatter, g5_heatmap, g6_rent_burden,
              g7b_map_html, g8_remaining_avg, g9_rent_centre, g10_pie, g11_histogram, g12_boxplot,
              g14_dashboard):
        g(table)
