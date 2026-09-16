"""Local administrative provisioning; never expose these operations as unauthenticated HTTP."""
import argparse
import json
import secrets
from sqlalchemy import select
from app.core.config import Settings
from app.core.security import token_digest
from app.db.session import build_engine, build_session_factory
from app.models import User
from app.schemas.incident import IncidentCreate
from app.services.incidents import create


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    operator = commands.add_parser("init-operator", help="Create a local API-only investigator; show a token once")
    operator.add_argument("--email", required=True)
    operator.add_argument("--name", required=True)
    incident = commands.add_parser("create-incident", help="Create an incident owned by the configured operator")
    incident.add_argument("--title", required=True)
    args = parser.parse_args()
    settings = Settings()
    engine = build_engine(settings)
    try:
        with build_session_factory(engine)() as db:
            if args.command == "init-operator":
                email = args.email.strip().lower()
                if not 3 <= len(email) <= 254 or '@' not in email or not 1 <= len(args.name.strip()) <= 120:
                    parser.error("Use a valid email and a display name of 1–120 characters")
                if db.scalar(select(User).where(User.email == email)):
                    parser.error("User already exists; existing identities are never overwritten")
                user = User(email=email, display_name=args.name.strip(), password_hash="!api-only-disabled")
                db.add(user)
                db.commit()
                token = "sv_operator_" + secrets.token_urlsafe(32)
                print(json.dumps({"operator_token": token, "SHADOWVAULT_OPERATOR_USER_ID": str(user.id),
                                  "SHADOWVAULT_OPERATOR_TOKEN_SHA256": token_digest(token)}, indent=2))
            else:
                user = db.get(User, settings.operator_user_id) if settings.operator_user_id else None
                if user is None or not user.is_active:
                    parser.error("Configure an active SHADOWVAULT_OPERATOR_USER_ID first")
                if not 1 <= len(args.title.strip()) <= 200:
                    parser.error("Incident title must contain 1–200 characters")
                incident = create(db,user.id,IncidentCreate(title=args.title.strip()),source='trusted_cli')
                db.commit()
                print(json.dumps({"incident_id": str(incident.id), "title": incident.title}))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
