"""
DocuPulse v1.2 - Autonomous Invoice, Receipt, AR Chaser & Financial Ledger Engine
Zero-dependency local-first financial document parser, duplicate/math anomaly detector,
progressive Accounts Receivable (AR) chaser, and expense categorizer.
"""

from docupulse.extractor import InvoiceExtractor
from docupulse.ledger import FinancialLedger
from docupulse.receivables import ReceivablesChaser
from docupulse.tax_mapper import ExpenseCategorizer

__product__ = "DocuPulse"
__version__ = "1.2.0"
__tagline__ = "Autonomous Invoice, Receipt & Financial Ledger Extraction Engine"

__all__ = [
    "InvoiceExtractor",
    "FinancialLedger",
    "ReceivablesChaser",
    "ExpenseCategorizer",
    "__product__",
    "__version__",
    "__tagline__"
]
