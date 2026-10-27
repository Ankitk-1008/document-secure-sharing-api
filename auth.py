from collections import defaultdict, deque
from time import time
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import get_db
from app.models.user import User, Role
from app.schemas.auth import UserRegister, UserPublic, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.dependencies import get_current_user
from app.services.audit import log_action

router = APIRouter(prefix="/auth", tags=["Authentication"])
_attempts = defaultdict(deque)

def throttle_login(request: Request):
    key = request.client.host if request.client else "unknown"
    now = time()
    q = _attempts[key]
    while q and q[0] < now - 60: q.popleft()
    if len(q) >= settings.RATE_LIMIT_LOGIN_PER_MINUTE:
        raise HTTPException(429, detail="Too many login attempts. Try again in one minute.")
    q.append(now)

@router.post("/register", response_model=UserPublic, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, detail="Email already registered")
    user = User(full_name=payload.full_name, email=email, password_hash=hash_password(payload.password), role=Role.USER)
    db.add(user); db.commit(); db.refresh(user)
    log_action(db, user.id, "user.registered"); db.commit()
    return user

@router.post("/login", response_model=TokenResponse)
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    throttle_login(request)
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if not user or not verify_password(form.password, user.password_hash) or not user.is_active:
        raise HTTPException(401, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    token = create_access_token(str(user.id), user.role.value)
    log_action(db, user.id, "user.login"); db.commit()
    return TokenResponse(access_token=token, expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES, user=user)

@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)):
    return current_user
