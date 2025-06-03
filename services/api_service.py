import os
from typing import Optional
import PyPDF2
from io import BytesIO
from fastapi import HTTPException, status
from schemas import api_schemas
from services.pipline_run import *
from services.pdf_preprocessing import *
from services.user_doc_types import *
from services import s3_services, mongo_database
from pymongo.errors import PyMongoError
from bson import ObjectId
import logging

# Configure logging
logger = logging.getLogger(__name__)


# Define the upload directory
UPLOAD_DIR = "saved_files"
# Create directory if it doesn't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
db_op = DatabaseOperations()
options_data = db_op.extract_table_data()

#Inference object
inference_obj = RUN_Inference()

processed_files = {}

# Helper function to get available document types
def get_doc_types() -> List[str]:
    options_data = db_op.extract_table_data()
    if options_data is not None and 'doc_type' in options_data and not options_data['doc_type'].empty:
        return list(options_data['doc_type'])
    return []

# async def upload_files_create_embeddings(files, doc_type, user_id):

#     # Initialize PDF reader
#     pdf_reader = PDF_reader(doc_type)

#     # Process uploaded files
#     newly_uploaded = []
#     file_details = []
#     for uploaded_file in files:
#         if not uploaded_file.filename.lower().endswith('.pdf'):
#             continue
            
#         file_name = uploaded_file.filename
#         file_path = os.path.join(f"{UPLOAD_DIR}/{user_id}", file_name)
#         # file_key = f"{doc_type}_{file_name}"

#         # Record upload in database
#         file_id = db_op.document_upload_info(file_name, user_id, doc_type)

#         # Create the directory structure if it doesn't exist
#         os.makedirs(os.path.dirname(file_path), exist_ok=True)

#         if not os.path.exists(file_path):
#             await uploaded_file.seek(0)
#             with open(file_path, "wb") as f:
#                 f.write(await uploaded_file.read())
#             newly_uploaded.append({"file_path": file_path, "file_id": file_id})
#             file_details.append({"file_name": file_name, "file_id": file_id})

#     if newly_uploaded:
#         for file_var in newly_uploaded:
#             pdf_reader.create_embeddings(filename=file_var["file_path"], file_id=file_var["file_id"])
    
#     return file_details

########################################### Pages Limit Check Utility functions###############################

def get_user_details(user_id: str) -> Optional[Dict]:

    """
        Get user details from MongoDB users collection
        
        Args:
            user_id: User identifier
            
        Returns:
            User details dictionary or None if not found
    """

    try:
        user = mongo_database.users_collection.find_one({"user_id": user_id})
        return user
    except PyMongoError as e:
        print(f"Error fetching user details: {e}")
        return None
    
def get_pdf_page_count(file_content: bytes) -> int:

    """
        Get the number of pages in a PDF file
        
        Args:
            file_content: PDF file content as bytes
            
        Returns:
            Number of pages in the PDF
    """
    try:
        pdf_file = BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        return len(pdf_reader.pages)
    except Exception as e:
        print(f"Error reading PDF pages: {e}")
        return 0

async def files_upload_and_processing(files, doc_type, user_id):
    # Initialize PDF reader
    pdf_reader = PDF_reader(doc_type)
    # Process uploaded files
    newly_uploaded = []
    file_details = []
    rejected_files = []


    for uploaded_file in files:
        if not uploaded_file.filename.lower().endswith('.pdf'):
            continue

        file_content = await uploaded_file.read()

        file_name = uploaded_file.filename

        # Create S3 key with user_id prefix. 
        s3_key = f"{user_id}/{file_name}"

        # Check if file already exists in S3
        if not await s3_services.s3_file_exists(s3_key):
            # Upload file to S3
            await uploaded_file.seek(0)
            
            success = await s3_services.upload_to_s3(file_content, s3_key)

            # Record upload in database
            file_id = db_op.document_upload_info(file_name, user_id, doc_type)
            if success and file_id:
                newly_uploaded.append({"file_path": s3_key, "file_id": file_id})
                file_details.append({"file_name": file_name, "file_id": file_id})
        else:
            rejected_files.append(file_name)
    
    # Create embeddings for newly uploaded files
    if newly_uploaded:
        for file_var in newly_uploaded:

            # Download file from S3 to temporary location for processing
            temp_file_path = await s3_services.download_s3_to_temp(file_var["file_path"])
            if temp_file_path:
                try:
                    pdf_reader.create_embeddings(filename=temp_file_path, file_id=file_var["file_id"])
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)

    return file_details, rejected_files

def get_plan_details(plan_id) -> str:

    """
        Get plan details from MongoDB plans collection
        
        Args:
            plan_id: Plan identifier
            
        Returns:
            Plan name or None if not found
    """

    try:
        plan = mongo_database.plan_collection.find_one({"_id": ObjectId(plan_id)})
        return plan["plan_name"]
    except PyMongoError as e:
        print(f"Error fetching plan details: {e}")
        return None

##############################################################################################################


async def upload_files_create_embeddings(files, doc_type, user_id):
    """
        Upload files to S3 bucket and create embeddings with page count validation.
        
        Args:
            files: List of uploaded files
            doc_type(folder): Document or folder name
            user_id: User identifier
        
        Returns:
            Dict containing:
                - file_details: List of file details with file_name and file_id
                - rejected_files: List of rejected file names
                - status_code: 200/404/422 etc.
                - message: Status message
    """

    # 1. Get user details from MongoDB
    user_details = get_user_details(user_id)

    user_subs_status = user_details.get("status")
    uploaded_pages_count = user_details.get("uploaded_pages_count")

    plan_name = get_plan_details(user_details.get("current_subscriptions")["plan_id"])

    if not plan_name:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail= "The subscribed plan is not found.")

    if user_subs_status == "expired":
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail = "Please upgrade your subscription plan. The page upload limit has been exceeded.")

    # Calculate total pages in new files before processing
    total_new_pages = 0
    total_pages_count = 0
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            continue
        
        try:
            file_content = await file.read()
            pages_count = get_pdf_page_count(file_content)

            total_new_pages += pages_count

        except Exception as e:
            print(f"Error reading PDF {file.filename}: {e}")
            continue

    total_pages_count = uploaded_pages_count + total_new_pages
    if user_subs_status == "trial":
        if total_pages_count <= 15000:
            file_details, rejected_files = await files_upload_and_processing(files, doc_type, user_id)
            return file_details, rejected_files 
        else:
            raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail = "Please upgrade your subscription plan. The page upload limit has been exceeded.")
        
    elif user_subs_status == "active":
        if plan_name == "standard":
            if total_pages_count <= 15000:
                file_details, rejected_files = await files_upload_and_processing(files, doc_type, user_id)
                return file_details, rejected_files 
            else:
                raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail = "Please upgrade your subscription plan. The page upload limit has been exceeded.") 
            
        elif plan_name == "growth":
            if total_pages_count <= 50000:
                file_details, rejected_files = await files_upload_and_processing(files, doc_type, user_id)
                return file_details, rejected_files 
            else:
                raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail = "Please upgrade your subscription plan. The page upload limit has been exceeded.")
    
        elif plan_name == "scale":
            if total_pages_count <= 150000:
                file_details, rejected_files = await files_upload_and_processing(files, doc_type, user_id)
                return file_details, rejected_files 
            else:
                raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail = "Please upgrade your subscription plan. The page upload limit has been exceeded.")
        
        else:
            raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail= "Something went wrong, try again after sometime.")


async def add_new_category(user_id, new_option):

    db_op.update_table_data(user_id,new_option)

    response = api_schemas.CommonResponse(status_code=200, data="Option added successfully!")
    return response

async def manage_category(user_id):

    data = db_op.extract_table_data_by_user_id(user_id)
    response = api_schemas.ManageOptionResponse(status_code=200, data=data)
    return response


async def conversations(request):
    
    # Get answer
    response = inference_obj.get_answer(
        request.prompt, 
        selected_doc_type=request.folders, 
        user_id=request.user_id,
        session_id = request.session_id,
        doc_file_mapping = request.folder_file_mapping
    )

    return response

async def file_details_by_doc_type(user_id, doc_type):

    data = db_op.extract_doc_upload_table_data(user_id, doc_type)
    response = api_schemas.ManageOptionResponse(status_code=200, data=data)

    return response

async def get_chat_history(user_id):

    data = db_op.extract_all_chat_history_by_user_id(user_id)
    response = api_schemas.ChatHistoryRespponse(status_code=200, data=data)
    
    return response

async def get_session_chat_history(user_id, session_id):

    data = db_op.extract_session_chat_history_by_user_and_session_id(user_id, session_id)
    response = api_schemas.ChatHistoryRespponse(status_code=200, data=data)
    
    return response
