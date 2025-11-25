from fastapi import FastAPI
from .generate import generate_handler

app = FastAPI()

# Route: POST /api/generate
@app.post("/api/generate")
async def generate(request):
    return await generate_handler(request)
