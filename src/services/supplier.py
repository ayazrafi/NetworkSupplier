from bson import ObjectId
from datetime import datetime
from typing import Dict, Any, Tuple, List
from src.repositories.supplier import SupplierRepository
from src.repositories.workzone import WorkZoneRepository
from src.repositories.vehicle import VehicleRepository

class SupplierService:
    def __init__(self):
        self.repository = SupplierRepository()
        self.wz_repository = WorkZoneRepository()
        self.vehicle_repository = VehicleRepository()

    async def create(self, supplier_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        # Validate WorkZone exists
        wz = await self.wz_repository.get_by_id("WorkZoneId", supplier_data["WorkZoneId"])
        if not wz:
            raise ValueError(f"WorkZone with ID '{supplier_data['WorkZoneId']}' does not exist.")

        # Validate unique code
        existing = await self.repository.get_by_code(supplier_data["SupplierCode"])
        if existing:
            raise ValueError(f"Supplier with code '{supplier_data['SupplierCode']}' already exists.")

        # Validate allocated vehicles exist
        vehicles = supplier_data.get("Vehicles", []) or []
        for v in vehicles:
            vid = v["vehicleId"]
            if not await self.vehicle_repository.get_by_id("VehicleId", vid):
                raise ValueError(f"Vehicle with ID '{vid}' does not exist.")

        now = datetime.utcnow()
        supplier_data["SupplierId"] = str(ObjectId())
        supplier_data["CreatedBy"] = created_by
        supplier_data["CreatedDate"] = now
        supplier_data["UpdatedBy"] = created_by
        supplier_data["UpdatedDate"] = now

        return await self.repository.create(supplier_data)

    async def update(self, supplier_id: str, supplier_data: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("SupplierId", supplier_id)
        if not existing:
            raise KeyError(f"Supplier with ID '{supplier_id}' not found.")

        # Validate WorkZone if changing
        if "WorkZoneId" in supplier_data:
            wz = await self.wz_repository.get_by_id("WorkZoneId", supplier_data["WorkZoneId"])
            if not wz:
                raise ValueError(f"WorkZone with ID '{supplier_data['WorkZoneId']}' does not exist.")

        # Validate allocated vehicles if changing
        if "Vehicles" in supplier_data:
            vehicles = supplier_data.get("Vehicles", []) or []
            for v in vehicles:
                vid = v["vehicleId"]
                if not await self.vehicle_repository.get_by_id("VehicleId", vid):
                    raise ValueError(f"Vehicle with ID '{vid}' does not exist.")

        supplier_data["UpdatedBy"] = updated_by
        supplier_data["UpdatedDate"] = datetime.utcnow()

        updated_doc = await self.repository.update("SupplierId", supplier_id, supplier_data)
        if not updated_doc:
            raise RuntimeError("Failed to update Supplier record.")
        return updated_doc

    async def delete(self, supplier_id: str) -> bool:
        existing = await self.repository.get_by_id("SupplierId", supplier_id)
        if not existing:
            raise KeyError(f"Supplier with ID '{supplier_id}' not found.")
        return await self.repository.delete("SupplierId", supplier_id)

    async def get_by_id(self, supplier_id: str) -> Dict[str, Any]:
        existing = await self.repository.get_by_id("SupplierId", supplier_id)
        if not existing:
            raise KeyError(f"Supplier with ID '{supplier_id}' not found.")
        return existing

    async def get_list(
        self, 
        query: Dict[str, Any], 
        skip: int = 0, 
        limit: int = 10, 
        sort_by: str = "CreatedDate", 
        sort_order: int = -1
    ) -> Tuple[List[Dict[str, Any]], int]:
        return await self.repository.get_list(query, skip, limit, sort_by, sort_order)
        
    async def get_all(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        return await self.repository.get_all(query)
