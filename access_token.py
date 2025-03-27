import msal
import os
from dotenv import load_dotenv
import logging
# Load environment variables from .env file
load_dotenv(dotenv_path = ".env")
logger = logging.getLogger('tt_sharepoint_logger')


def get_access_token():
    CLIENT_ID = os.getenv("CLIENT_ID")
    AUTHORITY = os.getenv("AUTHORITY")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    SCOPE = ["https://graph.microsoft.com/.default"]

    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
    )

    result = app.acquire_token_for_client(scopes=SCOPE)

    if "access_token" in result:
        access_token = result["access_token"]
        logger.info("Access token acquired successfully.")
        return access_token
    else:
        logger.critical("Error acquiring token:")
        logger.error(result.get("error"))
        logger.error(result.get("error_description"))
        raise SystemExit("Failed to acquire access token; terminating program.")
