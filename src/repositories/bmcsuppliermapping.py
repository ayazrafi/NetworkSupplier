from typing import Optional, Dict, Any
from src.repositories.base import BaseRepository, serialize_doc

class BMCSupplierMappingRepository(BaseRepository):
    def __init__(self):
        super().__init__("BMCSupplierMapping")

    async def clear_and_insert_many(self, documents: list) -> int:
        await self.collection.delete_many({})
        if documents:
            result = await self.collection.insert_many(documents)
            return len(result.inserted_ids)
        return 0
