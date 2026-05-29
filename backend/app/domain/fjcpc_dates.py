"""实习报表日期校验（自旧版 app_excel 迁移）。"""

from calendar import monthrange
from datetime import datetime, timedelta


def is_workday(date: datetime) -> bool:
    """周一到周五为工作日。"""
    return date.weekday() < 5


def get_last_workday_of_month(year: int, month: int) -> datetime:
    """指定月份最后一个工作日。"""
    last_day = monthrange(year, month)[1]
    last_date = datetime(year, month, last_day)

    while not is_workday(last_date):
        last_date -= timedelta(days=1)

    return last_date


def validate_report_dates(
    reports_list: list[dict],
    report_type: str,
) -> tuple[bool, str | None, list[dict] | None]:
    """验证报告日期列表，返回 (是否有效, 错误信息, 有效报告列表)。"""
    type_name = {"day": "日报", "week": "周报", "month": "月报"}.get(report_type, report_type)

    if not reports_list:
        return True, None, []

    seen_dates: set[str] = set()
    valid_reports: list[dict] = []
    errors: list[str] = []
    now = datetime.now()

    for i, report in enumerate(reports_list):
        report_date = report["date"]

        if report_date is None:
            errors.append(f"{type_name}第{i + 1}条：日期不能为空")
            continue

        if isinstance(report_date, str):
            try:
                report_date = datetime.strptime(report_date, "%Y-%m-%d")
            except ValueError:
                errors.append(
                    f'{type_name}第{i + 1}条：日期格式错误 "{report_date}"，应为YYYY-MM-DD格式'
                )
                continue

        date_str = report_date.strftime("%Y-%m-%d")

        if report_date > now:
            errors.append(f'{type_name}第{i + 1}条：日期 "{date_str}" 是未来日期，不允许上传')
            continue

        if date_str in seen_dates:
            errors.append(
                f'{type_name}第{i + 1}条：日期 "{date_str}" 与前面的记录重复，不允许重复上传'
            )
            continue

        seen_dates.add(date_str)
        report["date"] = report_date
        valid_reports.append(report)

    if errors:
        return False, "；".join(errors), None

    return True, None, valid_reports
