import logging
from blob_sharepoint_funcs import get_list_data
#from access_token import get_access_token
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path = "config.env")

logger = logging.getLogger('mergelists_logger')
list_name="Risk Register"
container_name = os.getenv("container_name")
result = get_list_data(container_name, list_name)