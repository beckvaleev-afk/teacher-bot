"""
Sheets logging is now handled inside services/drive.py
This file redirects to drive.py for backward compatibility.
"""
from services.drive import log_to_sheets

__all__ = ["log_to_sheets"]
