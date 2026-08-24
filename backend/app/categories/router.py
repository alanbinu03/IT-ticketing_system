from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AuthContext, get_current_user, require_permission
from app.categories.schemas import CategoryCreate, CategoryOut, CategoryUpdate
from app.categories.service import CategoryService
from app.database.session import get_db

categories_router = APIRouter(prefix="/categories", tags=["categories"])


@categories_router.get("", response_model=list[CategoryOut])
async def list_categories(
    include_inactive: bool = Query(default=False),
    _auth: AuthContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[CategoryOut]:
    return await CategoryService(session).list_tree(active_only=not include_inactive)


@categories_router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate,
    _auth: AuthContext = Depends(require_permission("category.manage")),
    session: AsyncSession = Depends(get_db),
) -> CategoryOut:
    return await CategoryService(session).create(payload)


@categories_router.patch("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    _auth: AuthContext = Depends(require_permission("category.manage")),
    session: AsyncSession = Depends(get_db),
) -> CategoryOut:
    return await CategoryService(session).update(category_id, payload)
