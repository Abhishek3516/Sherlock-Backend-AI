import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import tempfile
import os
from dotenv import load_dotenv

load_dotenv()

# S3 configuration - you'll need to set these values
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")  # Replace with your S3 bucket name
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")  # Replace with your AWS access key
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")  # Replace with your AWS secret key
AWS_REGION = os.getenv("AWS_REGION")  # Replace with your preferred AWS region


# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

async def s3_file_exists(s3_key):
    """
    Check if file exists in S3 bucket
    
    Args:
        s3_key: S3 object key
    
    Returns:
        Boolean indicating if file exists
    """
    try:
        s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            # Handle other errors
            print(f"Error checking S3 file existence: {e}")
            return False


async def upload_to_s3(file_content, s3_key):
    """
    Upload file content to S3 bucket
    
    Args:
        file_content: File content as bytes
        s3_key: S3 object key
    
    Returns:
        Boolean indicating upload success
    """
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            ContentType='application/pdf'
        )
        print(f"File uploaded successfully to S3: {s3_key}")
        return True
    except NoCredentialsError:
        print("AWS credentials not available")
        return False
    except ClientError as e:
        print(f"Error uploading to S3: {e}")
        return False

async def download_s3_to_temp(s3_key):
    """
    Download file from S3 to temporary location
    
    Args:
        s3_key: S3 object key
    
    Returns:
        Temporary file path or None if failed
    """
    try:
        # Create temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
        
        # Download from S3
        with os.fdopen(temp_fd, 'wb') as temp_file:
            s3_client.download_fileobj(S3_BUCKET_NAME, s3_key, temp_file)
        
        return temp_path
    except ClientError as e:
        print(f"Error downloading from S3: {e}")
        return None