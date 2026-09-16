"""Institutional market conventions for ASRQuant 1.3.0.

The module is deliberately explicit: date adjustment, day counts and schedule
construction are first-class objects because small convention differences can
change accrued interest, PV and hedge sensitivities.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Iterable
import calendar as _calendar

import pandas as pd


class BusinessDayConvention(str, Enum):
    UNADJUSTED = "unadjusted"
    FOLLOWING = "following"
    MODIFIED_FOLLOWING = "modified_following"
    PRECEDING = "preceding"
    MODIFIED_PRECEDING = "modified_preceding"


class DayCount(str, Enum):
    ACT_360 = "ACT/360"
    ACT_365F = "ACT/365F"
    ACT_ACT_ISDA = "ACT/ACT ISDA"
    THIRTY_360_US = "30/360 US"
    THIRTY_E_360 = "30E/360"


def _date(value: date | str | pd.Timestamp) -> date:
    return value if isinstance(value, date) and not isinstance(value, pd.Timestamp) else pd.Timestamp(value).date()


def _eom(d: date) -> bool:
    return d.day == _calendar.monthrange(d.year, d.month)[1]


def _add_months(d: date, months: int, *, preserve_eom: bool = False) -> date:
    total = d.year * 12 + (d.month - 1) + months
    year, month0 = divmod(total, 12)
    month = month0 + 1
    last = _calendar.monthrange(year, month)[1]
    day = last if preserve_eom and _eom(d) else min(d.day, last)
    return date(year, month, day)


def year_fraction(start: date | str, end: date | str, convention: DayCount | str = DayCount.ACT_365F) -> float:
    s, e = _date(start), _date(end)
    if e < s:
        raise ValueError("end must not precede start")
    dc = DayCount(convention)
    if dc is DayCount.ACT_360:
        return (e - s).days / 360.0
    if dc is DayCount.ACT_365F:
        return (e - s).days / 365.0
    if dc is DayCount.THIRTY_E_360:
        d1, d2 = min(s.day, 30), min(e.day, 30)
        return ((e.year-s.year)*360 + (e.month-s.month)*30 + d2-d1) / 360.0
    if dc is DayCount.THIRTY_360_US:
        d1 = 30 if s.day == 31 else s.day
        d2 = 30 if e.day == 31 and d1 >= 30 else e.day
        return ((e.year-s.year)*360 + (e.month-s.month)*30 + d2-d1) / 360.0
    if s == e:
        return 0.0
    cursor = s
    value = 0.0
    while cursor < e:
        year_end = date(cursor.year + 1, 1, 1)
        stop = min(e, year_end)
        denom = 366.0 if _calendar.isleap(cursor.year) else 365.0
        value += (stop - cursor).days / denom
        cursor = stop
    return value


@dataclass(frozen=True)
class Calendar:
    name: str = "weekend-only"
    holidays: frozenset[date] = field(default_factory=frozenset)
    weekend: tuple[int, ...] = (5, 6)

    def is_business_day(self, value: date | str) -> bool:
        d = _date(value)
        return d.weekday() not in self.weekend and d not in self.holidays

    def adjust(self, value: date | str, convention: BusinessDayConvention | str = BusinessDayConvention.FOLLOWING) -> date:
        d = _date(value)
        conv = BusinessDayConvention(convention)
        if conv is BusinessDayConvention.UNADJUSTED or self.is_business_day(d):
            return d
        if conv in {BusinessDayConvention.FOLLOWING, BusinessDayConvention.MODIFIED_FOLLOWING}:
            out = d
            while not self.is_business_day(out):
                out += timedelta(days=1)
            if conv is BusinessDayConvention.MODIFIED_FOLLOWING and out.month != d.month:
                return self.adjust(d, BusinessDayConvention.PRECEDING)
            return out
        out = d
        while not self.is_business_day(out):
            out -= timedelta(days=1)
        if conv is BusinessDayConvention.MODIFIED_PRECEDING and out.month != d.month:
            return self.adjust(d, BusinessDayConvention.FOLLOWING)
        return out

    def advance_business_days(self, value: date | str, days: int) -> date:
        if days == 0:
            return self.adjust(value, BusinessDayConvention.FOLLOWING)
        step = 1 if days > 0 else -1
        left = abs(days)
        out = _date(value)
        while left:
            out += timedelta(days=step)
            if self.is_business_day(out):
                left -= 1
        return out

    def with_holidays(self, holidays: Iterable[date | str]) -> "Calendar":
        return Calendar(self.name, self.holidays | frozenset(_date(x) for x in holidays), self.weekend)


def weekend_calendar() -> Calendar:
    return Calendar()


def _easter_sunday(year: int) -> date:
    a = year % 19; b = year // 100; c = year % 100
    d = b // 4; e = b % 4; f = (b + 8) // 25; g = (b - f + 1) // 3
    h = (19*a + b - d - g + 15) % 30; i = c // 4; k = c % 4
    l = (32 + 2*e + 2*i - h - k) % 7; m = (a + 11*h + 22*l) // 451
    month = (h + l - 7*m + 114) // 31
    day = ((h + l - 7*m + 114) % 31) + 1
    return date(year, month, day)


def target_calendar(years: Iterable[int] | None = None) -> Calendar:
    years = list(years or range(1999, 2101))
    holidays: set[date] = set()
    for y in years:
        easter = _easter_sunday(y)
        holidays.update({date(y,1,1), easter-timedelta(days=2), easter+timedelta(days=1), date(y,5,1), date(y,12,25), date(y,12,26)})
    return Calendar("TARGET", frozenset(holidays))


@dataclass(frozen=True)
class SchedulePeriod:
    accrual_start: date
    accrual_end: date
    payment_date: date
    fixing_date: date
    accrual_factor: float


@dataclass(frozen=True)
class Schedule:
    periods: tuple[SchedulePeriod, ...]
    calendar: Calendar
    day_count: DayCount
    frequency_months: int

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([p.__dict__ for p in self.periods])


def generate_schedule(start: date | str, end: date | str, *, frequency_months: int = 6, calendar: Calendar | None = None, business_day_convention: BusinessDayConvention | str = BusinessDayConvention.MODIFIED_FOLLOWING, day_count: DayCount | str = DayCount.ACT_365F, payment_lag_business_days: int = 0, fixing_lag_business_days: int = 2, end_of_month: bool = False) -> Schedule:
    s, e = _date(start), _date(end)
    if e <= s or frequency_months <= 0:
        raise ValueError("require end > start and positive frequency_months")
    cal = calendar or weekend_calendar(); dc = DayCount(day_count)
    dates = [s]; cursor = s
    while True:
        nxt = _add_months(cursor, frequency_months, preserve_eom=end_of_month)
        if nxt >= e:
            dates.append(e); break
        dates.append(nxt); cursor = nxt
    periods: list[SchedulePeriod] = []
    for raw_start, raw_end in zip(dates[:-1], dates[1:]):
        a0 = cal.adjust(raw_start, business_day_convention); a1 = cal.adjust(raw_end, business_day_convention)
        pay = cal.advance_business_days(a1, payment_lag_business_days) if payment_lag_business_days else a1
        fix = cal.advance_business_days(a0, -fixing_lag_business_days) if fixing_lag_business_days else a0
        periods.append(SchedulePeriod(a0, a1, pay, fix, year_fraction(a0, a1, dc)))
    return Schedule(tuple(periods), cal, dc, frequency_months)


__all__ = ["BusinessDayConvention", "DayCount", "Calendar", "SchedulePeriod", "Schedule", "year_fraction", "weekend_calendar", "target_calendar", "generate_schedule"]
