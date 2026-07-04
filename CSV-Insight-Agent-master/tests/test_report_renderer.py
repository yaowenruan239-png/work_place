from src.reporting.content_builder import ReportContentBuilder
from src.reporting.html_renderer import ReportHTMLRenderer
from src.reporting.models import ChartNarrative, ReportDocument


def sample_profile():
    return {
        "rows": 36,
        "columns": 6,
        "column_names": ["月份", "销售额", "利润"],
        "numeric_columns": ["销售额", "利润"],
        "categorical_columns": ["月份"],
    }


def test_report_renderer_contains_consulting_sections(tmp_path):
    chart_path = tmp_path / "chart.png"
    chart_path.write_bytes(b"png")
    document = ReportContentBuilder().build(
        profile=sample_profile(),
        charts=[{"title": "销售趋势", "path": str(chart_path), "chart_type": "bar"}],
        insights=["销售额整体稳定增长。"],
        query="生成销售分析报告",
    )

    html = ReportHTMLRenderer(base_dir=tmp_path).render(document)

    assert "执行摘要" in html
    assert "关键指标" in html
    assert "核心发现" in html
    assert "图文分析" in html
    assert "行动建议" in html
    assert "局限性说明" in html
    assert "附录" in html


def test_report_renderer_embeds_chart_images(tmp_path):
    chart_path = tmp_path / "chart.png"
    chart_path.write_bytes(b"png")
    document = ReportDocument(
        title="CSV 数据分析报告",
        subtitle="咨询报告",
        query="分析销售",
        summary="本报告分析销售数据。",
        metrics=[],
        findings=[],
        chart_narratives=[
            ChartNarrative(
                title="销售趋势",
                image_path=str(chart_path),
                chart_type="bar",
                why_it_matters="用于观察趋势。",
                observation="销售额上升。",
                recommendation="继续关注高峰月份。",
            )
        ],
        recommendations=["关注高峰月份。"],
        limitations=["仅基于上传 CSV。"],
        appendix={"字段": "月份, 销售额, 利润"},
    )

    html = ReportHTMLRenderer(base_dir=tmp_path).render(document)

    assert "销售趋势" in html
    assert "file:///" in html
    assert "chart.png" in html


def test_report_renderer_normalizes_windows_image_paths(tmp_path):
    chart_dir = tmp_path / "outputs" / "charts"
    chart_dir.mkdir(parents=True)
    chart_path = chart_dir / "chart.png"
    chart_path.write_bytes(b"png")
    windows_path = str(chart_path).replace("/", "\\")
    document = ReportContentBuilder().build(
        profile=sample_profile(),
        charts=[{"title": "销售趋势", "path": windows_path, "chart_type": "bar"}],
        insights=["销售额整体稳定增长。"],
        query="生成销售分析报告",
    )

    html = ReportHTMLRenderer(base_dir=tmp_path).render(document)

    assert "file:///" in html
    assert "\\" not in html.split("chart.png")[0].split("src=")[-1]


def test_report_renderer_handles_missing_chart_image(tmp_path):
    document = ReportContentBuilder().build(
        profile=sample_profile(),
        charts=[{"title": "缺失图表", "path": str(tmp_path / "missing.png"), "chart_type": "bar"}],
        insights=["图表文件不存在。"],
        query="生成销售分析报告",
    )

    html = ReportHTMLRenderer(base_dir=tmp_path).render(document)

    assert "图表文件不可用" in html
    assert "missing.png" in html
