from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    neologisms = relationship("Neologism", back_populates="user")


class Neologism(Base):
    __tablename__ = "neologisms"
    
    id = Column(Integer, primary_key=True, index=True)
    word = Column(String, nullable=False, index=True)
    user_definition = Column(Text, nullable=False)
    context = Column(Text)
    status = Column(String, default="pending")  # pending, evaluated, conflict, resolved
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="neologisms")
    llm_responses = relationship("LLMResponse", back_populates="neologism")
    evaluations = relationship("Evaluation", back_populates="neologism")


class LLMResponse(Base):
    __tablename__ = "llm_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    neologism_id = Column(Integer, ForeignKey("neologisms.id"))
    provider = Column(String, nullable=False)  # openai, anthropic, google
    response_data = Column(JSON, nullable=False)
    confidence = Column(Integer)  # 0-100
    created_at = Column(DateTime, default=func.now())
    
    neologism = relationship("Neologism", back_populates="llm_responses")


class Evaluation(Base):
    __tablename__ = "evaluations"
    
    id = Column(Integer, primary_key=True, index=True)
    neologism_id = Column(Integer, ForeignKey("neologisms.id"))
    conflicts_detected = Column(JSON)  # Array of conflict descriptions
    resolution_required = Column(Boolean, default=False)
    evaluator_response = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    
    neologism = relationship("Neologism", back_populates="evaluations")