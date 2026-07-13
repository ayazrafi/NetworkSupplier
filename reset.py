import asyncio
from src.config.db import DatabaseConnection
from src.repositories.request import OptimizationRequestsRepository
async def main():
    await DatabaseConnection.connect()
    repo = OptimizationRequestsRepository()
    await repo.collection.update_many({"status": {"$in": ["Failed", "InProgress"]}}, {"$set": {"status": "Pending"}})
    print("Reset done")
asyncio.run(main())
