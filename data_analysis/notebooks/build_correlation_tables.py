from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "notebooks" / "lib"))

import pantry_eda as eda


def main() -> None:
    sales = eda.read_pos_item_selections()
    weather = eda.read_weather_daily(year=2026)
    pd = eda.pd
    try:
        product_mix = eda.read_product_mix_export()
    except FileNotFoundError:
        product_mix = {}
    product_mix_summary = pd.DataFrame(
        [
            {
                "file": name,
                "rows": len(frame),
                "columns": frame.shape[1],
                "has_daily_granularity": eda.product_mix_has_daily_granularity(frame),
            }
            for name, frame in product_mix.items()
        ],
        columns=["file", "rows", "columns", "has_daily_granularity"],
    )

    daily = eda.daily_sales(sales).merge(eda.daily_category_sales(sales), on="business_date", how="left")
    daily["avg_qty_per_order"] = daily["qty"] / daily["orders"]
    daily["avg_net_sales_per_order"] = daily["net_sales"] / daily["orders"]
    daily["date"] = pd.to_datetime(daily["business_date"])
    daily["weekday"] = daily["date"].dt.day_name()
    daily["weekday_num"] = daily["date"].dt.weekday
    daily["month"] = daily["date"].dt.month_name()
    daily["is_weekend"] = daily["weekday_num"].isin([4, 5, 6])

    joined = daily.merge(weather, on="business_date", how="inner")
    joined["had_precipitation"] = joined["daily_precipitation_in"].fillna(0).gt(0)
    joined["had_snowfall"] = joined.get("daily_snowfall_in", 0).fillna(0).gt(0)
    joined["temperature_range_f"] = (
        joined["daily_maximum_dry_bulb_temperature_f"]
        - joined["daily_minimum_dry_bulb_temperature_f"]
    )

    demand_cols = [
        "qty",
        "orders",
        "net_sales",
        "avg_qty_per_order",
        "avg_net_sales_per_order",
    ] + [column for column in joined.columns if column.startswith("qty_")]

    weather_cols = [
        "daily_maximum_dry_bulb_temperature_f",
        "daily_minimum_dry_bulb_temperature_f",
        "daily_average_dry_bulb_temperature_f",
        "temperature_range_f",
        "daily_precipitation_in",
        "daily_snowfall_in",
        "daily_snow_depth_in",
        "daily_average_wind_speed_mph",
        "daily_sustained_wind_speed_mph",
        "daily_peak_wind_speed_mph",
        "daily_average_relative_humidity",
        "daily_average_dew_point_temperature_f",
    ]
    weather_cols = [column for column in weather_cols if column in joined.columns]

    ranked_weekday = rank_weekday_correlations(joined, demand_cols, pd)
    ranked_month = rank_month_correlations(joined, demand_cols, pd)
    ranked_weather = rank_correlations(joined, demand_cols, weather_cols, "demand_metric", "weather_metric")
    ranked_share = rank_category_share_correlations(joined, weather_cols, pd)
    ranked_item_weather = rank_item_weather_correlations(sales, weather, weather_cols)
    multivariable_effects, multivariable_scores = build_multivariable_models(joined, pd)
    weekday_summary = build_weekday_summary(joined)
    month_summary = build_month_summary(joined)
    rain_summary = build_rain_summary(joined)

    outputs = PROJECT_ROOT / "notebooks" / "outputs"
    outputs.mkdir(exist_ok=True)
    product_mix_summary.to_csv(outputs / "product_mix_2026_to_date_export_summary.csv", index=False)
    if "All levels.csv" in product_mix:
        product_mix["All levels.csv"].to_csv(outputs / "product_mix_2026_to_date_all_levels.csv", index=False)
    joined.to_csv(outputs / "daily_toast_correlation_base_2026_to_date.csv", index=False)
    weekday_summary.to_csv(outputs / "weekday_summary_2026_to_date.csv", index=False)
    month_summary.to_csv(outputs / "month_summary_2026_to_date.csv", index=False)
    rain_summary.to_csv(outputs / "rain_summary_2026_to_date.csv", index=False)
    ranked_weekday.to_csv(outputs / "ranked_weekday_correlations_2026_to_date.csv", index=False)
    ranked_month.to_csv(outputs / "ranked_month_correlations_2026_to_date.csv", index=False)
    ranked_weather.to_csv(outputs / "ranked_weather_correlations_2026_to_date.csv", index=False)
    ranked_share.to_csv(outputs / "ranked_category_share_weather_correlations_2026_to_date.csv", index=False)
    ranked_item_weather.to_csv(outputs / "ranked_item_weather_correlations_2026_to_date.csv", index=False)
    multivariable_effects.to_csv(outputs / "ranked_multivariable_effects_2026_to_date.csv", index=False)
    multivariable_scores.to_csv(outputs / "multivariable_model_scores_2026_to_date.csv", index=False)

    print(f"Wrote correlation tables to {outputs}")
    if not product_mix_summary.empty:
        print("\nProduct Mix export summary:")
        print(product_mix_summary.to_string(index=False))
    if product_mix_summary.empty or not product_mix_summary["has_daily_granularity"].any():
        print(
            "\nNote: the Jan-Apr Product Mix export is aggregate-only. "
            "Daily correlations use the joined monthly Item Selection Details files."
        )
    print(f"Joined days: {joined['business_date'].nunique()}")
    print("\nTop weekday correlations:")
    print(ranked_weekday.head(10).to_string(index=False))
    print("\nTop month correlations:")
    print(ranked_month.head(10).to_string(index=False))
    print("\nTop weather correlations:")
    print(ranked_weather.head(10).to_string(index=False))
    print("\nTop multivariable effects:")
    print(multivariable_effects.head(12).to_string(index=False))
    print("\nMultivariable model scores:")
    print(multivariable_scores.to_string(index=False))
    print("\nTop item-weather correlations:")
    print(ranked_item_weather.head(10).to_string(index=False))


def rank_weekday_correlations(joined, demand_cols: list[str], pd):
    weekday_dummies = pd.get_dummies(joined["weekday"], prefix="weekday").astype(int)
    weekday_corr = (
        pd.concat([joined[demand_cols], weekday_dummies], axis=1)
        .corr(numeric_only=True)
        .loc[demand_cols, weekday_dummies.columns]
    )
    ranked = weekday_corr.stack().reset_index().rename(
        columns={"level_0": "demand_metric", "level_1": "weekday_metric", 0: "correlation"}
    )
    ranked["abs_correlation"] = ranked["correlation"].abs()
    return ranked.sort_values("abs_correlation", ascending=False)


def rank_month_correlations(joined, demand_cols: list[str], pd):
    month_dummies = pd.get_dummies(joined["month"], prefix="month").astype(int)
    month_corr = (
        pd.concat([joined[demand_cols], month_dummies], axis=1)
        .corr(numeric_only=True)
        .loc[demand_cols, month_dummies.columns]
    )
    ranked = month_corr.stack().reset_index().rename(
        columns={"level_0": "demand_metric", "level_1": "month_metric", 0: "correlation"}
    )
    ranked["abs_correlation"] = ranked["correlation"].abs()
    return ranked.sort_values("abs_correlation", ascending=False)


def rank_correlations(frame, row_cols: list[str], col_cols: list[str], row_name: str, col_name: str):
    corr = frame[row_cols + col_cols].corr(numeric_only=True).loc[row_cols, col_cols]
    ranked = corr.stack().reset_index().rename(
        columns={"level_0": row_name, "level_1": col_name, 0: "correlation"}
    )
    ranked["abs_correlation"] = ranked["correlation"].abs()
    return ranked.sort_values("abs_correlation", ascending=False)


def rank_category_share_correlations(joined, weather_cols: list[str], pd):
    category_cols = [column for column in joined.columns if column.startswith("qty_")]
    mix = joined[["business_date", "qty"] + category_cols + weather_cols].copy()
    for column in category_cols:
        mix[f"{column}_share"] = mix[column] / mix["qty"]
    share_cols = [column for column in mix.columns if column.endswith("_share")]
    return rank_correlations(mix, share_cols, weather_cols, "category_share_metric", "weather_metric")


def rank_item_weather_correlations(sales, weather, weather_cols: list[str]):
    top_item_names = eda.top_items(sales, n=25)["menu_item"].tolist()
    item_daily = (
        sales[sales["menu_item"].isin(top_item_names)]
        .pivot_table(index="business_date", columns="menu_item", values="qty", aggfunc="sum", fill_value=0)
        .reset_index()
    )
    item_weather = item_daily.merge(weather, on="business_date", how="inner")
    item_weather["temperature_range_f"] = (
        item_weather["daily_maximum_dry_bulb_temperature_f"]
        - item_weather["daily_minimum_dry_bulb_temperature_f"]
    )
    return rank_correlations(item_weather, top_item_names, weather_cols, "menu_item", "weather_metric")


def build_weekday_summary(joined):
    return (
        joined.groupby("weekday", as_index=False)
        .agg(
            days=("business_date", "nunique"),
            avg_qty=("qty", "mean"),
            avg_orders=("orders", "mean"),
            avg_net_sales=("net_sales", "mean"),
            avg_food_qty=("qty_food", "mean"),
            avg_liquor_qty=("qty_liquor", "mean"),
        )
        .sort_values("avg_qty", ascending=False)
    )


def build_month_summary(joined):
    return (
        joined.groupby("month", as_index=False)
        .agg(
            days=("business_date", "nunique"),
            avg_qty=("qty", "mean"),
            avg_orders=("orders", "mean"),
            avg_net_sales=("net_sales", "mean"),
            avg_food_qty=("qty_food", "mean"),
            avg_liquor_qty=("qty_liquor", "mean"),
        )
        .sort_values("avg_qty", ascending=False)
    )


def build_rain_summary(joined):
    return (
        joined.groupby("had_precipitation", as_index=False)
        .agg(
            days=("business_date", "nunique"),
            avg_qty=("qty", "mean"),
            avg_orders=("orders", "mean"),
            avg_net_sales=("net_sales", "mean"),
            avg_food_qty=("qty_food", "mean"),
            avg_liquor_qty=("qty_liquor", "mean"),
            avg_beer_qty=("qty_beer", "mean"),
        )
        .sort_values("had_precipitation")
    )


def build_multivariable_models(joined, pd):
    import numpy as np

    frame = joined.copy()
    frame["is_friday"] = frame["weekday"].eq("Friday").astype(int)
    frame["is_saturday"] = frame["weekday"].eq("Saturday").astype(int)
    frame["is_sunday"] = frame["weekday"].eq("Sunday").astype(int)
    frame["is_april"] = frame["month"].eq("April").astype(int)
    frame["is_precip_day"] = frame["daily_precipitation_in"].fillna(0).gt(0).astype(int)
    frame["warm_day"] = (
        frame["daily_maximum_dry_bulb_temperature_f"]
        >= frame["daily_maximum_dry_bulb_temperature_f"].median()
    ).astype(int)
    frame["windy_day"] = (
        frame["daily_average_wind_speed_mph"] >= frame["daily_average_wind_speed_mph"].median()
    ).astype(int)

    base_features = [
        "daily_maximum_dry_bulb_temperature_f",
        "daily_precipitation_in",
        "daily_average_wind_speed_mph",
        "daily_average_relative_humidity",
        "is_friday",
        "is_saturday",
        "is_sunday",
        "is_april",
        "is_precip_day",
        "warm_day",
        "windy_day",
    ]
    interaction_pairs = [
        ("is_friday", "warm_day"),
        ("is_saturday", "warm_day"),
        ("is_sunday", "warm_day"),
        ("is_friday", "is_precip_day"),
        ("is_saturday", "is_precip_day"),
        ("is_sunday", "is_precip_day"),
        ("is_friday", "windy_day"),
        ("is_saturday", "windy_day"),
        ("is_april", "warm_day"),
        ("is_april", "is_precip_day"),
    ]

    feature_cols = list(base_features)
    for left, right in interaction_pairs:
        name = f"{left}_x_{right}"
        frame[name] = frame[left] * frame[right]
        feature_cols.append(name)

    targets = ["qty", "orders", "net_sales", "avg_qty_per_order"]
    rows = []
    score_rows = []
    for target in targets:
        model_frame = frame[[target] + feature_cols].dropna()
        X = model_frame[feature_cols].astype(float)
        y = model_frame[target].astype(float)
        X_scaled = (X - X.mean()) / X.std(ddof=0).replace(0, 1)
        design = np.column_stack([np.ones(len(X_scaled)), X_scaled.to_numpy()])
        coefficients, *_ = np.linalg.lstsq(design, y.to_numpy(), rcond=None)
        predictions = design @ coefficients
        residual = y.to_numpy() - predictions
        sse = float((residual**2).sum())
        sst = float(((y.to_numpy() - y.mean()) ** 2).sum())
        r_squared = 1 - (sse / sst) if sst else 0
        adjusted_r_squared = 1 - ((1 - r_squared) * (len(y) - 1) / max(len(y) - len(feature_cols) - 1, 1))
        score_rows.append(
            {
                "target": target,
                "rows": len(y),
                "features": len(feature_cols),
                "r_squared": r_squared,
                "adjusted_r_squared": adjusted_r_squared,
            }
        )
        for feature, coefficient in zip(feature_cols, coefficients[1:]):
            rows.append(
                {
                    "target": target,
                    "feature": feature,
                    "standardized_coefficient": coefficient,
                    "abs_standardized_coefficient": abs(coefficient),
                    "feature_type": "interaction" if "_x_" in feature else "main_effect",
                }
            )

    effects = pd.DataFrame(rows).sort_values("abs_standardized_coefficient", ascending=False)
    scores = pd.DataFrame(score_rows).sort_values("adjusted_r_squared", ascending=False)
    return effects, scores


if __name__ == "__main__":
    main()
