from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database.mongodb import connect_to_mongodb, close_mongodb
from app.routes import analytics, patients, query_lab, database, prediction, model_insights
settings = get_settings()

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
