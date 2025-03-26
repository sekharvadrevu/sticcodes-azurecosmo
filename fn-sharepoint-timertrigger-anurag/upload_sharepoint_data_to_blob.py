
import json
import requests
import logging
from typing import List
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
from dotenv import load_dotenv
from typing import Any
import os
import re
load_dotenv(dotenv_path = "config.env")
logger = logging.getLogger('mergelists_logger')

hostname = os.getenv("hostname")
sitepath = os.getenv("sitepath")
CONNECTION_STRING= os.getenv("CONNECTION_STRING")

def get_blob_service_client(CONNECTION_STRING):
    try:
        blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
        return blob_service_client
    except Exception as e:
        raise e


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

def create_blob_container(blob_service_client:BlobServiceClient,container_name: str):
    """
    Create a blob container or return the existing container client if it exists.
    """
    try:
        container_client = blob_service_client.create_container(name=container_name)
    except ResourceExistsError:
        logger.info("A container with this name already exists.")
    except Exception as e:
        logger.error(f"Error creating blob container: {e}")
        raise e

def upload_list_to_blob(data,blob_service_client,container_name: str,blob_filename:str):
    """
    Retrieve, clean, merge data from SharePoint lists and upload the merged JSON to Azure Blob Storage.
    Cleaning should not be done for blob storage. That should be done after downloading from blob storage.
    """
    try:

        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_filename) 
        blob_client.upload_blob(data=data,overwrite=True)
    except Exception as e:
        raise e

def upload_lists(ACCESS_TOKEN,container_name):
    """
    Fetch predefined lists and upload it to blob

    Params:
    ACCESS_TOKEN-> required to access sharepoint list data
    container_name -> name of your blob container
    """

    blob_service_client = get_blob_service_client(CONNECTION_STRING)
    create_blob_container(blob_service_client,container_name)
    
    lists_to_be_uploaded = ["Risk Register", "Risk Mitigations", "Follow up"]

    # get data from sharepoint
    for list_name in lists_to_be_uploaded:
        list_data = get_list_details(ACCESS_TOKEN,list_name)
        list_name = list_name.replace(" ","_")
        upload_list_to_blob(list_data,blob_service_client,container_name,f"{list_name}.json")


