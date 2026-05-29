"""纯文本实习报告解析（自 app_excel.parse_report_content 迁移）。"""


def parse_report_content(content: str) -> list[dict]:
    """每 3 行为一组：工作 / 收获 / 问题。"""
    lines = [line.strip() for line in content.split("\n") if line.strip()]

    if len(lines) < 3:
        return []

    reports: list[dict] = []
    for i in range(0, len(lines), 3):
        if i + 2 < len(lines):
            reports.append(
                {
                    "work": lines[i],
                    "achievement": lines[i + 1],
                    "problem": lines[i + 2],
                }
            )

    return reports
