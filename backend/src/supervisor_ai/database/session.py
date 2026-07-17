from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from supervisor_ai.core.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionFactory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
