from typing import List
from fastapi import APIRouter, File, Form, UploadFile
import logging
import time

from schemas import api_schemas
from services import api_service, decorators

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Router configuration
router = APIRouter(
    prefix="/v1",
    responses={
        404: {"description": "Resource not found"},
        422: {"description": "Validation error"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"}
    },
    tags=["Sherlock Application"],
)

@router.post(
        "/upload-files", 
        summary="Upload files and conversations",
        description="Upload multiple files for document processing with user and document type information"
    )
@decorators.log_requests
async def upload_files(
                doc_type: str = Form(...),
                user_id: str = Form(...),
                files: List[UploadFile]= File(...)
            ):

    """
        Upload files and save embeddings into database with validation and error handling.
        
        - **doc_type**: Type of document being uploaded.
        - **user_id**: ID of the user uploading files.
        - **files**: List of files to upload.
    """
    
    file_details = await api_service.upload_files_create_embeddings(files, doc_type, user_id)

    response = api_schemas.UploadFilesResponse(
                            status_code=201, 
                            message= f"Successfully uploaded and processed {len(response)} files.", 
                            data = file_details
                        )
    return response

@router.post(
        "/sherlock-conversation",
        summary="Chat with Sherlock AI.",
        description="Get AI-generated answers from uploaded PDF documents under selected doc types or folders."
    )
@decorators.log_requests
async def chat(request: api_schemas.ChatRequestBody):

    """
        Get answer to query from PDF documents.
    
        Process user queries against uploaded documents and return AI-generated responses.
    """
    
    result = await api_service.conversations(request)
    response = api_schemas.CommonResponse(
                                        status_code=200,
                                        data= result
                                    )

    return response

@router.post(
        "/add-option",
        summary="Add new document category",
        description="Add a new document type option for the user."
    )
@decorators.log_requests
async def add_new_option(
            user_id: str,
            new_option: str 
        ):
    """
        Add a new document category option or folders.
        
        - **user_id**: ID of the user adding the option.
        - **new_option**: Name of the new category or folder to add.
    """

    response = await api_service.add_new_category(user_id, new_option)

    return response


@router.get(
        "/manage-options",
        summary="Get list of user's created document categories or folders.",
        description="Retrieve all document type options for a user."
    )
@decorators.log_requests
async def manage_options(
            user_id: str 
        ):
    """
        Get all document category options for a user.
        
        - **user_id**: ID of the user whose options to retrieve.
    """

    response = await api_service.manage_category(user_id)

    return response


@router.get(
        "/get-file-details",
        summary="Get file details by document type and user id.",
        description="Retrieve uploaded file details filtered by document type for particular user."
    )
@decorators.log_requests
async def get_uploaded_file_details_by_doc_type(
            user_id: str,
            doc_type: str 
        ):
    """
        Get uploaded file details filtered by document type.
        
        - **user_id**: ID of the user whose files to retrieve.
        - **doc_type**: Type of documents to filter by.

    """

    response = await api_service.file_details_by_doc_type(user_id, doc_type)

    return response

@router.get(
        "/chat-history",
        summary="Get user's all chat history.",
        description="Retrieve all chat history for a user."
    )
@decorators.log_requests
async def get_all_chat_history_by_user_id(
            user_id: str
        ):
    """
        Get all chat history for a user.
        
        - **user_id**: ID of the user whose chat history to retrieve.
    """

    response = await api_service.get_chat_history(user_id)

    return response

# Health check endpoint
@router.get(
    "/health",
    summary="Health check",
    description="Check API health status",
    tags=["Health"]
)
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "timestamp": time.time()}