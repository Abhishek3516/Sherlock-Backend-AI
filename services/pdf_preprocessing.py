from PyPDF2 import PdfReader
from services.get_model import Call_Models
from services.vectorDB import PGVectorDB
from langchain_core.documents import Document
import tiktoken
import uuid
import os
import re
from glob import glob
from langchain_text_splitters import RecursiveCharacterTextSplitter

#Call Embedding model
model_call = Call_Models()
llm,embed = model_call.get_open_ai_model()

#Call VectorDB
open_vecDB = PGVectorDB(embed)
parent_vecDB = open_vecDB.call_vectorDB("parent_embedding")
child_vecDB = open_vecDB.call_vectorDB("child_embedding")

#Class to read PDF files
class PDF_reader:
    
    def __init__(self,doc_type):
        self.existing_ids = []
        self.emb_ctx_length = embed.embedding_ctx_length
        self.doc_type = doc_type

    def read_pdf(self,path):
        file = PdfReader(path)
        self.extracted_pages = [page.extract_text() for page in file.pages]
    
    def get_unique_id(self):
        new_id = str(uuid.uuid4())
        while new_id in self.existing_ids:
            new_id = str(uuid.uuid4())
            self.existing_ids.extend(new_id)
        return new_id

    def create_child_docs(self,page,parent_id, file_id):
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=50)
        child_chunks = text_splitter.split_text(page)

        for chunk in child_chunks:
            doc = Document(page_content = chunk,
                            metadata = {"file_id": file_id,
                                            "document_id":parent_id,
                                            "doc_type":self.doc_type})
            
            self.child_docs.append(doc)
            

    def create_parent_docs(self, file_id):
        self.parent_docs = []
        self.child_docs = []
        for ix,page in enumerate(self.extracted_pages):
            print("Page No {} processed out of {} pages".format(ix+1,len(self.extracted_pages)))
            #Create Id
            doc_id = self.get_unique_id()

            #Table identification
            page = self.table_identification(page)

            doc = Document(page_content = page,
                           metadata = {"file_id": file_id,
                                        "document_id":doc_id,
                                        "doc_type":self.doc_type})
            
            self.parent_docs.append(doc)
            
            #create child docs
            self.create_child_docs(page,doc_id, file_id)

    def table_identification(self,page_content,threshold=30):
        """
        Analyzes extracted PDF page content to determine if it likely contains tables
        based on the count of numeric values present.
        
        Args:
            page_content (str): The extracted text content from a PDF page
            threshold (int, optional): The minimum number of numeric values required 
                                    to classify as a table page. Defaults to 10.
        
        Returns:
            str: 'page contain tables' if number count exceeds threshold, else 'text page'
        """
     
        
        # This regex pattern matches integers, decimals, negative numbers, and scientific notation
        number_pattern = r'(?<!\w)[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?(?!\w)'
        
        # Find all numbers in the page content
        numbers = re.findall(number_pattern, page_content)
        
        # Count the numbers found
        number_count = len(numbers)
        
        # Determine if the page likely contains tables based on the threshold
        if number_count > threshold:
            page_content = self.table_processing(page_content)
        
        return page_content
    
    def table_processing(self,page_content):
        prompt = f"""
        You are given a text extract which possibly contains tables in some portion or table only in whole extract.
        Your job is to restructure the extract in such a way that text and tables are easy to interpret.
        Restructuring logic:
        1. Keep the text part(if it's there) as it is.
        2. Restructure the tables into dictionary(json)
        
        text extract:
        //
        {page_content}
        //

        //
        **Restructured output only**
        //

        """
        result = llm.invoke(prompt).content
        return result
                        
    def create_embeddings(self,filename):
        # pdf_path = f'.\saved_files\{user_id}'
        file_path = filename
        self.read_pdf(file_path)
        file_id = str(uuid.uuid4())
        self.create_parent_docs(file_id)
        
        parent_vecDB.add_documents(self.parent_docs) 
        child_vecDB.add_documents(self.child_docs)
    
    def tiktoken_encoder(self):
        self.encoding = tiktoken.get_encoding("o200k_base")


    def count_tokens(self,page):
        token_count = len(self.encoding.encode(page))
        return token_count

    def break_page_content(self):
        for page in self.extracted_pages:
            token_count = self.count_tokens(page)
            print(token_count)