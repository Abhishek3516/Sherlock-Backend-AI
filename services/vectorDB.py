from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector
from dotenv import load_dotenv
import os

load_dotenv()

class PGVectorDB:
    def __init__(self,embed):
        self.embed = embed
        self.connection = os.getenv("DATABASE_URL")  # Uses psycopg3!

    def call_vectorDB(self,collection_name):
        vector_store = PGVector(
            embeddings=self.embed,
            collection_name=collection_name,
            connection=self.connection,
            use_jsonb=True,
        )
        return vector_store
        


