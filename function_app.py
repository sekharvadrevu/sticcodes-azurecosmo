import azure.functions as func
import json
import logging
from azure.cosmos import CosmosClient
from httpTrigger_funcs_anurag import get_list_data
from timertrigger_funcs_anurag import upload_sharepoint_lists
from access_token import get_access_token
from dotenv import load_dotenv
import os
from openai import AzureOpenAI

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


app = func.FunctionApp()

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
    
    for field in old_doc:
       
        if field.startswith("_"):
            continue
        
        if field in new_doc and old_doc[field] != new_doc[field]:
            modified_fields.append({
                "field": field,
                "previous_value": old_doc[field],
                "new_value": new_doc[field]
                
            })

    return modified_fields


# def generate_ai_response(modified_fields):
   
#     structured_response = {
#         "modified_fields": modified_fields
#     }

#     try:
       
#         summary_text = json.dumps(modified_fields, indent=4)


#         prompt = f"Here is a list of modified fields between two versions of a document:\n{summary_text}\n\n" \
#                  "Please provide a summary of these changes with the field name, previous value, and new value in a clean JSON format."

#         response = client_openai.chat.completions.create(
#             messages=[{
#                 "role": "user",
#                 "content": prompt
#             }],
#             model="gpt-4o",
#             max_tokens=500,
#             temperature=0.7
#         )

        
#         response_update = response.choices[0].message.content
#         structured_response["summary"] = response_update

#         return json.dumps(structured_response, indent=2)

#     except Exception as e:
#         logging.error(f"Azure OpenAI API error: {str(e)}")
#         return json.dumps({"error": f"Failed to generate AI response: {str(e)}"}, indent=2)
def generate_ai_response(modified_fields):
    try:
        # Create a prompt that will guide the LLM to generate a clean JSON summary
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
    


# Anurag's endpoint

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
    container_name = os.getenv("container_name")

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
    container_name = os.getenv("container_name")
    ACCESS_TOKEN = get_access_token()
    upload_sharepoint_lists(ACCESS_TOKEN,container_name)

