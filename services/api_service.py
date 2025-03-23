import os
import shutil

from fastapi import HTTPException, status
from services.pipline_run import *
from services.pdf_preprocessing import *
from services.user_doc_types import *


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

async def upload_files_conversation(files, doc_type, user_id):

    # Initialize PDF reader
    pdf_reader = PDF_reader(doc_type)

    # Process uploaded files
    newly_uploaded = []
    for uploaded_file in files:
        if not uploaded_file.filename.lower().endswith('.pdf'):
            continue
            
        file_name = uploaded_file.filename
        file_path = os.path.join(f"{UPLOAD_DIR}\{user_id}", file_name)
        # file_key = f"{doc_type}_{file_name}"

        # Record upload in database
        db_op.document_upload_info(file_name, user_id)

        # Create the directory structure if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        if not os.path.exists(file_path):
            await uploaded_file.seek(0)
            with open(file_path, "wb") as f:
                f.write(await uploaded_file.read())
            newly_uploaded.append(file_name)

    if newly_uploaded:
        for file_name in newly_uploaded:
            pdf_reader.create_embeddings(filename=file_path, user_id=user_id)
    
    return {
        "message": f"Successfully uploaded and processed {len(newly_uploaded)} files.",
        "uploaded_files": newly_uploaded
    }


async def add_new_category(user_id, new_option):

    db_op.update_table_data(user_id,new_option)

    return {
        "status_code": 200,
        "message": "Option added successfully!"
    }

async def manage_category(user_id):

    data = db_op.extract_table_data_by_user_id(user_id)

    return data

async def conversations(request):

    # Get answer
    response = inference_obj.get_answer(
        request.prompt, 
        selected_doc_type=request.doc_type, 
        user_id=request.user_id
    )

    return response

