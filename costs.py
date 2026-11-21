"""Load and clean europe_allyouneed.csv and calculate a monthly spending basket.

The CSV has one row per item and country, with prices stored as text ('€1,574.71').
The wide table has one row per country and one column per item.
"""
from pathlib import Path

import pandas as pd

RENT_OUT = "1 Bedroom Apartment Outside of City Centre"
RENT_IN = "1 Bedroom Apartment in City Centre"
NET_SALARY = "Average Monthly Net Salary (After Tax)"
MIN_WAGE = "Minimum Wage"
RENT = "Rent"
HOUSEHOLD_BILLS = "Household bills"
TRANSPORT = "Transport"
GROCERIES = "Groceries"
EATING_OUT = "Eating out"
LEISURE = "Leisure"

BASKET_ITEM = "item"
BASKET_GROUP = "group"
BASKET_QUANTITY = "quantity"
BASKET_COLUMNS = [BASKET_ITEM, BASKET_GROUP, BASKET_QUANTITY]

# Default monthly basket for one person living alone, editable in the dashboard.
# (item, basket group, monthly quantity)
DEFAULT_BASKET = [
    ("Basic Utilities for 85 m2 Apartment (Electricity, Heating, Cooling, Water, Garbage)", HOUSEHOLD_BILLS, 1),
    ("Broadband Internet (Unlimited Data, 60 Mbps or Higher)", HOUSEHOLD_BILLS, 1),
    ("Mobile Phone Plan (Monthly, with Calls and 10GB+ Data)", HOUSEHOLD_BILLS, 1),
    ("Monthly Public Transport Pass (Regular Price)", TRANSPORT, 1),
    ("Milk (Regular, 1 Liter)", GROCERIES, 8),
    ("Fresh White Bread (500 g Loaf)", GROCERIES, 6),
    ("White Rice (1 kg)", GROCERIES, 1),
    ("Eggs (12, Large Size)", GROCERIES, 2),
    ("Local Cheese (1 kg)", GROCERIES, 0.5),
    ("Chicken Fillets (1 kg)", GROCERIES, 2),
    ("Beef Round or Equivalent Back Leg Red Meat (1 kg)", GROCERIES, 1),
    ("Apples (1 kg)", GROCERIES, 2),
    ("Bananas (1 kg)", GROCERIES, 2),
    ("Oranges (1 kg)", GROCERIES, 2),
    ("Tomatoes (1 kg)", GROCERIES, 2),
    ("Potatoes (1 kg)", GROCERIES, 3),
    ("Onions (1 kg)", GROCERIES, 1),
    ("Lettuce (1 Head)", GROCERIES, 4),
    ("Bottled Water (1.5 Liter)", GROCERIES, 10),
    ("Meal at an Inexpensive Restaurant", EATING_OUT, 4),
    ("Cappuccino (Regular Size)", EATING_OUT, 4),
    ("Monthly Fitness Club Membership", LEISURE, 1),
    ("Cinema Ticket (International Release)", LEISURE, 2),
]
GROUPS = [RENT, HOUSEHOLD_BILLS, TRANSPORT, GROCERIES, EATING_OUT, LEISURE]

# Dashboard categories combine groceries and eating out under Food.
BASKET_CATEGORIES = {
    HOUSEHOLD_BILLS: HOUSEHOLD_BILLS,
    TRANSPORT: TRANSPORT,
    GROCERIES: "Food",
    EATING_OUT: "Food",
    LEISURE: LEISURE,
}


def load_prices(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return cleaned prices in long format and as a wide country-by-item table."""
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["price_eur"] = pd.to_numeric(
        df["price"].astype(str).str.replace(r"[€,]", "", regex=True), errors="coerce")
    # "Imported Beer (0.33 Liter Bottle)" appears in both 'eat out' and 'groceries', so add the category to distinguish them.
    dup = df.duplicated(["item", "country"], keep=False)
    df.loc[dup, "item"] = df.loc[dup, "item"] + " [" + df.loc[dup, "category"] + "]"
    wide = df.pivot(index="country", columns="item", values="price_eur")
    return df, wide


def basket_cost(wide: pd.DataFrame, basket: pd.DataFrame, rent_item: str) -> pd.DataFrame:
    """Calculate monthly costs by country and group from the basket columns."""
    parts = {RENT: wide[rent_item]}
    for group, g in basket.groupby(BASKET_GROUP):
        parts[group] = (wide[g[BASKET_ITEM]] * g[BASKET_QUANTITY].values).sum(axis=1)
    out = pd.DataFrame(parts).reindex(columns=GROUPS, fill_value=0.0)
    out["Total"] = out.sum(axis=1)
    return out
