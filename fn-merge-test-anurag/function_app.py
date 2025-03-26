import azure.functions as func
import logging
from blob_sharepoint_funcs import upload
from access_token import get_access_token
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path = "config.env")


logger = logging.getLogger('mergelists_logger')
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler("function_app.log")
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="get_list")
def upload_list(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing upload_list request.")

    # Try to get the "list_name" parameter from the query string or the request body.
    list_name = req.params.get("list_name")
    if not list_name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            list_name = req_body.get("list_name")

    if not list_name:
        return func.HttpResponse(
            "Please pass a 'list_name' parameter in the query string or in the request body.",
            status_code=400
        )

    # Define your container name (could also come from environment settings)
    container_name = os.getenv("container_name")

    try:
        # Call the upload function with the provided container_name and list_name.
        # Assume 'upload' returns a string (e.g., JSON data) that we want to return in the response.
        ACCESS_TOKEN = get_access_token()
        result = upload(ACCESS_TOKEN,container_name, list_name)
        if result == "List name is invalid or out of proccessing scope":
            return func.HttpResponse(result,status_code=400)
        else:   
            return func.HttpResponse(result, status_code=200,mimetype="application/json")
    except Exception as e:
        logging.error(f"Error in upload: {e}")
        return func.HttpResponse(
            f"Error during upload: {str(e)}",
            status_code=500
        )
