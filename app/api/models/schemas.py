from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class AnalyzeRequest(BaseModel):
    query: str = Field(..., description="Stock symbol or query to analyze")


class AnalyzeResponse(BaseModel):
    report_id: str
    status: str


class Report(BaseModel):
    id: str
    symbol: str
    timestamp: str
    quant_analysis: Optional[Dict[str, Any]] = None
    news_sentiment: Optional[Dict[str, Any]] = None
    social_sentiment: Optional[Dict[str, Any]] = None


class ServiceStatus(BaseModel):
    available: bool
    url: str
    error: Optional[str] = None


class MCPStatus(BaseModel):
    market_data: ServiceStatus
    news_search: ServiceStatus


class HealthResponse(BaseModel):
    status: str
    timestamp: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
