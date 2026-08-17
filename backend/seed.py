"""
Phase 1 bootstrap seed: creates Counter 1 / Counter 2 and an initial
Owner + Employee account if they don't already exist.

Run once after migrations:
    python seed.py

Safe to re-run — it checks for existing rows before inserting.
Every value, including full_name, comes from environment variables —
nothing here assumes a specific person's name or that any particular
counter belongs to any particular person. If full_name isn't provided,
it falls back to the username itself rather than guessing a name.
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

        admin_username = os.getenv("SEED_ADMIN_USERNAME", "owner")
        admin_password = os.getenv("SEED_ADMIN_PASSWORD", "change_me_immediately")
        admin_full_name = os.getenv("SEED_ADMIN_FULL_NAME", admin_username)

        if not db.query(User).filter_by(username=admin_username).first():
            owner = User(
                username=admin_username,
                full_name=admin_full_name,
                hashed_password=hash_password(admin_password),
                role=RoleName.OWNER,
                default_counter_id=counter1.id,
            )
            db.add(owner)
            print(f"Created OWNER user '{admin_username}'. CHANGE THIS PASSWORD after first login.")
        else:
            print(f"Owner user '{admin_username}' already exists, skipping.")

        employee_username = os.getenv("SEED_EMPLOYEE_USERNAME", "employee")
        employee_password = os.getenv("SEED_EMPLOYEE_PASSWORD", "change_me_too")
        employee_full_name = os.getenv("SEED_EMPLOYEE_FULL_NAME", employee_username)

        if not db.query(User).filter_by(username=employee_username).first():
            employee = User(
                username=employee_username,
                full_name=employee_full_name,
                hashed_password=hash_password(employee_password),
                role=RoleName.EMPLOYEE,
                default_counter_id=counter2.id,
            )
            db.add(employee)
            print(f"Created EMPLOYEE user '{employee_username}'. CHANGE THIS PASSWORD after first login.")
        else:
            print(f"Employee user '{employee_username}' already exists, skipping.")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
