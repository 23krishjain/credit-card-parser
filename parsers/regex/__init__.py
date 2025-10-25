"""Regex-based parsers for specific banks"""
from .combined_parsers import (
    HDFCParser,
    AxisParser,
    ICICIParser,
    IDFCParser,
    SyndicateParser
)

__all__ = [
    'HDFCParser',
    'AxisParser', 
    'ICICIParser',
    'IDFCParser',
    'SyndicateParser'
]