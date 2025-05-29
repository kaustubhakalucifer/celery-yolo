import enum
import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Enum as AlchemyEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from backend.app.config import settings

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    ERROR = "ERROR"

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    image_name = Column(String(255), index=True)
    job_id = Column(String(255), unique=True, index=True, nullable=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    time_taken_ms = Column(Integer, nullable=True)
    objects_found = Column(Text, nullable=True)  # JSON string of objects
    processed_image_path = Column(String(512), nullable=True)
    original_image_path = Column(String(512), nullable=True)  # Store this for easier access
    status = Column(AlchemyEnum(JobStatus), default=JobStatus.QUEUED)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC))


def create_db_and_tables():
    Base.metadata.create_all(bind=engine)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
