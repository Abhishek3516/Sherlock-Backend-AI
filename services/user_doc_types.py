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

    def document_upload_info(self, doc_name: str, user_id: str, doc_type: str):
        """
        Insert a new document upload entry into user_doc_upload_tbl.
        Ensures that the generated document ID (UUID) is unique.

        Args:
            doc_name (str): Name of the uploaded document.
            user_id (str): Unique User ID.
        """
        new_doc_id = str(uuid.uuid4())  # Generate a new UUID for the document
        while True:
            
            # Check if the generated doc_id already exists in the table
            if not self.check_doc_id_exists(new_doc_id):  # If doc_id does not exist, insert it
                query = """
                INSERT INTO public.user_doc_upload_tbl (user_id, doc_name, doc_id, doc_type) 
                VALUES (%s, %s, %s, %s);
                """

                try:
                    with self._get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute(query, (user_id, doc_name, new_doc_id, doc_type))
                        conn.commit()  # Commit the transaction
                    print(f"✅ New document inserted with doc_id: {new_doc_id}")
                except psycopg2.Error as e:
                    print(f"Error inserting document: {e}")      
                
                # break  # Exit the loop once a valid doc_id is inserted
            
            return new_doc_id
        

    def extract_doc_upload_table_data(self, user_id: str, doc_type: str) -> Dict[str, Any]:
        """
        Extract all upload doc data according to the given user id and doc type from user_doc_upload_tbl table.

        Returns:
             Dict[str, Any]: Query results formatted as a dictionary with user_id, doc_type, and doc_details.
        """
        query = """SELECT 
                    %s AS user_id, 
                    %s AS doc_type,
                    json_agg(
                        json_build_object(
                            'doc_name', doc_name,
                            'doc_id', doc_id
                        )
                    ) AS doc_details
                    FROM public.user_doc_upload_tbl 
                    WHERE user_id = %s AND doc_type = %s
                    GROUP BY 1, 2;
                """
        
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, (user_id, doc_type, user_id, doc_type))
                    result = cur.fetchall()
                    
                    # If there are no matching records, return the structure with an empty doc_details list
                    if not result:
                        return {
                            "user_id": user_id,
                            "doc_type": doc_type,
                            "doc_details": []
                        }
                    
                    return result[0]
                
        except psycopg2.Error as e:
            print(f"Error extracting data: {e}")
            raise HTTPException(status_code = status, detail = str(e))  
        
    def extract_all_chat_history_by_user_id(self, user_id):
        """
            Extract all chat history data according to the given user id from user_chat_history_table table.

            Returns:
                Dict[str, Any]: Query results formatted as a dictionary .
        """

        query = """
                    SELECT
                        user_id,
                        session_id,
                        doc_types,
                        response_content,
                        created_time
                    FROM (
                        SELECT
                            user_id,
                            session_id,
                            array_agg(DISTINCT unnested_doc_type ORDER BY unnested_doc_type) as doc_types,
                            (
                                SELECT json_agg(
                                    json_build_object('role', role_type, 'content', content_text)
                                    ORDER BY sort_order
                                )
                                FROM (
                                    SELECT 'user' as role_type, question as content_text,
                                        time_stamp, (time_stamp::text || '_1') as sort_order
                                    FROM public.chat_history_table t2
                                    WHERE t2.user_id = t1.user_id AND t2.session_id = t1.session_id
                                    UNION ALL
                                    SELECT 'assistant' as role_type, response as content_text,
                                        time_stamp, (time_stamp::text || '_2') as sort_order
                                    FROM public.chat_history_table t3
                                    WHERE t3.user_id = t1.user_id AND t3.session_id = t1.session_id
                                ) conversation_parts
                            ) as response_content,
                            MIN(time_stamp) as created_time
                        FROM (
                            SELECT 
                                user_id,
                                session_id,
                                time_stamp,
                                question,
                                response,
                                TRIM(unnest(string_to_array(doc_category, ','))) as unnested_doc_type
                            FROM public.chat_history_table
                            WHERE doc_category IS NOT NULL AND doc_category != ''
                        ) t1
                        WHERE t1.user_id = %s
                        GROUP BY user_id, session_id
                    ) grouped_data
                    ORDER BY user_id, session_id;
                """ 
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, (user_id,))
                    result = cur.fetchall()

                    if not result:
                        pass
                    return result
        except psycopg2.Error as e:
            print(f"Error extracting data: {e}")
            raise HTTPException(status_code = status, detail = str(e))