import pandas as pd
import io
from .pdf_parser import PDFParser
from .csv_parser import CSVParser

class BankParser:
    """Main parser class that handles different bank formats"""
    
    def __init__(self):
        self.pdf_parser = PDFParser()
        self.csv_parser = CSVParser()
        
    def parse_file(self, uploaded_file):
        """Parse uploaded file based on its type and bank format"""
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        try:
            if file_extension == 'pdf':
                return self.pdf_parser.parse_pdf(uploaded_file)
            elif file_extension == 'csv':
                return self.csv_parser.parse_csv(uploaded_file)
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
                
        except Exception as e:
            raise Exception(f"Error parsing file {uploaded_file.name}: {str(e)}")
    
    def detect_bank_format(self, content):
        """Detect bank format from file content"""
        content_lower = content.lower()
        
        # US Banks
        if 'chase' in content_lower or 'jpmorgan' in content_lower:
            return 'chase'
        elif 'wells fargo' in content_lower or 'wellsfargo' in content_lower:
            return 'wells_fargo'
        elif 'bank of america' in content_lower or 'bankofamerica' in content_lower:
            return 'bank_of_america'
        elif 'citibank' in content_lower or 'citi' in content_lower:
            return 'citibank'
        
        # International Banks
        elif 'hdfc' in content_lower:
            return 'hdfc'
        elif 'axis' in content_lower:
            return 'axis'
        
        return 'unknown'

