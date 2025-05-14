# custom_fields.py
"""
Custom fields management functions for CallHub API.
"""

import json
import sys
from typing import Dict, List, Union, Optional, Any

from .auth import get_account_config
from .utils import build_url, api_call, get_auth_headers

def list_custom_fields(params: dict) -> dict:
    """
    List all custom fields for the account.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - page (optional): Page number for pagination
            - pageSize (optional): Number of results per page
            
    Returns:
        Dictionary with custom field results
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)

    headers = get_auth_headers(api_key)
    query = {}
    if params.get("page"):
        query["page"] = params["page"]
    if params.get("pageSize"):
        query["page_size"] = params["pageSize"]

    url = build_url(base_url, "v1/custom_fields/")
    result = api_call("GET", url, headers, params=query)
    
    # Handle the unusual response format where multiple JSON objects are concatenated
    if isinstance(result, str):
        try:
            # Split the string by "}{", then fix each item to be valid JSON
            parts = result.split("}{") 
            json_objects = []
            
            for i, part in enumerate(parts):
                # Add closing brace to all except last part
                if i < len(parts) - 1 and not part.endswith("}"):
                    part += "}"
                # Add opening brace to all except first part
                if i > 0 and not part.startswith("{"):
                    part = "{" + part
                # Try to parse as JSON
                try:
                    obj = json.loads(part)
                    json_objects.append(obj)
                except json.JSONDecodeError:
                    sys.stderr.write(f"[callhub] Failed to parse JSON part: {part}\n")
            
            # Return a standard format with results array
            return {
                "count": len(json_objects),
                "results": json_objects
            }
            
        except Exception as e:
            sys.stderr.write(f"[callhub] Error processing custom fields response: {str(e)}\n")
            # Return original response on error
            return {"isError": True, "content": [{"type": "text", "text": f"Failed to parse response: {str(e)}"}]}
    
    # If not a string or parsing failed, return the original result
    return result

def get_custom_field(params: dict) -> dict:
    """
    Retrieve a single custom field by name and field_type.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - customFieldId: ID of the custom field to retrieve
            - name (alternative): Name of the custom field
            - field_type (if using name): Type of field (1: "Text", 2: "Number", 3: "Boolean", 4: "Multi-choice")
            
    Returns:
        Dictionary with custom field details
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)

    field_id = params.get("customFieldId")
    name = params.get("name")
    field_type = params.get("field_type")
    
    # Per API docs, need to provide name and field_type, not just ID
    if not field_id and not (name and field_type):
        raise ValueError("Either 'customFieldId' or both 'name' and 'field_type' are required.")

    headers = get_auth_headers(api_key)
    
    if field_id:
        # Try using the ID directly
        url = build_url(base_url, "v1/custom_fields/{}/", field_id)
        return api_call("GET", url, headers)
    else:
        # Use name and field_type as path parameters
        url = build_url(base_url, "v1/custom_fields/")
        # Add as query parameters
        query_params = {"name": name, "field_type": field_type}
        return api_call("GET", url, headers, params=query_params)


def create_custom_field(params: dict) -> dict:
    """
    Create a new custom field.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - name: Name of the custom field (required)
            - field_type: Type of the field (required, e.g., "Text", "Number", "Boolean", "Multi-choice")
            - choices: For "Multi-choice" type, a list of options (optional)
            
    Returns:
        Dictionary with created custom field details
    """
    account_name = params.pop("accountName", None)
    _, api_key, base_url = get_account_config(account_name)

    # Ensure required fields are provided
    if "name" not in params:
        raise ValueError("'name' field is required to create a custom field")
    if "field_type" not in params:
        raise ValueError("'field_type' is required to create a custom field")

    # Prepare the request data
    request_data = {
        "name": params["name"],
        "field_type": params["field_type"]
    }
    
    # Add choice array for Multi-choice type fields
    if params["field_type"] == "Multi-choice" and "choices" in params:
        request_data["choice"] = params["choices"]

    # Debug output to help troubleshoot
    sys.stderr.write(f"[callhub] Creating custom field with params: {request_data}\n")

    headers = get_auth_headers(api_key)
    url = build_url(base_url, "v1/custom_fields/")
    
    return api_call("POST", url, headers, json_data=request_data)

def update_custom_field(params: dict) -> dict:
    """
    Update an existing custom field by ID.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - customFieldId: ID of the custom field to update
            - name (optional): New name for the custom field
            - options (optional): For "select" type, a list of options
            
    Returns:
        Dictionary with updated custom field details
    """
    account_name = params.pop("accountName", None)
    _, api_key, base_url = get_account_config(account_name)

    field_id = params.pop("customFieldId", None)
    if not field_id:
        raise ValueError("'customFieldId' is required.")

    update_data = {}
    if "name" in params:
        update_data["name"] = params["name"]
    if "options" in params:
        update_data["options"] = params["options"]

    # Debug output to help troubleshoot
    sys.stderr.write(f"[callhub] Updating custom field {field_id} with params: {update_data}\n")

    headers = get_auth_headers(api_key)
    url = build_url(base_url, "v1/custom_fields/{}/", field_id)
    
    # API docs say to use PUT, not PATCH
    return api_call("PUT", url, headers, json_data=update_data)


def delete_custom_field(params: dict) -> dict:
    """
    Delete a custom field by ID.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - customFieldId: ID of the custom field to delete
            
    Returns:
        Dictionary with deletion status
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)

    field_id = params.get("customFieldId")
    if not field_id:
        raise ValueError("'customFieldId' is required.")

    headers = get_auth_headers(api_key)
    url = build_url(base_url, "v1/custom_fields/{}/", field_id)
    
    result = api_call("DELETE", url, headers)
    
    # If successful, return a standardized response
    if "isError" not in result:
        return {"deleted": True, "customFieldId": field_id}
    return result

def get_custom_field_info(account_name, custom_field_id):
    """
    Get custom field information by using list_custom_fields and filtering.
    
    Args:
        account_name (str): The account to use
        custom_field_id (str): ID of the custom field to retrieve
        
    Returns:
        dict: The custom field information or error response
    """
    _, api_key, base_url = get_account_config(account_name)
    headers = get_auth_headers(api_key)
    
    # Call the list_custom_fields endpoint
    url = build_url(base_url, "v1/custom_fields/")
    result = api_call("GET", url, headers)
    
    # Handle the response
    if isinstance(result, dict) and result.get("isError"):
        return result
    
    # Handle string response (concatenated JSON objects)
    if isinstance(result, str):
        sys.stderr.write(f"[callhub] Got a string response: {result[:100]}...\n")
        try:
            # Split the string by "}{"
            parts = result.split("}{") 
            sys.stderr.write(f"[callhub] Split into {len(parts)} parts\n")
            
            for i, part in enumerate(parts):
                # Add closing brace to all except last part
                if i < len(parts) - 1 and not part.endswith("}"):
                    part += "}"
                # Add opening brace to all except first part
                if i > 0 and not part.startswith("{"):
                    part = "{" + part
                    
                sys.stderr.write(f"[callhub] Processing part {i+1}/{len(parts)}: {part[:50]}...\n")
                    
                # Try to parse as JSON
                try:
                    field_obj = json.loads(part)
                    sys.stderr.write(f"[callhub] Parsed JSON: id={field_obj.get('id')}\n")
                    if str(field_obj.get("id")) == str(custom_field_id):
                        sys.stderr.write(f"[callhub] Found matching field!\n")
                        return field_obj
                except json.JSONDecodeError as e:
                    sys.stderr.write(f"[callhub] JSON decode error: {str(e)}\n")
                    continue
            
            sys.stderr.write(f"[callhub] No matching field found\n")
        except Exception as e:
            sys.stderr.write(f"[callhub] Error parsing custom fields: {str(e)}\n")
            return {"isError": True, "content": [{"type": "text", "text": f"Error processing custom fields: {str(e)}"}]}
    
    # If we get here, we didn't find the field
    return {"isError": True, "content": [{"type": "text", "text": f"Custom field with ID {custom_field_id} not found"}]}


def update_contact_custom_field(params: dict) -> dict:
    """
    Update a custom field value for a specific contact.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - contactId: ID of the contact
            - customFieldId: ID of the custom field
            - value: New value for the custom field
            
    Returns:
        Dictionary with operation status
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)

    contact_id = params.get("contactId")
    field_id = params.get("customFieldId")
    value = params.get("value")
    
    if not contact_id or not field_id:
        raise ValueError("Both 'contactId' and 'customFieldId' are required.")
        
    # Value can be None to clear the field, but must be provided as a parameter
    if "value" not in params:
        raise ValueError("'value' parameter is required (can be null to clear the field).")

    headers = get_auth_headers(api_key)
    
    # First, get the contact to get the current data and the field name
    contact_url = build_url(base_url, "v1/contacts/{}/", contact_id)
    contact_result = api_call("GET", contact_url, headers)
    
    if "isError" in contact_result:
        return contact_result
        
    # Use our new helper function instead of direct getCustomField
    custom_field = get_custom_field_info(account_name, field_id)
    
    if "isError" in custom_field:
        return custom_field
    
    # Extract the field name
    field_name = custom_field.get("name")
    if not field_name:
        return {"isError": True, "content": [{"type": "text", "text": f"Custom field with ID {field_id} has no name"}]}
    
    # Now we have the field name, update the contact
    # Start with the basic required field - contact phone number
    update_data = {"contact": contact_result.get("contact")}
    
    # Add the custom field value
    update_data[field_name] = value
    
    # Debug output
    sys.stderr.write(f"[callhub] Updating contact {contact_id} with custom field '{field_name}' = {value}\n")
    sys.stderr.write(f"[callhub] Request URL: {contact_url}\n")
    sys.stderr.write(f"[callhub] Request payload: {update_data}\n")
    
    # Make the API call to update the contact
    result = api_call("PUT", contact_url, headers, json_data=update_data)
    
    # If successful, standardize the response
    if "isError" not in result:
        return {
            "success": True,
            "message": f"Custom field '{field_name}' (ID: {field_id}) updated for contact {contact_id}",
            "contactId": contact_id,
            "customFieldId": field_id,
            "customFieldName": field_name,
            "value": value
        }
    
    # If failed, return the error
    return result
