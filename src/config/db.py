import logging
from motor.motor_asyncio import AsyncIOMotorClient
from src.config.environment import Environment

logger = logging.getLogger(__name__)

class DatabaseConnection:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    async def connect(cls):
        try:
            logger.info("Connecting to MongoDB...")
            cls.client = AsyncIOMotorClient(Environment.MONGO_URI)
            cls.db = cls.client[Environment.MONGO_DB]
            # Ping database to verify connection
            await cls.client.admin.command('ping')
            logger.info("MongoDB Connected successfully!")
        except Exception as e:
            logger.error(f"Database Connection Failed: {e}")
            raise e

    @classmethod
    def get_db(cls):
        if cls.db is None:
            raise RuntimeError("Database not initialized. Call connect() first.")
        return cls.db

    @classmethod
    async def close(cls):
        if cls.client:
            cls.client.close()
            logger.info("MongoDB connection closed.")
