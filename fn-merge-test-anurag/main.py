
import logging
from blob_sharepoint_funcs import upload
from access_token import get_access_token
from dotenv import load_dotenv
import os
ACCESS_TOKEN = get_access_token()
container_name = os.getenv("container_name")
result = upload(ACCESS_TOKEN,container_name, "Countries")
print(result)