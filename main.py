from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.routers import auth, users, documents, sharing, health

app = FastAPI(title=settings.APP_NAME, version="1.0.0", description="Secure document management and file sharing API")
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
register_exception_handlers(app)
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(
    users.router,
    prefix="/api/v1",
)
app.include_router(documents.router, prefix="/api/v1")
app.include_router(sharing.router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Document Management & Secure File Sharing API", "docs": "/docs"}
