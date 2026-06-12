from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.role import Role
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.common import TableQueryParams
from app.schemas.user import UserRead
from app.utils.filters import split_filter


class UserRepository(BaseRepository[User]):
    def __init__(self) -> None:
        super().__init__(User)

    def list_users(
        self,
        db: Session,
        query: TableQueryParams,
        *,
        role: str | None = None,
    ) -> tuple[list[UserRead], int]:
        statement = select(User, Role.name.label("role_name"), Role.permissions).outerjoin(Role, Role.id == User.role_id)
        roles = split_filter(role)
        if roles:
            statement = statement.where(Role.name.in_(roles))
        rows, total = self.list_simple(
            db,
            query,
            base_statement=statement,
            sort_map={
                "id": User.id,
                "name": User.name,
                "email": User.email,
                "role": Role.name,
                "lastLogin": User.last_login,
                "createdAt": User.created_at,
            },
            search_columns=[User.name, User.email, Role.name],
            date_column=User.created_at,
        )
        data = [
            UserRead(
                id=user.id,
                name=user.name,
                role=role_name,
                role_id=user.role_id,
                email=user.email,
                permissions=permissions or {},
                last_login=user.last_login,
                created_at=user.created_at,
            )
            for user, role_name, permissions in rows
        ]
        return data, total
