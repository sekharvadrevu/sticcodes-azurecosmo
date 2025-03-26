import json
import requests
import logging
from typing import List
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
from dotenv import load_dotenv
from typing import Any
import os
from data_cleaning import merge_lists
from data_cleaning import clean_and_format_data
load_dotenv(dotenv_path = "config.env")
logger = logging.getLogger('mergelists_logger')

hostname = os.getenv("hostname")
sitepath = os.getenv("sitepath")
CONNECTION_STRING= os.getenv("CONNECTION_STRING")


# ------------------------------
# Blob and SharePoint Functions
# ------------------------------
def get_site_id(ACCESS_TOKEN):
    """
    Get site ID by calling the Microsoft Graph API.
    """
    try:
        site_id_url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:{sitepath}"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
        response = requests.get(url=site_id_url, headers=headers)
        response.raise_for_status()
        site_info = response.json()
        site_ids = site_info["id"].split(",")
        site_id = site_ids[1]
        return site_id
    except Exception as e:
        logger.error(f"Error getting site ID: {e}")
        raise 

def get_list_details(ACCESS_TOKEN,list_name: str):
    """
    Fetch list details from SharePoint using the Microsoft Graph API.
    """
    try:
        site_id = get_site_id(ACCESS_TOKEN)
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}/items?expand=fields"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers)
        logger.debug(f"Response status: {response.status_code}")
        response.raise_for_status()
        items = response.json().get("value", [])
        return json.dumps(items)
    except Exception as e:
        logger.error(f"Error getting list details for '{list_name}': {e}")
        return None

def create_blob_container(blob_service_client: BlobServiceClient, container_name: str):
    """
    Create a blob container or return the existing container client if it exists.
    """
    #create blob service client
    blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    try:
        container_client = blob_service_client.create_container(name=container_name)
    except ResourceExistsError:
        logger.info("A container with this name already exists.")
    except Exception as e:
        logger.error(f"Error creating blob container: {e}")
        raise

def download_blob(container_name:str,blob_filename:str):
    blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_filename)
    blob_data = blob_client.download_blob().readall()
    return json.loads(blob_data)

def upload_list_to_blob(data,container_name: str,blob_filename:str):
    """
    Retrieve, clean, merge data from SharePoint lists and upload the merged JSON to Azure Blob Storage.
    Cleaning should not be done for blob storage. That should be done after downloading from blob storage.
    """
    blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_filename) 

    blob_client.upload_blob(data=data,overwrite=True)

def upload_merged_data(ACCESS_TOKEN,compatible_list,container_name):
    #list1
    l1 = get_list_details(ACCESS_TOKEN,compatible_list[0])
    item1_name = compatible_list[0].replace(" ","_")
    l1_upload_data = upload_list_to_blob(l1,container_name,item1_name)
    l1_downloaded_data = download_blob(container_name,item1_name)
    
    
    #list2
    l2 = get_list_details(ACCESS_TOKEN,compatible_list[1])
    item2_name = compatible_list[1].replace(" ","_")
    l2_upload_data = upload_list_to_blob(l2,container_name,item2_name)
    l2_downloaded_data = download_blob(container_name,item2_name)
    merged_data = merge_lists(l1_downloaded_data, l2_downloaded_data)  


    upload_list_to_blob(json.dumps(merged_data),container_name,f"{item1_name}-{item2_name}-merged.json")

    return merged_data
def upload(ACCESS_TOKEN,container_name:str, list1_name: str, list2_name: str = None) -> Any: 
    
    #define what lists are compatible for merging
    compatible_lists = [
        ["Risk Register","Risk Mitigations"]
    ]
   
    if list2_name!=None:
        for item in compatible_lists:
            if list1_name and list2_name in item: # only checks if list1_name and list2_name are compatible
                return upload_merged_data(ACCESS_TOKEN,item,container_name)
        
        return f"{list1_name} and {list2_name} canot be merged"

    else:
        # if only list1_name arguement is given -> check if it is compatible with any other list and merge the data. if not -> return the cleaned data
        #for that list
        for item in compatible_lists:
            if list1_name in item:
                return upload_merged_data(ACCESS_TOKEN,item,container_name)
                

        # else continue with cleaning and uploading the single list
        l1 = get_list_details(ACCESS_TOKEN,list1_name)
        if l1 == None:
            return "List name is invalid"
        logging.info(f"{list1_name} cannot be merged with any other list. Uploading {list1_name} to blob.....")
        output_l1 = clean_and_format_data(json.loads(l1),list1_name)
        
        if output_l1 == None:
            return "list name is out of processing scope"
         
        formatted_list1_name = list1_name.replace(" ","_") #Remove whitespace and replace with underscore
        upload_list_to_blob(output_l1,container_name,f"{formatted_list1_name}.json")

        
        return output_l1
    


