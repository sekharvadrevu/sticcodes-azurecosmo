import requests
import logging
import os
import io
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
from dotenv import load_dotenv

hostname = os.getenv("SITE_HOSTNAME")
sitepath = os.getenv("SITE_PATH")

def get_site_id(ACCESS_TOKEN):
    """
    Get site ID by calling the Microsoft Graph API

    Params:
    ACCESS_TOKEN -> Required to access sharepoint site
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
        logging.error(f"Error getting site ID: {e}")
        raise e
    
def get_drive_id(ACCESS_TOKEN,site_id):
    """
    Get drive id of document library 
    
    Params:
    ACCESS_TOKEN -> Required to access sharepoint site
    site_id -> Get the drive id in a specific site
    """
    try:
        drive_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
        response = requests.get(url=drive_url,headers=headers)
        response.raise_for_status()
        drive_info = response.json()

        for drive in drive_info.get("value"):
            if drive.get("name") == "Documents":
                return drive["id"]
        raise Exception("Drive not found")
    except Exception as e:
        logging.error(f"{e}")
        raise e
    


def download_pptx(ACCESS_TOKEN,file_path):
    """
    Pptx data will be stored in memory. There is no need to save the file. pptx library is able to 
    handle file like objects and the same actions can be performed on this file as it were a presentation.

    Params:
    ACCESS_TOKEN -> Required to access sharepoint site
    file_path -> path of the pptx file relative to "Documents" document library in sharepoint
    """
    try:
        site_id = get_site_id(ACCESS_TOKEN)
        drive_id = get_drive_id(ACCESS_TOKEN,site_id)
        file_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{file_path}:/content"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
        response = requests.get(url=file_url,headers=headers,allow_redirects=True)
        if response.status_code == 200:
            pptx_data = response.content
            pptx_file = io.BytesIO(pptx_data)
            return pptx_file
        elif response.status_code == 404:
            logging.error("Invalid file path")
            return "Invalid file path"
            
    except Exception as e:
        logging.error(f"Failed to write pptx data to memory.Error: {e}")
        raise e  

