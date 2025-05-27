import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.database import SessionLocal
from backend.app import crud, tasks, models
from typing import List

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


@app.post("/start-processing/", status_code=202)
async def start_processing_image(db: Session = Depends(get_db)):
    image_files = [f for f in os.listdir(settings.INPUT_IMAGE_DIR)
                   if os.path.isfile(os.path.join(settings.INPUT_IMAGE_DIR, f))
                   and f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not image_files:
        raise HTTPException(status_code=404, detail="No images found in input folder.")

    queued_count = 0
    images_to_process = image_files[:50]

    for image_name in images_to_process:
        original_image_path = os.path.join(settings.INPUT_IMAGE_DIR, image_name)

        # Create a job record in the DB first
        db_job = crud.create_job(db, image_name=image_name, original_image_path=original_image_path)

        # Send task to celery
        # Pass the database job ID, not the full object
        tasks.process_image_task.delay(job_db_id=db_job.id, image_path=original_image_path)
        queued_count += 1

    return {"message": f"Successfully queued {queued_count} images for processing."}


@app.get("/jobs/", response_model=List[models.JobSchema])
async def read_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    jobs = crud.get_all_jobs(db, skip=skip, limit=limit)
    return jobs


if __name__ == "__main__":
    import uvicorn

    print(f"Input dir: {settings.INPUT_IMAGE_DIR}")
    print(f"Processed dir: {settings.PROCESSED_IMAGE_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
