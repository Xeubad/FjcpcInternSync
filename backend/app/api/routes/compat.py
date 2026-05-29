"""与旧版 Flask app_excel 路径兼容的 API（Bearer 替代原 Session）。"""

import json
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.deps import AuthUser, get_text_upload_service, get_upload_service
from app.core.errors import ErrorCode, api_error_payload
from app.core.limiter import limiter
from app.domain.excel_batch import (
    build_legacy_excel_analyze_response,
    full_data_to_parsed_like_excel,
    normalize_excel_parsed,
)
from app.domain.excel_parser import generate_excel_template, parse_excel_file
from app.domain.report_text_parser import parse_report_content
from app.schemas.auth import AnalyzeBody, SaveCookieBody, TextBatchUploadBody
from app.services.text_upload_service import TextUploadService
from app.services.upload_service import UploadService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["compat"])


def _upload_http_response(payload: dict) -> JSONResponse:
    status_code = int(payload.get("http_status", 200))
    body = {k: v for k, v in payload.items() if k != "http_status"}
    return JSONResponse(content=body, status_code=status_code)


@router.post("/upload/day")
@limiter.limit("10/minute")
async def compat_upload_day(
    request: Request,
    body: TextBatchUploadBody,
    session: AuthUser,
    svc: TextUploadService = Depends(get_text_upload_service),
):
    student_id = body.student_id.strip()
    platform_token = body.token.strip()
    if not student_id or not platform_token:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "请先配置您的API Token和学号"},
        )
    out = await svc.upload_day(student_id, platform_token, body.content, body.start_date)
    return _upload_http_response(out)


@router.post("/upload/week")
@limiter.limit("10/minute")
async def compat_upload_week(
    request: Request,
    body: TextBatchUploadBody,
    session: AuthUser,
    svc: TextUploadService = Depends(get_text_upload_service),
):
    student_id = body.student_id.strip()
    platform_token = body.token.strip()
    if not student_id or not platform_token:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "缺少必要参数：student_id 和 token"},
        )
    out = await svc.upload_week(student_id, platform_token, body.content, body.start_date)
    return _upload_http_response(out)


@router.post("/upload/month")
@limiter.limit("10/minute")
async def compat_upload_month(
    request: Request,
    body: TextBatchUploadBody,
    session: AuthUser,
    svc: TextUploadService = Depends(get_text_upload_service),
):
    student_id = body.student_id.strip()
    platform_token = body.token.strip()
    if not student_id or not platform_token:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "缺少必要参数：student_id 和 token"},
        )
    out = await svc.upload_month(student_id, platform_token, body.content, body.start_date)
    return _upload_http_response(out)


@router.post("/analyze")
@limiter.limit("10/minute")
async def compat_analyze(request: Request, body: AnalyzeBody, session: AuthUser):
    reports = parse_report_content(body.content)
    lines = [line for line in body.content.split("\n") if line.strip()]
    return {
        "success": True,
        "total_lines": len(lines),
        "report_count": len(reports),
        "reports": reports[:5] if len(reports) > 5 else reports,
    }


@router.post("/save_cookie")
@limiter.limit("20/minute")
async def compat_save_cookie(request: Request, body: SaveCookieBody, session: AuthUser):
    settings = request.app.state.settings
    path: Path = settings.browser_cookies_save_path
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as file:
                config = json.load(file)
            if "users" not in config:
                config = {"users": {}}
        except (json.JSONDecodeError, OSError):
            config = {"users": {}}
    else:
        config = {"users": {}}

    config["users"][body.student_id.strip()] = {
        "cookie_string": body.cookie_string.strip(),
        "token": body.token.strip(),
        "updated_at": datetime.now().isoformat(),
    }

    try:
        with path.open("w", encoding="utf-8") as file:
            json.dump(config, file, ensure_ascii=False, indent=2)
    except OSError as exc:
        logger.exception("保存 Cookie 失败")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"保存失败: {exc}"},
        )

    logger.info("已保存用户 %s 的浏览器 Cookie 到 %s", body.student_id, path)
    return {"success": True, "message": f"用户{body.student_id}的配置已保存", "path": str(path)}


@router.get("/config")
@limiter.limit("300/minute")
async def compat_config(request: Request):
    base_url = (request.app.state.settings.public_base_url or "").strip()
    if not base_url:
        base_url = str(request.base_url).rstrip("/")
    return {
        "success": True,
        "base_url": base_url,
        "auth_api_url": base_url,
        "main_app_url": base_url,
    }


@router.post("/excel/analyze")
@limiter.limit("10/minute")
async def compat_excel_analyze(
    request: Request,
    session: AuthUser,
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls", ".xlsm")):
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "请上传Excel文件(.xlsx或.xls)"},
        )
    raw = await file.read()
    try:
        parsed = parse_excel_file(raw)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"success": False, "message": str(exc)})
    except Exception as exc:
        logger.exception("分析 Excel 失败")
        return JSONResponse(status_code=500, content={"success": False, "message": f"分析失败: {exc}"})
    return build_legacy_excel_analyze_response(parsed)


@router.get("/excel/template")
async def compat_excel_template_download():
    """旧版路径 GET /api/excel/template（无需登录，与 Flask 一致）。"""
    try:
        buf = generate_excel_template()
        # Starlette 响应头须为 latin-1；中文文件名用 RFC5987 filename*
        utf8_name = quote("实习日志模板.xlsx")
        headers = {
            "Content-Disposition": (
                'attachment; filename="fjcpc_report_template.xlsx"; '
                f"filename*=UTF-8''{utf8_name}"
            )
        }
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )
    except Exception as exc:
        logger.exception("生成 Excel 模板失败")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"生成模板失败: {exc}"},
        )


@router.post("/upload/excel")
@limiter.limit("10/minute")
async def compat_upload_excel(
    request: Request,
    session: AuthUser,
    upload_service: UploadService = Depends(get_upload_service),
):
    """
    旧版 POST /api/upload/excel：支持 application/json（cached_data）或 multipart/form-data（file）。
    同步执行并返回 results/total/success_count（与 excel_upload.html 一致）。
    """
    content_type = (request.headers.get("content-type") or "").lower()

    if "application/json" in content_type:
        try:
            data = await request.json()
        except Exception:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "JSON 格式错误"},
            )
        student_id = str(data.get("student_id", "")).strip()
        token = str(data.get("token", "")).strip()
        cached_data = data.get("cached_data")
        fd = cached_data.get("full_data") if isinstance(cached_data, dict) else None
        if not isinstance(fd, dict):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "缺少 cached_data.full_data 或格式不正确"},
            )
        try:
            parsed = full_data_to_parsed_like_excel(fd)
        except (ValueError, TypeError, KeyError) as exc:
            return JSONResponse(status_code=400, content={"success": False, "message": str(exc)})
    else:
        try:
            form = await request.form()
        except Exception as exc:
            logger.exception("解析 multipart 失败")
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"表单解析失败: {exc}"},
            )
        student_id = str(form.get("student_id") or "").strip()
        token = str(form.get("token") or "").strip()
        up = form.get("file")
        if up is None or not getattr(up, "filename", None):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "请选择要上传的Excel文件"},
            )
        fname = str(up.filename).lower()
        if not fname.endswith((".xlsx", ".xls", ".xlsm")):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "请上传Excel文件(.xlsx或.xls)"},
            )
        raw = await up.read()
        try:
            parsed = parse_excel_file(raw)
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"success": False, "message": str(exc)})
        except Exception as exc:
            logger.exception("解析 Excel 失败")
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": f"解析失败: {exc}"},
            )

    all_errors, normalized_payload, _skipped = normalize_excel_parsed(parsed)
    if all_errors:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": f"文件检验失败：{'；'.join(all_errors)}。请修正后再上传。",
            },
        )

    payload, status_code = await upload_service.run_legacy_excel_upload_sync(
        student_id,
        token,
        normalized_payload,
    )
    return JSONResponse(content=payload, status_code=status_code)
