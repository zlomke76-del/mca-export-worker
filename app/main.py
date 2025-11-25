import os
import io
import csv

from fastapi import FastAPI, HTTPException, Request, Response

from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

from docx import Document

# FastAPI app that Vercel will discover automatically
app = FastAPI()

# Shared secret – must match PY_WORKER_KEY in BOTH projects:
# - studio.moralclarity.ai
# - mca-export-worker
PY_WORKER_KEY = os.getenv("PY_WORKER_KEY", "")


def generate_pdf(title: str, text: str) -> bytes:
    """Very simple PDF generator using reportlab."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()

    story = [Paragraph(f"<b>{title}</b>", styles["Heading1"])]

    for para in text.split("\n"):
        para = para.strip()
        if not para:
            continue
        story.append(Paragraph(para, styles["BodyText"]))

    doc.build(story)
    return buf.getvalue()


def generate_docx(title: str, text: str) -> bytes:
    """Very simple DOCX generator using python-docx."""
    doc = Document()
    doc.add_heading(title, level=1)

    for para in text.split("\n"):
        para = para.strip()
        if not para:
            continue
        doc.add_paragraph(para)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def generate_csv(text: str) -> bytes:
    """
    Simple CSV: one column, one row per line of text.
    Enough for Solace exports and easy to consume in Excel/Sheets.
    """
    buf = io.StringIO()
    writer = csv.writer(buf)

    for line in text.replace("\r", "").split("\n"):
        writer.writerow([line])

    return buf.getvalue().encode("utf-8")


@app.post("/api/generate")
async def generate(request: Request):
    """
    Single entrypoint Solace calls from:
      PY_WORKER_URL = https://mca-export-worker.vercel.app/api/generate

    Expects JSON payload like:
      { "type": "pdf" | "docx" | "csv", "title": "...", "content": "..." }

    Returns raw file bytes with appropriate Content-Type.
    """

    # ---- Guard: ensure key is configured ----
    if not PY_WORKER_KEY:
        raise HTTPException(
            status_code=500,
            detail="Worker misconfigured: PY_WORKER_KEY is not set.",
        )

    # ---- Auth check ----
    auth_header = request.headers.get("authorization", "")
    expected = f"Bearer {PY_WORKER_KEY}"

    if auth_header != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # ---- Parse body safely (no Pydantic model) ----
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    export_type = (body.get("type") or body.get("format") or "").strip().lower()
    title = (body.get("title") or "Solace Export").strip()
    content = body.get("content") or ""

    if not export_type:
        raise HTTPException(status_code=400, detail="Missing 'type' field")
    if export_type not in {"pdf", "docx", "csv"}:
        raise HTTPException(status_code=400, detail=f"Unsupported type: {export_type}")

    # ---- Generate bytes based on type ----
    if export_type == "pdf":
        data = generate_pdf(title, content)
        media_type = "application/pdf"
        filename = "solace-export.pdf"
    elif export_type == "docx":
        data = generate_docx(title, content)
        media_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        filename = "solace-export.docx"
    else:  # "csv"
        data = generate_csv(content)
        media_type = "text/csv"
        filename = "solace-export.csv"

    headers = {
        # Let Solace / browser treat it as a download if this URL is hit directly
        "Content-Disposition": f'inline; filename="{filename}"'
    }

    return Response(content=data, media_type=media_type, headers=headers)
