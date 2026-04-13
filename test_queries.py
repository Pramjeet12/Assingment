"""
test_queries.py — Run all 20 test questions against the /chat endpoint
and output results for RESULTS.md
"""

import json
import time
import requests

BASE_URL = "http://localhost:8000"

QUESTIONS = [
    "How many patients do we have?",
    "List all doctors and their specializations",
    "Show me appointments for last month",
    "Which doctor has the most appointments?",
    "What is the total revenue?",
    "Show revenue by doctor",
    "How many cancelled appointments last quarter?",
    "Top 5 patients by spending",
    "Average treatment cost by specialization",
    "Show monthly appointment count for the past 6 months",
    "Which city has the most patients?",
    "List patients who visited more than 3 times",
    "Show unpaid invoices",
    "What percentage of appointments are no-shows?",
    "Show the busiest day of the week for appointments",
    "Revenue trend by month",
    "Average appointment duration by doctor",
    "List patients with overdue invoices",
    "Compare revenue between departments",
    "Show patient registration trend by month",
]

def run_tests():
    passed = 0
    failed = 0
    results = []

    for i, question in enumerate(QUESTIONS, 1):
        print(f"\n{'='*60}")
        print(f"Q{i}: {question}")
        print(f"{'='*60}")

        try:
            start = time.time()
            resp = requests.post(
                f"{BASE_URL}/chat",
                json={"question": question},
                timeout=120,
            )
            elapsed = time.time() - start

            if resp.status_code == 200:
                data = resp.json()
                sql = data.get("sql_query")
                error = data.get("error")
                row_count = data.get("row_count", 0)
                columns = data.get("columns", [])
                rows = data.get("rows", [])
                chart_type = data.get("chart_type")

                if sql and not error:
                    passed += 1
                    status = "PASS"
                else:
                    failed += 1
                    status = "FAIL"

                print(f"Status: {status}")
                print(f"SQL: {sql}")
                print(f"Rows: {row_count}")
                if error:
                    print(f"Error: {error}")
                if rows and len(rows) <= 5:
                    print(f"Results: {json.dumps(rows, indent=2)}")
                elif rows:
                    print(f"Results (first 3): {json.dumps(rows[:3], indent=2)}")
                if chart_type:
                    print(f"Chart: {chart_type}")
                print(f"Time: {elapsed:.2f}s")

                results.append({
                    "num": i,
                    "question": question,
                    "sql": sql,
                    "status": status,
                    "row_count": row_count,
                    "columns": columns,
                    "rows_sample": rows[:3] if rows else [],
                    "error": error,
                    "chart_type": chart_type,
                    "time": f"{elapsed:.2f}s",
                })
            else:
                failed += 1
                print(f"HTTP Error: {resp.status_code}")
                results.append({
                    "num": i,
                    "question": question,
                    "sql": None,
                    "status": "FAIL",
                    "row_count": 0,
                    "columns": [],
                    "rows_sample": [],
                    "error": f"HTTP {resp.status_code}: {resp.text}",
                    "chart_type": None,
                    "time": f"{elapsed:.2f}s",
                })

        except Exception as e:
            failed += 1
            print(f"Exception: {e}")
            results.append({
                "num": i,
                "question": question,
                "sql": None,
                "status": "FAIL",
                "row_count": 0,
                "columns": [],
                "rows_sample": [],
                "error": str(e),
                "chart_type": None,
                "time": "N/A",
            })

    print(f"\n\n{'='*60}")
    print(f"SUMMARY: {passed}/{len(QUESTIONS)} passed, {failed}/{len(QUESTIONS)} failed")
    print(f"{'='*60}")
    with open("test_results.json", "w") as f:
        json.dump({"passed": passed, "failed": failed, "total": len(QUESTIONS), "results": results}, f, indent=2)

    return results, passed, failed


if __name__ == "__main__":
    run_tests()
