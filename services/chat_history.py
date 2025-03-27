import os
from fastapi import HTTPException, status
from services.get_model import Call_Models
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import datetime

class ChatHistory:
    
    def __init__(self):
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

    def update_chat_history(self, user_id, session_id, doc_category, question, response):
        """
        Insert a new record into the chat history table.
        
        Parameters:
        session_id (str): Unique identifier for the chat session
        doc_category (str): Category of document being discussed
        question (str): User's question
        response (str): System's response
        time (datetime, optional): Timestamp of the interaction. Defaults to current time if None.
        
        Returns:
        bool: True if insertion was successful, False otherwise
        """
            
        # Use parameterized query to properly handle string values
        query = """
        INSERT INTO public.chat_history_table 
        (user_id, session_id, doc_category, question, response)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Pass values as a tuple to properly handle quoting and escaping
                    cur.execute(query, (user_id, session_id, doc_category, question, response))
                    conn.commit()
                    print(f"Successfully inserted record for session {session_id}.")
                    return True
        except psycopg2.Error as e:
            print(f"Error inserting data: {e}")
            # Print the actual query and parameters for debugging
            print(f"Query: {query}")
            print(f"Parameters: {(session_id, doc_category, question, response)}")
            raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail = str(e))
            
    def get_chat_history(self, doc_category=None, session_id=None):
        """
        Retrieve chat history from the database based on document category.
        Returns the 3 most recent entries in descending order of timestamp.
        
        Parameters:
        doc_category (str, optional): If provided, retrieves only chats from this category
        session_id (str, optional): If provided, retrieves only chats from this session
        
        Returns:
        pandas.DataFrame: Contains the retrieved chat history (max 3 records)
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = "SELECT * FROM public.chat_history_table WHERE 1=1"
                    params = []
                    
                    if doc_category:
                        query += " AND doc_category = %s"
                        params.append(doc_category)
                    
                    if session_id:
                        query += " AND session_id = %s"
                        params.append(session_id)
                    
                    query += " ORDER BY time_stamp DESC LIMIT 3"
                    
                    cur.execute(query, tuple(params))
                    results = cur.fetchall()
                    df_chat_history = pd.DataFrame(results) if results else pd.DataFrame()
                    return df_chat_history
        except psycopg2.Error as e:
            print(f"Error retrieving chat history: {e}")
            return pd.DataFrame()
