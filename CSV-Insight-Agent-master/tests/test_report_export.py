from pathlib import Path

from src.skills.export_pdf import ExportPDFSkill


def test_export_markdown_creates_report_and_export_file(tmp_path):
    skill = ExportPDFSkill(report_dir=tmp_path / "reports", html_dir=tmp_path / "html")

    result = skill.run(run_id="r1", markdown="# 测试报告\n\n内容")

    assert result["success"] is True
    assert Path(result["report_path"]).exists()
    assert Path(result["html_path"]).exists()
    assert result["pdf_path"] is None or Path(result["pdf_path"]).exists()


def test_export_pdf_saves_structured_html_with_charts(tmp_path):
    chart_path = tmp_path / "chart.png"
    chart_path.write_bytes(b"png")
    skill = ExportPDFSkill(report_dir=tmp_path / "reports", html_dir=tmp_path / "html")

    result = skill.run(
        run_id="r2",
        markdown="# 结构化报告",
        profile={"rows": 10, "columns": 3, "column_names": ["月份", "销售额"], "numeric_columns": ["销售额"]},
        charts=[{"title": "销售趋势", "path": str(chart_path), "chart_type": "bar"}],
        insights=["销售额呈上升趋势。"],
        query="分析销售趋势",
    )

    html = Path(result["html_path"]).read_text(encoding="utf-8")
    assert "执行摘要" in html
    assert "关键指标" in html
    assert "图文分析" in html
    assert "销售趋势" in html
    assert "file:///" in html


def test_export_pdf_falls_back_to_html_when_pdf_backend_fails(tmp_path, monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "weasyprint":
            raise RuntimeError("missing pdf backend")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    skill = ExportPDFSkill(report_dir=tmp_path / "reports", html_dir=tmp_path / "html")

    result = skill.run(run_id="r3", markdown="# 测试报告")

    assert result["success"] is True
    assert result["pdf_path"] is None
    assert Path(result["html_path"]).exists()
    assert "missing pdf backend" in result["error"]
