from typing import Optional

from sqlalchemy.orm import Session

from backend.app import database, models


def create_job(db: Session, image_name: str, original_image_path: str) -> database.Job:
    db_job = database.Job(image_name=image_name, original_image_path=original_image_path,
                          status=database.JobStatus.QUEUED)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


def get_job_by_id(db: Session, job_db_id: int) -> Optional[database.Job]:
    return db.query(database.Job).filter(database.Job.id == job_db_id).first()


def get_job_by_celery_id(db: Session, celery_job_id: str) -> Optional[database.Job]:
    return db.query(database.Job).filter(database.Job.job_id == celery_job_id).first()


def update_job(db: Session, job_db_id: int, job_update: models.JobUpdate) -> Optional[database.Job]:
    db_job = get_job_by_id(db, job_db_id)
    if db_job:
        update_data = job_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_job, key, value)
        db.commit()
        db.refresh(db_job)
    return db_job


def get_all_jobs(db: Session, skip: int = 0, limit: int = 100) -> list[type[database.Job]]:
    return db.query(database.Job).order_by(database.Job.id).offset(skip).limit(limit).all()


def count_processed_jobs(db: Session) -> int:
    return db.query(database.Job).filter(database.Job.status == database.JobStatus.PROCESSED).count()


def count_total_jobs(db: Session) -> int:
    return db.query(database.Job).count()
