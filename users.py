from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.dependencies import get_current_user, require_roles
from app.models.user import User, Role
from app.schemas.auth import UserPublic

router = APIRouter(prefix="/users", tags=["Users"])


class RoleUpdate(BaseModel):
    role: Role


@router.get("/me", response_model=UserPublic)
def get_profile(
    user: User = Depends(get_current_user),
):
    return user


@router.get("", response_model=list[UserPublic])
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(
        require_roles(Role.ADMIN, Role.MANAGER)
    ),
):
    return list(
        db.scalars(
            select(User).order_by(User.id)
        ).all()
    )


@router.patch("/{user_id}/role")
def assign_role(
    user_id: int,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(Role.ADMIN)
    ),
):
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.role = payload.role
    db.commit()
    db.refresh(user)

    return {
        "message": "Role updated successfully",
        "user_id": user.id,
        "role": user.role,
    }
