CREATE DATABASE IF NOT EXISTS yolo_jobs;
SELECT 'Database yolo_jobs check/creation done' AS MSG; -- Debug
USE yolo_jobs;
SELECT 'Switched to yolo_jobs database' AS MSG; -- Debug

CREATE TABLE IF NOT EXISTS jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    image_name VARCHAR(255),
    job_id VARCHAR(255) UNIQUE,
    start_time DATETIME,
    end_time DATETIME,
    time_taken_ms INT,
    objects_found TEXT,
    processed_image_path VARCHAR(512),
    original_image_path VARCHAR(512),
    status ENUM('QUEUED', 'PROCESSING', 'PROCESSED', 'ERROR') DEFAULT 'QUEUED',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_image_name (image_name),
    INDEX idx_job_id (job_id)
);

SELECT 'Jobs table creation attempted' AS MSG; -- Debug