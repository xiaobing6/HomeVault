from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.seed import seed_auth_baseline


def main() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        admin = seed_auth_baseline(
            db,
            admin_username=settings.admin_username,
            admin_password=settings.admin_password,
        )
        print(f"管理员账号已就绪: {admin.username}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
