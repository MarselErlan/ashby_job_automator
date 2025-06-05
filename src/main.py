from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.app.api.endpoints import extractor, filler
from src.app.db.session import Base, engine

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Ashby Job Automator API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(extractor.router, prefix="/extractor", tags=["extractor"])
app.include_router(filler.router, prefix="/filler", tags=["filler"])