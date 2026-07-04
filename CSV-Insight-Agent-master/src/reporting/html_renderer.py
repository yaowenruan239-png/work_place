from __future__ import annotations

from html import escape
from pathlib import Path

from src.reporting.models import ReportDocument


class ReportHTMLRenderer:
    def __init__(self, base_dir: str | Path | None = None):
        self.base_dir = Path(base_dir or Path.cwd()).resolve()

    def render(self, document: ReportDocument) -> str:
        metrics = "".join(
            f"<div class='metric-card'><div class='metric-value'>{escape(metric.value)}</div><div class='metric-label'>{escape(metric.label)}</div><p>{escape(metric.description)}</p></div>"
            for metric in document.metrics
        )
        findings = "".join(
            f"<div class='finding'><strong>{escape(finding.title)}</strong><p>{escape(finding.detail)}</p></div>"
            for finding in document.findings
        )
        charts = "".join(self._render_chart(chart) for chart in document.chart_narratives)
        recommendations = "".join(f"<li>{escape(item)}</li>" for item in document.recommendations)
        limitations = "".join(f"<li>{escape(item)}</li>" for item in document.limitations)
        appendix = "".join(
            f"<tr><th>{escape(str(key))}</th><td>{escape(str(value))}</td></tr>"
            for key, value in document.appendix.items()
        )
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{escape(document.title)}</title>
<style>{self._css()}</style>
</head>
<body>
<section class="cover">
  <div class="eyebrow">CSV Insight Agent</div>
  <h1>{escape(document.title)}</h1>
  <p class="subtitle">{escape(document.subtitle)}</p>
  <div class="query">分析目标：{escape(document.query)}</div>
</section>
<section>
  <h2>执行摘要</h2>
  <p class="lead">{escape(document.summary)}</p>
</section>
<section>
  <h2>关键指标</h2>
  <div class="metric-grid">{metrics}</div>
</section>
<section>
  <h2>核心发现</h2>
  {findings}
</section>
<section>
  <h2>图文分析</h2>
  {charts or '<p class="missing">本次没有可嵌入的图表。</p>'}
</section>
<section>
  <h2>行动建议</h2>
  <ul>{recommendations}</ul>
</section>
<section>
  <h2>局限性说明</h2>
  <ul>{limitations}</ul>
</section>
<section>
  <h2>附录：字段概览</h2>
  <table>{appendix}</table>
</section>
</body>
</html>"""

    def _render_chart(self, chart) -> str:
        image_html = self._image_html(chart.image_path)
        return f"""<article class="chart-card">
<h3>{escape(chart.title)}</h3>
<p><strong>为什么看这张图：</strong>{escape(chart.why_it_matters)}</p>
{image_html}
<p><strong>观察：</strong>{escape(chart.observation)}</p>
<p><strong>建议：</strong>{escape(chart.recommendation)}</p>
</article>"""

    def _image_html(self, image_path: str | None) -> str:
        if not image_path:
            return "<div class='missing'>图表文件不可用：未提供路径</div>"
        path = Path(str(image_path).replace("\\", "/"))
        if not path.is_absolute():
            path = (self.base_dir / path).resolve()
        if not path.exists():
            return f"<div class='missing'>图表文件不可用：{escape(path.name)}</div>"
        return f"<img src=\"{path.as_uri()}\" alt=\"{escape(path.name)}\" />"

    def _css(self) -> str:
        return """
@page { size: A4; margin: 18mm; }
body { font-family: 'Microsoft YaHei', 'Noto Sans CJK SC', Arial, sans-serif; color: #172033; line-height: 1.65; }
.cover { min-height: 760px; display: flex; flex-direction: column; justify-content: center; background: linear-gradient(135deg, #102a43, #2f80ed); color: white; padding: 56px; border-radius: 24px; page-break-after: always; }
.eyebrow { letter-spacing: 0.18em; text-transform: uppercase; opacity: 0.8; }
h1 { font-size: 42px; margin: 18px 0; }
h2 { font-size: 24px; border-left: 6px solid #2f80ed; padding-left: 12px; margin-top: 30px; }
h3 { font-size: 19px; color: #102a43; }
.subtitle, .lead { font-size: 18px; }
.query { margin-top: 28px; padding: 14px 18px; background: rgba(255,255,255,0.14); border-radius: 12px; }
.metric-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
.metric-card, .finding, .chart-card { border: 1px solid #d9e2ec; border-radius: 16px; padding: 18px; margin: 14px 0; background: #ffffff; box-shadow: 0 6px 18px rgba(16,42,67,0.08); }
.metric-value { color: #2f80ed; font-size: 30px; font-weight: 700; }
.metric-label { font-weight: 700; margin-top: 4px; }
.chart-card { page-break-inside: avoid; }
.chart-card img { display: block; max-width: 100%; margin: 14px auto; border: 1px solid #e6edf5; border-radius: 12px; }
.missing { padding: 16px; background: #fff4e5; color: #8a4b00; border-radius: 10px; border: 1px solid #ffd599; }
table { width: 100%; border-collapse: collapse; }
th, td { border: 1px solid #d9e2ec; padding: 10px; text-align: left; }
th { width: 120px; background: #f5f7fb; }
"""
