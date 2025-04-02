import os
import logging
from openai import AzureOpenAI
from dotenv import load_dotenv
load_dotenv()
def get_client(model_name:str):
    """
    Returns an azure openai client instance. 

    Params:
    model_name -> To pass tha appropriate arguements into the client.
    o1 and gpt-4o have different api_version arguements.
    """
    try:
        chat_completion_models = ["gpt-4o"]
        reasoning_models = ["o1"]
        if model_name in chat_completion_models:
            logging.info(f"Model name : {model_name}")
            client = AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_INFERENCE_ENDPOINT"),
                api_key  = os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("OPENAI_CHAT_COMPLETION_API_VERSION")
            )
            return client    
        if model_name in reasoning_models:
            logging.info(f"Model name : {model_name}")
            client = AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_INFERENCE_ENDPOINT"),
                api_key  = os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("OPENAI_REASONING_API_VERSION")
            )

            return client

    except Exception as e:
        logging.error(f"Failed to connect to client. Error : {e}")
        return "Failed to connect to client"