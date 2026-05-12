"""
UniResolve — Gen-AI Powered Unified Complaint Intelligence
Main FastAPI application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.complaints import router as complaints_router

app = FastAPI(
    title="UniResolve API",
    description="Gen-AI Powered Unified Complaint Intelligence for Union Bank of India",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(complaints_router)


@app.get("/", tags=["health"])
async def root():
    return {
        "service": "UniResolve",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy"}
