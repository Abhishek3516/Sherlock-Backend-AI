from pymongo import MongoClient
import urllib.parse

MONGODB_URL = "mongodb+srv://ksatyam1729:s8xaHOnUQevmyq1k@ravian-cluster.ulapr.mongodb.net/sherlock-db-uat?retryWrites=true&w=majority"
mongodb_uri = f"{MONGODB_URL}&ssl=true&ssl_cert_reqs=CERT_NONE"
port = 8000
client = MongoClient(mongodb_uri, port)
db = client["sherlock-db-uat"]
users_collection = db["user-details"]
plan_collection = db["plans"]