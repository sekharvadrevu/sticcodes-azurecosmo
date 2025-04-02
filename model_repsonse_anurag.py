from dotenv import load_dotenv
import logging
import json
from helper_funcs_anurag import get_client
load_dotenv()

VersionHistory_Item_Schema = """  
This data represents the version history for ""Risk Register"" item. The version history has the following fields.

**id (string)** : Unique identifier for this version history entry.  
**list_title (string)** : Title of the list or category this item belongs to.  
**item_id (string or number)** : Unique identifier of the original item associated with this version.  
**version_label (string)** : Label representing the version (e.g., "2.0") of the item.  
**created (string, datetime)** : Timestamp indicating when this version was created. Timestamp will be in ISO 8601 format. Example : ""2025-03-17T10:41:16""  
**modified_by (object)** : Contains details about the user who modified the item.  
 - **id (number)** : User identifier.  
 - **display_name (string)** : User's display name.  
 - **email (string)** : User's email address.  
**fields (object)** : Contains all the specific attributes of the risk sharepoint item. Each sub-key represents a property of the risk record:  
 - **Created (string, datetime)** : Timestampt indicating when risk record was created. Timestamp will be in ISO 8601 format. Example : ""2025-03-17T10:41:16"" 
 - **Title (string)** : Title of the risk record.  
 - **EventType (string)** : Type of event, here noted as "Risk".  
 - **FinancialImpact (number)** : Numerical value indicating the financial impact.  
 - **Impact (string)** : Description of the impact.  
 - **ImpactStatement (string or null)** : Statement detailing the impact; can be null.  
 - **Likelihood (string)** : Describes the likelihood of the risk (e.g., "Rare").  
 - **RiskIssueRaisedBy (object)** : Details on who raised the risk issue in the following format: 
    - **LookupId (number)** : Identifier for the raiser.  
    - **LookupValue (string)** : Name associated with the raiser.  
    - **Email (string)** : Email of the person who raised the issue.  
 - **Status (string)** : Current status of the risk (e.g., "Cancelled").  
 - **RiskIssueStrategy (string)** : Strategy or approach to manage the risk issue. Example: ""Avoid"", ""Pursue"", ""Share"", ""Accept"", ""Reduce"". 
 - **RiskAppetite (string or null)** : The risk appetite, if specified, e.g., ""Risk Aversion"", ""Risk Reduction"", ""Risk Acceptance"", ""Risk Taking"".
 - **RiskCompass (string or null)** :  A categorization or metric related to the risk, e.g., ""Strategic"", ""Operational"", ""Emerging"".  
 - **RiskIssueDescription (string or null)** : Detailed description of the risk issue.  
 - **ResponseOwners (string or null)** : Email addresses of response owners.  
 - **ResponsePlan (string)** : A plan on how to respond to the risk.  
 - **ReasonsforClosing (string or null)** : Description on why the risk is closed.  
 - **ClosureDate (Date or null)** : Timestamp indicating when the risk was closed. Timestamp will be in ISO 8601 format. Example : ""2025-03-17T10:41:16"" 
 - **ClosingComments (string or null)** : Additonal comments upon closing the risk
 - **TrackingComments (string or null)** : Comments related to tracking the risk.
 - **RiskId (string)** : Identifier code for the risk (e.g., "R_0001").  
 - **CopyTrackingComment (string)** : Copy of TrackingComments.  
 - **RiskIssueOwner (Array of object)** : Contains an array of objects. Each object contains details about the owners in the following format:
    - **LookupId(number)** : Lookup identifier of the owner 
    - **LookupValue(string)** : Name of the owner
    - **Email(string)** : Email address of the owner
 - **CRID (string or null)** :  A unique identifier, possibly for cross-referencing. (confirm this later)  
 - **Objective (string or null)** : The objective assosciated with the risk. (confirm this)  
 - **Level1 (object)** : Contains a lookup ID and value, likely referring to a primary category or phase.  
    - **LookupId (number)** : Identifier for Level1 category.  
    - **LookupValue (string)** : Contains category name (e.g., "Phase 1 & 2").  
 - **Level2 (object)** : Contains lookup details for a secondary category.  
    - **LookupId (number)** : Identifier for Level2.  
    - **LookupValue (string)** : Contains category name.  
 - **Level3 (object)** : Contains lookup details for a tertiary category.  
    - **LookupId (number)** : Identifier for Level3.  
    - **LookupValue (string)** : Contains category name.  
 - **ProgramRisk (object)** : Contains details related to program-specific risk.  
    - **LookupId (number)** : Identifier for the program risk.  
    - **LookupValue (string)** : Description of the program risk.  
 - **IsEsclated (boolean)** : Flag indicating whether the risk has been escalated.  
 - **TargetDate (string, datetime)** : The intended date for risk resolution or review.  
 - **RevisedTargetDate (string or null)** : An updated target date, if applicable.  
 - **Countries (array)** : List of countries affected or involved.  
 - **Category (object)** : Contains lookup details for the risk category.  
    - **LookupId (number)** : Category identifier.  
    - **LookupValue (string)** : Category name.  
 - **Area (object)** : Contains lookup details for a geographical or business area.  
    - **LookupId (number)** : Area identifier.  
    - **LookupValue (string)** : Area name.  
 - **GisoPhases (object)** : Contains lookup details potentially related to GISO project phases.  
    - **LookupId (number)** : Identifier for the phase.  
    - **LookupValue (string)** : Phase name.  
 - **GISOMustHave (boolean)** : Indicates if GISO criteria are mandatory.  
 - **GeographicalImpact (object)** : Contains lookup details on geographical impact.  
    - **LookupId (number)** : Identifier for the geographical impact.  
    - **LookupValue (string)** : Name of impact.  
 - **LikelihoodtoMitigate (string or null)** : Likelihood of risk occuring after mitigation.  
 - **Archive (boolean)** : Indicates whether the record is archived.  
 - **Owners (string)** : Names or identifiers of the owners responsible for the risk.  
 - **ReasonforArchive (string or null)** : Reason for archiving the risk.  
 - **RaisedByEmail (string)** : Email address of the person who raised the risk issue.  
 - **ImpactScore (number)** : A numerical score representing the impact level.  
 - **LikelihoodScore (number)** : A numerical score representing the likelihood.  
 - **RiskScore (number)** : Calculated overall risk score from impact and likelihood.  
 - **Calculated_TargetDate (object)** : Contains calculation details; may hold an error message indicating a calculation issue.  
 - **ID (number)** : Unique identifier of the risk record.  
 - **Modified (string, datetime)** : Timestamp indicating the last modification of the risk record.  
**is_current_version (boolean)** : Indicates if this version is the most recent/current version.  
**timestamp (string, datetime)** : Timestamp for when this version record was recorded.  
**partition_key (string)** : Key used for partitioning the data in the storage system.  
**VersionCategory (string)** : Category of the version.  
"""

System_Message = f"""

    You are an AI assistant that generates SQL queries for Azure Cosmos DB. Your task is to carefully follow the provided schemas, instructions and then produce synctactically and logically correct SQL query. Follow the below rules:

    **General Instructions**
    - Analyze user intent and understand what fields the user is referring to.
    - Generate the SQL query by referring to the provided schema and instructions.
    - Return only the Cosmos DB SQL query as plain text in a single line and avoid any tabs or newline. The query should be formatted and should be ready for execution against Cosmos DB.
    
    **cosmos db query instructions**
    - Always use ""c"" keyword as the alias for the container being queried.
    **Schema**
    - Ensure that you refer to the schema given below and generate the cosmos db SQL query accordingly.
    {VersionHistory_Item_Schema}

"""

def get_ai_response(user_input:str,deployment_name:str):
    """
    Returns chat completion message.
    Params : 
    user_input -> Query of the user.
    deployment_name -> model name that the user wants to use (Must be available in endpoint).
    
    Note:
    client.chat.completions.create is different for gpt-4o and o1.
     
    """
    chat_completion_models = ["gpt-4o"]
    reasoning_models = ["o1"]
    try:

        if deployment_name in reasoning_models: 
            client = get_client(deployment_name)
            if client == "Failed to connect to client":
                return client
            chat_prompt = [
                {
                    "role":"system",
                    "content":[
                        {
                            "type":"text",
                            "text": System_Message
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_input
                        }
                    ]
                }
            ] 
                
            # Include speech result if speech is enabled  
            messages = chat_prompt 
            # response does not have completion tokens because o1 takes into account resoning and output tokens. 
            # An arugment will be given once the completion tokens can be accurately estimated for user inputs.
            response = client.chat.completions.create(  
                model=deployment_name,  
                messages=messages
            )  
            json_response = json.dumps({"model response": response.choices[0].message.content}) # clean escape characters like "\"
            print(json_response)
            return json_response
         
                    
        elif deployment_name in chat_completion_models:

            client = get_client(deployment_name)
            if client == "Failed to connect to client":
                return client
            response = client.chat.completions.create(
                model = deployment_name,
                messages=[{"role": "system", "content": System_Message},
                          {"role": "user", "content": user_input}],
                temperature=0.7
            )

            json_response = json.dumps({"model response": response.choices[0].message.content})
            print(json_response)
            return json_response
        else:
            logging.error("Invalid model name")
            return "Invalid model name"
    except Exception as e:
        logging.error(f"Failed to get response from model. Error :{e}")
        return "Failed to get response from model"
