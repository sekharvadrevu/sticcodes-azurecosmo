
import json
import requests
import logging
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
from dotenv import load_dotenv
from data_cleaning_anurag import merge_lists,clean_and_format_data
from typing import Any
import os
load_dotenv()
logger = logging.getLogger("tt_sharepoint_logger")

hostname = os.getenv("hostname")
sitepath = os.getenv("sitepath")
CONNECTION_STRING= os.getenv("CONNECTION_STRING")



def get_blob_service_client(connection_string):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
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
        raise e

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
        raise e

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
        raise e


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
    # upload uncleaned list data
    upload_list_to_blob(l1,container_name,f"uncleaned_lists/{item1_name}.json")
    # upload cleaned list data
    l1_cleaned = clean_and_format_data(json.loads(l1),compatible_list[0])
    upload_list_to_blob(l1_cleaned,container_name,f"cleaned_lists/{item1_name}.json")
    
    
    #list2
    l2 = get_list_details(ACCESS_TOKEN,compatible_list[1])
    item2_name = compatible_list[1].replace(" ","_")
    # uncleaned list data
    upload_list_to_blob(l2,container_name,f"uncleaned_lists/{item2_name}.json")
    # upload cleaned list data
    l2_cleaned = clean_and_format_data(json.loads(l2),compatible_list[1])
    upload_list_to_blob(l2_cleaned,container_name,f"cleaned_lists/{item2_name}.json")

    
    merged_data = merge_lists(json.loads(l1_cleaned), json.loads(l2_cleaned))  
    upload_list_to_blob(merged_data,container_name,f"cleaned_lists/{item1_name}_{item2_name}_merged.json")

    return merged_data
def upload(ACCESS_TOKEN,container_name:str, list1_name: str) -> Any: 
    
    
    #define what lists are compatible for merging
    compatible_lists = [
        ["Risk Register","Risk Mitigations"]
    ]
    

    # if list can be merged then upload the merged list
    for item in compatible_lists:
        if list1_name in item:
            upload_merged_data(ACCESS_TOKEN,item,container_name)
            return
    
    
    # upload the list if it cannot be merged
    l1 = get_list_details(ACCESS_TOKEN,list1_name)
    logging.info(f"{list1_name} cannot be merged with any other list. Uploading {list1_name} to blob.....")
    l1_cleaned = clean_and_format_data(json.loads(l1),list1_name)
    formatted_list1_name = list1_name.replace(" ","_") #Remove whitespace and replace with underscore
    # upload uncleaned data
    upload_list_to_blob(l1,container_name,f"uncleaned_lists/{formatted_list1_name}.json")
    # upload cleaned data
    upload_list_to_blob(l1_cleaned,container_name,f"cleaned_lists/{formatted_list1_name}.json")
                
    return 
    



def upload_sharepoint_lists(ACCESS_TOKEN,container_name):
    """
    Fetch predefined lists and upload it to blob

    Params:
    ACCESS_TOKEN-> required to access sharepoint list data
    container_name -> name of your blob container
    """

   
    
    lists_to_be_uploaded = ["Risk Register", "Risk Mitigations", "Follow up"]

    # get data from sharepoint
    for list_name in lists_to_be_uploaded:
        
        upload(ACCESS_TOKEN,container_name,list_name)

    return
