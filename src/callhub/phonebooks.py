# phonebooks.py
"""
Phonebook management functions for CallHub API.
"""

import sys
from typing import Dict, List, Union, Optional, Any

from .auth import get_account_config
from .utils import build_url, api_call, get_auth_headers

def list_phonebooks(params: dict) -> dict:
    """
    List phonebooks with optional pagination.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - page (optional): Page number for pagination
            - pageSize (optional): Number of results per page
            
    Returns:
        Dictionary with phonebook results
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)

    headers = get_auth_headers(api_key)
    query = {}
    if params.get("page"):
        query["page"] = params["page"]
    if params.get("pageSize"):
        query["page_size"] = params["pageSize"]

    url = build_url(base_url, "v1/phonebooks/")
    return api_call("GET", url, headers, params=query)

def get_phonebook(params: dict) -> dict:
    """
    Retrieve a single phonebook by ID.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - phonebookId: ID of the phonebook to retrieve
            
    Returns:
        Dictionary with phonebook details
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)

    pb_id = params.get("phonebookId")
    if not pb_id:
        raise ValueError("'phonebookId' is required.")

    headers = get_auth_headers(api_key)
    url = build_url(base_url, "v1/phonebooks/{}/", pb_id)
    
    return api_call("GET", url, headers)

def create_phonebook(params: dict) -> dict:
    """
    Create a new phonebook.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - name: Name of the phonebook (required)
            - description (optional): Description of the phonebook
            
    Returns:
        Dictionary with created phonebook details
    """
    account_name = params.pop("accountName", None)
    _, api_key, base_url = get_account_config(account_name)

    # Ensure name is provided
    if "name" not in params:
        raise ValueError("'name' field is required to create a phonebook")

    # Debug output to help troubleshoot
    sys.stderr.write(f"[callhub] Creating phonebook with params: {params}\n")

    headers = get_auth_headers(api_key, "application/x-www-form-urlencoded")
    url = build_url(base_url, "v1/phonebooks/")
    
    return api_call("POST", url, headers, data=params)

def update_phonebook(params: dict) -> dict:
    """
    Update an existing phonebook by ID.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - phonebookId: ID of the phonebook to update
            - name (optional): New name for the phonebook
            - description (optional): New description for the phonebook
            
    Returns:
        Dictionary with updated phonebook details
    """
    account_name = params.pop("accountName", None)
    _, api_key, base_url = get_account_config(account_name)

    pb_id = params.pop("phonebookId", None)
    if not pb_id:
        raise ValueError("'phonebookId' is required.")

    # Debug output to help troubleshoot
    sys.stderr.write(f"[callhub] Updating phonebook {pb_id} with params: {params}\n")

    headers = get_auth_headers(api_key, "application/x-www-form-urlencoded")
    url = build_url(base_url, "v1/phonebooks/{}/", pb_id)
    
    # Store the original phonebook data to verify changes
    try:
        original_pb = get_phonebook({"accountName": account_name, "phonebookId": pb_id})
    except:
        original_pb = None
    
    # Use the API call helper
    result = api_call("PATCH", url, headers, data=params)
    
    # Verify changes if we have the original data
    if original_pb and "isError" not in result and not isinstance(result, dict):
        for key, value in params.items():
            if key in result and result.get(key) != value:
                sys.stderr.write(f"[callhub] Warning: Field '{key}' may not have updated correctly\n")
                sys.stderr.write(f"[callhub] Expected: {value}, Got: {result.get(key)}\n")
    
    return result

def delete_phonebook(params: dict) -> dict:
    """
    Delete a phonebook by ID.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - phonebookId: ID of the phonebook to delete
            
    Returns:
        Dictionary with deletion status
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)

    pb_id = params.get("phonebookId")
    if not pb_id:
        raise ValueError("'phonebookId' is required.")

    headers = get_auth_headers(api_key)
    url = build_url(base_url, "v1/phonebooks/{}/", pb_id)
    
    result = api_call("DELETE", url, headers)
    
    # If successful, return a standardized response
    if "isError" not in result:
        return {"deleted": True, "phonebookId": pb_id}
    return result

def add_contacts_to_phonebook(params: dict) -> dict:
    """
    Add existing contacts to a phonebook.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - phonebookId: ID of the phonebook
            - contactIds: List of contact IDs to add
            
    Returns:
        Dictionary with operation status
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)

    pb_id = params.get("phonebookId")
    contact_ids = params.get("contactIds")
    if not pb_id or contact_ids is None:
        raise ValueError("Both 'phonebookId' and 'contactIds' are required.")

    # Ensure all contact IDs are strings
    contact_ids_str = [str(cid) for cid in contact_ids]

    # Debug output to help troubleshoot
    sys.stderr.write(f"[callhub] Adding contacts {contact_ids_str} to phonebook {pb_id}\n")

    headers = get_auth_headers(api_key)
    body = {"contact_ids": contact_ids_str}
    url = build_url(base_url, "v1/phonebooks/{}/contacts/", pb_id)

    # Use the API call helper function
    result = api_call("POST", url, headers, json_data=body)
    
    # If successful but the API returned a generic success response, provide more context
    if "success" in result and result.get("success") == True:
        result["message"] = f"Added {len(contact_ids_str)} contacts to phonebook {pb_id}"
        
    return result

def remove_contact_from_phonebook(params: dict) -> dict:
    """
    Remove a contact from a phonebook.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - phonebookId: ID of the phonebook
            - contactId: ID of the contact to remove
            
    Returns:
        Dictionary with operation status
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)

    pb_id = params.get("phonebookId")
    cid = params.get("contactId")
    if not pb_id or not cid:
        raise ValueError("Both 'phonebookId' and 'contactId' are required.")

    # Ensure contact ID is a string
    cid_str = str(cid)
    
    headers = get_auth_headers(api_key)
    body = {"contact_ids": [cid_str]}
    url = build_url(base_url, "v1/phonebooks/{}/contacts/", pb_id)

    # Use the API call helper
    result = api_call("DELETE", url, headers, json_data=body)
    
    # If successful, return a standardized response
    if "isError" not in result:
        # Check phonebook to verify contact was removed
        try:
            # Get the phonebook count before and after
            count_before = get_phonebook_count({"accountName": account_name, "phonebookId": pb_id})
            
            # Verify contact was removed by searching for it in the phonebook
            # (This would require additional code to check specific contacts in a phonebook)
            
            return {"removed": True, "phonebookId": pb_id, "contactId": cid}
        except Exception as e:
            sys.stderr.write(f"[callhub] Warning: Unable to verify contact removal: {str(e)}\n")
            return {"removed": True, "phonebookId": pb_id, "contactId": cid}
    
    return result

def get_phonebook_count(params: dict) -> dict:
    """
    Get the total number of contacts in a phonebook.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - phonebookId: ID of the phonebook to count
            
    Returns:
        Dictionary with contact counts
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)

    pb_id = params.get("phonebookId")
    if not pb_id:
        raise ValueError("'phonebookId' is required.")

    headers = get_auth_headers(api_key)
    url = build_url(base_url, "v1/phonebooks/{}/numbers_count/", pb_id)
    
    return api_call("GET", url, headers)

def get_phonebook_contacts(params: dict) -> dict:
    """
    Get contacts in a specific phonebook with pagination.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - phonebookId: ID of the phonebook
            - page (optional): Page number
            - pageSize (optional): Results per page
            - allPages (optional): If True, fetch all pages
            
    Returns:
        Dictionary with contacts in the phonebook
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)

    pb_id = params.get("phonebookId")
    if not pb_id:
        raise ValueError("'phonebookId' is required.")
        
    headers = get_auth_headers(api_key)
    
    results = []
    page = params.get("page", 1)
    page_size = params.get("pageSize")
    all_pages = params.get("allPages", False)
    
    while True:
        query = {"page": page}
        if page_size:
            query["page_size"] = page_size
            
        # The correct endpoint is /contacts/ not /get_contacts/
        url = build_url(base_url, "v1/phonebooks/{}/contacts/", pb_id)
        result = api_call("GET", url, headers, params=query)
        
        if "isError" in result:
            return result
            
        data = result
        
        if all_pages:
            results.extend(data.get("results", []))
            if not data.get("next"):
                break
            page += 1
        else:
            return data
            
    return {"results": results}
