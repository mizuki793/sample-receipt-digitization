from pymongo import MongoClient
from app.core.config import settings

mongo_client: MongoClient | None = None

def init_mongo_client():
    global mongo_client
    mongo_client = MongoClient(
        settings.MONGO_URL,
        maxPoolSize=10,
        minPoolSize=1
    )

def close_mongo_client():
    global mongo_client
    if mongo_client:
        mongo_client.close()