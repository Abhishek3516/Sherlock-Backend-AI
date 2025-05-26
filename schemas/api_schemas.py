from pydantic import BaseModel, Field
from typing import Optional, List


class ChatRequestBody(BaseModel):
    user_id: str = Field(
        ..., 
        examples=["uuid value"],
        description="Unique identifier for the user."
    )
    session_id: Optional[str] = Field(
        None, 
        examples=["uuid value"],
        description="Optional session identifier for conversation tracking"
    )
    doc_type_file_mapping: Optional[dict] = Field(
        None,
        examples=[{
                "doc type 1": ["file_001", "file_002"],
                "doc type 2": ["file_003", "file_004"]
            }],
            description="Mapping of document types to their corresponding file IDs."
            )
    doc_type: List[str] = Field(
        ...,
        examples=[["doc type 1", "doc type 2"]],
        description="List of document types to search within."
    )
    prompt: str = Field(
        ...,
        examples=["Ask question regarding uploaded files under selected doc type or folders."],
        description="User's question or prompt for the chat system"
    )

class UploadFilesResponse(BaseModel):
    status_code: int
    message: str
    data: List[dict]

class ManageOptionResponse(BaseModel):
    status_code: int
    data: dict

class ChatHistoryRespponse(BaseModel):
    status_code: int
    data: List[dict]