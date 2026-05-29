"""Excel 解析结果校验与旧版 analyze 响应结构。"""

from datetime import datetime
from typing import Any

from app.domain.fjcpc_dates import validate_report_dates


def serialize_valid_rows(valid: list[dict]) -> list[dict]:
    """将校验后的记录转为可 JSON 持久化的行（日期为 YYYY-MM-DD）。"""
    out: list[dict] = []
    for row in valid:
        date_val = row["date"]
        date_str = date_val.strftime("%Y-%m-%d") if hasattr(date_val, "strftime") else str(date_val)
        out.append(
            {
                "work": row.get("work", ""),
                "achievement": row.get("achievement", ""),
                "problem": row.get("problem", ""),
                "word_count": row.get("word_count", 0),
                "date": date_str,
            }
        )
    return out


def normalize_excel_parsed(parsed: dict) -> tuple[list[str], dict[str, list[dict]], dict[str, int]]:
    """返回 (错误列表, 规范化 parsed, skipped 统计)。"""
    all_errors: list[str] = []
    normalized: dict[str, list[dict]] = {"day": [], "week": [], "month": []}

    for report_type in ("day", "week", "month"):
        reports_list = list(parsed.get(report_type) or [])
        if not reports_list:
            continue
        is_valid, error_msg, valid_reports = validate_report_dates(reports_list, report_type)
        if not is_valid or valid_reports is None:
            all_errors.append(error_msg or "校验失败")
            continue
        normalized[report_type] = serialize_valid_rows(valid_reports)

    skipped = {
        "day": int(parsed.get("day_skipped", 0) or 0),
        "week": int(parsed.get("week_skipped", 0) or 0),
        "month": int(parsed.get("month_skipped", 0) or 0),
    }
    return all_errors, normalized, skipped


def full_data_to_parsed_like_excel(full_data: dict) -> dict:
    """将旧版 cached_data.full_data 转为 parse_excel_file 形状。"""
    out: dict[str, Any] = {"day": [], "week": [], "month": [], "day_skipped": 0, "week_skipped": 0, "month_skipped": 0}
    for key in ("day", "week", "month"):
        for item in full_data.get(key) or []:
            row = dict(item)
            d = row.get("date")
            if isinstance(d, str):
                row["date"] = datetime.strptime(d, "%Y-%m-%d")
            out[key].append(row)
    return out


def build_legacy_excel_analyze_response(parsed: dict) -> dict:
    """与旧版 /api/excel/analyze 返回结构一致。"""
    day_list = []
    day_full = []
    for item in parsed.get("day") or []:
        raw_d = item.get("date")
        date_str = raw_d.strftime("%Y-%m-%d") if raw_d is not None and hasattr(raw_d, "strftime") else str(raw_d or "")
        day_list.append({"date": date_str, "word_count": item.get("word_count", 0)})
        day_full.append(
            {
                "date": date_str,
                "work": item.get("work", ""),
                "achievement": item.get("achievement", ""),
                "problem": item.get("problem", ""),
                "word_count": item.get("word_count", 0),
            }
        )

    week_list = []
    week_full = []
    for item in parsed.get("week") or []:
        raw_d = item.get("date")
        date_str = raw_d.strftime("%Y-%m-%d") if raw_d is not None and hasattr(raw_d, "strftime") else str(raw_d or "")
        week_list.append({"date": date_str, "word_count": item.get("word_count", 0)})
        week_full.append(
            {
                "date": date_str,
                "work": item.get("work", ""),
                "achievement": item.get("achievement", ""),
                "problem": item.get("problem", ""),
                "word_count": item.get("word_count", 0),
            }
        )

    month_list = []
    month_full = []
    for item in parsed.get("month") or []:
        raw_d = item.get("date")
        date_str = raw_d.strftime("%Y-%m-%d") if raw_d is not None and hasattr(raw_d, "strftime") else str(raw_d or "")
        month_list.append({"date": date_str, "word_count": item.get("word_count", 0)})
        month_full.append(
            {
                "date": date_str,
                "work": item.get("work", ""),
                "achievement": item.get("achievement", ""),
                "problem": item.get("problem", ""),
                "word_count": item.get("word_count", 0),
            }
        )

    return {
        "success": True,
        "day_count": len(day_list),
        "day_skipped": parsed.get("day_skipped", 0),
        "week_count": len(week_list),
        "week_skipped": parsed.get("week_skipped", 0),
        "month_count": len(month_list),
        "month_skipped": parsed.get("month_skipped", 0),
        "day_list": day_list,
        "week_list": week_list,
        "month_list": month_list,
        "total": len(day_list) + len(week_list) + len(month_list),
        "total_skipped": (parsed.get("day_skipped", 0) or 0)
        + (parsed.get("week_skipped", 0) or 0)
        + (parsed.get("month_skipped", 0) or 0),
        "full_data": {"day": day_full, "week": week_full, "month": month_full},
    }
