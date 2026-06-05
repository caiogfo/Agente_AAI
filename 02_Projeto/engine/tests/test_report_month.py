"""The reported month is parameterized (REPORT_MONTH / --month), and the default
reproduces the case month (April 2025) exactly."""
import datetime as dt

import pytest

from engine import config


# ----------------------------------------------------------------- label & slug
@pytest.mark.parametrize("d,label,slug", [
    (dt.date(2025, 4, 1), "abril de 2025", "abr25"),
    (dt.date(2025, 5, 1), "maio de 2025", "mai25"),
    (dt.date(2026, 12, 1), "dezembro de 2026", "dez26"),
    (dt.date(2025, 1, 1), "janeiro de 2025", "jan25"),
])
def test_month_label_and_slug(d, label, slug):
    assert config.month_label_pt(d) == label
    assert config.month_slug(d) == slug


# ---------------------------------------------------- parse REPORT_MONTH values
@pytest.mark.parametrize("raw,expected", [
    ("2025-04", dt.date(2025, 4, 1)),
    ("2025-12", dt.date(2025, 12, 1)),
    (None, dt.date(2025, 4, 1)),       # default = case month
    ("garbage", dt.date(2025, 4, 1)),  # invalid falls back to default
])
def test_parse_report_month(raw, expected):
    assert config.parse_report_month(raw) == expected


# --------------------------------------------- letter dates derive from the month
def test_dates_derive_from_reported_month():
    # statement closes early next month; letter follows a few days later
    assert config.snapshot_date_for(dt.date(2025, 4, 1)) == dt.date(2025, 5, 7)
    assert config.issue_date_for(dt.date(2025, 4, 1)) == dt.date(2025, 5, 12)
    # a different month flows through coherently (e.g. May -> June dates)
    assert config.snapshot_date_for(dt.date(2025, 5, 1)) == dt.date(2025, 6, 7)
    assert config.issue_date_for(dt.date(2025, 12, 1)) == dt.date(2026, 1, 12)


# ------------------------------------------------ default reproduces the case month
def test_default_is_the_case_month():
    assert config.REFERENCE_MONTH == dt.date(2025, 4, 1)
    assert config.REFERENCE_MONTH_LABEL_PT == "abril de 2025"
    assert config.REFERENCE_MONTH_SLUG == "abr25"
    assert config.SNAPSHOT_DATE == dt.date(2025, 5, 7)
    assert config.ISSUE_DATE == dt.date(2025, 5, 12)
