from pymongo import MongoClient
import urllib.parse
from dotenv import load_dotenv
import os
load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
mongodb_uri = f"{MONGODB_URL}&ssl=true&ssl_cert_reqs=CERT_NONE"

port = 8000
client = MongoClient(mongodb_uri, port)
db = client["sherlock-db-uat"]
users_collection = db["sherlock-users"]
plan_collection = db["plans"]