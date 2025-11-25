import os
import io
import csv
from fastapi import FastAPI, HTTPException, Request, Response
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from docx import Document

app = FastAPI()
PY_WORKER_KEY = os.getenv("PY_WORKER_KEY", "")

def generate_pdf(title: str, text: str) -> bytes:
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
    buf = io.StringIO()
    writer = csv.writer(buf)
    for line in text.replace("\r", "").split("\n"):
        writer.writerow([line])
    return buf.getvalue().encode("utf-8")

@app.get("/")
async def root():
    return {"ok": True, "service": "mca-export-worker"}

@app.post("/api/generate")
async def generate(request: Request):
    if not PY_WORKER_KEY:
        raise HTTPException(status_code=500, detail="PY_WORKER_KEY not set")

    auth_header = request.headers.get("authorization", "")
    if auth_header != f"Bearer {PY_WORKER_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    body = await request.json()
    export_type = (body.get("type") or "").lower()
    title = body.get("title") or "Solace Export"
    content = body.get("content") or ""

    if export_type == "pdf":
        data = generate_pdf(title, content)
        media = "application/pdf"
        filename = "solace-export.pdf"
    elif export_type == "docx":
        data = generate_docx(title, content)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = "solace-export.docx"
    elif export_type == "csv":
        data = generate_csv(content)
        media = "text/csv"
        filename = "solace-export.csv"
    else:
        raise HTTPException(status_code=400, detail="Unsupported export type")

    headers = {
        "Content-Disposition": f'inline; filename="{filename}"'
    }

    return Response(content=data, media_type=media, headers=headers)

