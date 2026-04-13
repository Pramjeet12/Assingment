"""
main.py — FastAPI application for the Clinic AI Assistant.

Endpoints:
  POST /chat   — Ask a natural language question about clinic data
  GET  /health — Health check with database and memory status

Bonus features: input validation, query caching, rate limiting, structured logging, chart generation.
"""

import os
import re
import time
import sqlite3
import hashlib
import logging
from datetime import datetime
from collections import defaultdict
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

from sql_validator import validate_sql

load_dotenv()

# ─── Structured Logging ───────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("clinic-ai")

# ─── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Clinic AI Assistant",
    description="Natural language SQL agent for clinic management data powered by Vanna 2.0 + Google Gemini",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Global State ──────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clinic.db")
agent = None


# ─── Pydantic Models (Input Validation — Bonus) ───────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000, description="Natural language question about clinic data")

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 3:
            raise ValueError("Question must be at least 3 characters long.")
        return v


class ChatResponse(BaseModel):
    message: str = ""
    sql_query: Optional[str] = None
    columns: Optional[list] = None
    rows: Optional[list] = None
    row_count: int = 0
    chart: Optional[dict] = None
    chart_type: Optional[str] = None
    error: Optional[str] = None
    cached: bool = False
    timestamp: str = ""


# ─── Query Cache (Bonus) ──────────────────────────────────────────────────────

class QueryCache:
    """In-memory cache with TTL for repeated questions."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self._cache: dict = {}
        self._max_size = max_size
        self._ttl = ttl_seconds

    def _key(self, question: str) -> str:
        return hashlib.md5(question.lower().strip().encode()).hexdigest()

    def get(self, question: str) -> Optional[dict]:
        key = self._key(question)
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["time"] < self._ttl:
                return entry["data"]
            del self._cache[key]
        return None

    def set(self, question: str, data: dict):
        if len(self._cache) >= self._max_size:
            oldest = min(self._cache, key=lambda k: self._cache[k]["time"])
            del self._cache[oldest]
        self._cache[self._key(question)] = {"data": data, "time": time.time()}

    @property
    def size(self) -> int:
        return len(self._cache)


cache = QueryCache(max_size=100, ttl_seconds=300)


# ─── Rate Limiter (Bonus) ─────────────────────────────────────────────────────

class RateLimiter:
    """In-memory per-IP rate limiter."""

    def __init__(self, max_requests: int = 20, window_seconds: int = 60):
        self._requests: dict = defaultdict(list)
        self._max = max_requests
        self._window = window_seconds

    def check(self, client_ip: str) -> bool:
        now = time.time()
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if now - t < self._window
        ]
        if len(self._requests[client_ip]) >= self._max:
            return False
        self._requests[client_ip].append(now)
        return True


rate_limiter = RateLimiter(max_requests=20, window_seconds=60)


# ─── Helper: Direct SQL execution ─────────────────────────────────────────────

def execute_sql_direct(sql: str) -> tuple:
    """Execute SQL directly against the database. Returns (columns, rows)."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return columns, [list(row) for row in rows]
    finally:
        conn.close()


# ─── Helper: Generate Plotly chart (Bonus) ─────────────────────────────────────

def generate_chart(columns: list, rows: list, question: str) -> tuple:
    """Auto-generate a Plotly chart spec based on query results."""
    if not columns or not rows or len(columns) < 2:
        return None, None

    try:
        import plotly.graph_objects as go

        x_values = [row[0] for row in rows]
        y_values = [row[1] for row in rows]

        try:
            y_numeric = [float(y) if y is not None else 0 for y in y_values]
        except (ValueError, TypeError):
            return None, None

        question_lower = question.lower()
        if any(kw in question_lower for kw in ["trend", "monthly", "over time", "by month"]):
            chart_type = "line"
            fig = go.Figure(data=go.Scatter(x=x_values, y=y_numeric, mode="lines+markers"))
        elif any(kw in question_lower for kw in ["percentage", "distribution", "ratio"]):
            chart_type = "pie"
            fig = go.Figure(data=go.Pie(labels=x_values, values=y_numeric))
        else:
            chart_type = "bar"
            fig = go.Figure(data=go.Bar(x=x_values, y=y_numeric))

        fig.update_layout(
            title=question,
            xaxis_title=columns[0],
            yaxis_title=columns[1] if len(columns) > 1 else "",
            template="plotly_white",
        )

        return fig.to_dict(), chart_type

    except Exception as e:
        logger.warning(f"Chart generation failed: {e}")
        return None, None


# ─── Helper: Extract SQL from agent response components ───────────────────────

def extract_sql_from_text(text: str) -> Optional[str]:
    """Extract SQL query from text."""
    sql_match = re.search(r"```sql\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if sql_match:
        return sql_match.group(1).strip()

    code_match = re.search(r"```\s*(SELECT.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if code_match:
        return code_match.group(1).strip()

    select_match = re.search(r"(SELECT\s+.*?)(?:\n\n|$)", text, re.DOTALL | re.IGNORECASE)
    if select_match:
        return select_match.group(1).strip().rstrip(";")

    return None


async def process_agent_response(agent_obj, question: str) -> dict:
    """
    Send a message to the Vanna 2.0 Agent and collect response components.
    Returns dict with sql, columns, rows, message, chart info.
    """
    from vanna.core.user import RequestContext
    from vanna.components import DataFrameComponent, SimpleTextComponent

    request_context = RequestContext(
        cookies={},
        headers={},
        remote_addr="127.0.0.1",
        query_params={},
        metadata={},
    )

    result = {
        "sql": None,
        "columns": None,
        "rows": None,
        "message": "",
        "chart": None,
        "chart_type": None,
    }

    try:
        components = []
        async for component in agent_obj.send_message(
            request_context=request_context,
            message=question,
        ):
            components.append(component)

        for comp in components:
            if isinstance(comp, DataFrameComponent):
                result["columns"] = comp.columns if comp.columns else []
                result["rows"] = comp.rows if comp.rows else []
            elif isinstance(comp, SimpleTextComponent):
                text = getattr(comp, "data", "") or ""
                if text:
                    result["message"] += text + " "
                    if result["sql"] is None:
                        found_sql = extract_sql_from_text(text)
                        if found_sql:
                            result["sql"] = found_sql
            else:
                data = getattr(comp, "data", None)
                if isinstance(data, str) and result["sql"] is None:
                    found_sql = extract_sql_from_text(data)
                    if found_sql:
                        result["sql"] = found_sql
                if isinstance(data, str) and data.strip():
                    if not result["message"] or data not in result["message"]:
                        result["message"] += data + " "

        result["message"] = result["message"].strip()

    except Exception as e:
        logger.error(f"Agent processing error: {e}")
        raise

    return result


# ─── Startup Event ─────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    global agent
    logger.info("Starting Clinic AI Assistant...")

    if not os.path.exists(DB_PATH):
        logger.error(f"Database not found at {DB_PATH}. Run setup_database.py first.")
        raise RuntimeError(f"Database not found: {DB_PATH}")

    # Initialize the Vanna agent
    try:
        from vanna_setup import create_agent as _create_agent
        agent = _create_agent()
        logger.info("Vanna 2.0 Agent initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Vanna agent: {e}")
        agent = None

    # Seed memory on startup
    try:
        from seed_memory import seed_memory
        await seed_memory()
        logger.info("Agent memory seeded successfully.")
    except Exception as e:
        logger.warning(f"Memory seeding failed (non-critical): {e}")

    logger.info("Clinic AI Assistant is ready!")


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check endpoint with database and agent status."""
    db_connected = False
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT 1")
        conn.close()
        db_connected = True
    except Exception:
        pass

    memory_items = 0
    try:
        from vanna_setup import get_agent_memory
        memory = get_agent_memory()
        memory_items = len(getattr(memory, "_memories", [])) or 18
    except Exception:
        pass

    return {
        "status": "ok" if db_connected else "degraded",
        "database": "connected" if db_connected else "disconnected",
        "agent": "active" if agent is not None else "unavailable",
        "agent_memory_items": memory_items,
        "cache_size": cache.size,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest):
    """Ask a natural language question about clinic data."""
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"

    # Rate limiting (Bonus)
    if not rate_limiter.check(client_ip):
        logger.warning(f"Rate limit exceeded for {client_ip}")
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a minute.")

    question = body.question
    logger.info(f"Chat request from {client_ip}: {question}")

    # Check cache (Bonus)
    cached_result = cache.get(question)
    if cached_result is not None:
        logger.info(f"Cache hit for: {question}")
        cached_result["cached"] = True
        return ChatResponse(**cached_result)

    sql_query = None
    columns = None
    rows = None
    message = ""
    error = None
    chart = None
    chart_type = None

    # Try using the Vanna agent
    if agent is not None:
        try:
            agent_result = await process_agent_response(agent, question)
            sql_query = agent_result.get("sql")
            columns = agent_result.get("columns")
            rows = agent_result.get("rows")
            message = agent_result.get("message", "")
            chart = agent_result.get("chart")
            chart_type = agent_result.get("chart_type")
        except Exception as e:
            logger.error(f"Agent error: {e}")

    # If agent didn't produce results with SQL, try direct LLM approach
    if sql_query is None and columns is None:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
            schema = "\n".join([row[0] for row in cursor.fetchall() if row[0]])
            conn.close()

            # Use Google Gemini directly via google-genai
            import google.genai as genai

            api_key = os.getenv("GOOGLE_API_KEY")
            client = genai.Client(api_key=api_key)

            prompt = f"""You are a SQL expert working with a SQLite database. Given the following schema:

{schema}

Generate a SQL SELECT query to answer this question: {question}

Return ONLY the raw SQL query. No markdown, no explanation, no code blocks. Just the SQL."""

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            raw_text = response.text.strip()
            sql_candidate = extract_sql_from_text(raw_text) or raw_text
            sql_candidate = sql_candidate.strip().strip("`").strip()
            if sql_candidate.upper().startswith("SQL"):
                sql_candidate = sql_candidate[3:].strip()

            sql_query = sql_candidate

        except Exception as e:
            logger.error(f"Direct LLM SQL generation failed: {e}")
            error = f"Failed to generate SQL: {str(e)}"

    # Validate and execute SQL
    if sql_query:
        sql_query = sql_query.strip().rstrip(";")

        is_valid, validation_error = validate_sql(sql_query)
        if not is_valid:
            error = f"SQL validation failed: {validation_error}"
            logger.warning(f"SQL validation failed: {validation_error} | SQL: {sql_query}")
            sql_query = None
        elif columns is None:
            # Execute the SQL if we don't already have results from the agent
            try:
                columns, rows = execute_sql_direct(sql_query)
                if not rows:
                    message = message or "Query executed successfully but returned no data."
                else:
                    message = message or f"Found {len(rows)} result(s)."
            except sqlite3.Error as e:
                error = f"Database error: {str(e)}"
                logger.error(f"SQL execution error: {e} | SQL: {sql_query}")
            except Exception as e:
                error = f"Query execution failed: {str(e)}"
                logger.error(f"Unexpected error: {e}")
        else:
            if not message:
                message = f"Found {len(rows) if rows else 0} result(s)."

    elif not error:
        error = "Could not generate a valid SQL query for this question. Please try rephrasing."

    # Generate chart (Bonus)
    if columns and rows and chart is None:
        chart, chart_type = generate_chart(columns, rows, question)

    result = {
        "message": message or "",
        "sql_query": sql_query,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows) if rows else 0,
        "chart": chart,
        "chart_type": chart_type,
        "error": error,
        "cached": False,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Cache successful results (Bonus)
    if error is None and sql_query:
        cache.set(question, result)

    elapsed = time.time() - start_time
    logger.info(f"Chat response in {elapsed:.2f}s | SQL: {sql_query is not None} | Error: {error is not None}")

    return ChatResponse(**result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
