from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config.settings import settings

# In order to support Async MySQL connectivity in Python, we use the mysql+aiomysql driver
# and fallback/warn if we need to fall back.
# Configure SSL/TLS parameters for AWS MySQL encryption in transit
connect_args = {}
if settings.MYSQL_SSL_CA:
    import ssl
    try:
        # Create standard SSLContext configuration to validate certificates
        ssl_context = ssl.create_default_context(cafile=settings.MYSQL_SSL_CA)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        connect_args["ssl"] = ssl_context
    except Exception:
        # Fallback to raw path dictionary configuration if context setup errors
        connect_args["ssl"] = {"ssl_ca": settings.MYSQL_SSL_CA}
elif settings.MYSQL_SSL_VERIFY:
    connect_args["ssl"] = True

engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True,
    connect_args=connect_args,
    echo=False
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency for database session injection."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
