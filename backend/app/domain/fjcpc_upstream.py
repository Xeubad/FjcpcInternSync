"""FJCPC 实习日志上游提交（自 app_excel._do_upload_with_auth / submit_* 迁移，异步 httpx）。"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings
from app.domain.fjcpc_dates import get_last_workday_of_month

logger = logging.getLogger(__name__)

MAX_FAILS_PER_AUTH = 3


def classify_error(message: str) -> str:
    """将原始错误转换为可诊断信息。"""
    if not message:
        return "未知错误"
    if "HTTP错误: 403" in message:
        return "权限校验失败（HTTP 403），当前认证方式可能缺少必需会话上下文"
    if "HTTP错误: 404" in message:
        return "接口地址不可用（HTTP 404），请检查 FJCPC_API_URL 是否已变更"
    if "开始时间" in message:
        return "请求参数不匹配：缺少或使用了错误的开始时间字段"
    return message


def is_fatal_upload_error(message: str) -> bool:
    """是否应立即中止批量上传。"""
    if not message:
        return False
    fatal_keywords = (
        "认证失败（已尝试所有认证方式）",
        "没有可用的认证方式",
        "HTTP错误: 404",
    )
    return any(keyword in message for keyword in fatal_keywords)


def load_browser_cookie(settings: Settings, student_id: str | None) -> tuple[str | None, str | None]:
    """从 JSON 文件加载浏览器 Cookie（aTrust 等场景）。"""
    path = settings.browser_cookies_read_path
    if not path.exists():
        logger.warning("浏览器 Cookie 文件不存在: %s", path)
        return None, None
    try:
        with path.open("r", encoding="utf-8") as file:
            config = json.load(file)
        if "users" in config and student_id:
            user_data = config["users"].get(student_id, {})
            cookie = user_data.get("cookie_string", "")
            token = user_data.get("token", "")
            logger.info("已加载用户 %s 的浏览器 Cookie，长度=%s", student_id, len(cookie or ""))
            return cookie or None, token or None
        cookie = config.get("cookie_string", "")
        token = config.get("token", "")
        return cookie or None, token or None
    except OSError as exc:
        logger.warning("读取浏览器 Cookie 失败: %s", exc)
        return None, None


def _check_success(resp: httpx.Response) -> tuple[bool, str]:
    if resp.status_code != 200:
        return False, f"HTTP错误: {resp.status_code}"
    try:
        result = resp.json()
        if result.get("code") == 20000:
            return True, str(result.get("message", "成功"))
        return False, str(result.get("message", "业务失败"))
    except json.JSONDecodeError:
        return False, f"JSON解析错误: {resp.text[:300]}"


def _build_headers(settings: Settings, cookie_str: str, platform_token: str) -> dict[str, str]:
    headers = {
        "Host": settings.fjcpc_api_host,
        "Cookie": cookie_str,
        "User-Agent": settings.fjcpc_user_agent,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": settings.fjcpc_referer,
        "Origin": settings.fjcpc_origin,
        "Authorization": platform_token,
        "X-Requested-With": "XMLHttpRequest",
    }
    return headers


def build_day_form(report: dict[str, Any], report_date: datetime, student_id: str, platform_token: str) -> dict[str, Any]:
    return {
        "student_id": student_id,
        "token": platform_token,
        "business_type": "day",
        "start_date": report_date.strftime("%Y/%m/%d"),
        "end_date": report_date.strftime("%Y/%m/%d"),
        "report_date": report_date.strftime("%Y/%m/%d"),
        "content": json.dumps(
            [
                {"title": "实习工作具体情况及实习任务完成情况", "content": report["work"], "require": "0", "sort": 1},
                {"title": "主要收获及工作成绩", "content": report["achievement"], "require": "0", "sort": 2},
                {"title": "工作中的问题及需要老师的指导帮助", "content": report["problem"], "require": "0", "sort": 3},
            ],
            ensure_ascii=False,
        ),
        "attachment": "",
    }


def build_week_form(report: dict[str, Any], week_start_date: datetime, student_id: str, platform_token: str) -> dict[str, Any]:
    return {
        "student_id": student_id,
        "token": platform_token,
        "business_type": "week",
        "start_date": week_start_date.strftime("%Y/%m/%d"),
        "end_date": week_start_date.strftime("%Y/%m/%d"),
        "content": json.dumps(
            [
                {"title": "实习工作具体情况及实习任务完成情况", "content": report["work"], "require": "0", "sort": 1},
                {"title": "主要收获及工作成绩", "content": report["achievement"], "require": "0", "sort": 2},
                {"title": "工作中的问题及需要老师的指导帮助", "content": report["problem"], "require": "0", "sort": 3},
            ],
            ensure_ascii=False,
        ),
        "attachment": "",
    }


def build_month_form(
    report: dict[str, Any],
    month_start_date: datetime,
    month_end_date: datetime,
    student_id: str,
    platform_token: str,
) -> dict[str, Any]:
    return {
        "student_id": student_id,
        "token": platform_token,
        "business_type": "month",
        "start_date": month_start_date.strftime("%Y/%m/%d"),
        "end_date": month_end_date.strftime("%Y/%m/%d"),
        "content": json.dumps(
            [
                {"title": "实习工作具体情况及实习任务完成情况", "content": report["work"], "require": "0", "sort": 1},
                {"title": "主要收获及工作成绩", "content": report["achievement"], "require": "0", "sort": 2},
                {"title": "工作中的问题及需要老师的指导帮助", "content": report["problem"], "require": "0", "sort": 3},
            ],
            ensure_ascii=False,
        ),
        "attachment": "",
    }


class FjcPcUploadClient:
    """与旧版 _do_upload_with_auth 等价的异步客户端。"""

    def __init__(self, settings: Settings):
        self._settings = settings

    async def upload_with_form(
        self,
        client: httpx.AsyncClient,
        form_data: dict[str, Any],
        student_id: str,
        platform_token: str,
    ) -> tuple[bool, str]:
        browser_cookie, _browser_token = load_browser_cookie(self._settings, student_id)

        cookie_header_from_template = self._settings.fjcpc_api_cookie_template.replace("{token}", platform_token)
        token_method = ("Token", cookie_header_from_template)
        cookie_method = ("Cookie", browser_cookie) if browser_cookie else None

        auth_methods: list[tuple[str, str]] = []
        priority = self._settings.fjcpc_auth_priority.lower()
        if priority == "token_first":
            auth_methods.append(token_method)
            if cookie_method:
                auth_methods.append(cookie_method)
        else:
            if cookie_method:
                auth_methods.append(cookie_method)
            auth_methods.append(token_method)

        if not auth_methods:
            return False, "没有可用的认证方式（Token和Cookie都不可用）"

        failure_details: list[str] = []

        for auth_name, cookie_str in auth_methods:
            logger.info("开始 %s 认证", auth_name)
            stopped_early = False
            last_msg = "未知错误"

            for attempt in range(MAX_FAILS_PER_AUTH):
                headers = _build_headers(self._settings, cookie_str, platform_token)
                url = self._settings.fjcpc_api_url.rstrip("/")
                logger.info("POST %s (%s 第%s次)", url, auth_name, attempt + 1)
                try:
                    resp = await client.post(
                        url,
                        headers=headers,
                        data=form_data,
                        params={"token": platform_token, "sf_request_type": "ajax"},
                    )
                except httpx.TimeoutException:
                    last_msg = "请求超时"
                    logger.warning("%s 认证失败（第%s次）：%s", auth_name, attempt + 1, last_msg)
                    continue
                except httpx.RequestError as exc:
                    last_msg = str(exc)
                    logger.warning("%s 认证失败（第%s次）：%s", auth_name, attempt + 1, last_msg)
                    continue

                success, msg = _check_success(resp)
                last_msg = msg
                if success:
                    logger.info("%s 认证成功", auth_name)
                    return True, msg

                logger.warning("%s 认证失败（第%s次）：%s", auth_name, attempt + 1, msg)
                if "HTTP错误: 404" in msg or "HTTP错误: 403" in msg:
                    stopped_early = True
                    break

            failure_details.append(f"{auth_name}:{classify_error(last_msg)}")
            if stopped_early:
                logger.warning("%s 认证重试已提前中止，尝试切换认证方式", auth_name)
            else:
                logger.warning("%s 认证 %s 次全部失败，尝试切换认证方式", auth_name, MAX_FAILS_PER_AUTH)

        return False, "认证失败（已尝试所有认证方式）：" + "；".join(failure_details)

    async def submit_day(
        self,
        client: httpx.AsyncClient,
        report: dict[str, Any],
        report_date: datetime,
        student_id: str,
        platform_token: str,
    ) -> tuple[bool, str]:
        try:
            form = build_day_form(report, report_date, student_id, platform_token)
            return await self.upload_with_form(client, form, student_id, platform_token)
        except Exception as exc:
            return False, f"请求异常: {exc}"

    async def submit_week(
        self,
        client: httpx.AsyncClient,
        report: dict[str, Any],
        week_start_date: datetime,
        student_id: str,
        platform_token: str,
    ) -> tuple[bool, str]:
        try:
            form = build_week_form(report, week_start_date, student_id, platform_token)
            return await self.upload_with_form(client, form, student_id, platform_token)
        except Exception as exc:
            return False, f"请求异常: {exc}"

    async def submit_month(
        self,
        client: httpx.AsyncClient,
        report: dict[str, Any],
        month_anchor: datetime,
        student_id: str,
        platform_token: str,
    ) -> tuple[bool, str]:
        try:
            month_end = get_last_workday_of_month(month_anchor.year, month_anchor.month)
            form = build_month_form(report, month_anchor, month_end, student_id, platform_token)
            return await self.upload_with_form(client, form, student_id, platform_token)
        except Exception as exc:
            return False, f"请求异常: {exc}"


async def run_excel_batch(
    settings: Settings,
    student_id: str,
    platform_token: str,
    parsed_by_type: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], str | None]:
    """
    按旧版顺序上传 day/week/month。
    返回 (每条结果列表, 若致命错误则中止原因)。
    """
    client_holder = FjcPcUploadClient(settings)
    results: list[dict[str, Any]] = []
    abort_reason: str | None = None
    interval = max(0.0, settings.fjcpc_request_interval)

    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    async with httpx.AsyncClient(
        verify=settings.fjcpc_verify_tls,
        limits=limits,
        timeout=settings.fjcpc_request_timeout,
    ) as client:
        for report_type, reports_list in [
            ("day", parsed_by_type.get("day") or []),
            ("week", parsed_by_type.get("week") or []),
            ("month", parsed_by_type.get("month") or []),
        ]:
            if not reports_list:
                continue
            type_name = {"day": "日报", "week": "周报", "month": "月报"}.get(report_type, report_type)
            logger.info("开始上传 %s，共 %s 条", type_name, len(reports_list))

            for report in reports_list:
                report_date = report["date"]
                if isinstance(report_date, str):
                    report_date = datetime.strptime(report_date, "%Y-%m-%d")

                if report_type == "day":
                    ok, msg = await client_holder.submit_day(client, report, report_date, student_id, platform_token)
                elif report_type == "week":
                    ok, msg = await client_holder.submit_week(client, report, report_date, student_id, platform_token)
                else:
                    ok, msg = await client_holder.submit_month(client, report, report_date, student_id, platform_token)

                results.append(
                    {
                        "type": report_type,
                        "date": report_date.strftime("%Y-%m-%d"),
                        "success": ok,
                        "message": msg,
                    }
                )

                if not ok and is_fatal_upload_error(msg):
                    abort_reason = msg
                    logger.warning("检测到致命错误，终止后续上传: %s", msg)
                    break

                await asyncio.sleep(interval)

            if abort_reason:
                break

    return results, abort_reason
