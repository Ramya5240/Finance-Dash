"""
Unit tests for bank statement parsers
"""

import unittest
import pandas as pd
from io import StringIO
from datetime import datetime

from parsers.csv_parser import CSVParser
from parsers.bank_parser import BankParser

class TestCSVParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = CSVParser()
    
    def test_chase_csv_parsing(self):
        """Test Chase CSV format parsing"""
        chase_csv = """Transaction Date,Post Date,Description,Category,Type,Amount
01/15/2024,01/16/2024,STARBUCKS #1234,Food & Drink,Sale,-5.99
01/15/2024,01/16/2024,PAYROLL DEPOSIT,Payroll,Payment,3000.00"""
        
        # Create a mock uploaded file
        class MockFile:
            def __init__(self, content):
                self.content = content
                self.name = "chase_statement.csv"
            
            def read(self):
                return self.content.encode('utf-8')
        
        mock_file = MockFile(chase_csv)
        result = self.parser.parse_csv(mock_file)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertIn('date', result.columns)
        self.assertIn('description', result.columns)
        self.assertIn('amount', result.columns)
        self.assertIn('type', result.columns)

class TestBankParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = BankParser()
    
    def test_bank_detection(self):
        """Test bank format detection"""
        chase_content = "chase bank statement transaction"
        wells_content = "wells fargo account summary"
        
        self.assertEqual(self.parser.detect_bank_format(chase_content), 'chase')
        self.assertEqual(self.parser.detect_bank_format(wells_content), 'wells_fargo')
        self.assertEqual(self.parser.detect_bank_format("unknown bank"), 'unknown')

if __name__ == '__main__':
    unittest.main()
