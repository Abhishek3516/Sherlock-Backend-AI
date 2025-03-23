from typing import List
from fastapi import APIRouter, File, Form, UploadFile
import logging

from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services import api_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1",
    responses={404: {"description": "Not found"}},
    tags=["Sherlock Application"],
)

class ChatRequestBody(BaseModel):
    user_id: str
    doc_type: str
    prompt: str

@router.post("/upload-files")
async def upload_files_and_conversations(
                doc_type: str = Form(...),
                user_id: str = Form(...),
                files: List[UploadFile]= File(...)
            ):
    
    response = await api_service.upload_files_conversation(files, doc_type, user_id)

    return response

@router.post("/sherlock-conversation")
async def chat(request: ChatRequestBody):
    """Get answer to query from PDF documents"""

    response = await api_service.conversations(request)

    return response

@router.post("/add-option")
async def add_new_option(
            user_id: str,
            new_option: str 
        ):

    response = await api_service.add_new_category(user_id, new_option)

    return response


@router.get("/manage-options")
async def manage_options(
            user_id: str 
        ):

    response = await api_service.manage_category(user_id)

    return response
