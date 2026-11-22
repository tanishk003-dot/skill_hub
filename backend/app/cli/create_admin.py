import sys
import getpass
from app.core.database import SessionLocal
from app.core.security import hash_password, validate_password_complexity, validate_email_domain
from app.models.user import User, UserRole
from app.models.admin_audit_log import AdminAuditLog

def create_admin_interactive():
    print("==========================================================")
    print("L&K Skill Hub — Production Root Administrator Provisioning")
    print("==========================================================")

    db = SessionLocal()
    try:
        name = input("Enter Admin Full Name: ").strip()
        if not name:
            print("Error: Name cannot be empty.")
            sys.exit(1)

        email = input("Enter Admin Corporate Email: ").strip().lower()
        try:
            email = validate_email_domain(email)
        except Exception:
            print("Error: Use your @csm.tech email")
            sys.exit(1)

        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"Error: A user with email '{email}' already exists (Role: {existing.role}).")
            sys.exit(1)

        password = getpass.getpass("Enter Strong Password: ")
        is_valid, err_msg = validate_password_complexity(password)
        if not is_valid:
            print(f"Password Complexity Error: {err_msg}")
            sys.exit(1)

        confirm_pwd = getpass.getpass("Confirm Strong Password: ")
        if password != confirm_pwd:
            print("Error: Passwords do not match.")
            sys.exit(1)

        admin = User(
            name=name,
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
            is_demo=False
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        audit = AdminAuditLog(
            actor_id=admin.id,
            actor_email=admin.email,
            action="BOOTSTRAP_ROOT_ADMIN",
            target_type="USER",
            target_id=str(admin.id),
            details=f"Initialized root production administrator {admin.email} via CLI"
        )
        db.add(audit)
        db.commit()

        print(f"\n[SUCCESS] Root Administrator '{name}' <{email}> created successfully (ID: {admin.id}).")
        print("You may now log in to the system dashboard.")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_interactive()
