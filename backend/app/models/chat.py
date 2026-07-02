from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Any, Dict
import uuid
from datetime import datetime, timezone


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    apartment_id: str
    message: str
    response: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: str = ""
    guest_ip: str = ""
    content: str = ""
    type: str = ""


class ChatRequest(BaseModel):
    apartment_id: str
    message: str
    session_id: str = ""


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str = ""


class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    full_name: str
    phone: str = ""
    hashed_password: str
    brand_name: str = "My Host IQ"
    brand_logo_url: str = ""
    brand_primary_color: str = "#6366f1"
    brand_secondary_color: str = "#10b981"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict
