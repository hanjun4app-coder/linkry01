"""数据库连接和会话管理"""
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import logging
from app.config import settings
from app.models import Base

logger = logging.getLogger(__name__)

# 创建数据库引擎
engine = create_engine(
    settings.get_database_url,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,  # 验证连接有效性
    echo=settings.DEBUG,  # 调试模式下输出 SQL
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """获取数据库会话（FastAPI 依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """获取数据库上下文（非 FastAPI 使用）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库（创建所有表）"""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def drop_db():
    """删除所有表（仅用于测试）"""
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")


def verify_connection():
    """验证数据库连接"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


# 事件监听器已移除（SQLAlchemy 2.0+ 兼容性）
