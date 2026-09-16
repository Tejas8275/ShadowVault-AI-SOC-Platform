"""Explicit development-only schema bootstrap: python -m app.db.init_db."""

from app.core.config import Settings
from app.db.migrate import upgrade_database


def init_db(settings: Settings | None = None) -> None:
    settings = settings or Settings()
    if settings.environment == "production":
        raise RuntimeError("Use reviewed migrations for production; bootstrap is development-only")
    upgrade_database(settings)


if __name__ == "__main__":
    init_db()
    print("Development database upgraded. Legacy Phase 1 databases require explicit adoption.")
