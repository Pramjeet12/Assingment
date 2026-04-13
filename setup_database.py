"""
setup_database.py — Creates the clinic.db SQLite database with schema and realistic dummy data.

Tables: patients, doctors, appointments, treatments, invoices
"""

import sqlite3
import random
from datetime import datetime, timedelta

random.seed(42)

DB_PATH = "clinic.db"

# ─── Name and data pools ───────────────────────────────────────────────────────

FIRST_NAMES_MALE = [
    "James", "Robert", "John", "Michael", "David", "William", "Richard",
    "Joseph", "Thomas", "Christopher", "Daniel", "Matthew", "Anthony",
    "Mark", "Steven", "Andrew", "Paul", "Joshua", "Kenneth", "Kevin",
]

FIRST_NAMES_FEMALE = [
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth",
    "Susan", "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty",
    "Margaret", "Sandra", "Ashley", "Dorothy", "Kimberly", "Emily", "Donna",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson",
]

CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
    "Philadelphia", "San Antonio", "San Diego", "Dallas", "Mumbai",
]

SPECIALIZATIONS = ["Dermatology", "Cardiology", "Orthopedics", "General", "Pediatrics"]

DOCTOR_NAMES = [
    ("Rajesh", "Sharma"), ("Priya", "Patel"), ("Amit", "Gupta"),
    ("Sneha", "Reddy"), ("Vikram", "Singh"), ("Anita", "Desai"),
    ("Suresh", "Kumar"), ("Meera", "Nair"), ("Arjun", "Mehta"),
    ("Kavita", "Joshi"), ("Rahul", "Verma"), ("Deepa", "Iyer"),
    ("Sanjay", "Rao"), ("Pooja", "Mishra"), ("Nikhil", "Chopra"),
]

DEPARTMENTS = {
    "Dermatology": "Dermatology",
    "Cardiology": "Cardiology",
    "Orthopedics": "Orthopedics",
    "General": "General Medicine",
    "Pediatrics": "Pediatrics",
}

TREATMENT_NAMES = [
    "Blood Test", "X-Ray", "MRI Scan", "ECG", "Ultrasound",
    "Physical Therapy", "Vaccination", "Prescription Refill",
    "Minor Surgery", "Consultation", "CT Scan", "Dental Cleaning",
    "Eye Exam", "Allergy Test", "Skin Biopsy", "Wound Dressing",
    "Physiotherapy Session", "Lab Panel", "Cardiac Stress Test", "Bone Density Scan",
]

TREATMENT_COST_RANGES = {
    "Blood Test": (50, 200), "X-Ray": (100, 500), "MRI Scan": (800, 3000),
    "ECG": (100, 400), "Ultrasound": (200, 800), "Physical Therapy": (100, 500),
    "Vaccination": (50, 300), "Prescription Refill": (50, 150),
    "Minor Surgery": (1000, 5000), "Consultation": (100, 300),
    "CT Scan": (500, 2500), "Dental Cleaning": (100, 400),
    "Eye Exam": (75, 250), "Allergy Test": (100, 500),
    "Skin Biopsy": (300, 1500), "Wound Dressing": (50, 200),
    "Physiotherapy Session": (80, 300), "Lab Panel": (100, 600),
    "Cardiac Stress Test": (500, 2000), "Bone Density Scan": (200, 800),
}

APPOINTMENT_NOTES = [
    "Routine checkup", "Follow-up visit", "Patient reports improvement",
    "Referred to specialist", "Lab results pending", "Prescribed medication",
    "Needs further testing", "Patient stable", "Review in 2 weeks",
    "Symptoms subsiding", None, None, None,  # Some NULL notes
]


# ─── Helper functions ──────────────────────────────────────────────────────────

def random_date(start: datetime, end: datetime) -> str:
    """Return a random date string between start and end."""
    delta = end - start
    random_days = random.randint(0, delta.days)
    dt = start + timedelta(days=random_days)
    return dt.strftime("%Y-%m-%d")


def random_datetime(start: datetime, end: datetime) -> str:
    """Return a random datetime string between start and end."""
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    dt = start + timedelta(seconds=random_seconds)
    # Set time to business hours (8am-5pm)
    hour = random.randint(8, 17)
    minute = random.choice([0, 15, 30, 45])
    dt = dt.replace(hour=hour, minute=minute, second=0)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def random_phone():
    """Generate a random phone number or None."""
    if random.random() < 0.1:  # 10% chance of NULL
        return None
    return f"+1-{random.randint(200,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}"


def random_email(first_name, last_name):
    """Generate an email or None."""
    if random.random() < 0.1:  # 10% chance of NULL
        return None
    domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "email.com"]
    return f"{first_name.lower()}.{last_name.lower()}@{random.choice(domains)}"


# ─── Table creation ────────────────────────────────────────────────────────────

def create_tables(conn: sqlite3.Connection):
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS invoices")
    cursor.execute("DROP TABLE IF EXISTS treatments")
    cursor.execute("DROP TABLE IF EXISTS appointments")
    cursor.execute("DROP TABLE IF EXISTS doctors")
    cursor.execute("DROP TABLE IF EXISTS patients")

    cursor.execute("""
        CREATE TABLE patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            date_of_birth DATE,
            gender TEXT,
            city TEXT,
            registered_date DATE
        )
    """)

    cursor.execute("""
        CREATE TABLE doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT,
            department TEXT,
            phone TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            doctor_id INTEGER,
            appointment_date DATETIME,
            status TEXT,
            notes TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE treatments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER,
            treatment_name TEXT,
            cost REAL,
            duration_minutes INTEGER,
            FOREIGN KEY (appointment_id) REFERENCES appointments(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            invoice_date DATE,
            total_amount REAL,
            paid_amount REAL,
            status TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    """)

    conn.commit()


# ─── Data insertion ────────────────────────────────────────────────────────────

def insert_patients(conn: sqlite3.Connection, count: int = 200):
    cursor = conn.cursor()
    now = datetime.now()
    reg_start = now - timedelta(days=365 * 3)

    for _ in range(count):
        gender = random.choice(["M", "F"])
        if gender == "M":
            first_name = random.choice(FIRST_NAMES_MALE)
        else:
            first_name = random.choice(FIRST_NAMES_FEMALE)
        last_name = random.choice(LAST_NAMES)
        email = random_email(first_name, last_name)
        phone = random_phone()
        dob = random_date(datetime(1950, 1, 1), datetime(2010, 12, 31))
        city = random.choice(CITIES)
        registered_date = random_date(reg_start, now)

        cursor.execute(
            "INSERT INTO patients (first_name, last_name, email, phone, date_of_birth, gender, city, registered_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (first_name, last_name, email, phone, dob, gender, city, registered_date),
        )
    conn.commit()


def insert_doctors(conn: sqlite3.Connection):
    cursor = conn.cursor()
    for i, (first, last) in enumerate(DOCTOR_NAMES):
        spec = SPECIALIZATIONS[i % len(SPECIALIZATIONS)]
        dept = DEPARTMENTS[spec]
        phone = random_phone()
        name = f"Dr. {first} {last}"
        cursor.execute(
            "INSERT INTO doctors (name, specialization, department, phone) VALUES (?, ?, ?, ?)",
            (name, spec, dept, phone),
        )
    conn.commit()


def insert_appointments(conn: sqlite3.Connection, count: int = 500):
    cursor = conn.cursor()
    now = datetime.now()
    start = now - timedelta(days=365)

    # Make some patients repeat visitors (weighted selection)
    # First 30 patients have higher probability
    patient_weights = [5 if i < 30 else 1 for i in range(200)]
    patient_ids = list(range(1, 201))

    # Make some doctors busier
    doctor_weights = [3 if i < 5 else 1 for i in range(15)]
    doctor_ids = list(range(1, 16))

    statuses = ["Scheduled", "Completed", "Cancelled", "No-Show"]
    status_weights = [15, 55, 20, 10]  # Completed most common

    for _ in range(count):
        patient_id = random.choices(patient_ids, weights=patient_weights, k=1)[0]
        doctor_id = random.choices(doctor_ids, weights=doctor_weights, k=1)[0]
        appt_date = random_datetime(start, now)
        status = random.choices(statuses, weights=status_weights, k=1)[0]
        notes = random.choice(APPOINTMENT_NOTES)

        cursor.execute(
            "INSERT INTO appointments (patient_id, doctor_id, appointment_date, status, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (patient_id, doctor_id, appt_date, status, notes),
        )
    conn.commit()


def insert_treatments(conn: sqlite3.Connection, count: int = 350):
    cursor = conn.cursor()

    # Get completed appointment IDs
    cursor.execute("SELECT id FROM appointments WHERE status = 'Completed'")
    completed_ids = [row[0] for row in cursor.fetchall()]

    if not completed_ids:
        print("Warning: No completed appointments found for treatments.")
        return

    for _ in range(count):
        appt_id = random.choice(completed_ids)
        treatment = random.choice(TREATMENT_NAMES)
        cost_range = TREATMENT_COST_RANGES[treatment]
        cost = round(random.uniform(cost_range[0], cost_range[1]), 2)
        duration = random.choice([15, 20, 30, 45, 60, 90, 120])

        cursor.execute(
            "INSERT INTO treatments (appointment_id, treatment_name, cost, duration_minutes) "
            "VALUES (?, ?, ?, ?)",
            (appt_id, treatment, cost, duration),
        )
    conn.commit()


def insert_invoices(conn: sqlite3.Connection, count: int = 300):
    cursor = conn.cursor()
    now = datetime.now()
    start = now - timedelta(days=365)

    # Get patients who have appointments
    cursor.execute("SELECT DISTINCT patient_id FROM appointments")
    patient_ids = [row[0] for row in cursor.fetchall()]

    statuses = ["Paid", "Pending", "Overdue"]
    status_weights = [50, 30, 20]

    for _ in range(count):
        patient_id = random.choice(patient_ids)
        invoice_date = random_date(start, now)
        total_amount = round(random.uniform(50, 5000), 2)
        status = random.choices(statuses, weights=status_weights, k=1)[0]

        if status == "Paid":
            paid_amount = total_amount
        elif status == "Pending":
            paid_amount = round(random.uniform(0, total_amount * 0.5), 2)
        else:  # Overdue
            paid_amount = round(random.uniform(0, total_amount * 0.3), 2)

        cursor.execute(
            "INSERT INTO invoices (patient_id, invoice_date, total_amount, paid_amount, status) "
            "VALUES (?, ?, ?, ?, ?)",
            (patient_id, invoice_date, total_amount, paid_amount, status),
        )
    conn.commit()


# ─── Main ──────────────────────────────────────────────────────────────────────

def create_database(db_path: str = DB_PATH):
    """Create the clinic database with schema and dummy data."""
    conn = sqlite3.connect(db_path)

    print("Creating tables...")
    create_tables(conn)

    print("Inserting patients...")
    insert_patients(conn, 200)

    print("Inserting doctors...")
    insert_doctors(conn)

    print("Inserting appointments...")
    insert_appointments(conn, 500)

    print("Inserting treatments...")
    insert_treatments(conn, 350)

    print("Inserting invoices...")
    insert_invoices(conn, 300)

    # Print summary
    cursor = conn.cursor()
    tables = ["patients", "doctors", "appointments", "treatments", "invoices"]
    counts = {}
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cursor.fetchone()[0]

    conn.close()

    print(f"\n{'='*50}")
    print(f"Database '{db_path}' created successfully!")
    print(f"Created {counts['patients']} patients, "
          f"{counts['doctors']} doctors, "
          f"{counts['appointments']} appointments, "
          f"{counts['treatments']} treatments, "
          f"{counts['invoices']} invoices")
    print(f"{'='*50}")


if __name__ == "__main__":
    create_database()
