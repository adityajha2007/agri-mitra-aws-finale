from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.dashboard import router as dashboard_router
from app.api.upload import router as upload_router

app = FastAPI(
    title="Agri-Mitra API",
    description="GenAI-powered agricultural assistant for Indian farmers",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api/dashboard")
app.include_router(upload_router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "agri-mitra"}
