import logging
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
from dotenv import load_dotenv
from typing import Any
import os
import re
load_dotenv()
logger = logging.getLogger('mergelists_logger')
CONNECTION_STRING= os.getenv("Azure_CONNECTION_STRING")

def map_to_sharepoint_list_name(list_name:str) -> Any:

    list_name = re.sub(r"\s+", "", list_name).lower()

    name_mapping = {"riskregister": "Risk_Register",
                    "riskmitigations": "Risk_Mitigations",
                    "followup": "Follow_up"}
    if list_name in name_mapping:
        return name_mapping[list_name]
    return None

# -----------------------------
# Blob functions
#------------------------------
def download_blob(container_name:str,blob_filename:str):
    try:
        blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_filename)
        blob_data = blob_client.download_blob().readall()
        return blob_data
    except Exception as e:
        logger.error(f"Failed to download {blob_filename}. Error :{e}")
        return f"Failed to download {blob_filename}"
    

def blob_exists(container_name:str,blob_filename:str):
    try:

        blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(container_name)

        blob_list = container_client.list_blobs()
        for blob in blob_list:
            if blob_filename == blob.name:
                return True
        return False

    except Exception as e:
        logger.error(f"Error in getting blob list {e}")
        return False


def get_list_data(container_name:str, list1_name: str) -> Any: 
    
    # check for inconsistent cases like "Risk register/risk register" -> only handles whitespaces/tabs, does not handle special char
    list1_name = map_to_sharepoint_list_name(list1_name)
    if list1_name == None:
        return "List name is invalid or out of proccessing scope"
    #define what lists are compatible for merging
    compatible_lists = [
        ["Risk_Register","Risk_Mitigations"]
    ]
  
    for item in compatible_lists:
        if list1_name in item:
        
            item1_name = item[0]
            item2_name = item[1]
            if blob_exists(container_name,f"cleaned_lists/{item1_name}_{item2_name}_merged.json"):
                data = download_blob(container_name,f"cleaned_lists/{item1_name}_{item2_name}_merged.json")
                if data == f"Failed to download file":
                    return data
                return data

              
    if blob_exists(container_name,f"cleaned_lists/{list1_name}.json"):

        data = download_blob(container_name,f"cleaned_lists/{list1_name}.json")
        if data == "Failed to download file":
            return data
        return data
    else:
        return "Unable to retrieve requested file"
    


