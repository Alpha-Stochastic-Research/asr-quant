"""Market calendars, day counts, business-day rules, and payment schedules.

The implementation is deliberately self-contained so ASRQuant does not require a
large calendar dependency for core fixed-income workflows.  Built-in calendars
cover the most common TARGET, US Federal and UK bank-holiday rules and callers
can always supply additional holiday dates for institution-specific calendars.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Iterable, Sequence

import pandas as pd


class BusinessDayConvention(str, Enum):
    FOLLOWING = "following"
    MODIFIED_FOLLOWING = "modified_following"
    PRECEDING = "preceding"
    MODIFIED_PRECEDING = "modified_preceding"
    UNADJUSTED = "unadjusted"


class DayCount(str, Enum):
    ACT_360 = "ACT/360"
    ACT_365F = "ACT/365F"
    ACT_ACT_ISDA = "ACT/ACT ISDA"
    THIRTY_360 = "30/360"
    THIRTY_E_360 = "30E/360"


class StubConvention(str, Enum):
    SHORT_FRONT = "short_front"
    LONG_FRONT = "long_front"
    SHORT_BACK = "short_back"
    LONG_BACK = "long_back"


class Compounding(str, Enum):
    CONTINUOUS = "continuous"
    SIMPLE = "simple"
    ANNUAL = "annual"
    SEMIANNUAL = "semiannual"
    QUARTERLY = "quarterly"
    MONTHLY = "monthly"


class Frequency(str, Enum):
    ANNUAL = "1Y"
    SEMIANNUAL = "6M"
    QUARTERLY = "3M"
    BIMONTHLY = "2M"
    MONTHLY = "1M"

    @property
    def months(self) -> int:
        return {
            Frequency.ANNUAL: 12,
            Frequency.SEMIANNUAL: 6,
            Frequency.QUARTERLY: 3,
            Frequency.BIMONTHLY: 2,
            Frequency.MONTHLY: 1,
        }[self]


def _as_date(value: date | str | pd.Timestamp) -> date:
    return pd.Timestamp(value).date()


def _easter_sunday(year: int) -> date:
    # Gregorian Meeus/Jones/Butcher algorithm.
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _observed_fixed(d: date) -> date:
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    offset = (weekday - d.weekday()) % 7
    return d + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    d = (pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(1)).date()
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _target_holidays(year: int) -> set[date]:
    easter = _easter_sunday(year)
    return {
        date(year, 1, 1),
        easter - timedelta(days=2),
        easter + timedelta(days=1),
        date(year, 5, 1),
        date(year, 12, 25),
        date(year, 12, 26),
    }


def _us_federal_holidays(year: int) -> set[date]:
    # Federal calendar. Good Friday is intentionally not included.
    holidays = {
        _observed_fixed(date(year, 1, 1)),
        _nth_weekday(year, 1, 0, 3),   # MLK
        _nth_weekday(year, 2, 0, 3),   # Washington's Birthday
        _last_weekday(year, 5, 0),     # Memorial Day
        _observed_fixed(date(year, 6, 19)),
        _observed_fixed(date(year, 7, 4)),
        _nth_weekday(year, 9, 0, 1),   # Labor Day
        _nth_weekday(year, 10, 0, 2),  # Columbus Day
        _observed_fixed(date(year, 11, 11)),
        _nth_weekday(year, 11, 3, 4),  # Thanksgiving
        _observed_fixed(date(year, 12, 25)),
    }
    return holidays


def _uk_holidays(year: int) -> set[date]:
    easter = _easter_sunday(year)
    holidays = {
        _observed_fixed(date(year, 1, 1)),
        easter - timedelta(days=2),
        easter + timedelta(days=1),
        _nth_weekday(year, 5, 0, 1),
        _last_weekday(year, 5, 0),
        _last_weekday(year, 8, 0),
    }
    christmas = date(year, 12, 25)
    boxing = date(year, 12, 26)
    # UK substitute-day handling for the Christmas pair.
    if christmas.weekday() == 5:      # Saturday
        holidays.update({date(year, 12, 27), date(year, 12, 28)})
    elif christmas.weekday() == 6:    # Sunday
        holidays.update({date(year, 12, 27), date(year, 12, 28)})
    else:
        holidays.add(christmas)
        if boxing.weekday() == 5:
            holidays.add(date(year, 12, 28))
        elif boxing.weekday() == 6:
            holidays.add(date(year, 12, 28))
        else:
            holidays.add(boxing)
    return holidays


@dataclass(frozen=True)
class Calendar:
    """Business-day calendar with extensible holiday overrides."""

    name: str = "WEEKENDS"
    holidays: frozenset[date] = field(default_factory=frozenset)
    weekend: tuple[int, ...] = (5, 6)

    @classmethod
    def from_name(
        cls,
        name: str,
        *,
        years: Iterable[int] | None = None,
        additional_holidays: Iterable[date | str] = (),
    ) -> "Calendar":
        key = str(name).strip().upper().replace("-", "_").replace(" ", "_")
        years_set = set(years or range(date.today().year - 10, date.today().year + 31))
        holidays: set[date] = set()
        if key in {"WEEKENDS", "WEEKEND", "NONE"}:
            canonical = "WEEKENDS"
        elif key in {"TARGET", "TARGET2", "EUR", "EURO"}:
            canonical = "TARGET"
            for y in years_set:
                holidays.update(_target_holidays(y))
        elif key in {"US", "USD", "US_FEDERAL", "FEDERAL"}:
            canonical = "US_FEDERAL"
            for y in years_set:
                holidays.update(_us_federal_holidays(y))
        elif key in {"UK", "GBP", "UK_BANK", "LONDON"}:
            canonical = "UK_BANK"
            for y in years_set:
                holidays.update(_uk_holidays(y))
        else:
            raise ValueError(f"unknown built-in calendar {name!r}")
        holidays.update(_as_date(d) for d in additional_holidays)
        return cls(canonical, frozenset(holidays))

    def is_business_day(self, value: date | str | pd.Timestamp) -> bool:
        d = _as_date(value)
        return d.weekday() not in self.weekend and d not in self.holidays

    def adjust(
        self,
        value: date | str | pd.Timestamp,
        convention: BusinessDayConvention | str = BusinessDayConvention.MODIFIED_FOLLOWING,
    ) -> date:
        d = _as_date(value)
        conv = BusinessDayConvention(convention)
        if conv is BusinessDayConvention.UNADJUSTED or self.is_business_day(d):
            return d
        if conv in {BusinessDayConvention.FOLLOWING, BusinessDayConvention.MODIFIED_FOLLOWING}:
            moved = d
            while not self.is_business_day(moved):
                moved += timedelta(days=1)
            if conv is BusinessDayConvention.MODIFIED_FOLLOWING and moved.month != d.month:
                return self.adjust(d, BusinessDayConvention.PRECEDING)
            return moved
        moved = d
        while not self.is_business_day(moved):
            moved -= timedelta(days=1)
        if conv is BusinessDayConvention.MODIFIED_PRECEDING and moved.month != d.month:
            return self.adjust(d, BusinessDayConvention.FOLLOWING)
        return moved

    def advance_business_days(self, value: date | str | pd.Timestamp, days: int) -> date:
        d = _as_date(value)
        if days == 0:
            return d
        step = 1 if days > 0 else -1
        remaining = abs(days)
        while remaining:
            d += timedelta(days=step)
            if self.is_business_day(d):
                remaining -= 1
        return d


def _days_in_year(year: int) -> int:
    return 366 if pd.Timestamp(year=year, month=12, day=31).is_leap_year else 365


def year_fraction(
    start: date | str | pd.Timestamp,
    end: date | str | pd.Timestamp,
    convention: DayCount | str = DayCount.ACT_365F,
) -> float:
    """Return accrual year fraction under common fixed-income conventions."""
    s, e = _as_date(start), _as_date(end)
    if e < s:
        raise ValueError("end must not precede start")
    raw = str(convention.value if isinstance(convention, DayCount) else convention).upper().replace(" ", "")
    if raw in {"ACT/360", "ACT360"}:
        return (e - s).days / 360.0
    if raw in {"ACT/365F", "ACT365F", "ACT/365", "ACT365"}:
        return (e - s).days / 365.0
    if raw in {"ACT/ACTISDA", "ACTACTISDA", "ACT/ACT", "ACTACT"}:
        if s == e:
            return 0.0
        total = 0.0
        cursor = s
        while cursor < e:
            next_year = date(cursor.year + 1, 1, 1)
            segment_end = min(e, next_year)
            total += (segment_end - cursor).days / _days_in_year(cursor.year)
            cursor = segment_end
        return total
    if raw in {"30/360", "30U/360", "BOND"}:
        d1 = min(s.day, 30)
        d2 = min(e.day, 30) if d1 == 30 else e.day
        return ((e.year - s.year) * 360 + (e.month - s.month) * 30 + d2 - d1) / 360.0
    if raw in {"30E/360", "30E360"}:
        d1, d2 = min(s.day, 30), min(e.day, 30)
        return ((e.year - s.year) * 360 + (e.month - s.month) * 30 + d2 - d1) / 360.0
    raise ValueError("unsupported day-count convention")


def _frequency_months(value: Frequency | str | int) -> int:
    if isinstance(value, Frequency):
        return value.months
    if isinstance(value, int):
        if value <= 0 or 12 % value:
            raise ValueError("integer frequency must divide 12")
        return 12 // value
    text = str(value).strip().upper()
    aliases = {"ANNUAL": 12, "SEMIANNUAL": 6, "QUARTERLY": 3, "MONTHLY": 1}
    if text in aliases:
        return aliases[text]
    if text.endswith("Y"):
        months = int(float(text[:-1]) * 12)
    elif text.endswith("M"):
        months = int(text[:-1])
    else:
        raise ValueError("frequency must be a Frequency, payments/year integer, or tenor like 6M")
    if months <= 0:
        raise ValueError("frequency must be positive")
    return months


def _month_end(d: date) -> date:
    return (pd.Timestamp(d) + pd.offsets.MonthEnd(0)).date()


def _add_months(d: date, months: int, preserve_eom: bool = False) -> date:
    base = pd.Timestamp(d) + pd.DateOffset(months=months)
    if preserve_eom:
        base = base + pd.offsets.MonthEnd(0)
    return base.date()


@dataclass(frozen=True)
class Schedule:
    """Date schedule with unadjusted, adjusted, fixing and payment dates."""

    start: date | str
    end: date | str
    frequency: Frequency | str | int = Frequency.SEMIANNUAL
    calendar: Calendar | str = "WEEKENDS"
    business_day: BusinessDayConvention | str = BusinessDayConvention.MODIFIED_FOLLOWING
    stub: StubConvention | str = StubConvention.SHORT_FRONT
    end_of_month: bool = False
    payment_lag: int = 0
    fixing_lag: int = 0
    day_count: DayCount | str = DayCount.ACT_365F

    def __post_init__(self) -> None:
        s, e = _as_date(self.start), _as_date(self.end)
        if e <= s:
            raise ValueError("schedule end must be after start")
        object.__setattr__(self, "start", s)
        object.__setattr__(self, "end", e)
        if isinstance(self.calendar, str):
            years = range(s.year - 1, e.year + 2)
            object.__setattr__(self, "calendar", Calendar.from_name(self.calendar, years=years))
        object.__setattr__(self, "business_day", BusinessDayConvention(self.business_day))
        object.__setattr__(self, "stub", StubConvention(self.stub))
        if self.payment_lag < 0 or self.fixing_lag < 0:
            raise ValueError("payment_lag and fixing_lag must be non-negative")
        _frequency_months(self.frequency)

    @property
    def unadjusted_dates(self) -> tuple[date, ...]:
        months = _frequency_months(self.frequency)
        preserve_eom = self.end_of_month and (_month_end(self.end) == self.end)
        stub = StubConvention(self.stub)
        s, e = self.start, self.end
        dates: list[date]
        if stub in {StubConvention.SHORT_FRONT, StubConvention.LONG_FRONT}:
            dates = [e]
            cursor = e
            while True:
                nxt = _add_months(cursor, -months, preserve_eom)
                if nxt <= s:
                    break
                dates.append(nxt)
                cursor = nxt
            dates.append(s)
            dates = sorted(dates)
            if stub is StubConvention.LONG_FRONT and len(dates) > 2:
                first_regular = _add_months(dates[0], months, preserve_eom)
                if first_regular != dates[1]:
                    dates.pop(1)
        else:
            dates = [s]
            cursor = s
            while True:
                nxt = _add_months(cursor, months, self.end_of_month and _month_end(s) == s)
                if nxt >= e:
                    break
                dates.append(nxt)
                cursor = nxt
            dates.append(e)
            if stub is StubConvention.LONG_BACK and len(dates) > 2:
                last_regular = _add_months(dates[-2], months, self.end_of_month and _month_end(s) == s)
                if last_regular != dates[-1]:
                    dates.pop(-2)
        return tuple(dates)

    @property
    def adjusted_dates(self) -> tuple[date, ...]:
        cal = self.calendar
        assert isinstance(cal, Calendar)
        return tuple(cal.adjust(d, self.business_day) for d in self.unadjusted_dates)

    @property
    def periods(self) -> tuple[tuple[date, date], ...]:
        dates = self.adjusted_dates
        return tuple(zip(dates[:-1], dates[1:]))

    @property
    def payment_dates(self) -> tuple[date, ...]:
        cal = self.calendar
        assert isinstance(cal, Calendar)
        return tuple(cal.advance_business_days(end, self.payment_lag) for _, end in self.periods)

    @property
    def fixing_dates(self) -> tuple[date, ...]:
        cal = self.calendar
        assert isinstance(cal, Calendar)
        return tuple(cal.advance_business_days(start, -self.fixing_lag) for start, _ in self.periods)

    @property
    def accrual_fractions(self) -> tuple[float, ...]:
        return tuple(year_fraction(s, e, self.day_count) for s, e in self.periods)

    def to_frame(self) -> pd.DataFrame:
        rows = []
        for i, ((s, e), fixing, payment, accrual) in enumerate(
            zip(self.periods, self.fixing_dates, self.payment_dates, self.accrual_fractions),
            start=1,
        ):
            rows.append(
                {
                    "period": i,
                    "accrual_start": pd.Timestamp(s),
                    "accrual_end": pd.Timestamp(e),
                    "fixing_date": pd.Timestamp(fixing),
                    "payment_date": pd.Timestamp(payment),
                    "accrual_fraction": accrual,
                }
            )
        return pd.DataFrame(rows).set_index("period")


__all__ = [
    "BusinessDayConvention",
    "DayCount",
    "StubConvention",
    "Compounding",
    "Frequency",
    "Calendar",
    "Schedule",
    "year_fraction",
]
