from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# Document schemas
class DocSchema(BaseModel):
    id: int
    doc_id: str
    url: str
    normalized_path: Optional[str] = None
    outgoing_links: Optional[List[str]] = None
    title: Optional[str] = None
    section: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    last_crawled: Optional[datetime] = None

    class Config:
        from_attributes = True


# Entity schemas
class EntitySchema(BaseModel):
    id: int
    doc_id: str
    type: str
    data: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


# Crawler state schemas
class CrawlerStateSchema(BaseModel):
    id: int
    last_run: Optional[datetime] = None
    pages_total: int = 0
    pages_processed: int = 0
    status: str = "idle"  # running/idle/error
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# MCP tool request/response schemas
class SearchDocsRequest(BaseModel):
    query: str = Field(..., description="Search query string")


class SearchDocsResponse(BaseModel):
    results: List[Dict[str, Any]] = Field(..., description="List of matching documents")


class GetDocRequest(BaseModel):
    doc_id: str = Field(..., description="Document ID")


class GetDocResponse(BaseModel):
    doc: Dict[str, Any] = Field(..., description="Document data")


class GetEntitiesRequest(BaseModel):
    doc_id: str = Field(..., description="Document ID")
    entity_types: Optional[List[str]] = Field(None, description="Filter by entity types")


class GetEntitiesResponse(BaseModel):
    entities: List[Dict[str, Any]] = Field(..., description="List of entities")


class FindExamplesRequest(BaseModel):
    keywords: List[str] = Field(..., description="Keywords to search for")


class FindExamplesResponse(BaseModel):
    examples: List[Dict[str, Any]] = Field(..., description="List of examples")


class FindProcessPatternsRequest(BaseModel):
    pattern_type: str = Field(..., description="Pattern type: согласование, поручение, регистрация, архивирование, SLA")


class FindProcessPatternsResponse(BaseModel):
    patterns: List[Dict[str, Any]] = Field(..., description="List of process patterns")

