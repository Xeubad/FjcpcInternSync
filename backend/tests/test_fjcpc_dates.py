from datetime import datetime, timedelta

from app.domain.fjcpc_dates import get_last_workday_of_month, validate_report_dates


def test_get_last_workday_of_month_jan_2025():
    d = get_last_workday_of_month(2025, 1)
    assert d.month == 1
    assert d.weekday() < 5


def test_validate_report_dates_future_rejected():
    future = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    rows = [{"date": future, "work": "a" * 200, "achievement": "", "problem": ""}]
    ok, err, _ = validate_report_dates(rows, "day")
    assert ok is False
    assert err and "未来日期" in err


def test_validate_report_dates_ok():
    past = "2020-01-02"
    rows = [{"date": past, "work": "a" * 200, "achievement": "", "problem": ""}]
    ok, err, valid = validate_report_dates(rows, "day")
    assert ok is True
    assert err is None
    assert valid and isinstance(valid[0]["date"], datetime)
