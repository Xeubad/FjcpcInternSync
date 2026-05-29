"""旧版路径与兼容 API 测试。"""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_legacy_bookmark_html_redirects():
    """旧书签 *.html 跳转到对应 React 路由。"""
    with TestClient(app, follow_redirects=False) as client:
        pairs = [
            ("/login.html", "/login"),
            ("/select.html", "/app/dashboard"),
            ("/txt_upload.html", "/app/text-upload"),
            ("/excel_upload.html", "/app/tasks"),
            ("/admin_panel.html", "/app/admin/tokens"),
        ]
        for src, dst in pairs:
            response = client.get(src)
            assert response.status_code == 302
            assert response.headers.get("location") == dst


def test_legacy_api_excel_template_get():
    with TestClient(app) as client:
        response = client.get("/api/excel/template")
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers.get("content-type", "")
        disposition = response.headers.get("content-disposition", "")
        assert "filename=" in disposition
        assert "fjcpc_report_template.xlsx" in disposition or "filename*=" in disposition


def test_legacy_upload_excel_requires_bearer():
    with TestClient(app) as client:
        response = client.post(
            "/api/upload/excel",
            json={
                "student_id": "1",
                "token": "t",
                "cached_data": {"full_data": {"day": [], "week": [], "month": []}},
            },
        )
        assert response.status_code == 401


def test_legacy_upload_excel_json_dry_run(monkeypatch):
    monkeypatch.setattr(settings, "fjcpc_dry_run", True)
    with TestClient(app) as client:
        login = client.post(
            "/api/auth/login",
            json={"username": settings.admin_username, "password": settings.admin_password},
        )
        assert login.status_code == 200
        bearer = login.json()["data"]["token"]
        body = {
            "student_id": "2026001",
            "token": "platform-token",
            "cached_data": {
                "full_data": {
                    "day": [
                        {
                            "date": "2026-05-01",
                            "work": "w" * 200,
                            "achievement": "a" * 200,
                            "problem": "p" * 200,
                            "word_count": 600,
                        }
                    ],
                    "week": [],
                    "month": [],
                }
            },
        }
        response = client.post(
            "/api/upload/excel",
            json=body,
            headers={"Authorization": f"Bearer {bearer}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total"] == 1
        assert data["success_count"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["message"] == "DRY_RUN（未请求上游）"
