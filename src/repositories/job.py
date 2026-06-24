from typing import Optional, Dict, Any
from src.repositories.base import BaseRepository

class JobRepository(BaseRepository):
    def __init__(self):
        super().__init__("OptimizerJobs")

    async def get_next_pending(self) -> Optional[Dict[str, Any]]:
        # Retrieve the oldest pending job for FIFO processing
        doc = await self.collection.find_one(
            {"JobStatus": "Pending"}, 
            sort=[("CreatedDate", 1)]
        )
        if doc:
            doc["_id"] = str(doc["_id"])
            return doc
        return None
