import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse

from app.api.deps import AuthUser, get_upload_service
from app.core.errors import ErrorCode, api_error_payload
from app.domain.excel_batch import full_data_to_parsed_like_excel, normalize_excel_parsed
from app.domain.excel_parser import generate_excel_template, parse_excel_file
from app.schemas.auth import ExcelCachedSubmitBody
from app.schemas.common import ApiSuccess
from app.services.upload_service import UploadService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])


def _enqueue_excel_batch(
    upload_service: UploadService,
    session: dict,
    student_id: str,
    fjcpc_token: str,
    normalized_payload: dict,
    skipped: dict[str, int],
) -> str:
    task_payload = {
        "kind": "excel_batch",
        "student_id": student_id.strip(),
        "fjcpc_token": fjcpc_token.strip(),
        "parsed": normalized_payload,
        "skipped": skipped,
    }
    task = upload_service.create_task(
        "day",
        task_payload,
        created_by=session.get("username", "unknown"),
    )
    return task["id"]


@router.get("/template")
async def download_template(session: AuthUser):
    buf = generate_excel_template()
    headers = {"Content-Disposition": 'attachment; filename="fjcpc_report_template.xlsx"'}
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)


@router.post("/excel-parse")
async def parse_excel(session: AuthUser, file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        payload = api_error_payload(ErrorCode.PARAM_INVALID, "请上传 .xlsx / .xlsm 文件")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=payload)
    raw = await file.read()
    try:
        parsed = parse_excel_file(raw)
    except ValueError as exc:
        payload = api_error_payload(ErrorCode.PARAM_INVALID, str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=payload) from exc
    except Exception as exc:
        logger.exception("解析 Excel 失败")
        payload = api_error_payload(ErrorCode.SYSTEM_INTERNAL, "解析 Excel 失败", detail=str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=payload) from exc

    serializable = {}
    for key, val in parsed.items():
        if key.endswith("_skipped"):
            serializable[key] = val
            continue
        if isinstance(val, list):
            serializable[key] = []
            for row in val:
                if isinstance(row, dict):
                    row_copy = dict(row)
                    date_val = row_copy.get("date")
                    if hasattr(date_val, "strftime"):
                        row_copy["date"] = date_val.strftime("%Y-%m-%d")
                    serializable[key].append(row_copy)
        else:
            serializable[key] = val

    return ApiSuccess(data={"parsed": serializable}).model_dump()


@router.post("/excel-submit")
async def submit_excel(
    session: AuthUser,
    background_tasks: BackgroundTasks,
    upload_service: UploadService = Depends(get_upload_service),
    file: UploadFile = File(...),
    student_id: str = Form(...),
    fjcpc_token: str = Form(...),
):
    """解析 Excel 并创建异步上传任务（等价于旧版 /api/upload/excel 上传文件）。"""
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm", ".xls")):
        payload = api_error_payload(ErrorCode.PARAM_INVALID, "请上传 Excel 文件")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=payload)

    raw = await file.read()
    try:
        parsed = parse_excel_file(raw)
    except ValueError as exc:
        payload = api_error_payload(ErrorCode.PARAM_INVALID, str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=payload) from exc
    except Exception as exc:
        logger.exception("解析 Excel 失败")
        payload = api_error_payload(ErrorCode.SYSTEM_INTERNAL, "解析 Excel 失败", detail=str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=payload) from exc

    all_errors, normalized_payload, skipped = normalize_excel_parsed(parsed)
    if all_errors:
        payload = api_error_payload(
            ErrorCode.PARAM_INVALID,
            f"文件检验失败：{'；'.join(all_errors)}。请修正后再上传。",
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=payload)

    if not any(normalized_payload.values()):
        payload = api_error_payload(ErrorCode.PARAM_INVALID, "Excel 中无有效待上传记录")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=payload)

    task_id = _enqueue_excel_batch(upload_service, session, student_id, fjcpc_token, normalized_payload, skipped)
    background_tasks.add_task(upload_service.execute_task, task_id)
    logger.info("已创建 Excel 批量上传任务 task_id=%s user=%s", task_id, session.get("username"))

    return ApiSuccess(
        data={
            "task_id": task_id,
            "message": "任务已创建并排队执行，请在任务中心查看进度与结果",
        }
    ).model_dump()


@router.post("/excel-submit-json")
async def submit_excel_json(
    session: AuthUser,
    background_tasks: BackgroundTasks,
    body: ExcelCachedSubmitBody,
    upload_service: UploadService = Depends(get_upload_service),
):
    """旧版 JSON 提交（application/json + cached_data.full_data，等价跳过文件解析）。"""
    fd = body.cached_data.get("full_data") if isinstance(body.cached_data, dict) else None
    if not isinstance(fd, dict):
        payload = api_error_payload(ErrorCode.PARAM_INVALID, "cached_data.full_data 格式不正确")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=payload)

    parsed = full_data_to_parsed_like_excel(fd)
    all_errors, normalized_payload, skipped = normalize_excel_parsed(parsed)
    if all_errors:
        payload = api_error_payload(
            ErrorCode.PARAM_INVALID,
            f"文件检验失败：{'；'.join(all_errors)}。请修正后再上传。",
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=payload)

    if not any(normalized_payload.values()):
        payload = api_error_payload(ErrorCode.PARAM_INVALID, "无有效待上传记录")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=payload)

    task_id = _enqueue_excel_batch(
        upload_service,
        session,
        body.student_id,
        body.token,
        normalized_payload,
        skipped,
    )
    background_tasks.add_task(upload_service.execute_task, task_id)
    logger.info("已创建 Excel(JSON) 批量任务 task_id=%s", task_id)

    return ApiSuccess(
        data={
            "task_id": task_id,
            "message": "任务已创建并排队执行",
        }
    ).model_dump()
