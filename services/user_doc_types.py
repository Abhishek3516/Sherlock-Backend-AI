from fastapi import HTTPException, status
import psycopg2
from typing import List, Dict, Any
import pandas as pd
from psycopg2.extras import RealDictCursor
import uuid
import os 

class DatabaseOperations:
    def __init__(self):
        """
        Initialize database connection parameters.
        These values should match your PostgreSQL configuration.
        """
        self.conn_params = {
            "dbname": os.getenv("DATABASE_NAME"),   # Database name
            "user": os.getenv("DB_USER"),           # PostgreSQL username
            "password": os.getenv("DB_PASSWORD"),   # PostgreSQL password
            "host": os.getenv("HOST"),              # Database host
            "port": os.getenv("PORT")               # Default PostgreSQL port
        }

    def _get_connection(self):
        """
        Create and return a new database connection.
        Uses connection parameters stored in self.conn_params.
        """
        return psycopg2.connect(**self.conn_params)

    def extract_table_data(self) -> List[Dict[str, Any]]:
        """
        Extract all user_id and doc_type data from user_doc_type_tbl table.

        Returns:
            List[Dict[str, Any]]: Query results as a list of dictionaries.
        """
        query = """SELECT user_id, doc_type FROM public.user_doc_type_tbl;"""
        
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query)
                    results = cur.fetchall()
                    df = pd.DataFrame(results)  # Convert results to Pandas DataFrame
                    return df
        except psycopg2.Error as e:
            print(f"Error extracting data: {e}")
            return []
    
    def extract_table_data_by_user_id(self, user_id: str) -> Dict[str, Any]:
        """
        Extract all doc_type data according to the given user id from user_doc_type_tbl table.

        Returns:
            List[Dict[str, Any]]: Query results as a list of dictionaries.
        """
        query = """SELECT user_id, doc_type FROM public.user_doc_type_tbl WHERE user_id = %s;"""
        
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, (user_id, ))
                    results = cur.fetchall()
                    
                    # Initialize the result dictionary
                    formatted_result = {"user_id": user_id, "doc_type": []}
                
                    # Extract all doc_types into a list
                    if results:
                        formatted_result["doc_type"] = [row["doc_type"] for row in results]
                    
                    return formatted_result
                
        except psycopg2.Error as e:
            print(f"Error extracting data: {e}")

            raise HTTPException(status_code = status, detail = str(e))  

    def update_table_data(self, user_id: str, doc_type: str) -> None:
        """
        Insert a new record into user_doc_type_tbl table.

        Args:
            user_id (str): Unique User ID.
            doc_type (str): Document type associated with the user.
        """
        query = """
        INSERT INTO public.user_doc_type_tbl (user_id, doc_type) VALUES (%s, %s);
        """
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (user_id, doc_type))
                conn.commit()  # Commit the transaction after insertion
        except psycopg2.Error as e:
            print(f"Error inserting data: {e}")

    def check_doc_id_exists(self, doc_id: str) -> str:
        """
        Check if a specific document ID exists in the user_doc_upload_tbl table.

        Args:
            doc_id (str): Unique document ID.

        Returns:
            str: The existing doc_id if found, otherwise an empty string.
        """
        query = """
        SELECT doc_id FROM public.user_doc_upload_tbl 
        WHERE doc_id = %s;
        """

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (doc_id,))
                    result = cur.fetchone()
                    return result[0] if result else ""  # Return doc_id if exists, else empty string
        except psycopg2.Error as e:
            print(f"Error checking doc_id: {e}")
            return ""

    def document_upload_info(self, doc_name: str, user_id: str):
        """
        Insert a new document upload entry into user_doc_upload_tbl.
        Ensures that the generated document ID (UUID) is unique.

        Args:
            doc_name (str): Name of the uploaded document.
            user_id (str): Unique User ID.
        """
        while True:
            new_doc_id = str(uuid.uuid4())  # Generate a new UUID for the document
            
            # Check if the generated doc_id already exists in the table
            if not self.check_doc_id_exists(new_doc_id):  # If doc_id does not exist, insert it
                query = """
                INSERT INTO public.user_doc_upload_tbl (user_id, doc_name, doc_id) 
                VALUES (%s, %s, %s);
                """

                try:
                    with self._get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute(query, (user_id, doc_name, new_doc_id))
                        conn.commit()  # Commit the transaction
                    print(f"✅ New document inserted with doc_id: {new_doc_id}")
                except psycopg2.Error as e:
                    print(f"Error inserting document: {e}")      
                
                break  # Exit the loop once a valid doc_id is inserted
