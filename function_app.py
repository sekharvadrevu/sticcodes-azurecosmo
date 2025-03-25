import azure.functions as func
import json
import logging
from azure.cosmos import CosmosClient
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