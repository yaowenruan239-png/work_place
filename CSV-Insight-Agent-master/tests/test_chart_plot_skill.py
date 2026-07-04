from pathlib import Path

import pandas as pd

from src.skills.chart_plot import PlotChartSkill


def make_csv(tmp_path):
    csv_path = tmp_path / "sample.csv"
    pd.DataFrame(
        {
            "month": [1, 2, 3, 4],
            "sales": [10, 20, 15, 25],
            "profit": [2, 5, 3, 8],
            "region": ["A", "B", "A", "B"],
        }
    ).to_csv(csv_path, index=False)
    return csv_path


def assert_png(result):
    assert result["success"] is True
    assert Path(result["path"]).exists()
    assert result["path"].endswith(".png")


def test_plot_line_chart_creates_png(tmp_path):
    result = PlotChartSkill(output_dir=tmp_path).run(
        csv_path=str(make_csv(tmp_path)), run_id="r1", chart_type="line", x_col="month", y_col="sales", title="销售趋势"
    )
    assert_png(result)


def test_plot_bar_chart_creates_png(tmp_path):
    result = PlotChartSkill(output_dir=tmp_path).run(
        csv_path=str(make_csv(tmp_path)), run_id="r1", chart_type="bar", x_col="region", y_col="sales"
    )
    assert_png(result)


def test_plot_scatter_chart_creates_png(tmp_path):
    result = PlotChartSkill(output_dir=tmp_path).run(
        csv_path=str(make_csv(tmp_path)), run_id="r1", chart_type="scatter", x_col="sales", y_col="profit"
    )
    assert_png(result)


def test_plot_histogram_creates_png(tmp_path):
    result = PlotChartSkill(output_dir=tmp_path).run(
        csv_path=str(make_csv(tmp_path)), run_id="r1", chart_type="histogram", x_col="sales"
    )
    assert_png(result)


def test_plot_box_creates_png(tmp_path):
    result = PlotChartSkill(output_dir=tmp_path).run(
        csv_path=str(make_csv(tmp_path)), run_id="r1", chart_type="box", x_col="region", y_col="sales"
    )
    assert_png(result)


def test_correlation_heatmap_creates_png(tmp_path):
    result = PlotChartSkill(output_dir=tmp_path).run(csv_path=str(make_csv(tmp_path)), run_id="r1", chart_type="correlation_heatmap")
    assert_png(result)


def test_unknown_column_returns_structured_error(tmp_path):
    result = PlotChartSkill(output_dir=tmp_path).run(
        csv_path=str(make_csv(tmp_path)), run_id="r1", chart_type="line", x_col="missing", y_col="sales"
    )

    assert result["success"] is False
    assert "suggestion" in result


def test_invalid_chart_type_returns_suggestions(tmp_path):
    result = PlotChartSkill(output_dir=tmp_path).run(csv_path=str(make_csv(tmp_path)), run_id="r1", chart_type="pie")

    assert result["success"] is False
    assert "suggestion" in result
