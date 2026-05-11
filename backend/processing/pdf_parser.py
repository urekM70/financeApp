import os
import json
import re
import pymupdf
import pandas as pd
import io
from typing import List, Dict, Any, Optional

from core.llm_service import detect_structure_with_llm

def extract_words_from_pdf(pdf_input: Any) -> List[List[Dict[str, Any]]]:
    """
    Extracts all words and their coordinates from each page of a PDF.

    Args:
        pdf_input: A file path (str) or a file-like object (bytes or stream).

    Returns:
        A list of pages, where each page is a list of word dictionaries.
    """
    try:
        if isinstance(pdf_input, str):
            doc = pymupdf.open(pdf_input)
        else:
            # Handle in-memory file objects
            if hasattr(pdf_input, "seek"):
                pdf_input.seek(0)
            file_bytes = pdf_input.read() if hasattr(pdf_input, "read") else pdf_input
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
            
    except Exception as e:
        print(f"Error opening PDF: {repr(e)}")
        return []
        
    all_pages = []
    for page in doc:
        # get_text("words") returns a list of (x0, y0, x1, y1, text, block, line, word)
        words = page.get_text("words")
        page_data = [
            {"text": w[4], "x0": w[0], "y0": w[1], "x1": w[2], "y1": w[3]}
            for w in words
        ]
        all_pages.append(page_data)
    return all_pages

def group_words_by_lines(words: List[Dict[str, Any]], y_tolerance: int = 3) -> List[List[Dict[str, Any]]]:
    """
    Groups a list of words into lines based on their vertical alignment.

    Args:
        words: A list of word dictionaries, each with 'y0' and 'x0' coordinates.
        y_tolerance: The maximum vertical distance between words to be considered on the same line.

    Returns:
        A list of lines, where each line is a sorted list of word dictionaries.
    """
    if not words:
        return []
        
    # Sort words primarily by their vertical position, then horizontal
    sorted_words = sorted(words, key=lambda w: (w['y0'], w['x0']))
    
    lines = []
    current_line = [sorted_words[0]]
    
    for word in sorted_words[1:]:
        # Check if the current word is vertically close to the last word in the current line
        if abs(word['y0'] - current_line[-1]['y0']) < y_tolerance:
            current_line.append(word)
        else:
            lines.append(sorted(current_line, key=lambda w: w['x0']))
            current_line = [word]
    
    lines.append(sorted(current_line, key=lambda w: w['x0']))
    return lines

def find_header_coordinates(words: List[Dict[str, Any]], target_headers: List[str]) -> Optional[Dict[str, Dict[str, float]]]:
    """
    Locates the bounding boxes of specified header texts on a page.

    Args:
        words: A list of all words on the page.
        target_headers: The list of header strings to find.

    Returns:
        A dictionary mapping each found header to its coordinates, or None if not enough headers are found.
    """
    lines = group_words_by_lines(words)
    best_row = None
    max_matches = 0
    
    # Identify the line that most likely contains the headers
    for line in lines:
        line_text = " ".join(w['text'].lower() for w in line)
        matches = sum(1 for header in target_headers if header.lower() in line_text)
        if matches > max_matches:
            max_matches = matches
            best_row = line
            
    if not best_row or max_matches < 2: 
        return None

    # Get coordinates for each header found in the best-matching row
    coords = {}
    for header in target_headers:
        found_words = [w for w in best_row if header.lower() in w['text'].lower()]
        if found_words:
            coords[header] = {
                'x0': min(w['x0'] for w in found_words),
                'x1': max(w['x1'] for w in found_words),
                'y0': min(w['y0'] for w in found_words),
                'y1': max(w['y1'] for w in found_words)
            }
    return coords

def calculate_zones(coords: Dict[str, Dict[str, float]], page_width: float) -> Dict[str, tuple[float, float]]:
    """
    Calculates the horizontal zones (column boundaries) based on header coordinates.

    Args:
        coords: A dictionary of header coordinates.
        page_width: The width of the PDF page.

    Returns:
        A dictionary mapping each header to its horizontal start and end coordinates.
    """
    if not coords:
        return {}

    # Sort headers by their horizontal position
    sorted_headers = sorted(
        [{'key': k, **v} for k, v in coords.items() if v],
        key=lambda h: h['x0']
    )
    
    zones = {}
    for i, header in enumerate(sorted_headers):
        # The start of the zone is the midpoint between the previous header's end and this one's start
        start = (sorted_headers[i-1]['x1'] + header['x0']) / 2 if i > 0 else 0
        # The end of the zone is the midpoint between this header's end and the next one's start
        end = (header['x1'] + sorted_headers[i+1]['x0']) / 2 if i < len(sorted_headers) - 1 else page_width
        zones[header['key']] = (start, end)
        
    return zones

def detect_footer_cutoff(words: List[Dict[str, Any]], bottom_margin_ratio: float = 0.85) -> Optional[float]:
    """
    Identifies the starting Y-coordinate of a page footer based on common footer keywords.

    Args:
        words: A list of all words on the page.
        bottom_margin_ratio: The portion of the page from the top to start searching for footers.

    Returns:
        The Y-coordinate of the first line of the footer, or None if no footer is detected.
    """
    if not words:
        return None
        
    max_y = max(w['y1'] for w in words)
    search_start_y = max_y * bottom_margin_ratio
    
    footer_keywords = ["stran", "osnovni kapital", "sodni register", "www", "identifikacijska"]
    lines = group_words_by_lines(words)
    
    # Find the first line in the bottom margin that contains a footer keyword
    for line in lines:
        if line[0]['y0'] > search_start_y:
            line_text = " ".join(w['text'].lower() for w in line)
            if any(key in line_text for key in footer_keywords):
                return line[0]['y0'] - 2  # Return with a small buffer
             
    return None

def extract_rows_from_page(words: List[Dict[str, Any]], zones: Dict, header_y: float, footer_y: Optional[float]) -> List[Dict[str, str]]:
    """
    Extracts structured data rows from a page by assigning words to zones (columns).

    Args:
        words: A list of all words on the page.
        zones: The column zones calculated from headers.
        header_y: The Y-coordinate below which to start considering data rows.
        footer_y: The Y-coordinate above which to stop considering data rows.

    Returns:
        A list of dictionaries, where each dictionary represents a row.
    """
    lines = group_words_by_lines(words)
    data_rows = []
    
    for line in lines:
        line_y = line[0]['y0']
        
        # Skip header and footer lines
        if line_y <= header_y or (footer_y and line_y >= footer_y):
            continue
            
        row_data = {key: [] for key in zones}
        for word in line:
            center_x = (word['x0'] + word['x1']) / 2
            for zone_key, (start, end) in zones.items():
                if start <= center_x < end:
                    row_data[zone_key].append(word['text'])
                    break
        
        # Consolidate words in each zone and add if the row is not empty
        clean_row = {k: " ".join(v).strip() for k, v in row_data.items()}
        if any(clean_row.values()):
            data_rows.append(clean_row)
            
    return data_rows

def clean_amount(amount_str: str) -> float:
    """
    Converts a formatted amount string (e.g., "1.234,56") to a float.

    Args:
        amount_str: The string representation of the amount.

    Returns:
        The amount as a float, or 0.0 if conversion fails.
    """
    if not amount_str:
        return 0.0
    # Standardize decimal and thousand separators, then remove non-numeric characters
    clean_str = amount_str.replace('.', '').replace(',', '.')
    clean_str = re.sub(r'[^\d.-]', '', clean_str)
    try:
        return float(clean_str)
    except ValueError:
        return 0.0

def parse_pdf(pdf_input: Any) -> pd.DataFrame:
    """
    Orchestrates the end-to-end process of parsing a PDF to extract transaction data.

    Args:
        pdf_input: A file path (str) or a file-like object for the PDF.

    Returns:
        A pandas DataFrame with structured transaction data ('date', 'amount', 'description').
    """
    all_pages = extract_words_from_pdf(pdf_input)
    if not all_pages:
        return pd.DataFrame(columns=['date', 'amount', 'description'])

    # Use a sample from the first page to detect the table structure
    sample_lines = group_words_by_lines(all_pages[0])
    text_sample = [[w['text'] for w in line] for line in sample_lines[:50]]
    
    print(f"DEBUG [Text Extraction]: Extracted sample text for LLM structure detection: {json.dumps(text_sample)}")
    
    config = detect_structure_with_llm(text_sample)
    print(f"DEBUG [LLM Output]: Received config from LLM: {json.dumps(config) if config else None}")
    if not config or 'mapping' not in config:
        raise ValueError("Failed to detect a valid table structure in the PDF. Check LLM configuration.")
        
    mapping = config['mapping']
    all_headers = config['all_headers']
    all_rows_data = []
    
    # Process each page using the detected structure
    for i, page_words in enumerate(all_pages):
        header_coords = find_header_coordinates(page_words, all_headers)
        if not header_coords:
            continue
            
        header_y = max(c['y1'] for c in header_coords.values() if c)
        footer_y = detect_footer_cutoff(page_words)
        page_width = max(w['x1'] for w in page_words) if page_words else 0
        zones = calculate_zones(header_coords, page_width)
        
        page_rows = extract_rows_from_page(page_words, zones, header_y, footer_y)
        all_rows_data.extend(page_rows)

    # Map the extracted raw rows to the final structured format
    processed_transactions = []
    for row in all_rows_data:
        new_transaction = {}
        date_parts = [row.get(h) for h in mapping.get('date', []) if row.get(h)]
        new_transaction['date'] = " ".join(date_parts)

        desc_parts = [row.get(h) for h in mapping.get('description', []) if row.get(h)]
        new_transaction['description'] = " ".join(desc_parts)

        # Handle amount based on whether it's in a single or double column
        if mapping.get('amount_mode') == 'single':
            amount_str = " ".join([row.get(h) for h in mapping.get('amount_single', []) if row.get(h)])
            amount = clean_amount(amount_str)
            if amount_str.strip().endswith('-'):
                amount = -abs(amount)
        else:
            neg_val = sum(clean_amount(row.get(h)) for h in mapping.get('amount_neg', []) if row.get(h))
            pos_val = sum(clean_amount(row.get(h)) for h in mapping.get('amount_pos', []) if row.get(h))
            amount = -abs(neg_val) if neg_val != 0 else abs(pos_val)
        
        new_transaction['amount'] = amount
        processed_transactions.append(new_transaction)

    # Post-process to merge multi-line descriptions and filter noise
    final_table = []
    current_transaction = None
    for tx in processed_transactions:
        # A row is considered the start of a new transaction if it has a non-zero amount
        if tx['amount'] != 0:
            if current_transaction:
                final_table.append(current_transaction)
            current_transaction = tx
        # If amount is zero, merge the description into the previous transaction
        elif current_transaction:
            current_transaction['description'] += " " + tx['description']
            
    if current_transaction:
        final_table.append(current_transaction)

    return pd.DataFrame(final_table)
