"""纯文本日报/周报/月报批量上传（自 app_excel /api/upload/* 迁移，异步）。"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

from app.core.config import Settings
from app.domain.fjcpc_calendar import (
    get_friday_of_week,
    get_next_workday,
    get_workdays_in_range,
    is_workday,
)
from app.domain.fjcpc_dates import get_last_workday_of_month
from app.domain.fjcpc_upstream import FjcPcUploadClient, is_fatal_upload_error
from app.domain.report_text_parser import parse_report_content

logger = logging.getLogger(__name__)


class TextUploadService:
    def __init__(self, settings: Settings):
        self._settings = settings

    async def _sleep_interval(self) -> None:
        await asyncio.sleep(max(0.0, self._settings.fjcpc_request_interval))

    async def upload_day(
        self,
        student_id: str,
        platform_token: str,
        content: str,
        start_date_str: str,
    ) -> dict[str, Any]:
        if not content or not start_date_str:
            return {"success": False, "message": "缺少必要参数：content 和 start_date"}

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError:
            return {"success": False, "message": f"日期格式错误: {start_date_str}，应为YYYY-MM-DD格式"}

        now = datetime.now()
        if start_date > now:
            return {"success": False, "message": f'起始日期 "{start_date_str}" 是未来日期，不允许上传'}

        if not is_workday(start_date):
            start_date = get_next_workday(start_date)

        reports = parse_report_content(content)
        if not reports:
            return {
                "success": False,
                "message": "报告内容格式不正确，需要每3行为一组（工作内容/收获成绩/问题指导）",
            }

        for i, report in enumerate(reports):
            total_len = len(report["work"] or "") + len(report["achievement"] or "") + len(report["problem"] or "")
            if total_len < 200:
                return {
                    "success": False,
                    "message": f"第{i + 1}份日报内容不足200字（当前{total_len}字），请补充内容",
                }

        workdays = get_workdays_in_range(start_date, len(reports))
        if len(set(workdays)) != len(workdays):
            return {"success": False, "message": "工作日计算出现重复日期，请减少报告数量或调整起始日期"}

        results: list[dict[str, Any]] = []
        success_count = 0
        abort_reason: str | None = None

        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        async with httpx.AsyncClient(
            verify=self._settings.fjcpc_verify_tls,
            limits=limits,
            timeout=self._settings.fjcpc_request_timeout,
        ) as client:
            holder = FjcPcUploadClient(self._settings)
            for i, report in enumerate(reports):
                report_date = workdays[i]
                ok, msg = await holder.submit_day(client, report, report_date, student_id, platform_token)
                results.append(
                    {"index": i + 1, "date": report_date.strftime("%Y-%m-%d"), "success": ok, "message": msg}
                )
                if ok:
                    success_count += 1
                else:
                    if is_fatal_upload_error(msg):
                        abort_reason = msg
                        break
                if i < len(reports) - 1:
                    await self._sleep_interval()

        if abort_reason:
            return {
                "success": False,
                "message": f"上传已中止：{abort_reason}",
                "results": results,
                "total": len(reports),
                "success_count": success_count,
                "http_status": 500,
            }

        if success_count == 0:
            return {
                "success": False,
                "message": f"上传失败：所有{len(reports)}份日报均未提交成功。最后错误：{results[-1]['message'] if results else '未知错误'}",
                "results": results,
                "total": len(reports),
                "success_count": 0,
                "http_status": 500,
            }

        return {
            "success": True,
            "message": f"日报上传完成，成功 {success_count}/{len(reports)} 个",
            "results": results,
            "total": len(reports),
            "success_count": success_count,
            "http_status": 200,
        }

    async def upload_week(
        self,
        student_id: str,
        platform_token: str,
        content: str,
        start_date_str: str,
    ) -> dict[str, Any]:
        if not content or not start_date_str:
            return {"success": False, "message": "缺少必要参数：content 和 start_date"}

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError:
            return {"success": False, "message": f"日期格式错误: {start_date_str}，应为YYYY-MM-DD格式"}

        now = datetime.now()
        if start_date > now:
            return {"success": False, "message": f'起始日期 "{start_date_str}" 是未来日期，不允许上传'}

        if start_date.weekday() != 4:
            start_date = get_friday_of_week(start_date)

        reports = parse_report_content(content)
        if not reports:
            return {
                "success": False,
                "message": "报告内容格式不正确，需要每3行为一组（工作内容/收获成绩/问题指导）",
            }

        for i, report in enumerate(reports):
            total_len = len(report["work"] or "") + len(report["achievement"] or "") + len(report["problem"] or "")
            if total_len < 200:
                return {
                    "success": False,
                    "message": f"第{i + 1}份周报内容不足200字（当前{total_len}字），请补充内容",
                }

        fridays = [start_date + timedelta(days=i * 7) for i in range(len(reports))]
        if len(set(fridays)) != len(fridays):
            return {"success": False, "message": "周五日期计算出现重复，请减少报告数量或调整起始日期"}

        results: list[dict[str, Any]] = []
        success_count = 0
        abort_reason: str | None = None

        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        async with httpx.AsyncClient(
            verify=self._settings.fjcpc_verify_tls,
            limits=limits,
            timeout=self._settings.fjcpc_request_timeout,
        ) as client:
            holder = FjcPcUploadClient(self._settings)
            for i, report in enumerate(reports):
                current_friday = fridays[i]
                ok, msg = await holder.submit_week(client, report, current_friday, student_id, platform_token)
                results.append(
                    {"index": i + 1, "date": current_friday.strftime("%Y-%m-%d"), "success": ok, "message": msg}
                )
                if ok:
                    success_count += 1
                elif is_fatal_upload_error(msg):
                    abort_reason = msg
                    break
                if i < len(reports) - 1:
                    await self._sleep_interval()

        if abort_reason:
            return {
                "success": False,
                "message": f"上传已中止：{abort_reason}",
                "results": results,
                "total": len(reports),
                "success_count": success_count,
                "http_status": 500,
            }

        if success_count == 0:
            return {
                "success": False,
                "message": f"上传失败：所有{len(reports)}份周报均未提交成功。最后错误：{results[-1]['message'] if results else '未知错误'}",
                "results": results,
                "total": len(reports),
                "success_count": 0,
                "http_status": 500,
            }

        return {
            "success": True,
            "message": f"周报上传完成，成功 {success_count}/{len(reports)} 个",
            "results": results,
            "total": len(reports),
            "success_count": success_count,
            "http_status": 200,
        }

    async def upload_month(
        self,
        student_id: str,
        platform_token: str,
        content: str,
        start_date_str: str,
    ) -> dict[str, Any]:
        if not content or not start_date_str:
            return {"success": False, "message": "缺少必要参数：content 和 start_date"}

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError:
            return {"success": False, "message": f"日期格式错误: {start_date_str}，应为YYYY-MM-DD格式"}

        now = datetime.now()
        if start_date > now:
            return {"success": False, "message": f'起始日期 "{start_date_str}" 是未来日期，不允许上传'}

        reports = parse_report_content(content)
        if not reports:
            return {
                "success": False,
                "message": "报告内容格式不正确，需要每3行为一组（工作内容/收获成绩/问题指导）",
            }

        for i, report in enumerate(reports):
            total_len = len(report["work"] or "") + len(report["achievement"] or "") + len(report["problem"] or "")
            if total_len < 200:
                return {
                    "success": False,
                    "message": f"第{i + 1}份月报内容不足200字（当前{total_len}字），请补充内容",
                }

        month_ranges: list[tuple[datetime, datetime]] = []
        for i in range(len(reports)):
            year = start_date.year
            month = start_date.month + i
            if month > 12:
                month -= 12
                year += 1
            month_start = datetime(year, month, 1)
            month_end = get_last_workday_of_month(year, month)
            month_ranges.append((month_start, month_end))

        unique_ranges = set((r[0], r[1]) for r in month_ranges)
        if len(unique_ranges) != len(month_ranges):
            return {"success": False, "message": "月份日期范围计算出现重复，请减少报告数量或调整起始月份"}

        results: list[dict[str, Any]] = []
        success_count = 0
        abort_reason: str | None = None

        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        async with httpx.AsyncClient(
            verify=self._settings.fjcpc_verify_tls,
            limits=limits,
            timeout=self._settings.fjcpc_request_timeout,
        ) as client:
            holder = FjcPcUploadClient(self._settings)
            for i, report in enumerate(reports):
                month_start, month_end = month_ranges[i]
                ok, msg = await holder.submit_month(client, report, month_start, student_id, platform_token)
                results.append(
                    {
                        "index": i + 1,
                        "date_range": f"{month_start.strftime('%Y-%m-%d')} ~ {month_end.strftime('%Y-%m-%d')}",
                        "success": ok,
                        "message": msg,
                    }
                )
                if ok:
                    success_count += 1
                elif is_fatal_upload_error(msg):
                    abort_reason = msg
                    break
                if i < len(reports) - 1:
                    await self._sleep_interval()

        if abort_reason:
            return {
                "success": False,
                "message": f"上传已中止：{abort_reason}",
                "results": results,
                "total": len(reports),
                "success_count": success_count,
                "http_status": 500,
            }

        if success_count == 0:
            return {
                "success": False,
                "message": f"上传失败：所有{len(reports)}份月报均未提交成功。最后错误：{results[-1]['message'] if results else '未知错误'}",
                "results": results,
                "total": len(reports),
                "success_count": 0,
                "http_status": 500,
            }

        return {
            "success": True,
            "message": f"月报上传完成，成功 {success_count}/{len(reports)} 个",
            "results": results,
            "total": len(reports),
            "success_count": success_count,
            "http_status": 200,
        }
