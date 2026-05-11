from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from db.database import get_db
from db.models import Budget
from schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse
from api.auth import get_current_user
from schemas.auth import User

router = APIRouter(prefix="/budgets", tags=["budgets"])

@router.get("", response_model=List[BudgetResponse])
async def get_budgets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Retrieves all budgets for the current user.
    """
    return db.query(Budget).filter(Budget.user_id == current_user.id).all()

@router.post("", response_model=BudgetResponse)
async def create_budget(budget: BudgetCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Creates a new budget limit for a category for the current user.
    """
    db_budget = db.query(Budget).filter(Budget.category == budget.category, Budget.user_id == current_user.id).first()
    if db_budget:
        raise HTTPException(status_code=400, detail="Budget for this category already exists")

    new_budget = Budget(category=budget.category, amount=budget.amount, user_id=current_user.id)
    db.add(new_budget)
    db.commit()
    db.refresh(new_budget)
    return new_budget

@router.put("/{budget_id}", response_model=BudgetResponse)
async def update_budget(budget_id: int, budget_update: BudgetUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Updates an existing budget limit for the current user.
    """
    db_budget = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == current_user.id).first()
    if not db_budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    db_budget.amount = budget_update.amount
    db.commit()
    db.refresh(db_budget)
    return db_budget

@router.delete("/{budget_id}")
async def delete_budget(budget_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Deletes a budget for the current user.
    """
    db_budget = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == current_user.id).first()
    if not db_budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    db.delete(db_budget)
    db.commit()
    return {"message": "Budget deleted successfully"}
