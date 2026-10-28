"""Resume parser module for extracting ResumeData from master HTML resume."""

import re
from pathlib import Path
from bs4 import BeautifulSoup, Tag
import yaml

from config.settings import settings
from src.models.preferences import SearchPreferences
from src.models.resume import (
    BulletPoint,
    ContactInfo,
    Education,
    Experience,
    Project,
    ResumeData,
    SkillGroup,
)


class ResumeParserError(Exception):
    """Exception raised when parsing resume HTML fails."""


class ResumeParser:
    """Parses master HTML resume into structured ResumeData."""

    def __init__(self, html_path: str | Path | None = None):
        self.html_path = Path(html_path) if html_path else settings.master_resume_path

    def parse(self, html_content: str | None = None) -> ResumeData:
        """Parse resume HTML into ResumeData with deterministic bullet IDs."""
        if html_content is None:
            if not self.html_path.exists():
                raise ResumeParserError(f"Master resume not found at: {self.html_path}")
            html_content = self.html_path.read_text(encoding="utf-8")

        soup = BeautifulSoup(html_content, "html.parser")

        contact = self._extract_contact(soup)
        summary = self._extract_summary(soup)
        skills = self._extract_skills(soup)
        experience = self._extract_experience(soup)
        projects = self._extract_projects(soup)
        education = self._extract_education(soup)
        certifications = self._extract_certifications(soup)

        return ResumeData(
            contact=contact,
            summary=summary,
            skills=skills,
            experience=experience,
            projects=projects,
            education=education,
            certifications=certifications,
        )

    def _extract_contact(self, soup: BeautifulSoup) -> ContactInfo:
        """Extract contact information from header or contact section."""
        name = ""
        email = ""
        phone = ""
        linkedin = None
        github = None
        website = None
        location = None

        # Look for name in h1
        name_el = soup.find(class_=re.compile(r"r-name|name")) or soup.find("h1")
        if name_el:
            name = name_el.get_text(strip=True)
        elif soup.title:
            # Fallback to title tag if like "Name - ..."
            title_text = soup.title.get_text(strip=True)
            name = title_text.split("-")[0].split("—")[0].strip()

        # Search for links and text in header or whole doc
        contact_container = (
            soup.find("header")
            or soup.find(id="contact")
            or soup.find(class_=re.compile(r"r-contact|contact-info|header"))
            or soup
        )

        # Links extraction
        for a in contact_container.find_all("a", href=True):
            href = a["href"].strip()
            text = a.get_text(strip=True)
            if href.startswith("mailto:"):
                email = href.replace("mailto:", "").split("?")[0].strip()
            elif href.startswith("tel:"):
                phone = href.replace("tel:", "").strip()
            elif "linkedin.com" in href:
                linkedin = href
            elif "github.com" in href:
                github = href
            elif not website and href.startswith("http") and not any(x in href for x in ["linkedin", "github"]):
                website = href

        # Email & Phone regex fallback if not found in links
        container_text = contact_container.get_text(" ", strip=True)
        if not email:
            email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", container_text)
            if email_match:
                email = email_match.group(0)

        if not phone:
            phone_match = re.search(r"(\+?\(?\d[\d\s\-\(\)]{7,}\d)", container_text)
            if phone_match:
                candidate = phone_match.group(1).strip()
                # filter out simple years or short numbers
                if len(re.sub(r"\D", "", candidate)) >= 9:
                    phone = candidate

        if not linkedin:
            li_match = re.search(r"((?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-]+)", container_text)
            if li_match:
                linkedin = li_match.group(1)

        if not github:
            gh_match = re.search(r"((?:https?://)?(?:www\.)?github\.com/[\w\-]+)", container_text)
            if gh_match:
                github = gh_match.group(1)

        # Location extraction
        loc_el = contact_container.find(class_=re.compile(r"location|r-contact-item"))
        if loc_el:
            # Check items for location text (non-link item or containing common location patterns)
            for item in contact_container.find_all(class_=re.compile(r"r-contact-item|location")):
                if not item.find("a"):
                    text = item.get_text(strip=True)
                    if text and not re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text):
                        location = text
                        break

        # Fallback location from text if still none
        if not location:
            loc_candidates = re.findall(r"([A-Z][a-zA-Z\s\.]+(?:,\s*[A-Z][a-zA-Z\s\.]+)+)", container_text)
            for cand in loc_candidates:
                cand_clean = cand.strip()
                if not any(k in cand_clean.lower() for k in ["university", "institute", "technologies", "innovations", "developer", "engineer"]):
                    location = cand_clean
                    break

        return ContactInfo(
            name=name or "Candidate",
            email=email or "candidate@example.com",
            phone=phone or "N/A",
            linkedin=linkedin,
            github=github,
            website=website,
            location=location,
        )

    def _find_section(self, soup: BeautifulSoup, keywords: list[str]) -> Tag | None:
        """Find a section by ID or heading text."""
        # 1. By ID attribute
        for kw in keywords:
            sec = soup.find("section", id=re.compile(rf"^{kw}", re.I))
            if sec:
                return sec

        # 2. By class attribute
        for kw in keywords:
            sec = soup.find(class_=re.compile(rf"r-{kw}|{kw}-section", re.I))
            if sec:
                return sec

        # 3. By heading text
        for heading in soup.find_all(["h2", "h3"]):
            text = heading.get_text(strip=True).lower()
            if any(kw in text for kw in keywords):
                parent = heading.find_parent(["section", "div"])
                return parent or heading

        return None

    def _extract_summary(self, soup: BeautifulSoup) -> str:
        """Extract professional summary."""
        sec = self._find_section(soup, ["summary", "profile", "about"])
        if sec:
            p = sec.find("p") or sec.find(class_=re.compile(r"r-summary|summary"))
            if p:
                return p.get_text(" ", strip=True)
            # Otherwise get all text after heading
            text_lines = [
                t.strip() for t in sec.stripped_strings
                if not any(h in t.lower() for h in ["summary", "profile"])
            ]
            return " ".join(text_lines)
        return ""

    def _extract_skills(self, soup: BeautifulSoup) -> list[SkillGroup]:
        """Extract skill groups and categories."""
        sec = self._find_section(soup, ["skills", "technical-skills", "competencies"])
        if not sec:
            return []

        skill_groups: list[SkillGroup] = []

        # Check for skill rows like <div class="r-skill-row"><span class="r-skill-cat">...</span>...</div>
        rows = sec.find_all(class_=re.compile(r"r-skill-row|skill-group|skill-row"))
        if rows:
            for row in rows:
                cat_el = row.find(class_=re.compile(r"r-skill-cat|category")) or row.find(["strong", "b"])
                cat_text = cat_el.get_text(strip=True).rstrip(":") if cat_el else "General"
                
                list_el = row.find(class_=re.compile(r"r-skill-list|skills"))
                if list_el:
                    raw_skills = list_el.get_text(strip=True)
                else:
                    # Strip out category text
                    raw_skills = row.get_text(strip=True)
                    if cat_el:
                        raw_skills = raw_skills.replace(cat_el.get_text(strip=True), "")
                
                skills = [s.strip() for s in re.split(r"[,;•|]", raw_skills) if s.strip()]
                if skills:
                    skill_groups.append(SkillGroup(category=cat_text, skills=skills))
            return skill_groups

        # Fallback to definition lists or div blocks
        for div in sec.find_all("div"):
            strong = div.find(["strong", "b"])
            if strong:
                cat = strong.get_text(strip=True).rstrip(":")
                rest = div.get_text(" ", strip=True).replace(strong.get_text(strip=True), "")
                skills = [s.strip() for s in re.split(r"[,;•|]", rest) if s.strip()]
                if skills:
                    skill_groups.append(SkillGroup(category=cat, skills=skills))

        return skill_groups

    def _extract_experience(self, soup: BeautifulSoup) -> list[Experience]:
        """Extract work experience entries with deterministic bullet IDs."""
        sec = self._find_section(soup, ["experience", "employment", "work"])
        if not sec:
            return []

        experiences: list[Experience] = []
        job_classes = {"r-job", "job", "experience-item"}
        job_elements = [
            el for el in sec.find_all(class_=True)
            if any(cls in job_classes for cls in el.get("class", []))
        ]
        if not job_elements:
            # Try finding divs that contain an h3 or h4
            job_elements = [
                h.parent for h in sec.find_all(["h3", "h4"])
                if h.parent and h.parent.name in ["div", "section"]
            ]

        for job_idx, job in enumerate(job_elements, start=1):
            title = ""
            company = ""
            location = None
            dates = ""

            role_el = job.find(class_=lambda c: c and any(x in ["r-job-role", "role", "title"] for x in c.split())) or job.find(["h3", "h4"])
            if role_el:
                title = role_el.get_text(strip=True)

            date_el = job.find(class_=lambda c: c and any(x in ["r-job-date", "dates", "period"] for x in c.split()))
            if date_el:
                dates = date_el.get_text(strip=True)

            company_el = job.find(class_=lambda c: c and any(x in ["r-job-company", "company"] for x in c.split()))
            if company_el:
                comp_text = company_el.get_text(strip=True)
                # Split company and location if separated by • or | or -
                parts = [p.strip() for p in re.split(r"[•|]", comp_text) if p.strip()]
                if len(parts) >= 2:
                    company = parts[0]
                    location = parts[1]
                else:
                    company = comp_text

            # Parse start and end date from dates string (e.g. "Nov 2023 - Present")
            start_date = dates
            end_date = None
            if "-" in dates or "–" in dates:
                split_dates = re.split(r"[-–]", dates, maxsplit=1)
                start_date = split_dates[0].strip()
                end_date = split_dates[1].strip()

            bullets: list[BulletPoint] = []
            ul = job.find("ul")
            if ul:
                for b_idx, li in enumerate(ul.find_all("li"), start=1):
                    b_id = f"bullet_exp_{job_idx:02d}_{b_idx:02d}"
                    text = li.get_text(" ", strip=True)
                    bullets.append(BulletPoint(id=b_id, text=text, source_id=b_id))

            if title or company:
                experiences.append(
                    Experience(
                        company=company or "Company",
                        title=title or "Role",
                        location=location,
                        start_date=start_date or "N/A",
                        end_date=end_date,
                        bullets=bullets,
                    )
                )

        return experiences

    def _extract_projects(self, soup: BeautifulSoup) -> list[Project]:
        """Extract projects with deterministic bullet IDs."""
        sec = self._find_section(soup, ["projects", "key-projects", "portfolio"])
        if not sec:
            return []

        projects: list[Project] = []
        proj_classes = {"r-project", "project", "project-card"}
        project_elements = [
            el for el in sec.find_all(class_=True)
            if any(cls in proj_classes for cls in el.get("class", []))
        ]
        if not project_elements:
            project_elements = [
                h.parent for h in sec.find_all(["h3", "h4"])
                if h.parent and h.parent.name in ["div", "section"]
            ]

        for proj_idx, proj in enumerate(project_elements, start=1):
            name = ""
            url = None
            technologies: list[str] = []

            name_el = proj.find(class_=lambda c: c and any(x in ["r-project-name", "name"] for x in c.split())) or proj.find(["h3", "h4", "strong"])
            if name_el:
                name = name_el.get_text(strip=True)

            a_tag = proj.find("a", href=True)
            if a_tag:
                url = a_tag["href"].strip()
                if not name:
                    name = a_tag.get_text(strip=True)

            tech_el = proj.find(class_=lambda c: c and any(x in ["r-project-tech", "technologies", "tags"] for x in c.split()))
            if tech_el:
                tech_text = tech_el.get_text(strip=True)
                technologies = [t.strip() for t in re.split(r"[•,|/]", tech_text) if t.strip()]

            # Extract bullets or text
            bullets: list[BulletPoint] = []
            ul = proj.find("ul")
            if ul:
                for b_idx, li in enumerate(ul.find_all("li"), start=1):
                    b_id = f"bullet_proj_{proj_idx:02d}_{b_idx:02d}"
                    bullets.append(BulletPoint(id=b_id, text=li.get_text(" ", strip=True), source_id=b_id))

            full_desc = proj.get_text(" ", strip=True)
            if not bullets:
                # Use project text as single bullet
                b_id = f"bullet_proj_{proj_idx:02d}_01"
                # Remove name and tech from desc for cleaner text
                clean_text = full_desc
                if name:
                    clean_text = clean_text.replace(name, "")
                if tech_el:
                    clean_text = clean_text.replace(tech_el.get_text(strip=True), "")
                clean_text = re.sub(r"^[/–\-\s]+", "", clean_text).strip()
                bullets.append(BulletPoint(id=b_id, text=clean_text or full_desc, source_id=b_id))

            projects.append(
                Project(
                    name=name or f"Project {proj_idx}",
                    url=url,
                    description=full_desc,
                    bullets=bullets,
                    technologies=technologies,
                )
            )

        return projects

    def _extract_education(self, soup: BeautifulSoup) -> list[Education]:
        """Extract education entries."""
        sec = self._find_section(soup, ["education", "academic"])
        if not sec:
            return []

        education_list: list[Education] = []
        edu_classes = {"degree", "education-item", "edu-item"}
        entry_elements = [
            el for el in sec.find_all(class_=True)
            if any(cls in edu_classes for cls in el.get("class", []))
        ]

        if entry_elements:
            for item in entry_elements:
                deg_el = item.find(class_=lambda c: c and any(x in ["r-edu-degree", "degree"] for x in c.split())) or item.find(["h3", "h4", "strong"])
                school_el = item.find(class_=lambda c: c and any(x in ["r-edu-school", "institution", "school"] for x in c.split()))
                date_el = item.find(class_=lambda c: c and any(x in ["r-edu-date", "dates"] for x in c.split()))

                dates_str = date_el.get_text(strip=True) if date_el else None
                start_date, end_date = self._split_dates(dates_str)

                education_list.append(
                    Education(
                        institution=school_el.get_text(strip=True) if school_el else "Institution",
                        degree=deg_el.get_text(strip=True) if deg_el else "Degree",
                        start_date=start_date,
                        end_date=end_date,
                    )
                )
        else:
            # Check for r-edu-head elements
            edu_heads = sec.find_all(class_=lambda c: c and "r-edu-head" in c.split())
            if edu_heads:
                for head in edu_heads:
                    deg_el = head.find(class_=lambda c: c and "r-edu-degree" in c.split())
                    date_el = head.find(class_=lambda c: c and "r-edu-date" in c.split())
                    # Look for next sibling that is r-edu-school
                    school_el = head.find_next_sibling(class_=lambda c: c and "r-edu-school" in c.split())

                    dates_str = date_el.get_text(strip=True) if date_el else None
                    start_date, end_date = self._split_dates(dates_str)

                    education_list.append(
                        Education(
                            institution=school_el.get_text(strip=True) if school_el else "Institution",
                            degree=deg_el.get_text(strip=True) if deg_el else "Degree",
                            start_date=start_date,
                            end_date=end_date,
                        )
                    )
            else:
                deg_el = sec.find(class_=lambda c: c and any(x in ["r-edu-degree", "degree"] for x in c.split())) or sec.find(["h3", "h4"])
                school_el = sec.find(class_=lambda c: c and any(x in ["r-edu-school", "institution", "school"] for x in c.split()))
                date_el = sec.find(class_=lambda c: c and any(x in ["r-edu-date", "dates"] for x in c.split()))

                if deg_el or school_el:
                    dates_str = date_el.get_text(strip=True) if date_el else None
                    start_date, end_date = self._split_dates(dates_str)
                    education_list.append(
                        Education(
                            institution=school_el.get_text(strip=True) if school_el else "Institution",
                            degree=deg_el.get_text(strip=True) if deg_el else "Degree",
                            start_date=start_date,
                            end_date=end_date,
                        )
                    )

        return education_list

    def _split_dates(self, dates_str: str | None) -> tuple[str | None, str | None]:
        """Split a date range into start and end dates."""
        if not dates_str:
            return None, None
        if "-" in dates_str or "–" in dates_str:
            parts = re.split(r"[-–]", dates_str, maxsplit=1)
            return parts[0].strip(), parts[1].strip()
        return dates_str.strip(), None

    def _extract_certifications(self, soup: BeautifulSoup) -> list[str]:
        """Extract certifications if present."""
        sec = self._find_section(soup, ["certifications", "licenses", "certificates"])
        if not sec:
            return []

        certs: list[str] = []
        for li in sec.find_all("li"):
            text = li.get_text(strip=True)
            if text:
                certs.append(text)
        return certs


def load_preferences(preferences_path: str | Path | None = None) -> SearchPreferences:
    """Load and validate SearchPreferences from YAML file."""
    path = Path(preferences_path) if preferences_path else settings.preferences_path
    if not path.exists():
        raise FileNotFoundError(f"Preferences file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return SearchPreferences.model_validate(data)


def load_resume(html_path: str | Path | None = None) -> ResumeData:
    """Convenience helper to parse master resume."""
    parser = ResumeParser(html_path)
    return parser.parse()
