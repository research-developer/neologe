from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, neologisms
from app.core.database import engine
from app.models import Base

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Neologe API",
    description="An API for registering and evaluating neologisms with LLM providers",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(neologisms.router, prefix="/neologisms", tags=["neologisms"])


@app.get("/")
async def root():
    return {
        "message": "Welcome to Neologe API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}