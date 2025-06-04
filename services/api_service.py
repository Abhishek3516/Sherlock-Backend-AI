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
    
def update_page_count_by_user_id(user_id, total_pages_count):
    try:
        result = mongo_database.users_collection.update_one(
            {"user_id": user_id},  # Filter
            {"$set": {"uploaded_pages_count": total_pages_count}}  # Update operation
        )
        if result.matched_count > 0:
            print(f"Successfully updated {total_pages_count} for user {user_id}")
            return True
        else:
            print(f"No user found with user_id: {user_id}")
            return False
            
    except Exception as e:
        print(f"Error updating user field: {e}")
        return False

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

    # Plan limits configuration
    PLAN_LIMITS = {
        "trial": 15000,
        "active": {
            "standard": 15000,
            "growth": 50000,
            "scale": 150000
        }
    }

    try:
        # 1. Get user details from MongoDB
        user_details = get_user_details(user_id)

        user_subs_status = user_details.get("status")
        uploaded_pages_count = user_details.get("uploaded_pages_count", 0)

        plan_id = user_details.get("current_subscriptions", {}).get("plan_id")

        plan_name = get_plan_details(plan_id)

        if not plan_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The subscribed plan is not found."
                )

        if user_subs_status == "expired":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please subscribe any plans to continue."
            )
        
        # Determine page limit based on subscription status and plan
        if user_subs_status == "trial":
            page_limit = PLAN_LIMITS["trial"]
        elif user_subs_status == "active":
            if plan_name not in PLAN_LIMITS["active"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid subscription plan."
                )
            page_limit = PLAN_LIMITS["active"][plan_name]
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid subscription status."
            )

        # Calculate total pages in new files before processing
        total_new_pages = 0
        total_pages_count = 0
        for file in files:
            if not file.filename.lower().endswith('.pdf'):
                continue
            
            try:
                file_content = await file.read()
                total_new_pages += get_pdf_page_count(file_content)

            except Exception as e:
                print(f"Error reading PDF {file.filename}: {e}")
                continue

        total_pages_count = uploaded_pages_count + total_new_pages

        # Check page limit
        if total_pages_count > page_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please upgrade your subscription plan. The page upload limit has been exceeded."
            )
        
        # Update page count and process files
        if not update_page_count_by_user_id(user_id, total_pages_count):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Something went wrong, try again after sometime."
            )
        
        file_details, rejected_files = await files_upload_and_processing(files, doc_type, user_id)
        
        return file_details, rejected_files

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


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
