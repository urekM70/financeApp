from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form, Query, Header, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
import json
import pandas as pd
from pydantic import BaseModel
import io
import hashlib
from datetime import datetime
import logging

from db.database import get_db
from db.models import Transaction, ReportCache
from processing.transaction_parser import parse_transactions, generate_summary, map_columns_with_llm, categorize_transactions
from processing.pdf_parser import parse_pdf
from core.llm_service import analyze_transactions, generate_report_narrative
from core.i18n import _
from schemas.transaction import (
    TransactionSummary,
    TransactionCreate,
    TransactionUpdate,
    Transaction as TransactionSchema,
    PreviewResponse
)
from api.auth import get_current_user
from schemas.auth import User

router = APIRouter(prefix="/transactions", tags=["transactions"])


logging.basicConfig(level=logging.INFO)
@router.post("/batch/", response_model=TransactionSummary)
async def create_transactions_batch(
    transactions: List[TransactionCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates multiple transactions in the database from a provided list for the current user.
    This is typically used after a user previews and confirms an uploaded file.
    """
    if db is None:
        raise HTTPException(status_code=503, detail=_("Database not available"))

    # Create Transaction model instances and add them to the session
    db_transactions = [Transaction(**t.dict(), user_id=current_user.id) for t in transactions]
    db.add_all(db_transactions)
    db.commit()

    # Create a DataFrame for summary and analysis
    df = pd.DataFrame([t.dict() for t in transactions])
    summary = generate_summary(df)
    
    # Get LLM insights
    analysis_result = analyze_transactions(df)
    summary.insights = analysis_result.get("insights", [])
    
    return summary


class BulkDeleteRequest(BaseModel):
    ids: List[int]

# --- Helper Functions ---

def _process_transaction_file(file: io.BytesIO, filename: str, column_mapping: Optional[dict]) -> Tuple[pd.DataFrame, TransactionSummary]:
    """
    Processes an uploaded transaction file by parsing, categorizing, and summarizing it.

    Args:
        file: The file-like object containing the transaction data.
        filename: The name of the file.
        column_mapping: An optional dictionary for column name mapping.

    Returns:
        A tuple containing the processed DataFrame and a summary of the transactions.
    """
    # Parse the file into a DataFrame
    df = parse_transactions(file, filename, column_mapping)
    
    # Automatically categorize any transactions that lack a category
    df = categorize_transactions(df)
    
    # Generate summary statistics from the DataFrame
    summary = generate_summary(df)
    
    # Enhance the summary with LLM-powered insights
    analysis_result = analyze_transactions(df)
    summary.insights = analysis_result.get("insights", [])
    
    return df, summary

# --- API Endpoints ---

@router.get("", response_model=List[TransactionSchema])
async def get_transactions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Retrieves all transactions for the current user from the database.

    Raises:
        HTTPException: If the database is not available.

    Returns:
        A list of all transactions, with a 'type' field added dynamically.
    """
    if db is None:
        raise HTTPException(status_code=503, detail=_("Database connection is not available."))

    transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id).all()

    # Dynamically add a 'type' field (income/expense) to each transaction for frontend convenience
    return [
        TransactionSchema(
            id=t.id,
            date=t.date,
            description=t.description,
            amount=t.amount,
            category=t.category,
            type="income" if t.amount > 0 else "expense"
        )
        for t in transactions
    ]

@router.post("", response_model=TransactionSchema)
async def create_transaction(
    transaction: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a single new transaction in the database for the current user.
    """
    if db is None:
        raise HTTPException(status_code=503, detail=_("Database not available"))

    db_transaction = Transaction(**transaction.dict(), user_id=current_user.id)
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    
    return TransactionSchema(
        id=db_transaction.id,
        date=db_transaction.date,
        description=db_transaction.description,
        amount=db_transaction.amount,
        category=db_transaction.category,
        type="income" if db_transaction.amount > 0 else "expense"
    )

@router.put("/{transaction_id}", response_model=TransactionSchema)
async def update_transaction(
    transaction_id: int,
    transaction_update: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates an existing transaction by its ID for the current user.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    db_transaction = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == current_user.id).first()
    if not db_transaction:
        raise HTTPException(status_code=404, detail=_("Transaction not found"))

    update_data = transaction_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_transaction, key, value)

    db.commit()
    db.refresh(db_transaction)
    
    return TransactionSchema(
        id=db_transaction.id,
        date=db_transaction.date,
        description=db_transaction.description,
        amount=db_transaction.amount,
        category=db_transaction.category,
        type="income" if db_transaction.amount > 0 else "expense"
    )

@router.delete("/{transaction_id}")
async def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a single transaction by its ID for the current user.
    """
    if db is None:
        raise HTTPException(status_code=503, detail=_("Database not available"))

    db_transaction = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == current_user.id).first()
    if not db_transaction:
        raise HTTPException(status_code=404, detail=_("Transaction not found"))

    db.delete(db_transaction)
    db.commit()
    return {"message": _("Transaction deleted successfully")}

@router.post("/bulk/delete", status_code=200)
async def bulk_delete_transactions(
    request: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes multiple transactions based on a list of IDs for the current user.
    """
    if db is None:
        raise HTTPException(status_code=503, detail=_("Database not available"))

    if not request.ids:
        raise HTTPException(status_code=400, detail=_("No transaction IDs provided for deletion."))

    # Perform a bulk delete operation and get the count of deleted rows
    deleted_count = db.query(Transaction).filter(Transaction.id.in_(request.ids), Transaction.user_id == current_user.id).delete(synchronize_session=False)
    db.commit()

    if deleted_count == 0:
        return {"message": _("No transactions found with the given IDs."), "deleted_count": 0}

    return {"message": _("Successfully deleted {count} transaction(s).", count=deleted_count), "deleted_count": deleted_count}

@router.post("/batch/", response_model=TransactionSummary)
async def create_transactions_batch(
    transactions: List[TransactionCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates multiple transactions in the database from a provided list for the current user.
    This is typically used after a user previews and confirms an uploaded file.
    """
    if db is None:
        raise HTTPException(status_code=503, detail=_("Database not available"))

    # Create Transaction model instances and add them to the session
    db_transactions = [Transaction(**t.dict(), user_id=current_user.id) for t in transactions]
    db.add_all(db_transactions)
    db.commit()

    # Create a DataFrame for summary and analysis
    df = pd.DataFrame([t.dict() for t in transactions])
    summary = generate_summary(df)
    
    # Get LLM insights
    analysis_result = analyze_transactions(df)
    summary.insights = analysis_result.get("insights", [])
    
    return summary

@router.post("/preview", response_model=PreviewResponse)
async def preview_transactions(
    file: UploadFile = File(...),
    column_mapping: Optional[str] = Form(None)
):
    """
    Previews transactions from a CSV, Excel, or PDF file without saving them to the database.
    If parsing fails due to missing standard columns, it suggests a column mapping using an LLM.
    """
    mapping_dict = json.loads(column_mapping) if column_mapping else None
    
    try:
        # Process the file to get a DataFrame and summary
        df, summary = _process_transaction_file(file.file, file.filename, mapping_dict)
        
        # Convert DataFrame to a list of TransactionCreate schemas for the response
        transactions_to_preview = [
            TransactionCreate(**record) for record in df.to_dict('records')
        ]
            
        return PreviewResponse(
            success=True,
            summary=summary,
            transactions=transactions_to_preview
        )
        
    except ValueError as e:
        # This error is often raised by parse_transactions for column issues
        file.file.seek(0)
        try:
            # Attempt to get column names for the LLM to map
            if file.filename.lower().endswith(('.xls', '.xlsx')):
                df_raw = pd.read_excel(file.file, nrows=0)
            elif file.filename.lower().endswith('.pdf'):
                df_raw = parse_pdf(file.file)
            else:
                df_raw = pd.read_csv(file.file, nrows=0)
            
            columns = df_raw.columns.tolist()
            suggested_mapping = map_columns_with_llm(columns)
            
            return PreviewResponse(
                success=False,
                message=str(e),
                column_mapping=suggested_mapping,
                original_columns=columns
            )
        except Exception as read_error:
            # Handle errors during column extraction
            return PreviewResponse(
                success=False,
                message=f"Error reading file columns: {str(read_error)}"
            )
    except Exception as e:
        # Catch-all for other processing errors
        return PreviewResponse(
            success=False,
            message=f"An unexpected error occurred while processing the file: {str(e)}"
        )

@router.post("/upload", response_model=TransactionSummary)
async def upload_transactions(
    file: UploadFile = File(...),
    column_mapping: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads and saves transactions from a CSV, Excel, or PDF file to the database for the current user.
    """
    if db is None:
        raise HTTPException(status_code=503, detail=_("Database connection is not available."))

    mapping_dict = json.loads(column_mapping) if column_mapping else None

    try:
        # Process the file to get DataFrame and summary
        df, summary = _process_transaction_file(file.file, file.filename, mapping_dict)

        # Save the processed transactions to the database
        records = df.to_dict('records')
        db_transactions = [Transaction(**rec, user_id=current_user.id) for rec in records]
        db.add_all(db_transactions)
        db.commit()

        return summary
    except Exception as e:
        # Raise an HTTPException for any errors during processing or saving
        raise HTTPException(status_code=400, detail=f"Failed to process or upload file: {str(e)}")

@router.get("/report/summary")
async def get_report_summary(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    x_currency: str = Header("USD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Aggregates user financial data to create a high-level summary and generates a narrative.
    Uses SHA-256 caching via DB to completely bypass calculations and LLM requests if data is unchanged.
    """
    if db is None:
        raise HTTPException(status_code=503, detail=_("Database connection is not available."))

    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    transactions = query.all()
    if not transactions:
        return {
            "stats": {
                "total_income": 0,
                "total_expenses": 0,
                "net_savings": 0,
                "top_categories": {}
            },
            "narrative": "There are no transactions available in this timeframe. Try a different date range or upload some data!"
        }

    # 1. Calculate a stable SHA-256 hash of the transaction dataset
    # We sort by ID to ensure order doesn't affect the hash
    sorted_txs = sorted(transactions, key=lambda t: t.id)
    hash_input = f"{x_currency}|" + "|".join([f"{t.id}:{t.date.isoformat()}:{t.amount}:{t.category}" for t in sorted_txs])
    tx_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

    # 2. Check Database for matching hash
    cached_report = db.query(ReportCache).filter(ReportCache.transaction_hash == tx_hash).first()
    if cached_report:
        return {
            "stats": json.loads(cached_report.stats_json),
            "narrative": cached_report.narrative
        }

    # 3. If cache miss, use Pandas for pure-code robust aggregation
    df = pd.DataFrame([
        {
            "amount": t.amount,
            "category": t.category,
            "date": t.date
        } for t in transactions
    ])

    total_income = float(df[df['amount'] > 0]['amount'].sum())
    total_expenses = float(abs(df[df['amount'] < 0]['amount'].sum()))
    net_savings = total_income - total_expenses
    
    # Get top 3 expense categories
    expenses_df = df[df['amount'] < 0]
    top_categories = {}
    if not expenses_df.empty:
        cat_sums = expenses_df.groupby('category')['amount'].sum().abs().sort_values(ascending=False).head(3)
        top_categories = {str(k): float(v) for k, v in cat_sums.to_dict().items()}

    stats_summary = {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_savings": net_savings,
        "top_categories": top_categories
    }

    # Get LLM narrative based on this hard numerical data
    narrative = generate_report_narrative(stats_summary, currency=x_currency)

    # Save to Database Cache
    new_report = ReportCache(
        start_date=start_date,
        end_date=end_date,
        transaction_hash=tx_hash,
        stats_json=json.dumps(stats_summary),
        narrative=narrative
    )
    db.add(new_report)
    db.commit()

    return {
        "stats": stats_summary,
        "narrative": narrative
    }
