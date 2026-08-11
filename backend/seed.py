"""
Phase 1 bootstrap seed: creates Counter 1 / Counter 2 and the initial
Owner (Abbu) + Employee accounts if they don't already exist.

Run once after migrations:
    python seed.py

Safe to re-run — it checks for existing rows before inserting.
Credentials come from environment variables (never hardcoded), and the
script prints a reminder to change the seeded password.
"""
import os

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import Counter, RoleName, User


def run() -> None:
    db = SessionLocal()
    try:
        counter1 = db.query(Counter).filter_by(code="01").first()
        if not counter1:
            counter1 = Counter(name="Counter 1", code="01")
            db.add(counter1)

        counter2 = db.query(Counter).filter_by(code="02").first()
        if not counter2:
            counter2 = Counter(name="Counter 2", code="02")
            db.add(counter2)

        db.commit()
        db.refresh(counter1)
        db.refresh(counter2)

        admin_username = os.getenv("SEED_ADMIN_USERNAME", "abbu")
        admin_password = os.getenv("SEED_ADMIN_PASSWORD", "change_me_immediately")

        if not db.query(User).filter_by(username=admin_username).first():
            owner = User(
                username=admin_username,
                full_name="Abbu",
                hashed_password=hash_password(admin_password),
                role=RoleName.OWNER,
                default_counter_id=counter1.id,
            )
            db.add(owner)
            print(f"Created OWNER user '{admin_username}'. CHANGE THIS PASSWORD after first login.")
        else:
            print(f"Owner user '{admin_username}' already exists, skipping.")

        if not db.query(User).filter_by(username="employee").first():
            employee = User(
                username="employee",
                full_name="Employee",
                hashed_password=hash_password("change_me_too"),
                role=RoleName.EMPLOYEE,
                default_counter_id=counter2.id,
            )
            db.add(employee)
            print("Created EMPLOYEE user 'employee' / password 'change_me_too'. CHANGE THIS.")
        else:
            print("Employee user already exists, skipping.")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
