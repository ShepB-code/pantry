from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from pantry_engine.domain import DailyFeatures, EventSignal, ReservationDemand, WeatherSignal


def build_daily_features(
    *,
    reservations: list[ReservationDemand],
    weather: list[WeatherSignal],
    events: list[EventSignal],
    start: date,
    days: int,
) -> list[DailyFeatures]:
    reservations_by_date: dict[date, int] = defaultdict(int)
    for reservation in reservations:
        reservations_by_date[reservation.business_date] += reservation.covers

    attendance_by_date: dict[date, int] = defaultdict(int)
    for event in events:
        attendance_by_date[event.business_date] += event.expected_attendance or 0

    weather_by_date = {signal.business_date: signal for signal in weather}

    features: list[DailyFeatures] = []
    for offset in range(days):
        business_date = start + timedelta(days=offset)
        weather_signal = weather_by_date.get(business_date)
        features.append(
            DailyFeatures(
                business_date=business_date,
                day_of_week=business_date.weekday(),
                reservation_covers=reservations_by_date[business_date],
                event_attendance=attendance_by_date[business_date],
                weather_condition=weather_signal.condition if weather_signal else None,
                precipitation_probability=(
                    weather_signal.precipitation_probability if weather_signal else None
                ),
            )
        )
    return features
