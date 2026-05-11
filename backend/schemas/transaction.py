from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class TransactionBase(BaseModel):
    date: datetime
    amount: float
    description: str
    category: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    date: Optional[datetime] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    category: Optional[str] = None

class Transaction(TransactionBase):
    id: int
    type: Optional[str] = None

    class Config:
        from_attributes = True

class TransactionSummary(BaseModel):
    total_transactions: int
    total_amount: float
    categories: dict[str, float]
    date_range: tuple[datetime, datetime]
    insights: Optional[List[str]] = None

class TransactionPreview(BaseModel):
    summary: TransactionSummary
    transactions: List[TransactionCreate]

class PreviewResponse(BaseModel):
    success: bool
    summary: Optional[TransactionSummary] = None
    transactions: Optional[List[TransactionCreate]] = None
    column_mapping: Optional[dict[str, str]] = None
    message: Optional[str] = None
    original_columns: Optional[List[str]] = None

