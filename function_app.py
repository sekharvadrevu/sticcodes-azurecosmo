import azure.functions as func
import json
import logging
from azure.cosmos import CosmosClient
from httpTrigger_funcs_anurag import get_list_data
from timertrigger_funcs_anurag import upload_sharepoint_lists
from access_token import get_access_token
from dotenv import load_dotenv
import os

load_dotenv()
COSMOSDB_ENDPOINT = os.getenv("cosmoendpoint")
COSMOSDB_KEY = os.getenv("COSMOS_KEY")
COSMOS_DB_NAME = os.getenv("COSMOS_DB_NAME")
COSMOS_CONTAINER_NAME = os.getenv("COSMOS_CONTAINER_NAME")

client = CosmosClient(COSMOSDB_ENDPOINT, COSMOSDB_KEY)
database = client.get_database_client(COSMOS_DB_NAME)
container = database.get_container_client(COSMOS_CONTAINER_NAME)

app = func.FunctionApp()

@app.route(route="cosomodb", auth_level=func.AuthLevel.FUNCTION)
def cosmos_function_seesion(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing Azure FunctionApp for Cosmos DB")
    try:
        body = req.get_json()
        doc_id = body.get("ID")
        version_category = body.get("VersionCategory")
        startdate = body.get("startdate")
        enddate = body.get("enddate")

        if not version_category:
            return func.HttpResponse("Missing 'VersionCategory' parameter", status_code=400)
       
       
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
            return func.HttpResponse("Missing 'ID' or 'startdate'/'enddate' parameters", status_code=400)

        
        log_message = {
            "query": query,
            "parameters": parameters
        }
        logging.info(f"Executing Query: {json.dumps(log_message, indent=2)}")
        items = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

        if not items:
            return func.HttpResponse(f"No details found for provided parameters.", status_code=404)

        return func.HttpResponse(json.dumps(items, indent=2), mimetype="application/json", status_code=200)

    except Exception as e:
        logging.error(f"Cosmos DB error: {str(e)}")
        return func.HttpResponse(f"Cosmos DB error: {str(e)}", status_code=500)
    


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

