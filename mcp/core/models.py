from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class SearchDocsInput(BaseModel):
    query: str = Field(..., description="Search query string")


class SearchDocsOutput(BaseModel):
    results: List[Dict[str, Any]] = Field(..., description="List of matching documents with doc_id, title, section, snippet")


class GetDocInput(BaseModel):
    doc_id: str = Field(..., description="Document ID")


class GetDocOutput(BaseModel):
    doc: Dict[str, Any] = Field(..., description="Document data with structured content")


class GetEntitiesInput(BaseModel):
    doc_id: str = Field(..., description="Document ID")
    entity_types: Optional[List[str]] = Field(None, description="Filter by entity types: headers, lists, code_blocks, examples, api, special_blocks")


class GetEntitiesOutput(BaseModel):
    entities: List[Dict[str, Any]] = Field(..., description="List of entities")


class FindExamplesInput(BaseModel):
    keywords: List[str] = Field(..., description="Keywords to search for in examples")


class FindExamplesOutput(BaseModel):
    examples: List[Dict[str, Any]] = Field(..., description="List of examples found")


class FindProcessPatternsInput(BaseModel):
    pattern_type: str = Field(..., description="Pattern type: согласование, поручение, регистрация, архивирование, SLA")


class FindProcessPatternsOutput(BaseModel):
    patterns: List[Dict[str, Any]] = Field(..., description="List of process patterns found")

