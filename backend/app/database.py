import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from .config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Initialize database: create tables & default admin user."""
    from .models.server import Server  # noqa
    from .models.audit import AuditLog  # noqa
    from .models.admin import AdminUser  # noqa
    from .models.snapshot import SessionSnapshot  # noqa

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure default admin exists
    from .utils.security import get_password_hash

    async with async_session() as session:
        from .models.admin import AdminUser

        result = await session.execute(
            AdminUser.__table__.select().where(
                AdminUser.username == settings.DEFAULT_ADMIN_USERNAME
            )
        )
        admin = result.first()
        if not admin:
            session.add(
                AdminUser(
                    username=settings.DEFAULT_ADMIN_USERNAME,
                    hashed_password=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                    must_change_password=True,
                )
            )
            await session.commit()


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
