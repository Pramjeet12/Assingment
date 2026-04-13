"""
sql_validator.py — Validates AI-generated SQL before execution.

Rules:
- Must be SELECT only (no INSERT, UPDATE, DELETE, DROP, ALTER, etc.)
- No dangerous keywords (EXEC, xp_, sp_, GRANT, REVOKE, SHUTDOWN)
- No system table access (sqlite_master, sqlite_sequence, etc.)
"""

import re
from typing import Tuple


# Keywords that indicate write/destructive operations
FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "REPLACE", "MERGE",
    "EXEC", "EXECUTE", "GRANT", "REVOKE", "SHUTDOWN",
    "ATTACH", "DETACH", "PRAGMA",
]

# Dangerous patterns (stored procedures, system commands)
DANGEROUS_PATTERNS = [
    r"\bxp_\w+",       # SQL Server extended stored procedures
    r"\bsp_\w+",       # SQL Server system stored procedures
    r"\binto\s+\w+",   # SELECT INTO (creates tables)
]

# System tables that should not be accessed
SYSTEM_TABLES = [
    "sqlite_master", "sqlite_sequence", "sqlite_stat1",
    "sqlite_stat2", "sqlite_stat3", "sqlite_stat4",
    "sqlite_temp_master",
]


def validate_sql(sql: str) -> Tuple[bool, str]:
    """
    Validate that the SQL query is safe to execute.

    Returns:
        (is_valid, error_message) — error_message is empty string if valid.
    """
    if not sql or not sql.strip():
        return False, "Empty SQL query."

    normalized = sql.strip()
    upper = normalized.upper()

    # Must start with SELECT or WITH (for CTEs)
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return False, "Only SELECT queries are allowed. Query must start with SELECT or WITH."

    # Check for forbidden keywords (as whole words)
    for keyword in FORBIDDEN_KEYWORDS:
        pattern = rf'\b{keyword}\b'
        if re.search(pattern, upper):
            return False, f"Forbidden keyword detected: {keyword}"

    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, upper):
            return False, f"Dangerous pattern detected in query."

    # Check for system table access
    lower = normalized.lower()
    for table in SYSTEM_TABLES:
        if table in lower:
            return False, f"Access to system table '{table}' is not allowed."

    # Check for multiple statements (semicolon-separated)
    # Remove semicolons inside string literals first
    cleaned = re.sub(r"'[^']*'", "", normalized)
    cleaned = re.sub(r'"[^"]*"', "", cleaned)
    if ";" in cleaned.rstrip(";"):
        return False, "Multiple SQL statements are not allowed."

    return True, ""
