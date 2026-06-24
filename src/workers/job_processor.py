import asyncio
import os
import logging
from datetime import datetime
from src.services.job import JobService, OUTPUT_DIR
from src.services.optimizer import OptimizerService

logger = logging.getLogger(__name__)

async def job_processor_loop():
    logger.info("Background job processor loop started.")
    job_service = JobService()
    
    while True:
        try:
            # Query for next pending job (FIFO order)
            pending_job = await job_service.repository.get_next_pending()
            if pending_job:
                job_id = pending_job["JobId"]
                logger.info(f"Picking up job {job_id} for processing.")
                
                # Mark as InProgress
                await job_service.update(job_id, {
                    "JobStatus": "InProgress",
                    "StartedDate": datetime.utcnow()
                })
                
                input_path = pending_job["UploadedFilePath"]
                output_filename = f"results_{job_id}.xlsx"
                output_path = os.path.join(OUTPUT_DIR, output_filename)
                
                try:
                    result = await OptimizerService.process_job(job_id, input_path, output_path)
                    
                    # Mark as Completed
                    await job_service.update(job_id, {
                        "JobStatus": "Completed",
                        "TotalRecords": result["total_records"],
                        "ProcessedRecords": result["processed_records"],
                        "ResultFilePath": output_path,
                        "CompletedDate": datetime.utcnow()
                    })
                    logger.info(f"Job {job_id} processed successfully.")
                except Exception as ex:
                    logger.error(f"Job {job_id} execution failed: {ex}", exc_info=True)
                    await job_service.update(job_id, {
                        "JobStatus": "Failed",
                        "ErrorMessage": str(ex),
                        "CompletedDate": datetime.utcnow()
                    })
            else:
                # No pending jobs, poll every 5 seconds
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            logger.info("Background job processor loop received cancel signal.")
            break
        except Exception as e:
            logger.error(f"Exception in job processor loop: {e}", exc_info=True)
            await asyncio.sleep(5)
