from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.api.auth import get_current_user
from app.models import User, Neologism, LLMResponse, Evaluation
from app.schemas import (
    NeologismCreate, 
    Neologism as NeologismSchema, 
    NeologismList, 
    ConflictResolution
)
from app.services.llm_service import llm_service

router = APIRouter()


@router.post("/", response_model=NeologismSchema)
async def create_neologism(
    neologism_data: NeologismCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Create the neologism record
    db_neologism = Neologism(
        word=neologism_data.word,
        user_definition=neologism_data.user_definition,
        context=neologism_data.context,
        user_id=current_user.id,
        status="pending"
    )
    
    db.add(db_neologism)
    db.commit()
    db.refresh(db_neologism)
    
    # Get definitions from LLM providers
    try:
        llm_responses = await llm_service.get_definitions(
            neologism_data.word,
            neologism_data.user_definition,
            neologism_data.context
        )
        
        # Store LLM responses
        successful_responses = []
        for response in llm_responses:
            if response["success"]:
                db_response = LLMResponse(
                    neologism_id=db_neologism.id,
                    provider=response["provider"],
                    response_data=response["response"].dict(),
                    confidence=int(response["response"].confidence * 100)
                )
                db.add(db_response)
                successful_responses.append(response)
        
        # Evaluate conflicts if we have multiple successful responses
        if len(successful_responses) >= 2:
            evaluation_result = await llm_service.evaluate_conflicts(
                neologism_data.word,
                successful_responses
            )
            
            db_evaluation = Evaluation(
                neologism_id=db_neologism.id,
                conflicts_detected=evaluation_result.get("conflicts_detected", []),
                resolution_required=evaluation_result.get("resolution_required", False),
                evaluator_response=evaluation_result
            )
            db.add(db_evaluation)
            
            # Update neologism status
            if evaluation_result.get("resolution_required", False):
                db_neologism.status = "conflict"
            else:
                db_neologism.status = "evaluated"
        
        db.commit()
        db.refresh(db_neologism)
        
    except Exception as e:
        # If LLM processing fails, keep the neologism but mark as failed
        db_neologism.status = "llm_error"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing with LLM providers: {str(e)}"
        )
    
    return db_neologism


@router.get("/", response_model=List[NeologismList])
async def list_neologisms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    neologisms = db.query(Neologism).filter(Neologism.user_id == current_user.id).all()
    return neologisms


@router.get("/{neologism_id}", response_model=NeologismSchema)
async def get_neologism(
    neologism_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    neologism = db.query(Neologism).filter(
        Neologism.id == neologism_id,
        Neologism.user_id == current_user.id
    ).first()
    
    if not neologism:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Neologism not found"
        )
    
    return neologism


@router.post("/{neologism_id}/resolve")
async def resolve_conflict(
    neologism_id: int,
    resolution_data: ConflictResolution,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    neologism = db.query(Neologism).filter(
        Neologism.id == neologism_id,
        Neologism.user_id == current_user.id,
        Neologism.status == "conflict"
    ).first()
    
    if not neologism:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Neologism not found or not in conflict status"
        )
    
    # Update the evaluation with user's resolution
    evaluation = db.query(Evaluation).filter(
        Evaluation.neologism_id == neologism_id
    ).first()
    
    if evaluation:
        if evaluation.evaluator_response is None:
            evaluation.evaluator_response = {}
        
        evaluation.evaluator_response["user_resolution"] = {
            "choice": resolution_data.resolution_choice,
            "feedback": resolution_data.user_feedback
        }
        evaluation.resolution_required = False
    
    # Update neologism status
    neologism.status = "resolved"
    
    db.commit()
    
    return {"message": "Conflict resolved successfully"}