from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI,AzureOpenAIEmbeddings
import os

load_dotenv()

class Call_Models:
    def __init__(self):
        pass

    def get_open_ai_model(self):
        llm = AzureChatOpenAI(azure_deployment= "gpt-4o",
                          temperature=0)
        
        embed = AzureOpenAIEmbeddings(
                model=os.getenv("EMBEDDING_MODEL"),
                azure_endpoint=os.getenv("AZURE_ENDPOINT"),
                api_key=os.getenv("AZURE_API_KEY"),
                openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION")
            )
        
        return llm,embed


