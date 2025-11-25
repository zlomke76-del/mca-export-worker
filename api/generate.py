import os
from fastapi import Request, HTTPException
from fastapi.responses import Response
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.pagesizes import letter

WORKER_KEY = os.environ["PY_WORKER_KEY"]

async def generate_handler(request: Request):
    auth = request.headers.get("authorization", "")
    if auth != f"Bearer {WORKER_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    body = await request.json()
    content_type = body.get("type")
    title = body.get("title", "Document")
    content = body.get("content", "")

    if content_type not in ("docx", "pdf", "csv"):
        raise HTTPException(status_code=400, detail="Unsupported type")

    if content_type == "pdf":
        # Minimal PDF output
        doc = SimpleDocTemplate("out.pdf", pagesize=letter)
        story = [Paragraph(content)]
        doc.build(story)
        with open("out.pdf", "rb") as f:
            data = f.read()
        return Response(content=data, media_type="application/pdf")

    # You will fill DOCX + CSV later
    raise HTTPException(status_code=501, detail="Not yet implemented")
