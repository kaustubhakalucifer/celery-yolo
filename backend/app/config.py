from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    MYSQL_USER: str = "yolo_user"
    MYSQL_PASSWORD: str = "yolo_password"
    MYSQL_SERVER: str = "localhost"
    MYSQL_PORT: str = "3307"
    MYSQL_DB: str = "yolo_jobs"
    DATABASE_URL: str = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_SERVER}:{MYSQL_PORT}/{MYSQL_DB}"

    CELERY_BROKER_URL: str = "amqp://guest:guest@localhost:5672//"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    RABBITMQ_MANAGEMENT_URL: str = "http://guest:guest@localhost:15672/api"

    INPUT_IMAGE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "input"))
    PROCESSED_IMAGE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "processed"))
    YOLO_MODEL_NAME: str = "yolov8n.pt"

    # Ensure directories exist
    def __init__(self, **values):
        super().__init__(**values)
        os.makedirs(self.INPUT_IMAGE_DIR, exist_ok=True)
        os.makedirs(self.PROCESSED_IMAGE_DIR, exist_ok=True)


settings = Settings()
