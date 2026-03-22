from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from app.tasks.update_ohlc import update_daily_ohlc
from app.database.agent_history import init_db as init_agent_history_db
from app.services.realtime_agent import warmup_hot_cache

from .models import HealthResponse
from .routes import analyze, reports, system, settings, stocks, ohlc, history, okx, crypto, crypto_klines

logger = logging.getLogger(__name__)

# Create scheduler
scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Finance Agent API...")

    # Initialize agent history database
    db_path = os.getenv("AGENT_HISTORY_DB_PATH", "data/agent_history.db")
    init_agent_history_db(db_path)
    logger.info(f"✓ Agent history database initialized: {db_path}")

    # Warmup hot cache
    logger.info("Warming up hot cache...")
    await warmup_hot_cache()
    logger.info("✓ Hot cache warmed up")

    # Update daily after US market close (UTC 21:30 = EST 16:30)
    scheduler.add_job(
        update_daily_ohlc,
        'cron',
        hour=21,
        minute=30,
        id='daily_ohlc_update'
    )
    scheduler.start()
    logger.info("✓ Scheduler started: daily OHLC update at 21:30 UTC")

    yield

    # Shutdown
    logger.info("Shutting down Finance Agent API...")
    scheduler.shutdown()
    logger.info("✓ Scheduler stopped")


app = FastAPI(
    title="Finance Agent API",
    description="Multi-agent financial analysis system API",
    version="0.1.0",
    lifespan=lifespan
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(system.router, prefix="/api", tags=["system"])
app.include_router(settings.router, prefix="/api", tags=["settings"])
app.include_router(stocks.router, prefix="/api", tags=["stocks"])
app.include_router(ohlc.router, prefix="/api/stocks", tags=["ohlc"])
app.include_router(history.router, prefix="/api", tags=["history"])
app.include_router(okx.router, prefix="/api", tags=["okx"])
app.include_router(crypto.router, prefix="/api/crypto", tags=["crypto"])
app.include_router(crypto_klines.router, prefix="/api", tags=["crypto-klines"])


@app.get("/")
async def root():
    return {"message": "Finance Agent API", "version": "0.1.0"}


@app.get("/api/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
    )
