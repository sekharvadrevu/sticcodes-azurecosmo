import json
import requests
import logging
from typing import List
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
from dotenv import load_dotenv
from typing import Any
import os
# from data_cleaning import merge_lists
# from data_cleaning import clean_and_format_data
import re
load_dotenv(dotenv_path = "config.env")
logger = logging.getLogger('mergelists_logger')

CONNECTION_STRING= os.getenv("CONNECTION_STRING")


def map_to_sharepoint_list_name(list_name:str) -> Any:

    list_name = re.sub(r"\s+", "", list_name).lower()

    name_mapping = {"riskregister": "Risk Register",
                    "riskmitigations": "Risk Mitigations",
                    "followup": "Follow up"}
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
        return e
    

def blob_exists(container_name:str,blob_filename:str):
    blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(container_name)

    
    blob_list = container_client.list_blobs()
    for blob in blob_list:
        if blob_filename == blob.name:
            return True
    return False
    
def get_list_data(container_name:str, list1_name: str) -> Any: 
    
    # check for inconsistent cases like "Risk register/risk register" -> only handles whitespaces/tabs, does not handle special char
    list1_name = map_to_sharepoint_list_name(list1_name)
    if list1_name == None:
        return "List name is invalid or out of proccessing scope"
    #define what lists are compatible for merging
    compatible_lists = [
        ["Risk Register","Risk Mitigations"]
    ]
  
    for item in compatible_lists:
        if list1_name in item:
        
            item1_name = item[0].replace(" ","_")
            item2_name = item[1].replace(" ","_")
            if blob_exists(container_name,f"cleaned_lists/{item1_name}_{item2_name}_merged.json"):
                data = download_blob(container_name,f"cleaned_lists/{item1_name}_{item2_name}_merged.json")
                return data

              
    formatted_list1_name = list1_name.replace(" ","_")
    if blob_exists(container_name,f"cleaned_lists/{formatted_list1_name}.json"):
        data = download_blob(container_name,f"cleaned_lists/{formatted_list1_name}.json")
        
        return data
    else:
        return "Data not present"
    


