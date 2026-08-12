"""Locale-independent English date formatting helpers.

Note: do NOT use ``calendar.month_abbr`` for display — it is locale-aware
in Python 3.12 (derived from the active LC_TIME locale). This hardcoded
list is the stable English source of truth.
"""

MONTH_ABBR_EN = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
