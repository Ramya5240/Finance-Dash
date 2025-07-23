import pandas as pd
import io
from datetime import datetime

class CSVParser:
    """Parser for CSV bank statements"""
    
    def __init__(self):
        self.bank_column_mappings = {
            'chase': {
                'date': ['Transaction Date', 'Date'],
                'description': ['Description'],
                'amount': ['Amount'],
                'type': ['Type']
            },
            'wells_fargo': {
                'date': ['Date'],
                'description': ['Description'],
                'amount': ['Amount'],
                'type': ['Type']
            },
            'bank_of_america': {
                'date': ['Date'],
                'description': ['Description'],
                'amount': ['Amount'],
                'type': ['Type']
            },
            'citibank': {
                'date': ['Date'],
                'description': ['Description'], 
                'amount': ['Debit', 'Credit'],
                'type': ['Type']
            },
            'hdfc': {
                'date': ['Date'],
                'description': ['Narration', 'Description'],
                'amount': ['Debit', 'Credit', 'Amount'],
                'type': ['Type']
            },
            'axis': {
                'date': ['Tran Date', 'Date'],
                'description': ['Particulars', 'Description'],
                'amount': ['Debit', 'Credit', 'Amount'],
                'type': ['Type']
            }
        }
    
    def parse_csv(self, uploaded_file):
        """Parse CSV bank statement"""
        try:
            # Read CSV file
            csv_content = uploaded_file.read()
            df = pd.read_csv(io.StringIO(csv_content.decode('utf-8')))
            
            # Detect bank format from columns
            bank_format = self._detect_bank_from_columns(df.columns.tolist())
            
            if bank_format == 'unknown':
                return self._parse_generic_csv(df)
            
            # Parse based on detected bank format
            return self._parse_bank_specific_csv(df, bank_format)
            
        except Exception as e:
            raise Exception(f"Error parsing CSV: {str(e)}")
    
    def _detect_bank_from_columns(self, columns):
        """Detect bank from CSV column names"""
        columns_lower = [col.lower() for col in columns]
        columns_str = ' '.join(columns_lower)
        
        # Check for specific bank patterns in column names
        if 'transaction date' in columns_str or any('chase' in col for col in columns_lower):
            return 'chase'
        elif any('wells' in col for col in columns_lower):
            return 'wells_fargo'
        elif any('bofa' in col or 'bankofamerica' in col for col in columns_lower):
            return 'bank_of_america'
        elif any('citi' in col for col in columns_lower):
            return 'citibank'
        elif 'narration' in columns_str or any('hdfc' in col for col in columns_lower):
            return 'hdfc'
        elif 'particulars' in columns_str or 'tran date' in columns_str:
            return 'axis'
        
        return 'unknown'
    
    def _parse_bank_specific_csv(self, df, bank_format):
        """Parse CSV based on specific bank format"""
        column_mapping = self.bank_column_mappings.get(bank_format, {})
        
        transactions = []
        
        for _, row in df.iterrows():
            try:
                # Extract date
                date_col = self._find_column(row, column_mapping.get('date', []))
                if not date_col:
                    continue
                
                date = self._parse_date(row[date_col])
                if not date:
                    continue
                
                # Extract description
                desc_col = self._find_column(row, column_mapping.get('description', []))
                description = str(row[desc_col]) if desc_col else 'Unknown'
                
                # Extract amount and type
                amount, trans_type = self._extract_amount_and_type(row, column_mapping, bank_format)
                
                if amount is not None and amount != 0:
                    transactions.append({
                        'date': date,
                        'description': description.strip(),
                        'amount': abs(amount),
                        'type': trans_type,
                        'bank': bank_format
                    })
                    
            except Exception as e:
                continue  # Skip malformed rows
        
        return pd.DataFrame(transactions)
    
    def _parse_generic_csv(self, df):
        """Generic CSV parsing for unknown formats"""
        transactions = []
        
        # Try to identify columns by common names
        date_cols = [col for col in df.columns if any(word in col.lower() for word in ['date', 'time'])]
        desc_cols = [col for col in df.columns if any(word in col.lower() for word in ['description', 'narration', 'particulars', 'memo'])]
        amount_cols = [col for col in df.columns if any(word in col.lower() for word in ['amount', 'debit', 'credit'])]
        
        if not date_cols or not desc_cols or not amount_cols:
            raise Exception("Could not identify required columns in CSV")
        
        date_col = date_cols[0]
        desc_col = desc_cols[0]
        
        for _, row in df.iterrows():
            try:
                # Parse date
                date = self._parse_date(row[date_col])
                if not date:
                    continue
                
                # Get description
                description = str(row[desc_col])
                
                # Try to get amount from different columns
                amount = None
                trans_type = 'debit'
                
                for amount_col in amount_cols:
                    val = row[amount_col]
                    if pd.notna(val) and str(val).strip() != '':
                        try:
                            amount = float(str(val).replace(',', '').replace('$', '').replace('₹', ''))
                            if 'credit' in amount_col.lower():
                                trans_type = 'credit'
                            elif amount > 0 and 'debit' not in amount_col.lower():
                                trans_type = 'credit'
                            break
                        except ValueError:
                            continue
                
                if amount is not None and amount != 0:
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
    
    def _find_column(self, row, possible_names):
        """Find the first existing column from a list of possible names"""
        for name in possible_names:
            if name in row.index:
                return name
        return None
    
    def _extract_amount_and_type(self, row, column_mapping, bank_format):
        """Extract amount and transaction type from row"""
        amount_cols = column_mapping.get('amount', [])
        
        # Handle banks with separate debit/credit columns
        if bank_format in ['citibank', 'hdfc', 'axis']:
            debit_val = None
            credit_val = None
            
            for col in amount_cols:
                if col in row.index:
                    val = row[col]
                    if pd.notna(val) and str(val).strip() != '':
                        try:
                            amount = float(str(val).replace(',', '').replace('$', '').replace('₹', ''))
                            if 'debit' in col.lower():
                                debit_val = amount
                            elif 'credit' in col.lower():
                                credit_val = amount
                            else:
                                # Generic amount column
                                return abs(amount), 'debit' if amount < 0 else 'credit'
                        except ValueError:
                            continue
            
            if debit_val is not None and debit_val > 0:
                return debit_val, 'debit'
            elif credit_val is not None and credit_val > 0:
                return credit_val, 'credit'
        
        # Handle banks with single amount column
        for col in amount_cols:
            if col in row.index:
                val = row[col]
                if pd.notna(val) and str(val).strip() != '':
                    try:
                        amount = float(str(val).replace(',', '').replace('$', '').replace('₹', ''))
                        return abs(amount), 'debit' if amount < 0 else 'credit'
                    except ValueError:
                        continue
        
        return None, 'debit'
    
    def _parse_date(self, date_str):
        """Parse date string with flexible formats"""
        if pd.isna(date_str):
            return None
        
        date_str = str(date_str).strip()
        
        date_formats = [
            '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y',
            '%m-%d-%Y', '%d-%m-%Y', '%Y/%m/%d',
            '%m/%d/%y', '%d/%m/%y', '%y-%m-%d'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None

