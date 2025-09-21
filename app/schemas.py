from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


# User schemas
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class User(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


# Neologism schemas
class NeologismCreate(BaseModel):
    word: str
    user_definition: str
    context: Optional[str] = None


class LLMResponseData(BaseModel):
    word: str
    definition: str
    part_of_speech: str
    etymology: Optional[str] = None
    variations: Optional[Dict[str, str]] = None
    usage_examples: Optional[List[str]] = None
    confidence: float


class LLMResponse(BaseModel):
    id: int
    provider: str
    response_data: LLMResponseData
    confidence: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class Evaluation(BaseModel):
    id: int
    conflicts_detected: Optional[List[str]]
    resolution_required: bool
    evaluator_response: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class Neologism(BaseModel):
    id: int
    word: str
    user_definition: str
    context: Optional[str]
    status: str
    user_id: int
    created_at: datetime
    updated_at: datetime
    llm_responses: List[LLMResponse] = []
    evaluations: List[Evaluation] = []

    class Config:
        from_attributes = True


class NeologismList(BaseModel):
    id: int
    word: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConflictResolution(BaseModel):
    resolution_choice: str
    user_feedback: Optional[str] = None