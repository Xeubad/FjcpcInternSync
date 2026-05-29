import logging
from datetime import datetime
from typing import Any

import httpx

from app.core.config import Settings
from app.core.errors import ErrorCode
from app.domain.fjcpc_dates import validate_report_dates
from app.domain.fjcpc_upstream import FjcPcUploadClient, run_excel_batch
from app.repositories.interfaces import LogRepository, TaskRepository

logger = logging.getLogger(__name__)


class UploadService:
    """上传领域：任务编排、FJCPC 上游调用与批量 Excel。"""

    def __init__(
        self,
        settings: Settings,
        tasks: TaskRepository,
        logs: LogRepository,
    ):
        self._settings = settings
        self._tasks = tasks
        self._logs = logs

    def create_task(self, report_type: str, payload: dict[str, Any], created_by: str) -> dict[str, Any]:
        return self._tasks.create(
            {
                "type": report_type,
                "status": "pending",
                "created_by": created_by,
                "payload": payload,
            }
        )

    def _merge_payload(self, task_id: str, extra: dict[str, Any]) -> None:
        current = self._tasks.get(task_id) or {}
        base = dict(current.get("payload") or {})
        base.update(extra)
        self._tasks.update(task_id, {"payload": base})

    async def execute_task(self, task_id: str) -> dict[str, Any]:
        # 幂等守卫：上游接口不幂等，重复执行会在平台产生重复记录。
        # claim_for_run 在同一把文件锁内原子完成「读状态 + 改为 running」，
        # 因此并发触发（如连点两次「执行」）只有一个能抢占成功。
        # 如需重新上传，应走 /retry（会先将状态重置为 pending）。
        outcome, task = self._tasks.claim_for_run(task_id)
        if outcome == "not_found":
            return {"ok": False, "error": ErrorCode.PARAM_INVALID.value, "message": "任务不存在"}
        if outcome == "running":
            logger.warning("任务 %s 正在执行，忽略重复触发", task_id)
            return {"ok": False, "error": ErrorCode.PARAM_INVALID.value, "message": "任务正在执行中"}
        if outcome == "success":
            logger.warning("任务 %s 已成功，忽略重复触发（避免重复上传）", task_id)
            return {"ok": False, "error": ErrorCode.PARAM_INVALID.value, "message": "任务已完成，如需重新上传请使用重试"}

        assert task is not None  # outcome == "claimed"
        payload = dict(task.get("payload") or {})
        student_id = str(payload.get("student_id") or "").strip()
        platform_token = str(payload.get("fjcpc_token") or "").strip()
        kind = str(payload.get("kind") or "single")

        dry_reason: str | None = None
        if self._settings.fjcpc_dry_run:
            dry_reason = "FJCPC_DRY_RUN=true"
        elif not student_id or not platform_token:
            dry_reason = "缺少 student_id 或 fjcpc_token（平台实习接口凭证）"

        if dry_reason:
            detail = {"mode": "dry_run", "reason": dry_reason}
            self._tasks.update(task_id, {"status": "success", "error_code": None})
            self._merge_payload(task_id, detail)
            self._logs.append(
                "business",
                {"task_id": task_id, "event": "upload_skipped", "detail": detail},
            )
            return {"ok": True, **detail}

        if kind == "excel_batch":
            return await self._execute_excel_batch(task_id, student_id, platform_token, payload)

        return await self._execute_single_report(task_id, task.get("type", "day"), student_id, platform_token, payload)

    async def _execute_single_report(
        self,
        task_id: str,
        report_type: str,
        student_id: str,
        platform_token: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        report = payload.get("report")
        if not isinstance(report, dict):
            self._tasks.update(
                task_id,
                {"status": "failed", "error_code": ErrorCode.PARAM_MISSING.value},
            )
            self._merge_payload(task_id, {"upload_error": "缺少 payload.report"})
            return {"ok": False, "error": ErrorCode.PARAM_MISSING.value}

        date_raw = payload.get("report_date")
        if not date_raw:
            self._tasks.update(
                task_id,
                {"status": "failed", "error_code": ErrorCode.PARAM_MISSING.value},
            )
            self._merge_payload(task_id, {"upload_error": "缺少 payload.report_date"})
            return {"ok": False, "error": ErrorCode.PARAM_MISSING.value}

        if isinstance(date_raw, str):
            report_date = datetime.strptime(date_raw, "%Y-%m-%d")
        elif isinstance(date_raw, datetime):
            report_date = date_raw
        else:
            self._tasks.update(
                task_id,
                {"status": "failed", "error_code": ErrorCode.PARAM_INVALID.value},
            )
            return {"ok": False, "error": ErrorCode.PARAM_INVALID.value}

        client_holder = FjcPcUploadClient(self._settings)

        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        async with httpx.AsyncClient(
            verify=self._settings.fjcpc_verify_tls,
            limits=limits,
            timeout=self._settings.fjcpc_request_timeout,
        ) as client:
            if report_type == "day":
                ok, msg = await client_holder.submit_day(client, report, report_date, student_id, platform_token)
            elif report_type == "week":
                ok, msg = await client_holder.submit_week(client, report, report_date, student_id, platform_token)
            else:
                ok, msg = await client_holder.submit_month(client, report, report_date, student_id, platform_token)

        results = [{"type": report_type, "date": report_date.strftime("%Y-%m-%d"), "success": ok, "message": msg}]
        self._merge_payload(task_id, {"upload_results": results, "upload_summary": {"success": int(ok), "total": 1}})

        if ok:
            self._tasks.update(task_id, {"status": "success", "error_code": None})
            self._logs.append("business", {"task_id": task_id, "event": "upload_ok", "detail": msg})
            return {"ok": True, "message": msg}

        self._tasks.update(
            task_id,
            {"status": "failed", "error_code": ErrorCode.UPSTREAM_HTTP_ERROR.value},
        )
        self._logs.append("business", {"task_id": task_id, "event": "upload_failed", "detail": msg})
        return {"ok": False, "error": ErrorCode.UPSTREAM_HTTP_ERROR.value, "detail": msg}

    async def _execute_excel_batch(
        self,
        task_id: str,
        student_id: str,
        platform_token: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        parsed = payload.get("parsed")
        if not isinstance(parsed, dict):
            self._tasks.update(
                task_id,
                {"status": "failed", "error_code": ErrorCode.PARAM_INVALID.value},
            )
            self._merge_payload(task_id, {"upload_error": "缺少 payload.parsed"})
            return {"ok": False, "error": ErrorCode.PARAM_INVALID.value}

        all_errors: list[str] = []
        normalized: dict[str, list[dict[str, Any]]] = {"day": [], "week": [], "month": []}

        for report_type in ("day", "week", "month"):
            rows = list(parsed.get(report_type) or [])
            if not rows:
                continue
            ok, err_msg, valid = validate_report_dates(rows, report_type)
            if not ok or valid is None:
                all_errors.append(err_msg or "校验失败")
                continue
            normalized[report_type] = valid

        if all_errors:
            msg = "；".join(all_errors)
            self._tasks.update(
                task_id,
                {"status": "failed", "error_code": ErrorCode.PARAM_INVALID.value},
            )
            self._merge_payload(task_id, {"upload_error": msg})
            return {"ok": False, "error": ErrorCode.PARAM_INVALID.value, "detail": msg}

        results, abort_reason = await run_excel_batch(
            self._settings,
            student_id,
            platform_token,
            normalized,
        )

        success_count = sum(1 for item in results if item.get("success"))
        total_count = len(results)

        self._merge_payload(
            task_id,
            {
                "upload_results": results,
                "upload_summary": {
                    "success_count": success_count,
                    "total": total_count,
                    "aborted": bool(abort_reason),
                    "abort_reason": abort_reason,
                },
            },
        )

        if abort_reason:
            self._tasks.update(
                task_id,
                {"status": "failed", "error_code": ErrorCode.UPSTREAM_HTTP_ERROR.value},
            )
            self._logs.append(
                "business",
                {"task_id": task_id, "event": "upload_aborted", "detail": abort_reason},
            )
            return {"ok": False, "detail": abort_reason}

        if total_count == 0:
            self._tasks.update(task_id, {"status": "success", "error_code": None})
            self._merge_payload(task_id, {"upload_note": "无待上传记录"})
            return {"ok": True, "message": "无待上传记录"}

        if success_count == 0:
            last_msg = results[-1].get("message", "未知") if results else "未知"
            self._tasks.update(
                task_id,
                {"status": "failed", "error_code": ErrorCode.UPSTREAM_HTTP_ERROR.value},
            )
            self._logs.append("business", {"task_id": task_id, "event": "upload_all_failed", "detail": last_msg})
            return {"ok": False, "detail": last_msg}

        if success_count < total_count:
            self._tasks.update(
                task_id,
                {"status": "failed", "error_code": ErrorCode.UPSTREAM_HTTP_ERROR.value},
            )
            self._logs.append(
                "business",
                {
                    "task_id": task_id,
                    "event": "upload_partial",
                    "success_count": success_count,
                    "total": total_count,
                },
            )
            return {"ok": False, "detail": f"部分成功 {success_count}/{total_count}"}

        self._tasks.update(task_id, {"status": "success", "error_code": None})
        self._logs.append(
            "business",
            {"task_id": task_id, "event": "upload_batch_ok", "success_count": success_count},
        )
        return {"ok": True, "message": f"上传完成 {success_count}/{total_count}"}

    async def run_legacy_excel_upload_sync(
        self,
        student_id: str,
        platform_token: str,
        normalized_payload: dict[str, list[dict[str, Any]]],
    ) -> tuple[dict[str, Any], int]:
        """
        与旧 Flask POST /api/upload/excel 同步语义：立即跑完并返回 results/total/success_count。
        normalized_payload 须已通过 normalize_excel_parsed（日期可为 str）。
        """
        if not student_id or not platform_token:
            return ({"success": False, "message": "请先配置您的API Token和学号"}, 400)

        if not any(normalized_payload.values()):
            return ({"success": False, "message": "Excel 中无有效待上传记录"}, 400)

        if self._settings.fjcpc_dry_run:
            results: list[dict[str, Any]] = []
            for report_type in ("day", "week", "month"):
                for row in normalized_payload.get(report_type) or []:
                    date_raw = row.get("date", "")
                    date_str = (
                        date_raw.strftime("%Y-%m-%d")
                        if isinstance(date_raw, datetime)
                        else str(date_raw)
                    )
                    results.append(
                        {
                            "type": report_type,
                            "date": date_str,
                            "success": True,
                            "message": "DRY_RUN（未请求上游）",
                        }
                    )
            total = len(results)
            return (
                {
                    "success": True,
                    "message": f"上传完成，成功 {total}/{total} 条",
                    "results": results,
                    "total": total,
                    "success_count": total,
                },
                200,
            )

        results, abort_reason = await run_excel_batch(
            self._settings,
            student_id,
            platform_token,
            normalized_payload,
        )
        success_count = sum(1 for item in results if item.get("success"))
        total_count = len(results)

        if abort_reason:
            return (
                {
                    "success": False,
                    "message": f"上传已中止：{abort_reason}",
                    "results": results,
                    "total": total_count,
                    "success_count": success_count,
                },
                500,
            )

        if success_count == 0:
            last_msg = results[-1].get("message", "未知错误") if results else "未知错误"
            return (
                {
                    "success": False,
                    "message": (
                        f"上传失败：所有{len(results)}条报告均未提交成功。"
                        f"最后错误信息：{last_msg}"
                    ),
                    "results": results,
                    "total": total_count,
                    "success_count": 0,
                },
                500,
            )

        return (
            {
                "success": True,
                "message": f"上传完成，成功 {success_count}/{total_count} 条",
                "results": results,
                "total": total_count,
                "success_count": success_count,
            },
            200,
        )
