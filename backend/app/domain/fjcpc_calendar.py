"""工作日与周五计算（自 app_excel 迁移）。"""

from datetime import datetime, timedelta


def is_workday(date: datetime) -> bool:
    return date.weekday() < 5


def get_next_workday(date: datetime) -> datetime:
    next_day = date + timedelta(days=1)
    while not is_workday(next_day):
        next_day += timedelta(days=1)
    return next_day


def get_workdays_in_range(start_date: datetime, count: int) -> list[datetime]:
    workdays: list[datetime] = []
    current_date = start_date
    while len(workdays) < count:
        if is_workday(current_date):
            workdays.append(current_date)
        current_date += timedelta(days=1)
    return workdays


def get_friday_of_week(date: datetime) -> datetime:
    """获取指定日期所在周的周五（与旧版逻辑一致）。"""
    days_to_friday = (4 - date.weekday()) % 7
    if days_to_friday == 0 and date.weekday() != 4:
        days_to_friday = 7
    return date + timedelta(days=days_to_friday)
