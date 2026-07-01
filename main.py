import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from passlib.hash import bcrypt

from src.config.environment import Environment
from src.config.db import DatabaseConnection
from src.config.logging import setup_logging
from src.workers.job_processor import job_processor_loop

# Import routers
from src.controllers import auth, bmc, plant, vehicle, organization, workzone, vehicletype, supplier, cluster, mapping, job, product

# Import error handlers
from src.middlewares.errors import (
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler
)

setup_logging()
logger = logging.getLogger(__name__)

async def seed_admin_on_startup():
    try:
        from datetime import datetime
        from bson import ObjectId
        db = DatabaseConnection.get_db()
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
            logger.info("Admin user seeded on startup successfully.")

        # Seed default organization
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
            logger.info("Default organization seeded on startup successfully.")
            
        # Seed default workzone
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
            logger.info("Default workzone seeded on startup successfully.")
    except Exception as e:
        logger.error(f"Error seeding admin and default organization/workzone on startup: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Database Connection
    await DatabaseConnection.connect()
    
    # 2. Seed Default Database entries
    await seed_admin_on_startup()
    
    # 3. Start Background Job processor worker
    app.state.job_processor_task = asyncio.create_task(job_processor_loop())
    logger.info("Lifespan setup completed successfully.")
    
    yield
    
    # 4. Cleanup background worker
    logger.info("Lifespan shutting down: Cancelling background processor...")
    app.state.job_processor_task.cancel()
    try:
        await app.state.job_processor_task
    except asyncio.CancelledError:
        pass
        
    # 5. Close DB
    await DatabaseConnection.close()

# Initialize FastAPI
app = FastAPI(
    title="Network Supplier API",
    description="Backend API project for route/network optimization of dairy supply chains.",
    version="1.0.0",
    docs_url=Environment.API_DOCS_PATH if Environment.SWAGGER_ENABLED else None,
    redoc_url=None,
    lifespan=lifespan
)

# Exception handlers registration
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Controllers / Routers
app.include_router(auth.router)
app.include_router(organization.router)
app.include_router(workzone.router)
app.include_router(bmc.router)
app.include_router(plant.router)
app.include_router(vehicle.router)
app.include_router(vehicletype.router)
app.include_router(supplier.router)
app.include_router(cluster.router)
app.include_router(mapping.sc_router)
app.include_router(mapping.vs_router)
app.include_router(mapping.vc_router)
app.include_router(mapping.bsc_router)
app.include_router(job.router)
app.include_router(product.router)

@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    return RedirectResponse(url=Environment.API_DOCS_PATH)

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on port {Environment.PORT}...")
    uvicorn.run("main:app", host="0.0.0.0", port=Environment.PORT, reload=True)
