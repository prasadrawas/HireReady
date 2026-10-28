"""HTML resume generator using Jinja2."""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config.settings import settings
from src.models.resume import ResumeData
from src.models.tailored import TailoredResume


class HTMLGenerator:
    """Renders TailoredResume or ResumeData into semantic ATS-friendly HTML."""

    def __init__(self, templates_dir: Path | str | None = None):
        self.templates_dir = Path(templates_dir) if templates_dir else settings.templates_dir
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(
        self,
        resume: TailoredResume | ResumeData,
        target_role: str = "Software Engineer",
        output_path: Path | str | None = None,
    ) -> str:
        """Render resume model to ATS-compatible HTML5 string and optionally save to file."""
        template = self.env.get_template("resume.html.j2")
        rendered_html = template.render(
            contact=resume.contact,
            summary=resume.summary,
            skills=resume.skills,
            experience=resume.experience,
            projects=resume.projects,
            education=resume.education,
            certifications=resume.certifications,
            target_role=target_role,
        )

        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(rendered_html, encoding="utf-8")

        return rendered_html
