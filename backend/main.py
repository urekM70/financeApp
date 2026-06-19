from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn
import os

from api import transactions, auth, budgets
from db import models
from db.database import engine, SessionLocal
from core.i18n import set_lang
from sqlalchemy import inspect, text
from starlette.requests import Request

# --- Database Migration ---

def upgrade_db():
    """
    Checks for and applies necessary database schema upgrades.
    """
    db = SessionLocal()
    inspector = inspect(engine)
    try:
        # 1. Check if the 'user_id' column exists in the 'transactions' table
        columns = [c["name"] for c in inspector.get_columns("transactions")]
        if "user_id" not in columns:
            print("INFO:     Upgrading database: Adding 'user_id' to 'transactions' table.")
            db.execute(text("ALTER TABLE transactions ADD COLUMN user_id INTEGER REFERENCES users(id)"))
            db.commit()
            print("INFO:     Database upgrade complete.")
        
        # 2. Add other checks here in the future
        
    except Exception as e:
        print(f"ERROR:    Database migration failed: {e}")
        db.rollback()
    finally:
        db.close()

# --- Application Setup ---

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Apply database migrations
upgrade_db()

# Load environment variables
load_dotenv(override=True)

# Get environment variables
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Initialize FastAPI app
app = FastAPI(
    title="financeApp API",
    description="API for analyzing financial transactions",
    version="0.1.0",
    redirect_slashes=False  # Prevent redirects for missing trailing slashes
)

# Include routers
app.include_router(transactions.router)
app.include_router(auth.router)
app.include_router(budgets.router)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def language_middleware(request: Request, call_next):
    lang_header = request.headers.get("Accept-Language", "en")
    lang = "en"
    if lang_header.startswith("es"):
        lang = "es"
    elif lang_header.startswith("fr"):
        lang = "fr"
    set_lang(lang)
    response = await call_next(request)
    return response

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )
