from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT_DIR / "outputs"
UPLOAD_DIR = OUTPUT_DIR / "uploads"
CHART_DIR = OUTPUT_DIR / "charts"
REPORT_DIR = OUTPUT_DIR / "reports"
HTML_DIR = OUTPUT_DIR / "html"
MEMORY_DIR = ROOT_DIR / "memory"


def ensure_runtime_dirs() -> None:
    for path in [UPLOAD_DIR, CHART_DIR, REPORT_DIR, HTML_DIR, MEMORY_DIR]:
        path.mkdir(parents=True, exist_ok=True)
