from typing import List, Optional, Dict, Any, Tuple
from bson import ObjectId
from src.config.db import DatabaseConnection

def convert_field_val(field: str, val: Any) -> Any:
    if field in ("OrganizationId", "WorkZoneId", "_id") and isinstance(val, str):
        try:
            return ObjectId(val)
        except Exception:
            pass
    return val

def convert_id_fields(data: Any) -> Any:
    if isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            if k in ("OrganizationId", "WorkZoneId", "_id") and isinstance(v, str):
                try:
                    new_dict[k] = ObjectId(v)
                except Exception:
                    new_dict[k] = v
            elif isinstance(v, (dict, list)):
                new_dict[k] = convert_id_fields(v)
            else:
                new_dict[k] = v
        return new_dict
    elif isinstance(data, list):
        return [convert_id_fields(item) for item in data]
    return data

def convert_id_fields_to_str(data: Any) -> Any:
    if isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            if k in ("OrganizationId", "WorkZoneId", "_id") and isinstance(v, ObjectId):
                new_dict[k] = str(v)
            elif isinstance(v, (dict, list)):
                new_dict[k] = convert_id_fields_to_str(v)
            else:
                new_dict[k] = v
        return new_dict
    elif isinstance(data, list):
        return [convert_id_fields_to_str(item) for item in data]
    return data

def convert_query_ids(query: Any) -> Any:
    if isinstance(query, dict):
        new_query = {}
        for k, v in query.items():
            if k in ("OrganizationId", "WorkZoneId", "_id"):
                if isinstance(v, str):
                    try:
                        new_query[k] = ObjectId(v)
                    except Exception:
                        new_query[k] = v
                elif isinstance(v, dict):
                    new_query[k] = convert_query_ids(v)
                elif isinstance(v, list):
                    new_list = []
                    for item in v:
                        if isinstance(item, str):
                            try:
                                new_list.append(ObjectId(item))
                            except Exception:
                                new_list.append(item)
                        else:
                            new_list.append(item)
                    new_query[k] = new_list
                else:
                    new_query[k] = v
            elif k.startswith("$") or isinstance(v, (dict, list)):
                new_query[k] = convert_query_ids(v)
            else:
                new_query[k] = v
        return new_query
    elif isinstance(query, list):
        return [convert_query_ids(item) for item in query]
    return query

def serialize_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if doc:
        doc["_id"] = str(doc["_id"])
        return convert_id_fields_to_str(doc)
    return None


class BaseRepository:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    @property
    def collection(self):
        # Dynamically fetch DB reference to avoid importing before db is initialized
        return DatabaseConnection.get_db()[self.collection_name]

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        cleaned_data = convert_id_fields(data)
        result = await self.collection.insert_one(cleaned_data)
        cleaned_data["_id"] = str(result.inserted_id)
        return convert_id_fields_to_str(cleaned_data)

    async def update(self, id_field: str, id_val: Any, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        query_val = convert_field_val(id_field, id_val)
        cleaned_data = convert_id_fields(data)
        if id_field in cleaned_data:
            del cleaned_data[id_field]
        result = await self.collection.update_one({id_field: query_val}, {"$set": cleaned_data})
        if result.modified_count > 0 or result.matched_count > 0:
            return await self.get_by_id(id_field, id_val)
        return None

    async def delete(self, id_field: str, id_val: Any) -> bool:
        query_val = convert_field_val(id_field, id_val)
        result = await self.collection.delete_one({id_field: query_val})
        return result.deleted_count > 0

    async def get_by_id(self, id_field: str, id_val: Any) -> Optional[Dict[str, Any]]:
        query_val = convert_field_val(id_field, id_val)
        doc = await self.collection.find_one({id_field: query_val})
        return serialize_doc(doc)

    async def get_list(
        self, 
        query: Dict[str, Any], 
        skip: int = 0, 
        limit: int = 10, 
        sort_by: str = "CreatedDate", 
        sort_order: int = -1
    ) -> Tuple[List[Dict[str, Any]], int]:
        cleaned_query = convert_query_ids(query)
        cursor = self.collection.find(cleaned_query).sort(sort_by, sort_order).skip(skip).limit(limit)
        docs = []
        async for doc in cursor:
            docs.append(serialize_doc(doc))
        total = await self.collection.count_documents(cleaned_query)
        return docs, total
        
    async def get_all(self, query: Dict[str, Any], sort_by: str = "CreatedDate", sort_order: int = -1) -> List[Dict[str, Any]]:
        cleaned_query = convert_query_ids(query)
        cursor = self.collection.find(cleaned_query).sort(sort_by, sort_order)
        docs = []
        async for doc in cursor:
            docs.append(serialize_doc(doc))
        return docs
