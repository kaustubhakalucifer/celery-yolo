// pages/index.js
// No "use client;" needed here for Pages Router

import { useState, useEffect, useCallback } from 'react';
import Head from 'next/head'; // For setting the page title and other head elements
import axios from 'axios';
import { format } from 'date-fns';

// Get the API base URL from environment variable or use a default
// For Pages Router, NEXT_PUBLIC_ prefix is still needed for client-side access
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// A helper component for displaying summary items consistently
const SummaryItem = ({ label, value }) => (
  <div style={{ border: '1px solid #eee', padding: '10px', borderRadius: '5px', backgroundColor: '#f9f9f9' }}>
    <strong style={{ display: 'block', marginBottom: '5px', color: '#555', fontSize: '0.9em' }}>{label}:</strong>
    <span style={{ fontSize: '1.1em', color: '#333' }}>
      {value !== undefined && value !== null ? String(value) : 'N/A'}
    </span>
  </div>
);


export default function HomePage() {
  // State for summary data
  const [summary, setSummary] = useState({
    total_celery_workers: 1,
    total_yolo_models_pre_loaded: 1,
    total_images_target: 0,
    total_processed_db: 0,
    total_error_db: 0,
    total_remaining: 0,
    in_processing_queue_db: 0,
    rabbitmq_job_queue_size: 'N/A',
    total_time_taken_str: null,
  });

  // State for the list of jobs
  const [jobs, setJobs] = useState([]);

  // State for loading status of the "Start Processing" button
  const [isStarting, setIsStarting] = useState(false);
  // State to control data polling
  const [isPollingActive, setIsPollingActive] = useState(false);

  // State for displaying API errors
  const [apiError, setApiError] = useState(null);

  // State for the object list modal
  const [selectedObjects, setSelectedObjects] = useState(null);

  // Function to fetch data
  const fetchData = useCallback(async () => {
    console.log("Fetching data (Pages Router)...");
    try {
      const summaryRes = await axios.get(`${API_BASE_URL}/processing-summary/`);
      setSummary(summaryRes.data);

      const jobsRes = await axios.get(`${API_BASE_URL}/jobs/?limit=1000`);
      const sortedJobs = jobsRes.data.sort((a, b) => a.id - b.id);
      setJobs(sortedJobs);

      if (summaryRes.data.total_images_target > 0 &&
        (summaryRes.data.total_processed_db + summaryRes.data.total_error_db) >= summaryRes.data.total_images_target) {
        console.log("All target images processed or errored. Stopping polling (Pages Router).");
        setIsPollingActive(false);
      }
      setApiError(null);
    } catch (error) {
      console.error("Error fetching data:", error);
      setApiError(error.response?.data?.detail || "Failed to fetch data from backend. Is it running?");
    }
  }, []); // fetchData itself doesn't change

  // useEffect for polling data
  useEffect(() => {
    let intervalId = null;
    if (isPollingActive) {
      fetchData();
      intervalId = setInterval(fetchData, 3000);
      console.log("Polling started with interval ID (Pages Router):", intervalId);
    } else {
      console.log("Polling stopped (Pages Router).");
    }
    return () => {
      if (intervalId) {
        console.log("Clearing interval ID (Pages Router):", intervalId);
        clearInterval(intervalId);
      }
    };
  }, [isPollingActive, fetchData]);

  // Handler for the "Start Processing" button
  const handleStartProcessing = async () => {
    setIsStarting(true);
    setApiError(null);
    setJobs([]);
    setSummary({
      total_celery_workers: 1, total_yolo_models_pre_loaded: 1, total_images_found: 0,
      total_processed: 0, total_errored: 0, total_remaining: 0, in_processing_queue: 0,
      rabbitmq_job_queue_size: 'N/A', total_time_taken_to_process_50_images: null,
    });

    try {
      const response = await axios.post(`${API_BASE_URL}/start-processing/`);
      console.log(response.data.message);
      setIsPollingActive(true);
    } catch (error) {
      console.error("Error starting processing:", error);
      setApiError(error.response?.data?.detail || "Failed to start processing.");
      setIsPollingActive(false);
    } finally {
      setIsStarting(false);
    }
  };

  // Function to view original or processed image
  const viewImage = async (jobDbId, type) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/image/${jobDbId}?type=${type}`);
      const { base64_image, content_type } = response.data;
      const imageWindow = window.open();
      if (imageWindow) {
        imageWindow.document.write(
          `<title>${type.charAt(0).toUpperCase() + type.slice(1)} Image - Job ${jobDbId}</title>
           <body style="margin:0; display:flex; justify-content:center; align-items:center; min-height:100vh; background-color:#f0f0f0;">
             <img src="data:${content_type};base64,${base64_image}" alt="${type} image" style="max-width:95%; max-height:95vh; object-fit:contain;"/>
           </body>`
        );
        imageWindow.document.close();
      }
    } catch (error) {
      console.error(`Error fetching ${type} image for job ${jobDbId}:`, error);
      alert(`Failed to load ${type} image. Check console for details.`);
    }
  };

  // Function to show detected objects
  const showObjectsModal = (objectsJsonString) => {
    if (!objectsJsonString) {
      setSelectedObjects([{ error: "No object data provided." }]);
      return;
    }
    try {
      const objects = JSON.parse(objectsJsonString);
      setSelectedObjects(objects);
    } catch (e) {
      console.error("Error parsing objects JSON:", e);
      setSelectedObjects([{ error: "Invalid object data." }]);
    }
  };

  // Function to close the modal
  const closeModal = () => {
    setSelectedObjects(null);
  };

  // Helper to format datetime
  const formatDateTime = (dateTimeString) => {
    if (!dateTimeString) return 'N/A';
    try {
      return format(new Date(dateTimeString), 'yyyy-MM-dd HH:mm:ss');
    } catch (e) {
      return 'Invalid Date';
    }
  };

  return (
    <> {/* Use a Fragment or a single root div */}
      <Head>
        <title>YOLO Image Processing</title>
        <meta name="description" content="YOLO Object Detection Image Processing Dashboard" />
        <link rel="icon" href="/favicon.ico" /> {/* Assuming you have a favicon */}
      </Head>

      <div style={{ padding: '25px', fontFamily: 'Arial, Helvetica, sans-serif', maxWidth: '1300px', margin: '20px auto', backgroundColor: '#fff', borderRadius: '8px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>

        <header style={{ textAlign: 'center', marginBottom: '30px', paddingBottom: '20px', borderBottom: '1px solid #eee' }}>
          <h1 style={{ color: '#2c3e50', fontWeight: '300' }}>YOLO Image Processing Dashboard</h1>
        </header>

        <section style={{ marginBottom: '30px', textAlign: 'center' }}>
          <button
            onClick={handleStartProcessing}
            disabled={isStarting || isPollingActive}
            style={{
              padding: '12px 28px',
              fontSize: '1.1em',
              color: 'white',
              backgroundColor: (isStarting || isPollingActive) ? '#bdc3c7' : '#3498db',
              border: 'none',
              borderRadius: '5px',
              cursor: (isStarting || isPollingActive) ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.3s ease',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}
          >
            {isStarting ? 'Starting...' : (isPollingActive ? 'Processing In Progress...' : 'Start Processing (New Run)')}
          </button>
          {apiError && <p style={{ color: '#e74c3c', marginTop: '15px', fontWeight: 'bold' }}>API Error: {apiError}</p>}
        </section>

        <section style={{ marginBottom: '30px', padding: '20px', border: '1px solid #ecf0f1', borderRadius: '8px', backgroundColor: '#f8f9fa' }}>
          <h2 style={{ marginTop: '0', marginBottom: '20px', color: '#34495e', borderBottom: '1px solid #eee', paddingBottom: '10px', fontWeight: '400' }}>
            Summary Report
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '15px' }}>
            <SummaryItem label="Target Images (Total Found)" value={summary.total_images_found} />
            <SummaryItem label="Total Processed" value={summary.total_processed_db} />
            <SummaryItem label="Total Errored" value={summary.total_error_db} />
            <SummaryItem label="Total Remaining" value={summary.total_remaining} />
            <SummaryItem label="In DB Queue/Processing" value={summary.in_processing_queue_db} />
            <SummaryItem label="RabbitMQ Job Queue Size" value={summary.rabbitmq_job_queue_size} />
            <SummaryItem label="Total Time (Target {summary.total_images_found})" value={summary.total_time_taken_str || "N/A"} />
            <SummaryItem label="Celery Workers" value={summary.total_celery_workers} />
            <SummaryItem label="YOLO Models Loaded" value={summary.total_yolo_models_pre_loaded} />
          </div>
        </section>

        <section>
          <h2 style={{ marginBottom: '20px', color: '#34495e', fontWeight: '400' }}>Detailed Report</h2>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9em' }}>
              <thead>
                <tr style={{ backgroundColor: '#e9ecef', color: '#495057' }}>
                  {['S.No', 'Image Name', 'Celery Job ID', 'Exec Start', 'Exec End', 'Time (ms)', 'View Original', 'View Processed', 'List of Objects', 'Status'].map(header => (
                    <th key={header} style={{ border: '1px solid #dee2e6', padding: '10px 12px', textAlign: 'left', fontWeight: '500' }}>{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(jobs.length > 0 ? jobs : Array.from({ length: summary.total_images_found || 0 })).map((job, index) => (
                  job ? (
                    <tr key={job.id || `placeholder-${index}`} style={{ backgroundColor: index % 2 === 0 ? '#fff' : '#fbfcfc', borderBottom: '1px solid #eee' }}>
                      <td style={{ border: '1px solid #e0e0e0', padding: '8px 12px' }}>{index + 1}</td>
                      <td style={{ border: '1px solid #e0e0e0', padding: '8px 12px', wordBreak: 'break-all' }}>{job.image_name}</td>
                      <td style={{ border: '1px solid #e0e0e0', padding: '8px 12px', wordBreak: 'break-all' }}>{job.job_id || 'N/A'}</td>
                      <td style={{ border: '1px solid #e0e0e0', padding: '8px 12px' }}>{formatDateTime(job.start_time)}</td>
                      <td style={{ border: '1px solid #e0e0e0', padding: '8px 12px' }}>{formatDateTime(job.end_time)}</td>
                      <td style={{ border: '1px solid #e0e0e0', padding: '8px 12px', textAlign: 'right' }}>{job.time_taken_ms === null || job.time_taken_ms === undefined ? 'N/A' : job.time_taken_ms}</td>
                      <td style={{ border: '1px solid #e0e0e0', padding: '8px 12px', textAlign: 'center' }}>
                        <button onClick={() => viewImage(job.id, 'original')} className="action-button">View</button>
                      </td>
                      <td style={{ border: '1px solid #e0e0e0', padding: '8px 12px', textAlign: 'center' }}>
                        {job.status === 'PROCESSED' && job.processed_image_path ? (
                          <button onClick={() => viewImage(job.id, 'processed')} className="action-button">View</button>
                        ) : 'N/A'}
                      </td>
                      <td style={{ border: '1px solid #e0e0e0', padding: '8px 12px', textAlign: 'center' }}>
                        {job.status === 'PROCESSED' && job.objects_found && JSON.parse(job.objects_found).length > 0 ? (
                          <button onClick={() => showObjectsModal(job.objects_found)} className="action-button">
                            {JSON.parse(job.objects_found).length} Objects
                          </button>
                        ) : (job.status === 'ERROR' && job.objects_found ? 'Error Info' : 'N/A')}
                      </td>
                      <td style={{ border: '1px solid #e0e0e0', padding: '8px 12px', fontWeight: 'bold', color: job.status === 'PROCESSED' ? 'green' : (job.status === 'ERROR' ? 'red' : (job.status === 'PROCESSING' ? 'orange' : '#555')) }}>
                        {job.status}
                      </td>
                    </tr>
                  ) : (
                    <tr key={`placeholder-${index}`} style={{ backgroundColor: index % 2 === 0 ? '#fff' : '#fbfcfc' }}>
                      <td style={{ border: '1px solid #e0e0e0', padding: '8px 12px', color: '#aaa' }}>{index + 1}</td>
                      <td style={{ border: '1px solid #e0e0e0', padding: '8px 12px', color: '#aaa' }} colSpan={9}>Awaiting job data...</td>
                    </tr>
                  )
                ))}
                {jobs.length === 0 && (summary.total_images_found > 0) &&
                  Array.from({ length: summary.total_images_found }).map((_, index) => (
                    <tr key={`empty-placeholder-${index}`} style={{ backgroundColor: index % 2 === 0 ? '#fff' : '#fbfcfc' }}>
                      <td style={{ border: '1px solid #e0e0e0', padding: '8px 12px', color: '#aaa' }}>{index + 1}</td>
                      <td style={{ border: '1px solid #e0e0e0', padding: '8px 12px', color: '#aaa' }} colSpan={9}>Waiting for processing to start...</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </section>

        {selectedObjects && (
          <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.6)', display: 'flex',
            alignItems: 'center', justifyContent: 'center', zIndex: 1000,
            padding: '20px'
          }}>
            <div style={{
              backgroundColor: 'white', padding: '25px', borderRadius: '8px',
              maxHeight: '85vh', overflowY: 'auto', minWidth: '320px',
              maxWidth: '600px', width: '100%', boxShadow: '0 5px 25px rgba(0,0,0,0.2)'
            }}>
              <h3 style={{ marginTop: 0, marginBottom: '15px', color: '#333', borderBottom: '1px solid #eee', paddingBottom: '10px' }}>Detected Objects</h3>
              <pre style={{
                whiteSpace: 'pre-wrap', wordBreak: 'break-all', backgroundColor: '#f0f2f5',
                padding: '15px', borderRadius: '5px', fontSize: '0.9em', color: '#2c3e50',
                maxHeight: 'calc(85vh - 150px)', overflowY: 'auto'
              }}>
                {JSON.stringify(selectedObjects, null, 2)}
              </pre>
              <button onClick={closeModal} style={{
                marginTop: '20px', padding: '10px 20px', cursor: 'pointer',
                backgroundColor: '#3498db', color: 'white', border: 'none',
                borderRadius: '5px', fontSize: '1em'
              }}>Close</button>
            </div>
          </div>
        )}

        {/* Global styles for action buttons, can also be in a global CSS file imported in _app.js */}
        <style jsx global>{`
          .action-button {
            padding: 6px 12px;
            font-size: 0.85em;
            cursor: pointer;
            background-color: #f0f8ff; /* AliceBlue */
            color: #1e90ff; /* DodgerBlue */
            border: 1px solid #add8e6; /* LightBlue */
            border-radius: 4px;
            transition: background-color 0.2s ease;
          }
          .action-button:hover {
            background-color: #e0f0ff;
          }
          .action-button:disabled {
            background-color: #f0f0f0;
            color: #aaa;
            cursor: not-allowed;
            border-color: #ddd;
          }
        `}</style>
      </div>
    </>
  );
}