from typing import Optional

from sqlalchemy.orm import Session
import database


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
