"""Use application configuration without interpolating database credentials into INI."""
from alembic import context
from app.core.config import Settings
from app.db.base import Base
from app.db.session import build_engine
from app import models  # noqa: F401


def run(connection):
    context.configure(connection=connection, target_metadata=Base.metadata,
                      render_as_batch=connection.dialect.name == "sqlite", compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("Use online migrations; SQLite schema upgrades require reflection")
elif context.config.attributes.get("connection") is not None:
    run(context.config.attributes["connection"])
else:
    engine = build_engine(Settings())
    try:
        with engine.connect() as connection:
            if connection.dialect.name == "sqlite":
                connection.exec_driver_sql("BEGIN")
            run(connection)
            connection.commit()
    finally:
        engine.dispose()
