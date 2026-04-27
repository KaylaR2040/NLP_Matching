"""
Seed fake demo mentors into the database.

These mentors are fictional — all names, emails, companies, and details are made up.
They are tagged with is_demo=TRUE so the public demo account (eceaccount) only
sees this fake data, never real mentor information.

Run:
    python wrapper/backend/scripts/seed_demo_mentors.py
    python wrapper/backend/scripts/seed_demo_mentors.py --clear   # remove demo mentors first
    python wrapper/backend/scripts/seed_demo_mentors.py --dry-run  # preview only
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path

# Allow running from repo root without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    import psycopg
except ImportError:
    print("ERROR: psycopg not installed. Run: pip install psycopg[binary]")
    sys.exit(1)

DEMO_MENTORS = [
    {
        "first_name": "Alex",
        "last_name": "Rivera",
        "email": "alex.rivera.demo@example.com",
        "current_job_title": "Software Engineer II",
        "current_company": "Cloudbridge Technologies",
        "current_city": "Raleigh",
        "current_state": "NC",
        "current_location": "Raleigh, NC",
        "degrees_text": "BS Electrical and Computer Engineering, NC State University, 2019",
        "industry_focus_area": "Software Engineering",
        "professional_experience": "3 years of backend development in Python and Go. Previously interned at a cloud infrastructure startup.",
        "about_yourself": "I enjoy mentoring students transitioning into software roles from ECE backgrounds.",
        "students_interested": 2,
        "preferred_contact_method": "Email",
        "is_active": True,
    },
    {
        "first_name": "Jordan",
        "last_name": "Kim",
        "email": "jordan.kim.demo@example.com",
        "current_job_title": "Embedded Systems Engineer",
        "current_company": "Nexwave Semiconductor",
        "current_city": "Austin",
        "current_state": "TX",
        "current_location": "Austin, TX",
        "degrees_text": "BS Electrical Engineering, NC State University, 2020; MS Electrical Engineering, UT Austin, 2022",
        "industry_focus_area": "Embedded Systems / Hardware",
        "professional_experience": "Firmware development for IoT devices. RTOS, C/C++, ARM Cortex-M.",
        "about_yourself": "Happy to talk about embedded systems, graduate school applications, or the transition from academic to industry projects.",
        "students_interested": 1,
        "preferred_contact_method": "LinkedIn",
        "is_active": True,
    },
    {
        "first_name": "Morgan",
        "last_name": "Patel",
        "email": "morgan.patel.demo@example.com",
        "current_job_title": "Machine Learning Engineer",
        "current_company": "Lumen AI",
        "current_city": "San Francisco",
        "current_state": "CA",
        "current_location": "San Francisco, CA",
        "degrees_text": "BS Computer Engineering, NC State University, 2018; MS Computer Science, Stanford, 2020",
        "industry_focus_area": "Machine Learning / AI",
        "professional_experience": "Building production ML pipelines. Experience with PyTorch, TensorFlow, and MLOps tooling.",
        "about_yourself": "Love talking about AI/ML research, career paths in data science, and how ECE prepares you for ML roles.",
        "students_interested": 2,
        "preferred_contact_method": "Email",
        "is_active": True,
    },
    {
        "first_name": "Taylor",
        "last_name": "Nguyen",
        "email": "taylor.nguyen.demo@example.com",
        "current_job_title": "Product Manager",
        "current_company": "Prism Software",
        "current_city": "New York",
        "current_state": "NY",
        "current_location": "New York, NY",
        "degrees_text": "BS Electrical and Computer Engineering, NC State University, 2017",
        "industry_focus_area": "Product Management / Tech",
        "professional_experience": "Started as an engineer, transitioned to PM after 2 years. Now leading a developer tools product team.",
        "about_yourself": "Happy to share how to pivot from an engineering track to product management.",
        "students_interested": 2,
        "preferred_contact_method": "Email",
        "is_active": True,
    },
    {
        "first_name": "Casey",
        "last_name": "Okafor",
        "email": "casey.okafor.demo@example.com",
        "current_job_title": "VLSI Design Engineer",
        "current_company": "CoreLogic Chips",
        "current_city": "San Jose",
        "current_state": "CA",
        "current_location": "San Jose, CA",
        "degrees_text": "BS Electrical Engineering, NC State University, 2016; MS Electrical Engineering, UC San Diego, 2018",
        "industry_focus_area": "VLSI / Chip Design",
        "professional_experience": "RTL design and verification for RISC-V processors. Tools: Cadence, Synopsys, SystemVerilog.",
        "about_yourself": "Open to mentoring students interested in chip design, VLSI, and the semiconductor industry.",
        "students_interested": 1,
        "preferred_contact_method": "Email",
        "is_active": True,
    },
    {
        "first_name": "Riley",
        "last_name": "Chen",
        "email": "riley.chen.demo@example.com",
        "current_job_title": "Data Engineer",
        "current_company": "Meridian Analytics",
        "current_city": "Charlotte",
        "current_state": "NC",
        "current_location": "Charlotte, NC",
        "degrees_text": "BS Computer Engineering, NC State University, 2021",
        "industry_focus_area": "Data Engineering",
        "professional_experience": "Building ETL pipelines using Spark, Airflow, and dbt. Strong background in SQL and Python.",
        "about_yourself": "Recent grad who wants to help others navigate the job search and early career decisions.",
        "students_interested": 3,
        "preferred_contact_method": "Email",
        "is_active": True,
    },
    {
        "first_name": "Sam",
        "last_name": "Johansson",
        "email": "sam.johansson.demo@example.com",
        "current_job_title": "RF Engineer",
        "current_company": "Aether Wireless",
        "current_city": "Raleigh",
        "current_state": "NC",
        "current_location": "Raleigh, NC",
        "degrees_text": "BS Electrical Engineering, NC State University, 2015; MS Electrical Engineering, NC State University, 2017",
        "industry_focus_area": "RF / Communications",
        "professional_experience": "Antenna design and RF system integration for 5G base station hardware.",
        "about_yourself": "Passionate about wireless communications and happy to discuss graduate research and industry applications.",
        "students_interested": 2,
        "preferred_contact_method": "LinkedIn",
        "is_active": True,
    },
    {
        "first_name": "Drew",
        "last_name": "Martinez",
        "email": "drew.martinez.demo@example.com",
        "current_job_title": "Cybersecurity Analyst",
        "current_company": "ShieldNet Security",
        "current_city": "Washington",
        "current_state": "DC",
        "current_location": "Washington, DC",
        "degrees_text": "BS Computer Engineering, NC State University, 2019",
        "industry_focus_area": "Cybersecurity",
        "professional_experience": "Penetration testing, vulnerability assessments, and security operations for government clients.",
        "about_yourself": "Interested in helping students break into cybersecurity from an ECE or CS background.",
        "students_interested": 2,
        "preferred_contact_method": "Email",
        "is_active": True,
    },
    {
        "first_name": "Avery",
        "last_name": "Williams",
        "email": "avery.williams.demo@example.com",
        "current_job_title": "Controls Engineer",
        "current_company": "Dynamo Robotics",
        "current_city": "Detroit",
        "current_state": "MI",
        "current_location": "Detroit, MI",
        "degrees_text": "BS Electrical and Computer Engineering, NC State University, 2020",
        "industry_focus_area": "Robotics / Controls",
        "professional_experience": "PID and model-predictive control for robotic arms. ROS, MATLAB, Simulink.",
        "about_yourself": "Let's talk about robotics, controls theory, and how to get hands-on experience before graduation.",
        "students_interested": 2,
        "preferred_contact_method": "Email",
        "is_active": True,
    },
    {
        "first_name": "Quinn",
        "last_name": "Abrams",
        "email": "quinn.abrams.demo@example.com",
        "current_job_title": "Power Systems Engineer",
        "current_company": "Vertex Energy Group",
        "current_city": "Houston",
        "current_state": "TX",
        "current_location": "Houston, TX",
        "degrees_text": "BS Electrical Engineering, NC State University, 2014; PE License, Texas, 2020",
        "industry_focus_area": "Power Systems / Energy",
        "professional_experience": "Transmission and distribution grid analysis. PSCAD, PowerWorld, and protection relay design.",
        "about_yourself": "Happy to mentor students considering the utility or energy sector, and those pursuing PE licensure.",
        "students_interested": 2,
        "preferred_contact_method": "Email",
        "is_active": True,
    },
    {
        "first_name": "Blake",
        "last_name": "Torres",
        "email": "blake.torres.demo@example.com",
        "current_job_title": "DevOps Engineer",
        "current_company": "Strata Cloud",
        "current_city": "Seattle",
        "current_state": "WA",
        "current_location": "Seattle, WA",
        "degrees_text": "BS Computer Engineering, NC State University, 2018",
        "industry_focus_area": "DevOps / Cloud Infrastructure",
        "professional_experience": "Kubernetes, Terraform, CI/CD pipelines, and cloud cost optimization on AWS and GCP.",
        "about_yourself": "Here to help students understand cloud infrastructure careers and how to build DevOps skills early.",
        "students_interested": 2,
        "preferred_contact_method": "LinkedIn",
        "is_active": True,
    },
    {
        "first_name": "Skyler",
        "last_name": "Robinson",
        "email": "skyler.robinson.demo@example.com",
        "current_job_title": "Biomedical Engineer",
        "current_company": "MedTech Innovations",
        "current_city": "Boston",
        "current_state": "MA",
        "current_location": "Boston, MA",
        "degrees_text": "BS Electrical and Computer Engineering, NC State University, 2017; MS Biomedical Engineering, Boston University, 2019",
        "industry_focus_area": "Biomedical Devices",
        "professional_experience": "Signal processing for wearable cardiac monitors. FDA 510(k) submission experience.",
        "about_yourself": "Great fit for students at the intersection of ECE and healthcare. Can discuss grad school or industry paths.",
        "students_interested": 1,
        "preferred_contact_method": "Email",
        "is_active": True,
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed fake demo mentors")
    parser.add_argument("--clear", action="store_true", help="Delete existing demo mentors first")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be inserted, do not write")
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL") or os.getenv("WRAPPER_MENTOR_DATABASE_URL")
    if not database_url:
        print("ERROR: Set DATABASE_URL environment variable first.")
        sys.exit(1)

    if args.dry_run:
        print(f"DRY RUN — would insert {len(DEMO_MENTORS)} demo mentors:")
        for m in DEMO_MENTORS:
            print(f"  {m['first_name']} {m['last_name']} — {m['current_job_title']} at {m['current_company']}")
        return

    with psycopg.connect(database_url, autocommit=False) as conn, conn.cursor() as cur:
        if args.clear:
            cur.execute("DELETE FROM mentor_records WHERE is_demo = TRUE")
            deleted = cur.rowcount
            print(f"Cleared {deleted} existing demo mentor(s).")

        inserted = 0
        skipped = 0
        for mentor in DEMO_MENTORS:
            mentor_id = f"demo_{str(uuid.uuid4())[:8]}"
            email = mentor.get("email", "")
            full_name = f"{mentor.get('first_name', '')} {mentor.get('last_name', '')}".strip()

            # Skip if a demo mentor with this email already exists.
            cur.execute(
                "SELECT mentor_id FROM mentor_records WHERE lower(trim(email)) = lower(trim(%s)) AND is_demo = TRUE",
                (email,),
            )
            if cur.fetchone():
                print(f"  SKIP (already exists): {full_name}")
                skipped += 1
                continue

            cur.execute(
                """
                INSERT INTO mentor_records (
                    mentor_id, email, first_name, last_name, full_name,
                    current_job_title, current_company,
                    current_city, current_state, current_location,
                    degrees_text, industry_focus_area,
                    professional_experience, about_yourself,
                    students_interested, preferred_contact_method,
                    is_active, is_demo,
                    source_csv_path, last_modified_by,
                    extra_fields, enrichment_provider_metadata,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    '{}', '{}',
                    NOW(), NOW()
                )
                """,
                (
                    mentor_id,
                    email,
                    mentor.get("first_name", ""),
                    mentor.get("last_name", ""),
                    full_name,
                    mentor.get("current_job_title", ""),
                    mentor.get("current_company", ""),
                    mentor.get("current_city", ""),
                    mentor.get("current_state", ""),
                    mentor.get("current_location", ""),
                    mentor.get("degrees_text", ""),
                    mentor.get("industry_focus_area", ""),
                    mentor.get("professional_experience", ""),
                    mentor.get("about_yourself", ""),
                    mentor.get("students_interested", 1),
                    mentor.get("preferred_contact_method", "Email"),
                    mentor.get("is_active", True),
                    True,  # is_demo
                    "seed_demo_mentors",
                    "seed_demo_mentors",
                ),
            )
            print(f"  INSERTED: {full_name} — {mentor.get('current_job_title')} at {mentor.get('current_company')}")
            inserted += 1

        conn.commit()
        print(f"\nDone. Inserted {inserted}, skipped {skipped} (already existed).")
        print("Demo account (eceaccount) will now show these mentors.")


if __name__ == "__main__":
    main()
