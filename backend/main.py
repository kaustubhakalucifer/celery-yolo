import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.database import SessionLocal, JobStatus
from backend.app import crud, models, database
from backend.celery_app import celery_app as celery_application
from typing import List, Optional
import requests
import datetime
from pydantic import BaseModel

app = FastAPI(title="YOLO Image Processing Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_rabbitmq_queue_size(queue_name: str = "celery") -> int:
  try:
    url = f"{settings.RABBITMQ_MANAGEMENT_URL}/queues/%2F/{queue_name}"
    response = requests.get(url)
    response.raise_for_status()
    queue_info = response.json()
    return queue_info.get("messages", 0)
  except requests.exceptions.RequestException as e:
    print(f"Error fetching RabbitMQ queue size: {e}")
    return -1 # Indicate error
  except Exception as e:
    print(f"Unexpected error fetching RabbitMQ queue size: {e}")
    return -1
  
class ProcessingSummaryResponse(BaseModel):
  total_celery_workers: int
  total_yolo_models_pre_loaded: int
  total_images_target: int
  total_processed_db: int
  total_error_db: int
  total_remaining: int
  in_processing_queue_db: int
  rabbitmq_job_queue_size: int | str
  total_time_taken_str: Optional[str] = None

overall_processing_start_time: Optional[datetime.datetime] = None
overall_processing_completed_flag: bool = False

@app.post("/start-processing/", status_code=202)
async def start_processing_image(db: Session = Depends(get_db)):
  global overall_processing_start_time, overall_processing_completed_flag
  overall_processing_start_time = datetime.datetime.now(datetime.UTC)
  overall_processing_completed_flag = False
  db.query(database.Job).delete()
  db.commit()
  print('Cleared existing jobs for a fresh run.')
  
  image_files =[
    f for f in os.listdir(settings.INPUT_IMAGE_DIR)
    if os.path.isfile(os.path.join(settings.INPUT_IMAGE_DIR,f))
    and f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]
  
  if not image_files:
    overall_processing_start_time = None
    raise HTTPException(status_code=404, detail="No images found in input folder.")
  
  queued_count = 0
  images_to_process = image_files
  
  for image_name in images_to_process:
    original_image_path = os.path.join(settings.INPUT_IMAGE_DIR, image_name)
    db_job = crud.create_job(db, image_name=image_name, original_image_path=original_image_path)
    # tasks.process_image_task.delay(job_db_id=db_job.id, image_path=original_image_path)
    celery_application.send_task("process_image_task", args=[db_job.id, original_image_path])
    queued_count += 1

  return {"message": f"Successfully queued {queued_count} images for processing. Overall timer started."}


@app.get("/jobs/", response_model=List[models.JobSchema])
async def read_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    jobs = crud.get_all_jobs(db, skip=skip, limit=limit)
    return jobs

@app.get("/jobs/{job_db_id}/", response_model=models.JobSchema)
async def read_job(job_db_id: int, db: Session = Depends(get_db)):
  db_job = crud.get_job_by_id(db, job_db_id)
  if db_job is None:
    raise HTTPException(status_code=404, detail='Job not found')
  
@app.get("/processing-summary/")
async def get_processing_summary(db: Session = Depends(get_db)):
  global overall_processing_start_time, overall_processing_completed_flag
  total_images_target = db.query(database.Job).count()

  total_processed_db = db.query(database.Job).filter(database.Job.status == JobStatus.PROCESSED).count()
  total_error_db = db.query(database.Job).filter(database.Job.status == JobStatus.ERROR).count()

  # "Total Remaining" = Target - (Processed + Error)
  # Ensure it doesn't go below zero if more than 50 jobs somehow get processed/errored
  # This counts against the target of 50.
  # We need to consider jobs that were created for this run.
  # For simplicity, assuming jobs table primarily reflects the current 50-image run.
  # If jobs are cumulative, this logic needs adjustment.
  current_run_job_count = db.query(database.Job).count() # Count all jobs, assuming they are for this run
  
  # If we are strictly talking about the target 50:
  processed_for_target = total_processed_db
  errored_for_target = total_error_db
  
  total_remaining = total_images_target - (processed_for_target + errored_for_target)
  total_remaining = max(0, total_remaining) # Don't go negative


  # "In Processing Queue" from UI spec implies Celery queue + DB tasks in QUEUED/PROCESSING state
  # For DB part:
  queued_in_db = db.query(database.Job).filter(database.Job.status == JobStatus.QUEUED).count()
  processing_in_db = db.query(database.Job).filter(database.Job.status == JobStatus.PROCESSING).count()
  in_processing_queue_db = queued_in_db + processing_in_db

  # For Celery queue part:
  rabbitmq_job_queue_size_val = get_rabbitmq_queue_size(queue_name="celery")

  total_time_taken_str = None
  if overall_processing_start_time and not overall_processing_completed_flag:
    # Check if all target jobs are done (processed or errored)
    # This assumes the jobs in DB are for the current run up to 50.
    # If you have more than 50 jobs in DB from previous runs, this needs refinement.
    # Let's count jobs that are either PROCESSED or ERROR
    finished_jobs_count = total_processed_db + total_error_db

    # We consider the run complete if the number of finished jobs (processed + error)
    # reaches the target of 50, OR if there are no more jobs in QUEUED or PROCESSING states
    # AND we have at least one job processed or errored (to avoid triggering completion on an empty queue at start).
    
    # A more robust way: if we have dispatched 50 tasks, and all 50 have a terminal state (PROCESSED/ERROR)
    # For this, we'd need to know how many tasks were actually dispatched for the "current run".
    # Let's assume the "target 50" is the key.
    
    if finished_jobs_count >= total_images_target and current_run_job_count >= total_images_target:
      print(finished_jobs_count >= total_images_target, current_run_job_count >= total_images_target)
      overall_processing_completed_flag = True # Mark as completed for this request
      end_time = datetime.datetime.now(datetime.UTC)
      duration = end_time - overall_processing_start_time
      
      total_seconds = int(duration.total_seconds())
      hours = total_seconds // 3600
      minutes = (total_seconds % 3600) // 60
      seconds = total_seconds % 60
      milliseconds = duration.microseconds // 1000 # Convert microseconds to milliseconds
      total_time_taken_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{milliseconds:03d}"

  elif overall_processing_completed_flag and overall_processing_start_time: # If already completed in a previous call
    # Recalculate and show the stored/final time
    # This part is tricky with a global variable. For simplicity, if completed, we won't update the time
    # unless we store the end_time globally too. A better approach would be to store this in Redis/DB.
    # For now, if completed_flag is true, total_time_taken_str might remain None or from a previous calculation.
    # To ensure it's always shown once calculated:
    # This needs a stored end time or duration.
    # Let's assume if completed_flag is true, the time was calculated and should be available.
    # This logic needs to be more robust for a production system.
    # A simple fix: if completed, try to calculate if not already set.
    if total_time_taken_str is None: # Attempt to calculate if it wasn't set by the completion logic
      # This will use the current time as end time if called after completion.
      # Ideally, the exact end time of the 50th job processing is needed.
      end_time = datetime.datetime.now(datetime.UTC)
      duration = end_time - overall_processing_start_time
      total_seconds = int(duration.total_seconds())
      hours = total_seconds // 3600
      minutes = (total_seconds % 3600) // 60
      seconds = total_seconds % 60
      milliseconds = duration.microseconds // 1000
      total_time_taken_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{milliseconds:03d}"


  return ProcessingSummaryResponse(
    total_celery_workers=1,
    total_yolo_models_pre_loaded=1,
    total_images_target=total_images_target,
    total_processed_db=total_processed_db, # Actual total processed in DB
    total_error_db=total_error_db,       # Actual total errors in DB
    total_remaining=total_remaining,       # Remaining out of the target 50
    in_processing_queue_db=in_processing_queue_db,
    rabbitmq_job_queue_size=rabbitmq_job_queue_size_val if rabbitmq_job_queue_size_val != -1 else "Error fetching",
    total_time_taken_str=total_time_taken_str
  )

if __name__ == "__main__":
    import uvicorn

    print(f"Input dir: {settings.INPUT_IMAGE_DIR}")
    print(f"Processed dir: {settings.PROCESSED_IMAGE_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
