import pandas as pd
import pdfplumber
import re
from datetime import datetime
import io

class PDFParser:
    """Parser for PDF bank statements"""
    
    def __init__(self):
        self.bank_patterns = {
            'chase': {
                'transaction_pattern': r'(\d{2}/\d{2})\s+(.+?)\s+(-?\$?[\d,]+\.?\d*)',
                'date_format': '%m/%d'
            },
            'wells_fargo': {
                'transaction_pattern': r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?\$?[\d,]+\.?\d*)',
                'date_format': '%m/%d/%Y'
            },
            'bank_of_america': {
                'transaction_pattern': r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?\$?[\d,]+\.?\d*)',
                'date_format': '%m/%d/%Y'
            },
            'citibank': {
                'transaction_pattern': r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?\$?[\d,]+\.?\d*)',
                'date_format': '%m/%d/%Y'
            },
            'hdfc': {
                'transaction_pattern': r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?\₹?[\d,]+\.?\d*)',
                'date_format': '%d/%m/%Y'
            },
            'axis': {
                'transaction_pattern': r'(\d{2}-\d{2}-\d{4})\s+(.+?)\s+(-?\₹?[\d,]+\.?\d*)',
                'date_format': '%d-%m-%Y'
            }
        }
    
    def parse_pdf(self, uploaded_file):
        """Parse PDF bank statement"""
        try:
            # Read PDF content
            pdf_bytes = uploaded_file.read()
            
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                full_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n"
            
            # Detect bank format
            bank_format = self._detect_bank_from_pdf(full_text)
            
            if bank_format == 'unknown':
                # Try generic parsing
                return self._parse_generic_pdf(full_text)
            
            # Parse based on detected bank format
            return self._parse_bank_specific_pdf(full_text, bank_format)
            
        except Exception as e:
            raise Exception(f"Error parsing PDF: {str(e)}")
    
    def _detect_bank_from_pdf(self, text):
        """Detect bank from PDF content"""
        text_lower = text.lower()
        
        if 'chase' in text_lower or 'jpmorgan' in text_lower:
            return 'chase'
        elif 'wells fargo' in text_lower:
            return 'wells_fargo'
        elif 'bank of america' in text_lower:
            return 'bank_of_america'
        elif 'citibank' in text_lower or 'citi' in text_lower:
            return 'citibank'
        elif 'hdfc' in text_lower:
            return 'hdfc'
        elif 'axis' in text_lower:
            return 'axis'
        
        return 'unknown'
    
    def _parse_bank_specific_pdf(self, text, bank_format):
        """Parse PDF based on specific bank format"""
        pattern_info = self.bank_patterns.get(bank_format)
        if not pattern_info:
            return self._parse_generic_pdf(text)
        
        transactions = []
        pattern = pattern_info['transaction_pattern']
        date_format = pattern_info['date_format']
        
        matches = re.findall(pattern, text, re.MULTILINE)
        
        for match in matches:
            try:
                date_str, description, amount_str = match
                
                # Parse date
                if len(date_str.split('/')) == 2:  # MM/DD format
                    current_year = datetime.now().year
                    date = datetime.strptime(f"{date_str}/{current_year}", f"{date_format}/{current_year}")
                else:
                    date = datetime.strptime(date_str, date_format)
                
                # Parse amount
                amount = self._parse_amount(amount_str)
                
                # Determine transaction type
                trans_type = 'debit' if amount < 0 else 'credit'
                
                transactions.append({
                    'date': date,
                    'description': description.strip(),
                    'amount': abs(amount),
                    'type': trans_type,
                    'bank': bank_format
                })
                
            except Exception as e:
                continue  # Skip malformed transactions
        
        return pd.DataFrame(transactions)
    
    def _parse_generic_pdf(self, text):
        """Generic PDF parsing for unknown formats"""
        transactions = []
        
        # Generic pattern for date, description, amount
        patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+(-?\$?[\d,]+\.?\d*)',
            r'(\d{1,2}/\d{1,2})\s+(.+?)\s+(-?\$?[\d,]+\.?\d*)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            
            for match in matches:
                try:
                    date_str, description, amount_str = match
                    
                    # Parse date
                    date = self._parse_date_flexible(date_str)
                    if not date:
                        continue
                    
                    # Parse amount
                    amount = self._parse_amount(amount_str)
                    
                    # Determine transaction type
                    trans_type = 'debit' if amount < 0 else 'credit'
                    
                    transactions.append({
                        'date': date,
                        'description': description.strip(),
                        'amount': abs(amount),
                        'type': trans_type,
                        'bank': 'unknown'
                    })
                    
                except Exception as e:
                    continue
        
        return pd.DataFrame(transactions)
    
    def _parse_amount(self, amount_str):
        """Parse amount string to float"""
        # Remove currency symbols and spaces
        cleaned = re.sub(r'[^\d.,-]', '', amount_str)
        cleaned = cleaned.replace(',', '')
        
        # Handle negative amounts
        is_negative = '-' in amount_str or '(' in amount_str
        
        try:
            amount = float(cleaned)
            return -amount if is_negative else amount
        except ValueError:
            return 0.0
    
    def _parse_date_flexible(self, date_str):
        """Parse date with flexible formats"""
        date_formats = [
            '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d',
            '%m-%d-%Y', '%d-%m-%Y',
            '%m/%d', '%d/%m'
        ]
        
        for fmt in date_formats:
            try:
                if len(date_str.split('/')) == 2 or len(date_str.split('-')) == 2:
                    # Add current year for MM/DD or DD/MM format
                    current_year = datetime.now().year
                    if '/' in fmt:
                        date_str_with_year = f"{date_str}/{current_year}"
                        fmt_with_year = f"{fmt}/{current_year}"
                    else:
                        date_str_with_year = f"{date_str}-{current_year}"
                        fmt_with_year = f"{fmt}-{current_year}"
                    return datetime.strptime(date_str_with_year, fmt_with_year)
                else:
                    return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None

