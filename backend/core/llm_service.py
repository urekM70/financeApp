from typing import List, Dict, Any, Optional
import pandas as pd
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Basic in-memory caching to prevent duplicate LLM requests within the same run/session
_structure_cache: Dict[str, Any] = {}
_category_cache: Dict[str, str] = {}
_insights_cache: Dict[str, Any] = {}

class LLMClientManager:
    _clients: Dict[str, Any] = {}

    @classmethod
    def get_client(cls, provider: str = "openai") -> Optional[Any]:
        if provider not in cls._clients:
            cls._clients[provider] = cls._create_client(provider)
        return cls._clients[provider]

    @staticmethod
    def _create_client(provider: str) -> Optional[Any]:
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL")
            if not api_key:
                print("OpenAI credentials (OPENAI_API_KEY or LLM_API_KEY) are not set.")
                return None
            return OpenAI(api_key=api_key, base_url=base_url)
        
        return None

def generate_report_narrative(stats_summary: Dict[str, Any], currency: str = "USD") -> str:
    """
    Generates a short, personalized financial report narrative based on pre-calculated statistics.
    """
    client = LLMClientManager.get_client()
    if not client:
        return "AI analysis is currently unavailable. Please check your LLM configuration."
        
    prompt = f"""
    Act as a friendly, professional financial advisor. Below is a summary of the user's recent finances.
    Please use the currency '{currency}' when referring to monetary values.
    
    Data:
    {json.dumps(stats_summary, indent=2)}
    
    Tasks:
    1. Write a 2-paragraph financial report summarizing their standing.
    2. Highlight their biggest expense category and note if their net savings are positive or negative.
    3. Give exactly ONE actionable piece of advice based on these numbers.
    
    Keep the tone encouraging, concise, and do not use markdown headers, just paragraphs.
    """
    
    try:
        model_name = os.getenv("LLM_MODEL", "qwen/qwen3-next-80b-a3b-instruct:free")
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a financial advisor."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating report narrative: {repr(e)}")
        return "Could not generate AI report at this time due to an error."

def analyze_transactions(transactions: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyzes a DataFrame of transactions to generate financial insights using an OpenAI model.

    Args:
        transactions: A pandas DataFrame containing transaction data.

    Returns:
        A dictionary containing AI-generated 'insights' and basic 'statistics'.
    """
    if transactions.empty:
        return {
            "insights": ["No transactions to analyze."],
            "statistics": {"transaction_count": 0, "total_spent": 0.0, "average_transaction": 0.0}
        }

    stats = {
        "transaction_count": len(transactions),
        "total_spent": float(transactions['amount'].sum()),
        "average_transaction": float(transactions['amount'].mean())
    }

    client = LLMClientManager.get_client()
    if not client:
        return {
            "insights": ["OpenAI analysis is not configured. Please set the OPENAI_API_KEY."],
            "statistics": stats
        }
        
    data_sample = transactions.head(50).to_dict(orient='records')
    data_str = json.dumps(data_sample, default=str)
    
    cache_key = data_str
    if cache_key in _insights_cache:
        return {"insights": _insights_cache[cache_key], "statistics": stats}
    
    prompt = f"""
    As a financial analyst, review the following transactions and provide 3-5 concise, actionable
    insights regarding spending habits, potential savings, or noteworthy patterns.

    Please return ONLY a valid JSON object in the following format:
    {{
        "insights": ["Insightful observation 1", "Insightful observation 2", ...]
    }}

    Transaction Data:
    {data_str}
    """
    
    try:
        model_name = os.getenv("LLM_MODEL", "qwen/qwen3-next-80b-a3b-instruct:free")
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful financial analyst. Your response must be valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )
        content = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        result = json.loads(content)
        insights = result.get("insights", [])
        _insights_cache[cache_key] = insights
        
        return {"insights": insights, "statistics": stats}
        
    except Exception as e:
        print(f"Error during LLM analysis: {repr(e)}")
        return {"insights": [f"Failed to generate AI insights: {repr(e)}"], "statistics": stats}

def detect_structure_with_llm(text_sample: List[List[str]]) -> Optional[Dict[str, Any]]:
    """
    Uses an OpenAI model to analyze a text sample from a PDF to determine the table structure.

    Args:
        text_sample: A sample of text from the PDF.

    Returns:
        A dictionary with the detected structure, or None on failure.
    """
    client = LLMClientManager.get_client()
    if not client:
        print("LLM client for structure detection could not be initialized.")
        return None

    cache_key = json.dumps(text_sample, ensure_ascii=False)
    if cache_key in _structure_cache:
        return _structure_cache[cache_key]

    prompt = f"""
    Analyze the following text from a financial statement to identify its table structure.

    Text Sample:
    {json.dumps(text_sample, ensure_ascii=False, indent=2)}

    Return a JSON object with this exact structure:
    {{
        "all_headers": ["Header1", "Header2", ...],
        "mapping": {{
            "date": ["HeaderForDate"],
            "description": ["HeaderForDescription"],
            "amount_mode": "single" or "double",
            "amount_single": ["HeaderIfSingleMode"],
            "amount_neg": ["HeaderForDebit"],
            "amount_pos": ["HeaderForCredit"]
        }}
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4-turbo"),
            messages=[
                {"role": "system", "content": "You are a data extraction specialist. Respond with valid JSON."},
                {"role": "user", "content": prompt}
            ]
        )
        result = json.loads(response.choices[0].message.content)
        _structure_cache[cache_key] = result
        return result
    except Exception as e:
        print(f"LLM structure detection failed: {repr(e)}")
        return None

def map_columns_with_llm(columns: List[str]) -> Dict[str, str]:
    """
    Uses an OpenAI model to suggest a mapping from file columns to the application's standard schema.
    """
    client = LLMClientManager.get_client()
    if not client:
        return {}

    model_name = os.getenv("LLM_MODEL", "qwen/qwen3-next-80b-a3b-instruct:free")
    
    prompt = f"""
    Analyze the following column headers and map them to our standard format.

    Standard Format: "date", "amount", "amount_debit", "amount_credit", "description", "category".

    Input Columns: {json.dumps(columns)}

    Return a JSON object mapping input columns to the standard format.
    """

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a data mapping expert. Respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error during LLM column mapping: {repr(e)}")
        return {}

def categorize_transactions_with_llm(df: pd.DataFrame, standard_categories: List[str]) -> pd.DataFrame:
    """
    Uses an OpenAI model to categorize transactions that do not already have a category.
    """
    if 'category' not in df.columns:
        df['category'] = 'Uncategorized'
    else:
        df['category'] = df['category'].fillna('Uncategorized')

    uncategorized_mask = df['category'].str.lower() == 'uncategorized'
    if not uncategorized_mask.any():
        return df
    
    client = LLMClientManager.get_client()
    if not client:
        return df
    
    batch_size = 50
    uncategorized_indices = df[uncategorized_mask].index
    
    for i in range(0, len(uncategorized_indices), batch_size):
        batch_indices = uncategorized_indices[i:i + batch_size]
        
        transactions_to_ask = []
        for idx in batch_indices:
            row = df.loc[idx]
            cache_key = f"{row.get('description', '')}_{row.get('amount', 0)}"
            if cache_key in _category_cache:
                df.loc[idx, 'category'] = _category_cache[cache_key]
            else:
                transactions_to_ask.append({"index": idx, "description": row.get('description', ''), "amount": row.get('amount', 0)})
        
        if not transactions_to_ask:
            continue
            
        prompt = f"""
        Categorize these transactions into one of the following: {', '.join(standard_categories)}.
        Return ONLY a JSON object mapping the transaction index to its category.
        
        Transactions:
        {json.dumps(transactions_to_ask, default=str)}
        """
        
        try:
            model_name = os.getenv("LLM_MODEL", "xiaomi/mimo-v2-flash:free")
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            categories = json.loads(response.choices[0].message.content)
            for idx_str, category in categories.items():
                idx = int(idx_str)
                if category in standard_categories:
                    df.loc[idx, 'category'] = category
                    row = df.loc[idx]
                    cache_key = f"{row.get('description', '')}_{row.get('amount', 0)}"
                    _category_cache[cache_key] = category
        except Exception as e:
            print(f"Error during batch categorization: {repr(e)}")

    return df
