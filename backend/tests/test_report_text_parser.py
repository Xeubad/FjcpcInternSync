from app.domain.report_text_parser import parse_report_content


def test_parse_report_content_groups():
    text = "工作A\n收获B\n问题C\n工作2\n收获2\n问题2"
    rows = parse_report_content(text)
    assert len(rows) == 2
    assert rows[0]["work"] == "工作A"
