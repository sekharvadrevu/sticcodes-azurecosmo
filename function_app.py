import azure.functions as func
import datetime
import json
import logging
import os
import msal
import requests
from azure.cosmos import CosmosClient
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient
from azure.functions import FunctionApp, HttpRequest, HttpResponse

from httpTrigger_funcs_anurag import get_list_data
from timertrigger_funcs_anurag import upload_sharepoint_lists
load_dotenv()

COSMOSDB_ENDPOINT = os.getenv("cosmoendpoint")
COSMOSDB_KEY = os.getenv("COSMOS_KEY")
COSMOS_DB_NAME = os.getenv("COSMOS_DB_NAME")
COSMOS_CONTAINER_NAME = os.getenv("COSMOS_CONTAINER_NAME")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")  # Azure OpenAI endpoint
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY") 
Azure_OPENAI_VERSION=os.getenv("Azure_openaiVersion")
Azure_DEPLOYMENT_NAME=os.getenv("Azure_DEPLOYMENT_NAME")
client = CosmosClient(COSMOSDB_ENDPOINT, COSMOSDB_KEY)
database = client.get_database_client(COSMOS_DB_NAME)
container = database.get_container_client(COSMOS_CONTAINER_NAME)
client_openai = AzureOpenAI(
    api_version=Azure_OPENAI_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
)
#endpoint for sharepoint vishnu
SECONDARY_LISTS = ["Risk Mitigations"]

CONTAINER_NAME = os.getenv("AZure_CONTAINER_NAME")

CONNECTION_STRING = os.getenv("Azure_CONNECTION_STRING")
CLIENT_ID = os.getenv("CLIENT_ID")
AUTHORITY = os.getenv("AUTHORITY")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SCOPE = [os.getenv("SCOPE")]
SITE_HOSTNAME = os.getenv("SITE_HOSTNAME")
SITE_PATH = os.getenv("SITE_PATH")

def get_access_token():
    """Acquires an app-only access token using MSAL."""
    app_msal = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )
    token_response = app_msal.acquire_token_for_client(scopes=SCOPE)
    if "access_token" in token_response:
        logging.info("Access token acquired.")
        return token_response["access_token"]
    else:
        raise Exception("Access token could not be obtained")

def get_site_id(access_token):
    """Retrieves the SharePoint site ID from Microsoft Graph."""
    url = f"https://graph.microsoft.com/v1.0/sites/{SITE_HOSTNAME}:{SITE_PATH}"
    headers = {"Authorization": f"Bearer {access_token}"}
    logging.info(f"get_site_id() URL: {url}")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    site_info = response.json()
    if not site_info.get("id"):
        raise Exception("Site ID not found in response.")
    return site_info["id"]

def get_list_details(listname, access_token):
    
    site_id = get_site_id(access_token)
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{listname}/items?expand=fields"
    headers = {"Authorization": f"Bearer {access_token}"}
    logging.info(f"Retrieving list '{listname}' from URL: {url}")
    response = requests.get(url, headers=headers)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        if response.status_code == 404:
            raise Exception(f"List '{listname}' not found. Please check the list name.")
    data = response.json()
    if data is None:
        raise Exception(f"No data returned for list '{listname}'.")
    return data

def clean_data(data):
    """Recursively cleans the data by removing unwanted values and characters."""
    if isinstance(data, dict):
        cleaned_dict = {}
        for key, value in data.items():
            cleaned_value = clean_data(value)
            if cleaned_value is not None and cleaned_value != "":
                cleaned_dict[key] = cleaned_value
        return cleaned_dict
    elif isinstance(data, list):
        return [clean_data(item) for item in data if clean_data(item) not in (None, "")]
    elif isinstance(data, str):
        data = data.replace(";", "")
        data = data.replace("#Name?", "Name")
        return data
    else:
        return data

def convert_numeric(data):
    """Recursively converts numeric strings to numbers and converts 'no' to 0."""
    if isinstance(data, dict):
        return {k: convert_numeric(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_numeric(item) for item in data]
    elif isinstance(data, str):
        if data.strip().lower() == "no":
            return 0
        try:
            int_val = int(data)
            if str(int_val) == data:
                return int_val
        except ValueError:
            pass
        try:
            float_val = float(data)
            if "." in data or "e" in data.lower():
                return float_val
        except ValueError:
            pass
        return data
    else:
        return data

def create_blob_container(blob_service_client, container_name):
    """Creates an Azure Blob Storage container if it does not already exist."""
    try:
        blob_service_client.create_container(name=container_name)
        logging.info(f"Container '{container_name}' created successfully.")
    except ResourceExistsError:
        logging.info(f"Container '{container_name}' already exists.")

def remove_unwanted_fields(data, unwanted_keys=["@odata.context", "@odata.etag", "eTag", "webUrl", "fields@odata.context"]):
    """Recursively removes unwanted keys from the JSON data."""
    if isinstance(data, dict):
        return {k: remove_unwanted_fields(v, unwanted_keys) for k, v in data.items() if k not in unwanted_keys}
    elif isinstance(data, list):
        return [remove_unwanted_fields(item, unwanted_keys) for item in data]
    else:
        return data

def get_merged_json(merged_data):
    """Cleans merged data and returns it as a formatted JSON string."""
    merged_data = remove_unwanted_fields(merged_data)
    cleaned_data = clean_data(merged_data)
    converted_data = convert_numeric(cleaned_data)
    return json.dumps(converted_data, indent=2)

def filter_mitigation_fields(mitigation_fields):
   
    allowed_keys = [
        "ResponsePlan", "RiskId", "ResponseDate",
        "ResponseOwnerEmail", "id", "ContentType", "Modified", "Created",
        "AuthorLookupId", "EditorLookupId", "Attachments", "ItemChildCount",
        "FolderChildCount","ResponseOwner"
    ]
    return {k: mitigation_fields[k] for k in allowed_keys if k in mitigation_fields}

def merge_multiple_lists(primary_data, secondary_list_names, access_token):
   
    reg_list = primary_data.get("value", [])
    aggregated_sec_index = {}
    for sec_name in secondary_list_names:
        sec_data = get_list_details(sec_name, access_token)
        for record in sec_data.get("value", []):
            fields = record.get("fields", {})
            risk_id = fields.get("RiskId")
            if risk_id is not None:
                try:
                    risk_id_str = str(int(float(risk_id)))
                except Exception:
                    risk_id_str = str(risk_id)
                aggregated_sec_index.setdefault(risk_id_str, []).append(filter_mitigation_fields(fields))
    
    new_list = []
    for record in reg_list:
        reg_id = record.get("id")
        if "fields" in record:
            primary_fields = record["fields"].copy()
            primary_fields["id"] = reg_id
        else:
            primary_fields = {"id": reg_id}
# Only add "mitigations" if matching secondary records are found.
        if reg_id and aggregated_sec_index.get(str(reg_id)):
            primary_fields["mitigations"] = aggregated_sec_index.get(str(reg_id))
        new_list.append(primary_fields)
    
    return new_list

def find_matching_list_name(sharepoint_list_name, access_token):
    """Retrieve all SharePoint lists and return the correctly-cased name matching the given name (ignores spaces and case)."""
    site_id = get_site_id(access_token)
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    normalized_input_name = sharepoint_list_name.replace(" ", "").lower()
    
    all_lists = response.json().get("value", [])
    for lst in all_lists:
        normalized_list_name = lst["name"].replace(" ", "").lower()
        if normalized_list_name == normalized_input_name:
            return lst["name"]  
    
    raise Exception(f"List '{sharepoint_list_name}' not found.")


def upload(container_name, sharepoint_list_name, upload_to_blob=True):
    access_token = get_access_token()

    correct_list_name = find_matching_list_name(sharepoint_list_name, access_token)

    blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    create_blob_container(blob_service_client, container_name)

    primary_data = get_list_details(correct_list_name, access_token)

    if primary_data.get("value"):
        merged_data = merge_multiple_lists(primary_data, SECONDARY_LISTS, access_token)
    else:
        merged_data = primary_data

    merged_json = get_merged_json(merged_data)

    if upload_to_blob:
        change_list_name = correct_list_name.replace(" ", "_")
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=f"{change_list_name}_lists_merged.json"
        )
        blob_client.upload_blob(merged_json, overwrite=True)
        logging.info(f"Uploaded data to Azure Blob Storage as {change_list_name}_lists_merged.json.")

    return merged_json

app = func.FunctionApp()
#Vishnu endpoint
@app.route(route="get_sharepoint_data", methods=["GET"])
def get_sharepoint_data(req: HttpRequest) -> HttpResponse:
    logging.info("Processing get_sharepoint_data request.")
    
    sharepoint_list_name = req.params.get("sharepoint_list_name")
    upload_to_blob = req.params.get("upload_to_blob", "true").lower() == "true"
    return_response = req.params.get("return_response", "true").lower() == "true"

    if not sharepoint_list_name:
        return func.HttpResponse(
            "Please pass a 'list_name' parameter in the query string or in the request body.",
            status_code=400
        )

    try:
        result = upload(CONTAINER_NAME, sharepoint_list_name, upload_to_blob=upload_to_blob)

        if return_response:
            return func.HttpResponse(result, status_code=200, mimetype="application/json")
        else:
            return func.HttpResponse(f"Data uploaded to container '{CONTAINER_NAME}' successfully.",status_code=200 )

    except Exception as e:
        logging.error(f"Error: {e}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=404)
    
#ravishekar for cosmosdbquery
@app.route(route="cosmosdbquery", auth_level=func.AuthLevel.FUNCTION)
def cosmos_db_response_session(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing Azure FunctionApp for Cosmos DB")

    try:
       
        body = req.get_json()
        doc_id = body.get("ID")
        version_category = body.get("VersionCategory")
        startdate = body.get("startdate")
        enddate = body.get("enddate")

        if not version_category:
            return func.HttpResponse("Missing 'VersionCategory' parameter", status_code=404)
        
        if doc_id and version_category:
            query = "SELECT * FROM c WHERE c.fields.ID = @id AND c.VersionCategory = @VersionCategory"
            parameters = [
                {"name": "@id", "value": doc_id},
                {"name": "@VersionCategory", "value": version_category}
            ]
            
            if startdate and enddate:
                if not startdate.endswith('Z'):
                    startdate += 'Z'
                if not enddate.endswith('Z'):
                    enddate += 'Z'
                query += " AND (c.created >= @startdate AND c.created <= @enddate)"
                query += " AND (c.fields.Modified >= @startdate AND c.fields.Modified <= @enddate)"
                parameters.extend([
                    {"name": "@startdate", "value": startdate},
                    {"name": "@enddate", "value": enddate}
                ])

       
        elif version_category and startdate and enddate:
            if not startdate.endswith('Z'):
                startdate += 'Z'
            if not enddate.endswith('Z'):
                enddate += 'Z'

            query = "SELECT * FROM c WHERE c.VersionCategory = @VersionCategory"
            parameters = [
                {"name": "@VersionCategory", "value": version_category}
            ]

            query += " AND (c.created >= @startdate AND c.created <= @enddate)"
            query += " AND (c.fields.Modified >= @startdate AND c.fields.Modified <= @enddate)"
            parameters.extend([
                {"name": "@startdate", "value": startdate},
                {"name": "@enddate", "value": enddate}
            ])

        else:
            return func.HttpResponse("Missing 'ID' or 'startdate'/'enddate' parameters", status_code=404)
        
        log_message = {
            "query": query,
            "parameters": parameters
        }
        logging.info(f"Executing Query: {json.dumps(log_message, indent=2)}")

        
        items = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

        if not items:
            return func.HttpResponse(f"No details found for provided parameters.", status_code=404)
        

        modified_fields = compare_documents(items)
        if modified_fields:
            gpt_response = generate_ai_response(modified_fields)
            return func.HttpResponse(gpt_response, mimetype="application/json", status_code=200)
        else:
            return func.HttpResponse("No fields have been modified.", status_code=200)

    except Exception as e:
        logging.error(f"Cosmos DB error: {str(e)}")
        return func.HttpResponse(f"Cosmos DB error: {str(e)}", status_code=500)




def compare_documents(items):
    if len(items) < 2:
        return {}

    old_doc = items[0]
    new_doc = items[1]

    modified_fields = []

    # Extracting created and modified timestamps
    created_time_old = old_doc.get("created")  
    created_time_new = new_doc.get("created")
    modified_time_old = old_doc.get("fields", {}).get("Modified")
    modified_time_new = new_doc.get("fields", {}).get("Modified")
    
    # Now compare fields in the document
    for field in old_doc:
        if field.startswith("_"):
            continue
        
        if field in new_doc and old_doc[field] != new_doc[field]:
            modified_fields.append({
                "field": field,
                "previous_value": old_doc[field],
                "new_value": new_doc[field],
                "created_at_previous": created_time_old,
                "created_at_new": created_time_new,
                "modified_at_previous": modified_time_old,
                "modified_at_new": modified_time_new
            })

    # Optionally, add created and modified timestamps themselves
    modified_fields.append({
        "field": "created",
        "previous_value": created_time_old,
        "new_value": created_time_new,
        "created_at_previous": created_time_old,
        "created_at_new": created_time_new,
        "modified_at_previous": modified_time_old,
        "modified_at_new": modified_time_new
    })

    modified_fields.append({
        "field": "modified",
        "previous_value": modified_time_old,
        "new_value": modified_time_new,
        "created_at_previous": created_time_old,
        "created_at_new": created_time_new,
        "modified_at_previous": modified_time_old,
        "modified_at_new": modified_time_new
    })

    return modified_fields

def generate_ai_response(modified_fields):
    try:
       
        prompt = f"""
        Given the following list of modified fields between two versions of a document:

        {json.dumps(modified_fields, indent=4)}

        Please generate a clean JSON response summarizing the changes, showing each modified field with the previous and new values in the format:

        [
            {{
                "field": "<field_name>",
                "previous_value": "<previous_value>",
                "new_value": "<new_value>"
                
                
            }},
            ...
        ]
        The response should only contain the JSON and no additional text.
        """

        
        response = client_openai.chat.completions.create(
            messages=[{
                "role": "user",
                "content": prompt
            }],
            model="gpt-4o",  
            max_tokens=500,
            temperature=0.7
        )

        
        response_update = response.choices[0].message.content.strip()
        return response_update

    except Exception as e:
        logging.error(f"Azure OpenAI API error: {str(e)}")
        return json.dumps({"error": f"Failed to generate AI response: {str(e)}"}, indent=2)
    
@app.route(route="get_list", auth_level=func.AuthLevel.FUNCTION)
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
            "Pass list name in parameter or body.",
            status_code=400
        )

    # Define your container name (could also come from environment settings)
    container_name = os.getenv("AZure_container_name_anurag")

    try:
        # Call the upload function with the provided container_name and list_name.
        # Assume 'upload' returns a string (e.g., JSON data) that we want to return in the response.
        #ACCESS_TOKEN = get_access_token()
        result = get_list_data(container_name, list_name)
        if result == "List name is invalid or out of proccessing scope":
            return func.HttpResponse(result,status_code=400)
        if result == "Data not present":
            return func.HttpResponse(result,status_code=500)
        else:   
            return func.HttpResponse(result, status_code=200,mimetype="application/json")
    except Exception as e:
        logging.error(f"Error in upload: {e}")
        return func.HttpResponse(
            f"Error during upload: {e}",
            status_code=500
        )

@app.timer_trigger(schedule="0 0 * * * *", arg_name="myTimer", run_on_startup=False,
              use_monitor=False) 
def sharepoint_timer_trigger(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('Trigger lagging behind schedule')

    logging.info('Trigger func executed')
    container_name = os.getenv("AZure_container_name_anurag")
    ACCESS_TOKEN = get_access_token()
    upload_sharepoint_lists(ACCESS_TOKEN,container_name)

