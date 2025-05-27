import datetime
import json
import time

from backend.app.database import SessionLocal, JobStatus
from backend.app.yolo_utils import process_image_with_yolo
from backend.celery_app import celery_app
from backend.app import crud, models


@celery_app.task(name="process_image_task", bind=True)
def process_image_task(self, job_db_id: int, image_path: str):
    db = SessionLocal()
    try:
        job_update_processing = models.JobUpdate(job_id=self.request.id, status=JobStatus.PROCESSING,
                                                 start_time=datetime.datetime.now(datetime.UTC))
        crud.update_job(db, job_db_id=job_db_id, job_update=job_update_processing)
        db.commit()

        start_execution_time = time.time()

        processed_image_full_path, detections, error = process_image_with_yolo(image_path)

        end_execution_time = time.time()

        time_taken_ms = int((end_execution_time - start_execution_time) * 1000)

        if error:
            job_update_error = models.JobUpdate(
                status=JobStatus.ERROR,
                end_time=datetime.datetime.now(datetime.UTC),
                time_taken_ms=time_taken_ms,
                objects_found=json.dumps([{"error": error}])
            )
            crud.update_job(db, job_db_id=job_db_id, job_update=job_update_error)
            db.commit()
            return {"status": "ERROR", "error": error, "job_db_id": job_db_id}
        job_update_success = models.JobUpdate(
            status=JobStatus.PROCESSED,
            end_time=datetime.datetime.now(datetime.UTC),
            time_taken_ms=time_taken_ms,
            objects_found=json.dumps(detections),
            processed_image_path=processed_image_full_path
        )
        crud.update_job(db, job_db_id=job_db_id, job_update=job_update_success)
        db.commit()

        return {
            "status": "PROCESSED",
            "job_db_id": job_db_id,
            "processed_path": processed_image_full_path,
            "detections": detections,
            "time_taken_ms": time_taken_ms
        }
    except Exception as e:
        job_update_failure = models.JobUpdate(
            status=JobStatus.ERROR,
            end_time=datetime.datetime.now(datetime.UTC),
            objects_found=json.dumps([{"error": f"Task failed: {str(e)}"}])
        )
        crud.update_job(db, job_db_id=job_db_id, job_update=job_update_failure)
        db.commit()
        return {"status": "ERROR", "error": str(e), "job_db_id": job_db_id}
    finally:
        db.close()
