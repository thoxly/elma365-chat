from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class Doc(Base):
    __tablename__ = "docs"
    
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, unique=True, index=True, nullable=False)
    url = Column(Text, unique=True, index=True, nullable=False)
    normalized_path = Column(Text, unique=True, index=True, nullable=True)  # Normalized path for navigation
    outgoing_links = Column(ARRAY(Text), nullable=True)  # Array of normalized paths this document links to
    title = Column(Text)
    section = Column(Text)  # Combined breadcrumbs + URL segment
    content = Column(JSONB)  # Normalized structured blocks
    content_plain = Column(Text, nullable=True)  # Plaintext version for full-text search
    embedding = Column(Vector(1536), nullable=True)  # Document-level embedding (text-embedding-3-small)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_crawled = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DocChunk(Base):
    __tablename__ = "doc_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, ForeignKey("docs.doc_id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)  # Chunk-level embedding
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Entity(Base):
    __tablename__ = "entities"
    
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, ForeignKey("docs.doc_id"), index=True, nullable=False)
    type = Column(String, index=True, nullable=False)  # header, paragraph, code_block, list, special_block, etc.
    data = Column(JSONB)  # Entity-specific data
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Specification(Base):
    __tablename__ = "specifications"
    
    id = Column(Integer, primary_key=True, index=True)
    source_text = Column(Text)
    analyst_json = Column(JSONB)
    architect_json = Column(JSONB)
    spec_markdown = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CrawlerState(Base):
    __tablename__ = "crawler_state"
    
    id = Column(Integer, primary_key=True, index=True)
    last_run = Column(DateTime(timezone=True), nullable=True)
    pages_total = Column(Integer, default=0)
    pages_processed = Column(Integer, default=0)
    status = Column(String, default="idle")  # running/idle/error
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class KnowledgeRule(Base):
    """Хранение правил ELMA365 в БД"""
    __tablename__ = "knowledge_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_type = Column(String, unique=True, index=True, nullable=False)  # architecture_rules, process_rules, ui_rules, dictionary, patterns
    content = Column(JSONB, nullable=False)  # Для YAML - dict, для MD - {"text": "..."}
    version = Column(Integer, default=1)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String, nullable=True)  # Кто обновил (user_id или "system")


class TaskTemplate(Base):
    """Шаблоны заданий"""
    __tablename__ = "task_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # "Валидация процесса"
    description = Column(Text)  # Описание шаблона
    prompt = Column(Text, nullable=False)  # Промпт для LLM
    system_prompt = Column(Text)  # Системный промпт
    tools = Column(JSONB)  # Список MCP инструментов ["elma365.search_docs", ...]
    knowledge_rules = Column(JSONB)  # Какие правила применять ["architecture_rules", "process_rules"]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String, nullable=True)


class ChatSession(Base):
    """Сессии чата (список чатов пользователя)."""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, nullable=False, index=True)  # Бизнес-ключ, как в chat_messages
    user_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False, server_default="Новый чат")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ChatMessage(Base):
    """Сообщения в чате"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=False, index=True)  # Сессия чата
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    template_id = Column(Integer, ForeignKey("task_templates.id"), nullable=True)  # Если использован шаблон
    attachments = Column(JSONB)  # Загруженные документы
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatDocument(Base):
    """Документы, загруженные в чат"""
    __tablename__ = "chat_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    content = Column(Text)  # Текст документа
    file_type = Column(String)  # txt, pdf, docx, etc.
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())



