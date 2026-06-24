import os
from dotenv import load_dotenv

# Load standard .env file if it exists
load_dotenv()

class Environment:
    PORT = int(os.getenv("PORT", 3056))
    NODE_ENV = os.getenv("NODE_ENV", "development")
    
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://mfimongomaster:mongomongo%26*@localhost:27018/")
    MONGO_DB = os.getenv("MONGO_DB", "Network-Planner")
    
    JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-network-supplier")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    SWAGGER_ENABLED = os.getenv("SWAGGER_ENABLED", "true").lower() == "true"
    API_DOCS_PATH = os.getenv("API_DOCS_PATH", "/docs")

    @classmethod
    def is_production(cls) -> bool:
        return cls.NODE_ENV == "production"

    @classmethod
    def is_development(cls) -> bool:
        return cls.NODE_ENV == "development"
