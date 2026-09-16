"""Separate operator and device credentials; the browser login remains unchanged."""
import hashlib
import hmac
from typing import Annotated
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Agent, User
from app.models.common import utc_now

bearer = HTTPBearer(auto_error=False)
Database = Annotated[Session, Depends(get_db)]
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def denied():
    raise HTTPException(401, "Invalid or expired credential", headers={"WWW-Authenticate": "Bearer"})


def credential_digest(credentials) -> str:
    if credentials is None or len(credentials.credentials) > 256:
        denied()
    return token_digest(credentials.credentials)


def require_operator(request: Request, db: Database, credentials: Credentials) -> User:
    digest = credential_digest(credentials)
    settings = request.app.state.settings
    expected = settings.operator_token_sha256
    if expected is None or not hmac.compare_digest(digest, expected.get_secret_value()):
        denied()
    user = db.get(User, settings.operator_user_id) if settings.operator_user_id else None
    if user is None or not user.is_active:
        denied()
    return user


def active_agent(db: Session, digest: str) -> Agent:
    agent = db.scalar(select(Agent).where(Agent.token_sha256 == digest).execution_options(populate_existing=True))
    if agent is None or not agent.is_active or agent.token_expires_at <= utc_now():
        denied()
    owner = db.get(User, agent.registered_by_id, populate_existing=True)
    if owner is None or not owner.is_active:
        denied()
    return agent


def require_agent(db: Database, credentials: Credentials) -> Agent:
    return active_agent(db, credential_digest(credentials))


Operator = Annotated[User, Depends(require_operator)]
Device = Annotated[Agent, Depends(require_agent)]
