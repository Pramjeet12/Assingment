"""
seed_memory.py — Pre-seeds the Vanna 2.0 Agent Memory with 15+ known good
question-SQL pairs so the agent can learn from past successful interactions.

Run this after setup_database.py and before starting the API server.
"""

from vanna_setup import get_agent_memory, create_agent
from vanna import ToolContext
from vanna.core.user import User

# ─── Q&A Pairs covering all required categories ───────────────────────────────

QA_PAIRS = [
    # --- Patient queries ---
    {
        "question": "How many patients do we have?",
        "sql": "SELECT COUNT(*) AS total_patients FROM patients",
    },
    {
        "question": "List all patients from New York",
        "sql": "SELECT first_name, last_name, email, phone FROM patients WHERE city = 'New York'",
    },
    {
        "question": "How many male and female patients do we have?",
        "sql": "SELECT gender, COUNT(*) AS count FROM patients GROUP BY gender",
    },
    {
        "question": "Which city has the most patients?",
        "sql": "SELECT city, COUNT(*) AS patient_count FROM patients GROUP BY city ORDER BY patient_count DESC LIMIT 1",
    },

    # --- Doctor queries ---
    {
        "question": "List all doctors and their specializations",
        "sql": "SELECT name, specialization, department FROM doctors",
    },
    {
        "question": "Which doctor has the most appointments?",
        "sql": "SELECT d.name, COUNT(a.id) AS appointment_count FROM doctors d JOIN appointments a ON d.id = a.doctor_id GROUP BY d.id ORDER BY appointment_count DESC LIMIT 1",
    },
    {
        "question": "How many doctors are in each specialization?",
        "sql": "SELECT specialization, COUNT(*) AS doctor_count FROM doctors GROUP BY specialization ORDER BY doctor_count DESC",
    },

    # --- Appointment queries ---
    {
        "question": "Show me appointments for last month",
        "sql": "SELECT a.id, p.first_name, p.last_name, d.name AS doctor, a.appointment_date, a.status FROM appointments a JOIN patients p ON a.patient_id = p.id JOIN doctors d ON a.doctor_id = d.id WHERE a.appointment_date >= date('now', '-1 month') ORDER BY a.appointment_date DESC",
    },
    {
        "question": "How many cancelled appointments were there last quarter?",
        "sql": "SELECT COUNT(*) AS cancelled_count FROM appointments WHERE status = 'Cancelled' AND appointment_date >= date('now', '-3 months')",
    },
    {
        "question": "Show monthly appointment count for the past 6 months",
        "sql": "SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) AS appointment_count FROM appointments WHERE appointment_date >= date('now', '-6 months') GROUP BY month ORDER BY month",
    },

    # --- Financial queries ---
    {
        "question": "What is the total revenue?",
        "sql": "SELECT SUM(total_amount) AS total_revenue FROM invoices",
    },
    {
        "question": "Show revenue by doctor",
        "sql": "SELECT d.name, SUM(i.total_amount) AS total_revenue FROM invoices i JOIN appointments a ON a.patient_id = i.patient_id JOIN doctors d ON d.id = a.doctor_id GROUP BY d.name ORDER BY total_revenue DESC",
    },
    {
        "question": "Show unpaid invoices",
        "sql": "SELECT i.id, p.first_name, p.last_name, i.total_amount, i.paid_amount, i.status FROM invoices i JOIN patients p ON i.patient_id = p.id WHERE i.status IN ('Pending', 'Overdue') ORDER BY i.total_amount DESC",
    },
    {
        "question": "What is the average treatment cost by specialization?",
        "sql": "SELECT d.specialization, ROUND(AVG(t.cost), 2) AS avg_cost FROM treatments t JOIN appointments a ON t.appointment_id = a.id JOIN doctors d ON a.doctor_id = d.id GROUP BY d.specialization ORDER BY avg_cost DESC",
    },

    # --- Time-based queries ---
    {
        "question": "Show revenue trend by month",
        "sql": "SELECT strftime('%Y-%m', invoice_date) AS month, SUM(total_amount) AS monthly_revenue FROM invoices GROUP BY month ORDER BY month",
    },
    {
        "question": "Show patient registration trend by month",
        "sql": "SELECT strftime('%Y-%m', registered_date) AS month, COUNT(*) AS new_patients FROM patients GROUP BY month ORDER BY month",
    },

    # --- Complex queries ---
    {
        "question": "Top 5 patients by spending",
        "sql": "SELECT p.first_name, p.last_name, SUM(i.total_amount) AS total_spending FROM patients p JOIN invoices i ON p.id = i.patient_id GROUP BY p.id ORDER BY total_spending DESC LIMIT 5",
    },
    {
        "question": "What percentage of appointments are no-shows?",
        "sql": "SELECT ROUND(100.0 * SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) / COUNT(*), 2) AS noshow_percentage FROM appointments",
    },
]


def _make_tool_context():
    """Create a ToolContext for seeding memory."""
    memory = get_agent_memory()
    user = User(
        id="clinic_user",
        username="clinic_user",
        email="user@clinic.com",
        group_memberships=["clinic_users"],
        metadata={},
    )
    return ToolContext(
        user=user,
        conversation_id="seed_conversation",
        request_id="seed_request",
        agent_memory=memory,
        metadata={},
    )


async def seed_memory():
    """Seed the agent memory with known good Q&A pairs."""
    memory = get_agent_memory()
    context = _make_tool_context()

    print(f"Seeding {len(QA_PAIRS)} Q&A pairs into agent memory...")

    seeded = 0
    for i, pair in enumerate(QA_PAIRS, 1):
        try:
            await memory.save_tool_usage(
                question=pair["question"],
                tool_name="run_sql",
                args={"sql": pair["sql"]},
                context=context,
                success=True,
            )
            seeded += 1
            print(f"  [{i}/{len(QA_PAIRS)}] Seeded: {pair['question']}")
        except Exception as e:
            print(f"  [{i}/{len(QA_PAIRS)}] Warning: {e}")

    print(f"\nSuccessfully seeded {seeded}/{len(QA_PAIRS)} Q&A pairs into agent memory.")
    return seeded


def seed_memory_sync():
    """Synchronous wrapper."""
    import asyncio
    return asyncio.run(seed_memory())


if __name__ == "__main__":
    seed_memory_sync()
