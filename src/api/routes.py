import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from config.settings import settings
from src.api.service import APIService

router = APIRouter(prefix="/api")
service = APIService()


class TailorRequest(BaseModel):
    cover_letter: bool = True


class AutoApplyRequest(BaseModel):
    headed: bool = True
    auto_submit: bool = False
    review_timeout_sec: int = 15


class TrackerUpdateRequest(BaseModel):
    status: str
    notes: str | None = None


class AddATSLinkRequest(BaseModel):
    url: str | None = None
    platform: str | None = None
    company_slug: str | None = None


@router.get("/health")
def get_health() -> dict[str, str]:
    return {"status": "ok", "app": "HireReady"}


@router.get("/stats")
def get_stats() -> dict[str, Any]:
    jobs_data = service.get_jobs()
    tracker_data = service.get_tracker()
    apps = tracker_data.get("applications", [])

    status_counts = {}
    for app in apps:
        s = app.get("status", "saved")
        status_counts[s] = status_counts.get(s, 0) + 1

    return {
        "total_jobs_scanned": jobs_data.get("total", 0),
        "total_applications": len(apps),
        "pipeline": status_counts,
        "ats_configured_count": sum(
            len(c.get("companies", [])) if isinstance(c, dict) else len(c)
            for c in service.get_ats_companies().values()
        ),
    }


@router.get("/jobs")
def get_jobs(
    search: str | None = None,
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    page: int = Query(1, ge=1),
    page_size: int = Query(0, ge=0),
) -> dict[str, Any]:
    data = service.get_jobs()
    jobs = data.get("jobs", [])

    if min_score > 0:
        jobs = [j for j in jobs if (j.get("score") or 0) >= min_score]

    if search:
        q = search.lower()
        jobs = [
            j for j in jobs
            if q in j.get("title", "").lower()
            or q in j.get("company", "").lower()
            or q in j.get("location", "").lower()
            or q in j.get("ats_source", "").lower()
        ]

    total = len(jobs)
    if page_size > 0:
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_jobs = jobs[start_idx:end_idx]
    else:
        paginated_jobs = jobs

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1

    return {
        "jobs": paginated_jobs,
        "total": total,
        "page": page,
        "page_size": page_size or total,
        "total_pages": total_pages,
        "suggestions": data.get("suggestions", []),
    }


@router.get("/scan/stream")
async def scan_stream():
    async def event_generator():
        async for msg in service.scan_stream():
            yield {"data": msg}

    return EventSourceResponse(event_generator())


@router.post("/jobs/{job_id}/tailor")
def tailor_job(job_id: str, req: TailorRequest):
    try:
        result = service.tailor_job(job_id, generate_cover_letter=req.cover_letter)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/jobs/{job_id}/auto-apply")
def auto_apply_job(job_id: str, req: AutoApplyRequest = AutoApplyRequest()):
    try:
        result = service.auto_apply_job(
            job_id=job_id,
            headed=req.headed,
            auto_submit=req.auto_submit,
            review_timeout_sec=req.review_timeout_sec,
        )
        return {"success": result.get("success", False), "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/jobs/{job_id}/output")
def get_job_output(job_id: str):
    output = service.get_job_output(job_id)
    if not output.get("exists"):
        raise HTTPException(status_code=404, detail="Tailored output not found for this job.")
    return output


@router.get("/jobs/{job_id}/pdf")
def get_job_pdf(job_id: str):
    pdf_path = settings.output_dir / job_id / "resume.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Resume PDF not found.")
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"resume_{job_id}.pdf",
    )


@router.get("/jobs/{job_id}/html")
def get_job_html(job_id: str):
    html_path = settings.output_dir / job_id / "resume.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Resume HTML not found.")
    return FileResponse(
        path=html_path,
        media_type="text/html",
        filename=f"resume_{job_id}.html",
    )


@router.get("/resume/master/html")
def get_master_resume_html():
    path = settings.master_resume_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Master resume HTML not found at input/master_resume.html")
    return FileResponse(
        path=path,
        media_type="text/html",
        filename="master_resume.html",
    )


@router.get("/resume/master/data")
def get_master_resume_data():
    try:
        resume = service.get_resume()
        return {
            "success": True,
            "resume": resume.model_dump(),
            "raw_html_exists": settings.master_resume_path.exists(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resume/master/pdf")
def get_master_resume_pdf():
    pdf_path = settings.input_dir / "master_resume.pdf"
    if not pdf_path.exists():
        html_path = settings.master_resume_path
        if not html_path.exists():
            raise HTTPException(status_code=404, detail="Master resume HTML not found.")
        try:
            from src.pdf_generator import PDFGenerator
            generator = PDFGenerator()
            generator.generate_pdf(html_path, pdf_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate master resume PDF: {e}")

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename="master_resume.pdf",
    )


@router.get("/tracker")
def get_tracker():
    return service.get_tracker()


@router.post("/tracker/{job_id}")
@router.patch("/tracker/{job_id}")
def update_tracker_stage(job_id: str, req: TrackerUpdateRequest):
    return service.update_tracker(job_id, req.status, notes=req.notes)


@router.delete("/tracker/{job_id}")
def delete_tracker_job(job_id: str):
    return service.delete_tracker(job_id)


@router.get("/preferences")
def get_preferences():
    return service.get_preferences()


@router.put("/preferences")
def update_preferences(data: dict[str, Any]):
    try:
        updated = service.update_preferences(data)
        return {"success": True, "data": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ats-links")
def get_ats_links():
    return service.get_ats_companies()


@router.post("/ats-links")
def add_ats_link(req: AddATSLinkRequest):
    try:
        updated = service.add_ats_link(url=req.url, platform=req.platform, company_slug=req.company_slug)
        return {"success": True, "data": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/ats-links/{platform}/{company_slug}")
def delete_ats_link(platform: str, company_slug: str):
    try:
        updated = service.delete_ats_company(platform, company_slug)
        return {"success": True, "data": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
