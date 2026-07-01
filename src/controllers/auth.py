from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from datetime import timedelta
from typing import Optional, Dict, Any
from passlib.hash import bcrypt
from src.config.db import DatabaseConnection
from src.utils.jwt import create_access_token
from src.middlewares.auth import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    username: str = Field(..., example="admin")
    password: str = Field(..., example="Password123!")
    organizationCode: str = Field("NET_SUP", example="NET_SUP")

class LoginResponseData(BaseModel):
    token: str
    user: dict

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

@router.post("/login", response_model=Dict[str, Any])
async def login(credentials: LoginRequest):
    db = DatabaseConnection.get_db()
    user = await db["Users"].find_one({
        "username": credentials.username,
        "organizationCode": credentials.organizationCode
    })
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or organization code"
        )
        
    if not bcrypt.verify(credentials.password, user["passwordHash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Decoded payload for request contexts
    user_payload = {
        "userId": user["userId"],
        "username": user["username"],
        "organizationId": user["organizationId"],
        "organizationCode": user["organizationCode"],
        "roleCode": user.get("roleCode", "ADMIN")
    }

    token = create_access_token(user_payload, expires_delta=timedelta(hours=24))
    
    return {
        "success": True,
        "message": "Login successful",
        "data": {
            "token": token,
            "user": {
                "id": user["userId"],
                "username": user["username"],
                "organizationCode": user["organizationCode"],
                "roleCode": user.get("roleCode", "ADMIN")
            }
        }
    }

@router.post("/seed", response_model=Dict[str, Any])
async def seed_database():
    from datetime import datetime
    from bson import ObjectId
    db = DatabaseConnection.get_db()
    
    # 1. Seed admin user
    admin_user = await db["Users"].find_one({"username": "admin"})
    if not admin_user:
        hashed_password = bcrypt.hash("Password123!")
        await db["Users"].insert_one({
            "userId": "usr_admin",
            "username": "admin",
            "passwordHash": hashed_password,
            "organizationId": "6582a8b9f0290e21703043ad",
            "organizationCode": "NET_SUP",
            "roleCode": "ADMIN"
        })
        user_message = "Default user seeded (admin / Password123!)."
    else:
        user_message = "Admin user already exists."
        
    # Clear other collections to remove legacy UUID data and ensure clean integration test run
    collections_to_clear = [
        "OrganizationMaster", "WorkZoneMaster", "BMCMaster", "PlantMaster",
        "VehicleMaster", "VehicleTypeMaster", "SupplierMaster", "ClusterMaster",
        "SupplierClusterMapping", "VehicleSupplierMapping", "VehicleClusterMapping",
        "BMCSupplierClusterMapping", "JobMaster"
    ]
    for coll in collections_to_clear:
        await db[coll].delete_many({})
        
    # 2. Seed default organization
    org = await db["OrganizationMaster"].find_one({"OrganizationId": ObjectId("6582a8b9f0290e21703043ad")})
    if not org:
        await db["OrganizationMaster"].delete_many({"OrganizationId": {"$in": ["6582a8b9f0290e21703043ad", ObjectId("6582a8b9f0290e21703043ad")]}})
        await db["OrganizationMaster"].insert_one({
            "OrganizationId": ObjectId("6582a8b9f0290e21703043ad"),
            "OrganizationCode": "NET_SUP",
            "OrganizationName": "Network Supplier Org",
            "Description": "Default seeded organization",
            "IsActive": True,
            "CreatedBy": "usr_admin",
            "CreatedDate": datetime.utcnow(),
            "UpdatedBy": "usr_admin",
            "UpdatedDate": datetime.utcnow()
        })
        org_message = "Default organization seeded."
    else:
        org_message = "Organization already exists."
        
    # 3. Seed default workzone
    wz = await db["WorkZoneMaster"].find_one({"WorkZoneId": ObjectId("6582a8b9f0290e21703043ae")})
    if not wz:
        await db["WorkZoneMaster"].delete_many({"WorkZoneId": {"$in": ["6582a8b9f0290e21703043ae", ObjectId("6582a8b9f0290e21703043ae")]}})
        await db["WorkZoneMaster"].insert_one({
            "WorkZoneId": ObjectId("6582a8b9f0290e21703043ae"),
            "WorkZoneCode": "WZ_DEFAULT",
            "WorkZoneName": "Default WorkZone",
            "OrganizationId": ObjectId("6582a8b9f0290e21703043ad"),
            "Description": "Default seeded workzone",
            "IsActive": True,
            "CreatedBy": "usr_admin",
            "CreatedDate": datetime.utcnow(),
            "UpdatedBy": "usr_admin",
            "UpdatedDate": datetime.utcnow()
        })
        wz_message = "Default workzone seeded."
    else:
        wz_message = "Workzone already exists."
        
    return {
        "success": True,
        "message": f"Database seeding completed successfully. {user_message} {org_message} {wz_message}",
        "data": None
    }
