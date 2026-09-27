"""
Vercel serverless function entry point for CardioCare FastAPI backend.
Wraps the existing FastAPI app for Vercel's Python runtime.
"""
import os
import sys

# Add backend directory to Python path so `app` package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.mongodb import connect_to_mongodb, close_mongodb
from app.routes import analytics, patients, query_lab, database, prediction, model_insights

app = FastAPI(
    title="CardioCare API",
    version="1.0.0",
    description="Backend API for CardioCare Analytics Dashboard"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    connect_to_mongodb()

@app.on_event("shutdown")
async def shutdown_event():
    close_mongodb()

app.include_router(analytics.router, prefix="/api/v1")
app.include_router(patients.router, prefix="/api/v1")
app.include_router(query_lab.router, prefix="/api/v1")
app.include_router(database.router, prefix="/api/v1")
app.include_router(prediction.router, prefix="/api/v1")
app.include_router(model_insights.router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Welcome to CardioCare API"}

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "CardioCare API"}
