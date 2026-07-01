from typing import Optional, Dict, Any
from src.repositories.base import BaseRepository, serialize_doc


class ProductRepository(BaseRepository):
    def __init__(self):
        super().__init__("ProductMaster")

    async def get_by_code(self, product_code: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one({"ProductCode": product_code})
        return serialize_doc(doc)
