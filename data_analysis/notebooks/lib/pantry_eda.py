from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = PROJECT_ROOT / "data"
TOAST_ROOT = DATA_ROOT / "toast"
POS_ROOT = TOAST_ROOT / "pos"
XTRACHEF_ROOT = TOAST_ROOT / "xtraCHEF"
WEATHER_PATH = DATA_ROOT / "weather" / "chicago_2026_bulk.csv"
POS_2026_ROOT = POS_ROOT / "2026"


def stable_key(value: object) -> str:
    text = "" if value is None else str(value).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def find_files(root: Path = DATA_ROOT) -> pd.DataFrame:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rows.append(
                {
                    "path": str(path.relative_to(PROJECT_ROOT)),
                    "folder": str(path.parent.relative_to(PROJECT_ROOT)),
                    "name": path.name,
                    "suffix": path.suffix.lower(),
                    "size_kb": round(path.stat().st_size / 1024, 2),
                }
            )
    return pd.DataFrame(rows)


def latest_file(folder: Path, pattern: str) -> Path:
    matches = sorted(folder.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No files matched {folder / pattern}")
    return matches[-1]


def read_pos_item_selections(path: Path | None = None, include_uncategorized: bool = False) -> pd.DataFrame:
    if path is None and POS_2026_ROOT.exists():
        return read_pos_item_selection_files(
            sorted(POS_2026_ROOT.glob("ItemSelectionDetails*.csv")),
            include_uncategorized=include_uncategorized,
        )
    path = path or latest_file(POS_ROOT, "ItemSelectionDetails*.csv")
    return read_pos_item_selection_files([path], include_uncategorized=include_uncategorized)


def read_pos_item_selection_files(
    paths: list[Path],
    include_uncategorized: bool = False,
) -> pd.DataFrame:
    if not paths:
        raise FileNotFoundError("No ItemSelectionDetails CSV files found")
    frames = [_read_pos_item_selection_file(path, include_uncategorized=include_uncategorized) for path in paths]
    return pd.concat(frames, ignore_index=True).sort_values("sent_at").reset_index(drop=True)


def _read_pos_item_selection_file(path: Path, include_uncategorized: bool = False) -> pd.DataFrame:
    df = read_csv_with_fallback(path)
    df.columns = [clean_column(column) for column in df.columns]
    df["source_file"] = path.name
    df["sent_at"] = pd.to_datetime(df["sent_date"], format="%m/%d/%y %I:%M %p", errors="coerce")
    df["business_date"] = df["sent_at"].dt.date
    df["month"] = df["sent_at"].dt.to_period("M").astype(str)
    df["hour"] = df["sent_at"].dt.hour
    df["day_name"] = df["sent_at"].dt.day_name()
    df["is_void"] = df["void"].astype(str).str.lower().eq("true")
    df["qty"] = pd.to_numeric(df["qty"], errors="coerce").fillna(0)
    df["net_price"] = pd.to_numeric(df["net_price"], errors="coerce").fillna(0)
    df["menu_item_key"] = df["menu_item"].map(stable_key)

    keep = ~df["is_void"]
    if not include_uncategorized:
        keep = keep & df["sales_category"].notna() & df["sales_category"].astype(str).str.len().gt(0)
    return df.loc[keep].copy()


def read_pos_modifiers(path: Path | None = None) -> pd.DataFrame:
    path = path or latest_file(POS_ROOT, "ItemModifierSelectionDetails*.csv")
    df = read_csv_with_fallback(path)
    df.columns = [clean_column(column) for column in df.columns]
    df["sent_at"] = pd.to_datetime(df["sent_date"], format="%m/%d/%y %I:%M %p", errors="coerce")
    df["business_date"] = df["sent_at"].dt.date
    df["hour"] = df["sent_at"].dt.hour
    df["is_void"] = df["void"].astype(str).str.lower().eq("true")
    df["qty"] = pd.to_numeric(df["qty"], errors="coerce").fillna(0)
    df["net_price"] = pd.to_numeric(df["net_price"], errors="coerce").fillna(0)
    df["modifier_key"] = df["modifier"].map(stable_key)
    df["parent_menu_selection_key"] = df["parent_menu_selection"].map(stable_key)
    return df.loc[~df["is_void"]].copy()


def read_product_mix_zip(path: Path | None = None) -> dict[str, pd.DataFrame]:
    path = path or latest_file(POS_ROOT, "ProductMix*.zip")
    frames: dict[str, pd.DataFrame] = {}
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if name.endswith(".csv"):
                with archive.open(name) as file:
                    frame = pd.read_csv(file)
                frame.columns = [clean_column(column) for column in frame.columns]
                frames[name] = frame
    return frames


def read_product_mix_export(path: Path | None = None) -> dict[str, pd.DataFrame]:
    try:
        path = path or latest_product_mix_export()
    except FileNotFoundError:
        return {}
    if path.is_dir():
        frames: dict[str, pd.DataFrame] = {}
        for csv_path in sorted(path.glob("*.csv")):
            if csv_path.stat().st_size == 0:
                frames[csv_path.name] = pd.DataFrame()
                continue
            frame = read_csv_with_fallback(csv_path)
            frame.columns = [clean_column(column) for column in frame.columns]
            frames[csv_path.name] = frame
        return frames
    return read_product_mix_zip(path)


def latest_product_mix_export() -> Path:
    directories = sorted([path for path in POS_ROOT.glob("ProductMix*") if path.is_dir()])
    if directories:
        return directories[-1]
    return latest_file(POS_ROOT, "ProductMix*.zip")


def product_mix_all_levels(path: Path | None = None) -> pd.DataFrame:
    frames = read_product_mix_export(path)
    for name, frame in frames.items():
        if name.lower() == "all levels.csv":
            return frame.copy()
    raise KeyError("Product Mix export does not contain All levels.csv")


def product_mix_has_daily_granularity(frame: pd.DataFrame) -> bool:
    date_like_columns = {
        "date",
        "business_date",
        "sent_date",
        "order_date",
        "opened_date",
        "closed_date",
    }
    return any(column in date_like_columns for column in frame.columns)


def read_weather_daily(path: Path | None = None, year: int | None = None, month: int | None = None) -> pd.DataFrame:
    path = path or find_weather_file()
    raw = read_csv_with_fallback(path, low_memory=False)
    raw.columns = [clean_column(column) for column in raw.columns]
    raw["timestamp"] = pd.to_datetime(raw["date"], errors="coerce")
    raw["business_date"] = raw["timestamp"].dt.date

    df = raw
    if "report_type" in raw:
        df = raw[raw["report_type"].astype(str).str.upper().eq("SOD")].copy()

    if year is not None:
        df = df[df["timestamp"].dt.year.eq(year)].copy()
    if month is not None:
        df = df[df["timestamp"].dt.month.eq(month)].copy()

    keep_columns = [
        "business_date",
        "daily_maximum_dry_bulb_temperature",
        "daily_minimum_dry_bulb_temperature",
        "daily_average_dry_bulb_temperature",
        "daily_precipitation",
        "daily_snowfall",
        "daily_snow_depth",
        "daily_average_wind_speed",
        "daily_sustained_wind_speed",
        "daily_peak_wind_speed",
        "daily_average_relative_humidity",
        "daily_average_dew_point_temperature",
        "daily_weather",
    ]
    keep_columns = [column for column in keep_columns if column in df.columns]
    weather = df[keep_columns].copy()

    numeric_columns = [column for column in weather.columns if column not in {"business_date", "daily_weather"}]
    for column in numeric_columns:
        weather[column] = weather[column].map(parse_weather_number)

    weather = (
        weather.sort_values("business_date")
        .drop_duplicates(subset=["business_date"], keep="last")
        .reset_index(drop=True)
    )

    hourly = build_hourly_weather_fallbacks(raw, year=year, month=month)
    if not hourly.empty:
        weather = weather.merge(hourly, on="business_date", how="left")
        fill_pairs = {
            "daily_average_relative_humidity": "hourly_average_relative_humidity",
            "daily_average_dew_point_temperature": "hourly_average_dew_point_temperature",
            "daily_average_dry_bulb_temperature": "hourly_average_dry_bulb_temperature",
            "daily_average_wind_speed": "hourly_average_wind_speed",
        }
        for daily_column, hourly_column in fill_pairs.items():
            if daily_column in weather and hourly_column in weather:
                weather[daily_column] = pd.to_numeric(weather[daily_column], errors="coerce")
                weather[hourly_column] = pd.to_numeric(weather[hourly_column], errors="coerce")
                weather[daily_column] = pd.to_numeric(
                    weather[daily_column].fillna(weather[hourly_column]),
                    errors="coerce",
                )

    return add_standard_weather_units(weather)


def read_xtrachef_item_library(path: Path | None = None) -> pd.DataFrame:
    path = path or latest_file(XTRACHEF_ROOT, "*Item_Detail_Report*.csv")
    header_row = find_csv_header_row(path, "Location Name")
    df = pd.read_csv(path, skiprows=header_row)
    df.columns = [clean_column(column) for column in df.columns]
    df["last_purchased_date"] = pd.to_datetime(df["last_purchased_date"], errors="coerce")
    for column in ["contracted_price", "last_purchased_price"]:
        if column in df:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    df["item_key"] = df["item_description"].map(stable_key)
    df["category_group"] = df["category"].astype(str).str.split("-").str[0].str.strip()
    return df


def extract_recipe_pdf_text(path: Path | None = None) -> str:
    path = path or latest_file(XTRACHEF_ROOT, "*Recipe_Download*.pdf")
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise ImportError("Install pypdf to extract recipe PDF text: pip install pypdf") from error

    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def daily_sales(sales: pd.DataFrame) -> pd.DataFrame:
    return (
        sales.groupby("business_date", as_index=False)
        .agg(qty=("qty", "sum"), net_sales=("net_price", "sum"), orders=("order", "nunique"))
        .sort_values("business_date")
    )


def daily_category_sales(sales: pd.DataFrame) -> pd.DataFrame:
    daily = (
        sales.pivot_table(
            index="business_date",
            columns="sales_category",
            values="qty",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )
    rename = {column: f"qty_{stable_key(column).replace(' ', '_')}" for column in daily.columns if column != "business_date"}
    return daily.rename(columns=rename)


def top_items(sales: pd.DataFrame, n: int = 25) -> pd.DataFrame:
    return (
        sales.groupby(["menu_item_key", "menu_item", "sales_category"], as_index=False)
        .agg(qty=("qty", "sum"), net_sales=("net_price", "sum"), orders=("order", "nunique"))
        .sort_values(["qty", "net_sales"], ascending=False)
        .head(n)
    )


def clean_column(column: object) -> str:
    text = str(column).strip().lower()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(column).strip()).lower()
    text = re.sub(r"\(\$\)", "", text)
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    text = text.replace("void_", "void")
    return text


def find_csv_header_row(path: Path, first_column_name: str) -> int:
    with path.open(newline="") as file:
        for index, line in enumerate(file):
            if first_column_name in line:
                return index
    raise ValueError(f"Could not find header row containing {first_column_name!r} in {path}")


def find_weather_file() -> Path:
    if WEATHER_PATH.is_file():
        return WEATHER_PATH
    if WEATHER_PATH.is_dir():
        matches = sorted(
            [
                path
                for path in WEATHER_PATH.iterdir()
                if path.is_file() and path.suffix.lower() in {"", ".csv", ".txt"}
            ]
        )
        if matches:
            return matches[-1]
    raise FileNotFoundError(f"No weather export found at {WEATHER_PATH}")


def read_csv_with_fallback(path: Path, **kwargs) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8", **kwargs)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", **kwargs)


def parse_weather_number(value: object) -> float | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text in {"", "T"}:
        return 0.0 if text == "T" else None
    text = re.sub(r"[^0-9.\-]+", "", text)
    if text in {"", "-", "."}:
        return None
    return float(text)


def build_hourly_weather_fallbacks(raw: pd.DataFrame, year: int | None, month: int | None) -> pd.DataFrame:
    hourly = raw.copy()
    if "report_type" in hourly:
        hourly = hourly[~hourly["report_type"].astype(str).str.upper().eq("SOD")].copy()
    if year is not None:
        hourly = hourly[hourly["timestamp"].dt.year.eq(year)].copy()
    if month is not None:
        hourly = hourly[hourly["timestamp"].dt.month.eq(month)].copy()

    source_columns = {
        "hourly_relative_humidity": "hourly_average_relative_humidity",
        "hourly_dew_point_temperature": "hourly_average_dew_point_temperature",
        "hourly_dry_bulb_temperature": "hourly_average_dry_bulb_temperature",
        "hourly_wind_speed": "hourly_average_wind_speed",
    }
    available = [column for column in source_columns if column in hourly.columns]
    if not available:
        return pd.DataFrame()

    for column in available:
        hourly[column] = hourly[column].map(parse_weather_number)

    aggregated = (
        hourly.groupby("business_date", as_index=False)[available]
        .mean(numeric_only=True)
        .rename(columns=source_columns)
    )
    return aggregated


def add_standard_weather_units(weather: pd.DataFrame) -> pd.DataFrame:
    standardized = weather.copy()
    temp_columns = [
        "daily_maximum_dry_bulb_temperature",
        "daily_minimum_dry_bulb_temperature",
        "daily_average_dry_bulb_temperature",
        "daily_average_dew_point_temperature",
    ]
    for column in temp_columns:
        if column in standardized:
            standardized[f"{column}_f"] = standardized[column].map(celsius_to_fahrenheit)

    for column in ["daily_precipitation", "daily_snowfall", "daily_snow_depth"]:
        if column in standardized:
            standardized[f"{column}_in"] = standardized[column].map(millimeters_to_inches)

    wind_columns = [
        "daily_average_wind_speed",
        "daily_sustained_wind_speed",
        "daily_peak_wind_speed",
    ]
    for column in wind_columns:
        if column in standardized:
            standardized[f"{column}_mph"] = standardized[column].map(meters_per_second_to_mph)

    return standardized


def celsius_to_fahrenheit(value: float | None) -> float | None:
    return round((value * 9 / 5) + 32, 2) if value is not None and not pd.isna(value) else None


def millimeters_to_inches(value: float | None) -> float | None:
    return round(value / 25.4, 3) if value is not None and not pd.isna(value) else None


def meters_per_second_to_mph(value: float | None) -> float | None:
    return round(value * 2.236936, 2) if value is not None and not pd.isna(value) else None
