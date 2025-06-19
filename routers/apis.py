from typing import List
from fastapi import APIRouter, File, Form, Request, UploadFile
import logging
import time
from src.utilities.auth_checker import AuthChecker
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

authorizer = AuthChecker()

@router.post(
        "/upload-files", 
        summary="Upload files",
        description="Upload multiple files for document processing with user and document type information"
    )
@decorators.log_requests
@authorizer.auth_required
async def upload_files(
                request:Request,
                folder: str = Form(...),
                files: List[UploadFile]= File(...)
            ):

    """
        Upload files and save embeddings into database with validation and error handling.
        
        - **folder**: Type of document being uploaded.
        - **files**: List of files to upload.
    """
    user_id = request.state.user_payload.get('sub')
    file_details, rejected_files = await api_service.upload_files_create_embeddings(files, folder, user_id)

    response = api_schemas.UploadFilesResponse(
                            status_code=201, 
                            message= f"Successfully uploaded and processed {len(file_details)} files.", 
                            data = {"excepted_files": file_details, "rejected_files": rejected_files}
                        )
    return response

@router.post(
        "/sherlock-conversation",
        summary="Chat with Sherlock AI.",
        description="Get AI-generated answers from uploaded PDF documents under selected doc types or folders."
    )
@decorators.log_requests
@authorizer.auth_required
async def chat(request:Request, user_request: api_schemas.ChatRequestBody):

    """
        Get answer to query from PDF documents.
    
        Process user queries against uploaded documents and return AI-generated responses.
    """
    user_id = request.state.user_payload.get('sub')
    result = await api_service.conversations(user_request, user_id)
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
@authorizer.auth_required
async def add_new_option(
            request:Request,
            folder_name: str 
        ):
    """
        Add a new document category option or folders.
        
        - **folder_name**: Name of the new category or folder to add.
    """
    user_id = request.state.user_payload.get('sub')
    response = await api_service.add_new_category(user_id, folder_name)

    return response


@router.get(
        "/manage-options",
        summary="Get list of user's created document categories or folders.",
        description="Retrieve all document type options for a user."
    )
@decorators.log_requests
@authorizer.auth_required
async def manage_options(
            request:Request
        ):
    """
        Get all document category options for a user.
        
        - **user_id**: ID of the user whose options to retrieve.
    """
    user_id = request.state.user_payload.get('sub')
    response = await api_service.manage_category(user_id)

    return response


@router.get(
        "/get-file-details",
        summary="Get file details by document type and user id.",
        description="Retrieve uploaded file details filtered by document type for particular user."
    )
@decorators.log_requests
@authorizer.auth_required
async def get_uploaded_file_details_by_doc_type(
            request:Request,
            folder: str 
        ):
    """
        Get uploaded file details filtered by document type.
        
        - **doc_type**: Type of documents to filter by.

    """
    user_id = request.state.user_payload.get('sub')
    response = await api_service.file_details_by_doc_type(user_id, folder)

    return response

@router.get(
        "/chat-history",
        summary="Get user's all chat history.",
        description="Retrieve all chat history for a user."
    )
@decorators.log_requests
@authorizer.auth_required
async def get_all_chat_history_by_user_id(
            request:Request
        ):
    """
        Get all chat history for a user.
        
        - **user_id**: ID of the user whose chat history to retrieve.
    """
    user_id = request.state.user_payload.get('sub')
    response = await api_service.get_chat_history(user_id)

    return response

@router.get(
        "/session-chat-history",
        summary="Get user's session chat history.",
        description="Retrieve session chat history for a user."
    )
@decorators.log_requests
@authorizer.auth_required
async def get_session_chat_history_by_session_id(
            request:Request,
            session_id: str
        ):
    """
        Get session chat history for a user.
        
        - **session_id**: ID of the session whose chat history to retrieve.
    """
    user_id = request.state.user_payload.get('sub')
    response = await api_service.get_session_chat_history(user_id, session_id)

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