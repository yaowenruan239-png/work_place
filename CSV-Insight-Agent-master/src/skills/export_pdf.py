from __future__ import annotations

from pathlib import Path
from typing import Any

from src.reporting.content_builder import ReportContentBuilder
from src.reporting.html_renderer import ReportHTMLRenderer
from src.skills.base import BaseSkill
from src.utils.report_utils import markdown_to_html, write_text


class ExportPDFSkill(BaseSkill):
    name = "export_pdf"
    description = "保存 Markdown 报告并导出 PDF；PDF 失败时导出 HTML。"
    args_schema = {
        "type": "object",
        "properties": {"run_id": {"type": "string"}, "markdown": {"type": "string"}},
        "required": ["run_id", "markdown"],
    }

    def __init__(self, report_dir: str | Path = "outputs/reports", html_dir: str | Path = "outputs/html"):
        self.report_dir = Path(report_dir)
        self.html_dir = Path(html_dir)

    def run(self, **kwargs: Any) -> dict[str, Any]:
        run_id = kwargs["run_id"]
        markdown = kwargs["markdown"]
        report_path = Path(write_text(self.report_dir / f"{run_id}.md", markdown))
        html = self._build_html(markdown=markdown, kwargs=kwargs)
        html_path = Path(write_text(self.html_dir / f"{run_id}.html", html))
        pdf_path = self.report_dir / f"{run_id}.pdf"
        try:
            from weasyprint import HTML

            HTML(string=html, base_url=str(Path.cwd())).write_pdf(str(pdf_path))
            return {
                "success": True,
                "report_path": str(report_path),
                "pdf_path": str(pdf_path),
                "html_path": str(html_path),
                "error": None,
            }
        except Exception as exc:
            return {
                "success": True,
                "report_path": str(report_path),
                "pdf_path": None,
                "html_path": str(html_path),
                "error": f"PDF 导出失败，已生成 HTML: {exc}",
            }

    def _build_html(self, markdown: str, kwargs: dict[str, Any]) -> str:
        if kwargs.get("profile") or kwargs.get("charts") or kwargs.get("insights"):
            document = ReportContentBuilder().build(
                profile=kwargs.get("profile"),
                charts=kwargs.get("charts"),
                insights=kwargs.get("insights"),
                query=kwargs.get("query"),
            )
            return ReportHTMLRenderer(base_dir=Path.cwd()).render(document)
        return markdown_to_html(markdown)
