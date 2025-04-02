import logging
import json
import os
import requests
import msal
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
from dotenv import load_dotenv
load_dotenv()
# Azure OpenAI API details
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY") 
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT") 
API_VERSION = os.getenv("API_VERSION")
MODEL_NAME = os.getenv("MODEL_NAME")

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
AUTHORITY = os.getenv("AUTHORITY")
SCOPE = [os.getenv("SCOPE")]

SITE_HOSTNAME = os.getenv("SITE_HOSTNAME")
SITE_PATH = os.getenv("SITE_PATH")

CONNECTION_STRING = os.getenv("Azure_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("CONTAINER_NAME")

# Initialize the OpenAI client for Azure
class AzureOpenAI:
    def __init__(self, api_key, api_version, azure_endpoint):
        self.api_key = api_key
        self.api_version = api_version
        self.azure_endpoint = azure_endpoint

    def generate_embedding(self, text):
        """Generates an embedding using Azure OpenAI's text-embedding-ada-002 model."""
        try:
            # Construct the URL for the embedding request
            url = f"{self.azure_endpoint}/openai/deployments/{MODEL_NAME}/embeddings?api-version={self.api_version}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {"input": [text]}
            

            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status() 

            embedding = response.json()['data'][0]['embedding']
            return embedding
        except requests.exceptions.RequestException as e:
            logging.error(f"Error generating embedding for text: {text} - {str(e)}")
            return []  

# MSAL Authentication for Microsoft Graph
def get_access_token():
    """Acquires an app-only access token using MSAL."""
    app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )
    token_response = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" in token_response:
        logging.info("Access token acquired.")
        return token_response["access_token"]
    else:
        raise Exception("Access token could not be obtained")

# SharePoint API calls
def get_site_id(access_token):
    """Retrieves the SharePoint site ID from Microsoft Graph."""
    url = f"https://graph.microsoft.com/v1.0/sites/{SITE_HOSTNAME}:{SITE_PATH}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    site_info = response.json()
    return site_info["id"]

def get_list_details(listname, access_token):
    """Retrieves items from a specified SharePoint list (with expanded fields)."""
    site_id = get_site_id(access_token)
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{listname}/items?expand=fields"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

# Data cleaning and transformation functions
def clean_data(data):
    """Cleans data by removing empty values."""
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
        data = data.replace(";", "").replace("#Name?", "Name")
        return data
    else:
        return data

def convert_numeric(data):
    """Converts numeric strings to actual numbers where applicable."""
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

# Blob Storage functions
def create_blob_container(blob_service_client, container_name):
    """Creates an Azure Blob Storage container if it does not already exist."""
    try:
        blob_service_client.create_container(container_name)
        logging.info(f"Container '{container_name}' created successfully.")
    except ResourceExistsError:
        logging.info(f"A container with the name '{container_name}' already exists.")

def upload_merged_data(blob_service_client, container_name, merged_data):
    """Uploads merged data into the Blob Storage."""
    merged_data = clean_data(merged_data)
    converted_data = convert_numeric(merged_data)
    blob_data = json.dumps(converted_data, indent=2)
    blob_file_name = "Risk_Register_Merged.json"
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_file_name)
    blob_client.upload_blob(data=blob_data, overwrite=True)
    logging.info("Merged data uploaded successfully.")
    return "Merged data uploaded successfully."

# Merging risk data with mitigation data
def filter_risk_register_fields(risk_fields):
    """Filters out unnecessary fields from the risk register data."""
    allowed_keys = [
        "id", "Title", "EventType", "RiskId", "Impact", "Likelihood", "FinancialImpact", "Status", 
        "RiskIssueStrategy", "RiskIssueDescription", "ImpactScore", "LikelihoodScore", "RiskScore", 
        "Calculated_TargetDate", "Owners", "RaisedByEmail", "GISOMustHave", "Archive", 
        "RiskIssueRaisedByLookupId", "TargetDate", "Modified", "Created", "Level1LookupId", 
        "Level2LookupId", "Level3LookupId", "ProgramRiskLookupId", "Countries", "RiskIssueOwner", 
        "CategoryLookupId", "AreaLookupId", "GeographicalImpactLookupId", "GisoPhasesLookupId", "mitigations"
    ]
    return {k: risk_fields[k] for k in allowed_keys if k in risk_fields}

def filter_mitigation_fields(mitigation_fields):
    """Filters out unnecessary fields from the mitigation data.""" 
    allowed_keys = [
        "ResponsePlan", "RiskId", "ResponseDate", "ResponseOwnerEmail", "id", "ContentType", 
        "Modified", "Created", "AuthorLookupId", "EditorLookupId", "Attachments", 
        "ItemChildCount", "FolderChildCount", "ResponseOwner"
    ]
    return {k: mitigation_fields[k] for k in allowed_keys if k in mitigation_fields}

def merge_risk_data(risk_register_data, risk_mitigation_data, azure_openai_client):
    """Merges risk data and mitigation data, adding embeddings for multiple fields."""
    reg_list = risk_register_data.get("value", [])
    mit_list = risk_mitigation_data.get("value", [])
    mitigation_index = {}

    # Map mitigations to their corresponding risk ID
    for mit in mit_list:
        fields = mit.get("fields", {})
        risk_id = fields.get("RiskId")
        if risk_id is not None:
            mitigation_index.setdefault(str(risk_id), []).append(filter_mitigation_fields(fields))

    new_reg_list = []
    for risk in reg_list:
        reg_id = risk.get("id")
        if "fields" in risk:
            filtered_fields = filter_risk_register_fields(risk["fields"])
            if reg_id:
                filtered_fields["mitigations"] = mitigation_index.get(str(reg_id), [])
            else:
                filtered_fields["mitigations"] = []
            filtered_fields["id"] = reg_id

            # Add embeddings for multiple fields
            embedding_fields = ["Title", "Status", "Likelihood"]
            embeddings = {}
            for field in embedding_fields:
                if field in filtered_fields:
                    embeddings[field] = azure_openai_client.generate_embedding(filtered_fields[field])

            # Store the embeddings in the fields
            filtered_fields["embeddings"] = embeddings

            new_reg_list.append(filtered_fields)
        else:
            new_reg_list.append({"id": reg_id, "mitigations": mitigation_index.get(str(reg_id), [])})

    return new_reg_list

# Main function to run the process
def main():
    logging.basicConfig(level=logging.INFO)
    access_token = get_access_token()
    blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    create_blob_container(blob_service_client, CONTAINER_NAME)

    # Initialize Azure OpenAI client
    azure_openai_client = AzureOpenAI(AZURE_OPENAI_KEY, API_VERSION, AZURE_OPENAI_ENDPOINT)

    # Fetch risk and mitigation data
    risk_register_data = get_list_details("Risk Register", access_token)
    risk_mitigation_data = get_list_details("Risk Mitigations", access_token)

    # Merge data with client (AzureOpenAI instance)
    merged_data = merge_risk_data(risk_register_data, risk_mitigation_data, azure_openai_client)

    # Upload the merged data to Blob Storage
    result = upload_merged_data(blob_service_client, CONTAINER_NAME, merged_data)
    logging.info(result)

if __name__ == "__main__":
    main()
