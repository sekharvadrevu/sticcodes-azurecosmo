import re
import ast 
import logging
from dateutil.parser import parse as date_parse
from dateutil import parser
import json
import os
from dotenv import load_dotenv
import logging
from typing import Any
load_dotenv(dotenv_path = "config.env")


logger = logging.getLogger('mergelists_logger')


rm_columns = {
  "id":int,
  "createdDateTime": "date",
  "lastModifiedDateTime":"date",
  "ResponsePlan" : str,
  "ResponseOwner" : list,
  "RiskId": int,
  "RevisedResponseDate": "date",
  "ResponseDate": "date",
  "ResponseOwnerEmail": str,
  "AuthorLookupId": int,
  "EditorLookupId": int
}
include_keys_rm = [
            "id",
            "createdDatetime",
            "lastModifiedDateTime",
            "ResponsePlan",
            "ResponseOwner",
            "RiskId",
            "RevisedResponseDate",
            "ResponseDate",
            "ResponseOwnerEmail",
            "AuthorLookupId",
            "EditorLookupId"
        ]

rr_columns = {
  "id": int,
  "createdDateTime": "date",
  "lastModifiedDateTime":"date",
  "Title": str,
  "LinkTitleNoMenu": str,
  "LinkTitle": str,
  "EventType": str,
  "FinancialImpact": float,
  "Impact": str,
  "Likelihood": str,
  "RiskIssueRaisedByLookupId":int,
  "Status": str,
  "RiskId":str,
  "RiskIssueOwner": list, 
  "ImpactScore": int,
  "LikelihoodScore": int,
  "Calculated_TargetDate": "date",
  "RiskScore": int,
  "Level1LookupId": int,
  "Level2LookupId": int,
  "Level3LookupId": int,
  "ProgramRiskLookupId": int,
  "IsEsclated": bool,
  "TargetDate": str,
  "Countries": list,
  "CategoryLookupId": int,
  "AreaLookupId": int,
  "GisoPhasesLookupId": int,
  "GISOMustHave": bool,
  "GeographicalImpactLookupId": int,
  "Archive": bool,
  "Owners": str,
  "RaisedByEmail": str,
  "Attachments":bool,
  "Edit": str,
  "ItemChildCount": int,
  "FolderChildCount": int
}


include_keys_rr= [
            "id",
            "createdDatetime",
            "lastModifiedDateTime",
            "Title",
            "LinkTitleNoMenu",
            "LinkTitle",
            "EventType",
            "FinancialImpact",
            "Impact",
            "Likelihood",
            "RiskIssueRaisedByLookupId",
            "Status",
            "RiskId",
            "RiskIssueOwner",
            "ImpactScore",
            "LikelihoodScore",
            "Calculated_TargetDate",
            "RiskScore",
            "Level1LookupId",
            "Level2LookupId",
            "Level3LookupId",
            "ProgramRiskLookupId",
            "IsEsclated",
            "TargetDate",
            "Countries",
            "CategoryLookupId",
            "AreaLookupId",
            "GisoPhasesLookupId",
            "GISOMustHave",
            "GeographicalImpactLookupId",
            "Archive",
            "Owners",
            "RaisedByEmail",
            "Attachments",
            "Edit",
            "ItemChildCount",
            "FolderChildCount"
        ]
    


follow_up_columns = {
    "id":int,
    "createdDateTime": "date",
    "lastModifiedDateTime":"date",
    "Title":str,
    "Level1LookupId":int,
    "Level2":list, # a list of dictionaries where the dictionaries have lookupid and lookupvalue are present.
    "Owner":list, # list -> dict -> LookupId,LookupValue, Email
    "DueDate":"date",
    "Comments":str,
    "SourceEvent":str,
    "Status":str,
    "Level3LookupId":int,
    "Archive":bool,
    "ReasonforArchive":str,
    "Modified":"date",
    "Created":"date",
    "AuthorLookupId":int,
    "EditorLookupId":int,
    "Attachments":bool,
    "Edit":str,
    "LinkTitleNoMenu":str,
    "LinkTitle":str,
    "ItemChildCount":int,
    "FolderChildCount":int
}


include_keys_follow_up = [
    "id",
    "createdDateTime",
    "lastModifiedDateTime",
    "Title",
    "Level1LookupId",
    "Level2",
    "Owner",
    "DueDate",
    "Comments",
    "SourceEvent",
    "Status",
    "Level3LookupId",
    "Archive",
    "ReasonforArchive",
    "Modified",
    "Created",
    "AuthorLookupId",
    "EditorLookupId",
    "Attachments",
    "Edit",
    "LinkTitleNoMenu",
    "LinkTitle",
    "ItemChildCount",
    "FolderChildCount"
]
column_schema = {
    "Risk Register": rr_columns,
    "Risk Mitigations": rm_columns,
    "Follow up": follow_up_columns
}

allowed_columns = {
    "Risk Register": include_keys_rr,
    "Risk Mitigations": include_keys_rm,
    "Follow up": include_keys_follow_up
}

def format_columns(item):
    """
    Parameters:
      item: A key-value pair or a JSON object (dict or list)
    Returns:
      A cleaned version of the key(s) with special characters removed.
      For nested structures, processing is recursive.
    """
    if isinstance(item, dict):
        cleaned_column_dict = {}
        for key, value in item.items():
            # Remove special characters,whitespace and do not format "_"
            formatted_key = re.sub(r"\s+|[^a-zA-Z0-9_]", "", key)
            # Process the value based on its type.
            if isinstance(value, dict):
                formatted_value = format_columns(value)
            elif isinstance(value, list):
                formatted_value = [format_columns(sub_item) if isinstance(sub_item, dict) else sub_item for sub_item in value]
            else:
                formatted_value = value
            cleaned_column_dict[formatted_key] = formatted_value
        return cleaned_column_dict
    elif isinstance(item, list):
        return [format_columns(col) if isinstance(col, dict) else col for col in item]
    else:
        return item

# ------------------------------
# Helper: Recursive conversion & formatting 
# ------------------------------
def format_value(data, column_types):
    """
    Parameters:
      data: JSON data (dict or list) to process.
      column_types: Dict mapping keys to expected types (e.g., int, float, str, bool, "date", list, dict).
    Returns:
      Data with values converted based on column_types.
    """
    if isinstance(data, dict):
        new_data = {}
        for key, value in data.items():
            # Recursively process nested structures.
            if isinstance(value, dict):
                value = format_value(value, column_types)
            else:
                if isinstance(value, list):
                    value = [format_value(item, column_types) if isinstance(item, dict) else item for item in value]
            if key in column_types:
                expected_type = column_types[key]
                if expected_type == "date":
                    try:
                        parsed_date = date_parse(value)   
                        new_value = parsed_date.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception as e:
                        new_value = None
                elif expected_type == int:
                    try:
                        if value =="No":
                            new_value=0
                        else:
                            new_value = int(value)
                    except Exception:
                        new_value = None
                elif expected_type == float:
                    try:
                        new_value = float(value)
                    except Exception:
                        new_value = None
                elif expected_type == bool:
                    if isinstance(value, str):
                        lower_val = value.lower().strip()
                        if lower_val in ["yes", "1", "true"]:
                            new_value = True
                        elif lower_val in ["no", "0", "false"]:
                            new_value = False
                        else:
                            new_value = False
                    elif isinstance(value,int):
                        if value == 1:
                            new_value = True
                        elif value == 0:
                            new_value = False
                        else:
                            new_value = False
                    elif isinstance(value,float):
                        if value == 1.0:
                            new_value = True
                        elif value == 0.0:
                            new_value = False
                        else:
                            new_value = False
                    elif isinstance(value,bool):
                        new_value = value
                    else:
                        new_value = False
                elif expected_type == str:
                    # Handle nested list/dict represented as string.
                    try:
                        #check if list or dictionary is passed as a string
                        eval_value = ast.literal_eval(value)
                        if isinstance(eval_value, (list, dict)):
                            value = eval_value
                    except (ValueError, SyntaxError):
                        pass
                    if isinstance(value, str):
                        # remove unnecessary whitespaces
                        new_value = str(value).strip()
                elif isinstance(expected_type, list):
                    
                    if isinstance(value, list):
                        new_value = [format_value(item, column_types) if isinstance(item, dict) else item for item in value]
                    else:
                        new_value = value
                elif isinstance(expected_type, dict):
                    if isinstance(value, dict):
                        new_value = format_value(value, column_types)
                    else:
                        new_value = value
                else:
                    new_value = value
            else:
                new_value = value
            new_data[key] = new_value
        return new_data

    elif isinstance(data, list):
        return [format_value(item, column_types) if isinstance(item, dict) else item for item in data]
    else:

        return data
    
# ------------------------------
# Merged Data Cleaning Function
# ------------------------------
def clean_and_format_data(data, list_type)->Any:
    """
    Clean and format data received from SharePoint.
    For both risk register and risk mitigation items:
      - Only include top-level keys: "id", "createdDateTime", "lastModifiedDateTime", and "fields".
      - Within "fields", exclude unwanted keys.
    
    Parameters:
      - data: Json array of sharepoint list.
      - data_type: Either "Risk Register" or "Risk Mitigations" to select appropriate exclusion keys.
    
    Returns a list of cleaned items.
    """
    column_schema_present = False
    allowed_columns_present = False

    cleaned_column_data = format_columns(data)

    for key,value in allowed_columns.items():
        if key == list_type:
            allowed_columns_present = True # check if the values have to be formatted. Useful when we dont have the schema for a list.
            included_keys = value
            break

    if allowed_columns_present == False:
        return None
    
        
    #Extract only necessary fields
    cleaned_data = []
    for item in cleaned_column_data:
        cleaned_item = {}
        
        for key in included_keys:
            if key in item:

                cleaned_item[key] = item[key]
        if "fields" in item and isinstance(item["fields"], dict):
            for field_key, field_val in item["fields"].items():
                if field_key in included_keys:
                    cleaned_item[field_key] = item["fields"][field_key]
                if field_key == "Owners" and isinstance(item["fields"]["Owners"],str): # The email in Owners key has a ';' after the email. 
                    cleaned_item[field_key] = item["fields"]["Owners"].replace(";","")
        cleaned_data.append(cleaned_item)

    

    for key,value in column_schema.items():
        if key == list_type:
            allowed_columns_present = True # check if the values have to be formatted. Useful when we dont have the schema for a list.
            key_types = value
            cleaned_value_and_column_data = format_value(cleaned_data,key_types)
            break

    if allowed_columns_present == False:
        return json.dumps(cleaned_data)
    
    return json.dumps(cleaned_value_and_column_data)
        

# ------------------------------
# Merge Function: Merge risk register and mitigation data
# ------------------------------
def merge_lists(rr_data, rm_data):
    """
    Merge risk mitigation data into risk register data.
    For each risk register item, attach a list of corresponding mitigations under the key "Mitigations".
    Assumes that the risk register's "id" (converted to int) corresponds to the mitigation's "RiskId" in its "fields".
    """
    # get cleaned and formatted rr and rm data
    rr_data = json.loads(clean_and_format_data(rr_data,"Risk Register"))
    rm_data= json.loads(clean_and_format_data(rm_data,"Risk Mitigations"))

    print(rm_data[0])

    try:
        sorted_rm_data = sorted(rm_data, key=lambda x: int(x["RiskId"])) 
    except Exception as e:
        print("Error sorting risk mitigation data:", e)
        return rr_data

    merged_data = []
    rm_index = 0
    num_rm = len(sorted_rm_data)
    
    for rr_item in rr_data:
        rr_id = int(rr_item.get("id"))
        rr_item["Mitigations"] = []
        while rm_index < num_rm:
            
            rm_risk_id = int(sorted_rm_data[rm_index].get("RiskId"))
            if rm_risk_id == rr_id:
                rr_item["Mitigations"].append(sorted_rm_data[rm_index])
                rm_index += 1
            else:
                break
        merged_data.append(rr_item)
    return json.dumps(merged_data)
