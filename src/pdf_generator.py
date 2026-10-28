import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright

from config.settings import settings

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Renders HTML resume files into print-optimized PDF documents."""

    def __init__(
        self,
        paper_size: str | None = None,
        margin_top: str | None = None,
        margin_bottom: str | None = None,
        margin_left: str | None = None,
        margin_right: str | None = None,
    ):
        self.paper_size = paper_size or settings.pdf_paper_size
        self.margin_top = margin_top or settings.pdf_margin_top
        self.margin_bottom = margin_bottom or settings.pdf_margin_bottom
        self.margin_left = margin_left or settings.pdf_margin_left
        self.margin_right = margin_right or settings.pdf_margin_right

    def _render_sync(self, html_file: Path, out_file: Path):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                # Open HTML file as local URL
                page.goto(html_file.as_uri(), wait_until="load")
                page.emulate_media(media="print")

                # Print to PDF using configured margins and A4 paper size
                page.pdf(
                    path=str(out_file),
                    format=self.paper_size,
                    prefer_css_page_size=True,
                    print_background=True,
                    margin={
                        "top": self.margin_top,
                        "bottom": self.margin_bottom,
                        "left": self.margin_left,
                        "right": self.margin_right,
                    },
                )
            finally:
                browser.close()

    def generate_pdf(
        self,
        html_path: str | Path,
        pdf_path: str | Path | None = None,
    ) -> Path:
        """Render HTML resume file to PDF using Playwright headless Chromium."""
        html_file = Path(html_path).resolve()
        if not html_file.exists():
            raise FileNotFoundError(f"HTML resume not found: {html_file}")

        if pdf_path is None:
            pdf_path = html_file.with_suffix(".pdf")
        out_file = Path(pdf_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # Check if an asyncio event loop is currently active in this thread
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self._render_sync, html_file, out_file)
                future.result()
        else:
            self._render_sync(html_file, out_file)

        logger.info("Generated PDF resume at: %s", out_file)
        return out_file
