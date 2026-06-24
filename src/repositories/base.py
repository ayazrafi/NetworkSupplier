from typing import List, Optional, Dict, Any, Tuple
from src.config.db import DatabaseConnection

class BaseRepository:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    @property
    def collection(self):
        # Dynamically fetch DB reference to avoid importing before db is initialized
        return DatabaseConnection.get_db()[self.collection_name]

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = await self.collection.insert_one(data)
        # Add string version of ObjectId in case it's needed
        data["_id"] = str(result.inserted_id)
        return data

    async def update(self, id_field: str, id_val: Any, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        result = await self.collection.update_one({id_field: id_val}, {"$set": data})
        if result.modified_count > 0 or result.matched_count > 0:
            return await self.get_by_id(id_field, id_val)
        return None

    async def delete(self, id_field: str, id_val: Any) -> bool:
        result = await self.collection.delete_one({id_field: id_val})
        return result.deleted_count > 0

    async def get_by_id(self, id_field: str, id_val: Any) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one({id_field: id_val})
        if doc:
            doc["_id"] = str(doc["_id"])
            return doc
        return None

    async def get_list(
        self, 
        query: Dict[str, Any], 
        skip: int = 0, 
        limit: int = 10, 
        sort_by: str = "CreatedDate", 
        sort_order: int = -1
    ) -> Tuple[List[Dict[str, Any]], int]:
        cursor = self.collection.find(query).sort(sort_by, sort_order).skip(skip).limit(limit)
        docs = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            docs.append(doc)
        total = await self.collection.count_documents(query)
        return docs, total
        
    async def get_all(self, query: Dict[str, Any], sort_by: str = "CreatedDate", sort_order: int = -1) -> List[Dict[str, Any]]:
        cursor = self.collection.find(query).sort(sort_by, sort_order)
        docs = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            docs.append(doc)
        return docs
