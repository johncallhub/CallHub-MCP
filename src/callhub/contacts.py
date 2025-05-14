# contacts.py
"""
Contact management functions for CallHub API.
"""

import sys
import json
import requests
from typing import Dict, List, Union, Optional, Any

from .auth import get_account_config
from .utils import build_url, api_call, get_auth_headers, retry_with_backoff

def list_contacts(params: dict) -> dict:
    """
    List contacts with optional pagination and filters.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - page (optional): Page number for pagination
            - pageSize (optional): Number of results per page
            - filters (optional): Dictionary of filters
            - allPages (optional): If True, fetch all pages
            
    Returns:
        Dictionary with contact results
    """
    account_name = params.pop("accountName", None)
    _, api_key, base_url = get_account_config(account_name)

    headers = get_auth_headers(api_key)

    results = []
    page = params.get("page", 1)
    page_size = params.get("pageSize")
    all_pages = params.get("allPages", False)

    while True:
        query = {"page": page}
        if page_size:
            query["page_size"] = page_size
        if f := params.get("filters"):
            query.update(f)

        url = build_url(base_url, "v1/contacts/")
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

def get_contact(params: dict) -> dict:
    """
    Retrieve a single contact by ID.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - contactId: ID of the contact to retrieve
            
    Returns:
        Dictionary with contact details
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)

    cid = params.get("contactId")
    if not cid:
        raise ValueError("'contactId' is required.")

    headers = get_auth_headers(api_key)
    url = build_url(base_url, "v1/contacts/{}/", cid)
    
    return api_call("GET", url, headers)

def create_contact(params: dict) -> dict:
    """
    Create a new contact.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - contact: Phone number (string) used for voice campaigns
            - Additional fields like first_name, last_name, email, etc.
            
    Returns:
        Dictionary with created contact details
    """
    account_name = params.pop("accountName", None)
    _, api_key, base_url = get_account_config(account_name)

    # Ensure contact number is provided
    if "contact" not in params:
        raise ValueError("'contact' field is required to create a contact")

    # Debug output to help troubleshoot
    sys.stderr.write(f"[callhub] Creating contact with params: {params}\n")

    headers = get_auth_headers(api_key, "application/x-www-form-urlencoded")
    url = build_url(base_url, "v1/contacts/")
    
    return api_call("POST", url, headers, data=params)

def create_contacts_bulk(params: dict) -> dict:
    """
    Create multiple contacts by uploading a CSV file or providing a CSV URL.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - phonebook_id: Required - ID of the phonebook to associate contacts with
            - csv_file_path: Path to a local CSV file to upload (required if csv_url not provided)
            - csv_url: URL to a CSV file (required if csv_file_path not provided)
            - mapping: Dictionary mapping field IDs to column indexes in the CSV
              Example: {"0": 0, "2": 1, "3": 2} maps:
                   - Phone number (0) to column 0
                   - Last name (2) to column 1
                   - First name (3) to column 2
            - country_choice (optional): "file" (default) or "custom" 
            - country_iso (required if country_choice is "custom"): Country code
            
    Returns:
        Dictionary with bulk creation results or status message
        
    Note:
        This endpoint has a rate limit of 1 call per minute.
        The format of the mapping should be field_id:column_index
        Field IDs correspond to:
            - 0: Contact (phone number used for voice campaigns)
            - 1: Mobile (phone number used for SMS campaigns)
            - 2: Last name
            - 3: First name
            - 4: Email
            - 5: Country code
            - 6: Address
            - 7: City
            - 8: State
            - 9: Zipcode
            - 10: Job title
            - 11: Company name
            - 12: Company website
            - 13: Name
            - 14: Additional variables
            - 16: Tags (comma-separated)
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)
    
    # Check for required phonebook_id
    phonebook_id = params.get("phonebook_id")
    if not phonebook_id:
        return {"isError": True, "content": [{"type": "text", "text": "'phonebook_id' is required."}]}
    
    # Check if we have either a CSV file path or URL
    csv_file_path = params.get("csv_file_path")
    csv_url = params.get("csv_url")
    
    if not csv_file_path and not csv_url:
        return {"isError": True, "content": [{"type": "text", "text": "Either 'csv_file_path' or 'csv_url' must be provided."}]}
    
    # Get country_choice and country_iso if needed
    country_choice = params.get("country_choice", "file")
    country_iso = None
    if country_choice == "custom":
        country_iso = params.get("country_iso")
        if not country_iso:
            return {"isError": True, "content": [{"type": "text", "text": "'country_iso' is required when country_choice is 'custom'."}]}
    
    # Get mapping or create default mapping
    mapping = params.get("mapping", {})
    
    if not mapping:
        # Create a default mapping for a standard CSV format
        # Assuming CSV has: ContactNumber,LastName,FirstName,Email,...
        mapping = {
            "0": 0,  # Contact number in first column
            "2": 1,  # Last name in second column
            "3": 2,  # First name in third column
            "4": 3   # Email in fourth column
        }
    
    # Setup the common headers for both file upload and URL cases
    headers = {"Authorization": f"Token {api_key}"}
    url = build_url(base_url, "v1/contacts/bulk_create/")
    
    try:
        # Handle file upload
        if csv_file_path:
            try:
                with open(csv_file_path, 'rb') as csv_file:
                    # Prepare the form data
                    data = {
                        'phonebook_id': phonebook_id,
                        'country_choice': country_choice,
                        'mapping': json.dumps(mapping)
                    }
                    
                    # Add country_iso if needed
                    if country_choice == "custom":
                        data["country_iso"] = country_iso
                    
                    # Create the file payload
                    files = {'contacts_csv': (csv_file_path.split('/')[-1], csv_file, 'text/csv')}
                    
                    sys.stderr.write(f"[callhub] Bulk creating contacts from file: {csv_file_path}\n")
                    sys.stderr.write(f"[callhub] Using mapping: {mapping}\n")
                    sys.stderr.write(f"[callhub] With phonebook_id: {phonebook_id}\n")
                    
                    # Make the POST request
                    resp = requests.post(url, headers=headers, data=data, files=files)
            except FileNotFoundError:
                return {"isError": True, "content": [{"type": "text", "text": f"File not found: {csv_file_path}"}]}
            except IOError as e:
                return {"isError": True, "content": [{"type": "text", "text": f"Error opening file: {str(e)}"}]}
        
        # Handle CSV URL
        else:
            # Prepare the form data
            data = {
                'phonebook_id': phonebook_id,
                'country_choice': country_choice,
                'mapping': json.dumps(mapping),
                'csv_url': csv_url
            }
            
            # Add country_iso if needed
            if country_choice == "custom":
                data["country_iso"] = country_iso
            
            sys.stderr.write(f"[callhub] Bulk creating contacts from URL: {csv_url}\n")
            sys.stderr.write(f"[callhub] Using mapping: {mapping}\n")
            sys.stderr.write(f"[callhub] With phonebook_id: {phonebook_id}\n")
            
            # Make the POST request (content-type will be auto-set to form-urlencoded)
            resp = requests.post(url, headers=headers, data=data)
        
        # Handle responses for both cases
        sys.stderr.write(f"[callhub] Response status: {resp.status_code}\n")
        
        # For debugging
        if resp.status_code >= 400:
            sys.stderr.write(f"[callhub] Response headers: {resp.headers}\n")
            sys.stderr.write(f"[callhub] Response body: {resp.text}\n")
        
        # Handle rate limiting with a friendly message
        if resp.status_code == 429:
            retry_after = None
            if resp.headers:
                retry_after = resp.headers.get('retry-after') or resp.headers.get('Retry-After')
            
            retry_msg = ""
            if retry_after:
                retry_msg = f" Please try again in {retry_after} seconds."
            
            return {
                "isError": True,
                "content": [{
                    "type": "text", 
                    "text": f"The bulk create contacts API is currently rate limited. It can only be called once per minute.{retry_msg}"
                }],
                "isRateLimited": True,
                "retryAfter": retry_after if retry_after else 60
            }
        
        # For other errors
        if resp.status_code >= 400:
            resp.raise_for_status()
        
        # Success case
        if resp.status_code == 204 or not resp.text:
            return {"success": True, "message": "Bulk contact creation started successfully!"}
        
        return resp.json()
    
    except requests.exceptions.RequestException as e:
        # Special handling for rate limit errors
        if hasattr(e, 'response') and e.response and e.response.status_code == 429:
            # Extract retry time if available
            retry_after = None
            if e.response.headers:
                retry_after = e.response.headers.get('retry-after') or e.response.headers.get('Retry-After')
            
            retry_msg = ""
            if retry_after:
                retry_msg = f" Please try again in {retry_after} seconds."
            
            return {
                "isError": True,
                "content": [{
                    "type": "text", 
                    "text": f"The bulk create contacts API is currently rate limited. It can only be called once per minute.{retry_msg}"
                }],
                "isRateLimited": True,
                "retryAfter": retry_after if retry_after else 60
            }
        
        # For all other request exceptions
        return {"isError": True, "content": [{"type": "text", "text": str(e)}]}

def update_contact(params: dict) -> dict:
    """
    Update an existing contact identified by phone number.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - contact: Phone number to identify the contact
            - Additional fields to update
            
    Returns:
        Dictionary with updated contact details
        
    Note: 
        This function may create a new contact if multiple contacts
        have the same phone number or under certain conditions.
    """
    account_name = params.pop("accountName", None)
    _, api_key, base_url = get_account_config(account_name)

    # We need the contact phone number, not the ID
    phone = params.get("contact")
    if not phone:
        raise ValueError("'contact' (phone number) is required to identify the contact.")

    # First, let's try to find if there are multiple contacts with this phone number
    original_contact_ids = find_duplicate_contacts({
        "accountName": account_name,
        "contact": phone
    })
    
    if len(original_contact_ids) > 1:
        sys.stderr.write(f"[callhub] Warning: Multiple contacts ({len(original_contact_ids)}) found with phone {phone}\n")
    original_contact_id = original_contact_ids[0] if original_contact_ids else None

    # Debug output to help troubleshoot
    sys.stderr.write(f"[callhub] Updating contact with phone {phone} with params: {params}\n")

    headers = get_auth_headers(api_key, "application/x-www-form-urlencoded")
    url = build_url(base_url, "v1/contacts/")

    # Use api_call with retry logic
    result = api_call("POST", url, headers, data=params)
    
    # Additional verification for update operations
    if "isError" not in result and "id" in result and original_contact_id:
        if str(result["id"]) != str(original_contact_id):
            sys.stderr.write(f"[callhub] Warning: A new contact may have been created instead of updating existing one\n")
            sys.stderr.write(f"[callhub] New contact ID: {result['id']}, Original ID: {original_contact_id}\n")
    
    # Verify all fields were updated as expected
    if "isError" not in result:
        for key, value in params.items():
            if key != "contact" and key in result and str(result[key]) != str(value):
                sys.stderr.write(f"[callhub] Warning: Field '{key}' may not have updated correctly\n")
                sys.stderr.write(f"[callhub] Expected: {value}, Got: {result[key]}\n")
    
    return result

def delete_contact(params: dict) -> dict:
    """
    Delete a contact by ID.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - contactId: ID of the contact to delete
            
    Returns:
        Dictionary with deletion status
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)

    cid = params.get("contactId")
    if not cid:
        raise ValueError("'contactId' is required.")

    headers = get_auth_headers(api_key)
    url = build_url(base_url, "v1/contacts/{}/", cid)
    
    # Use the API call helper function
    result = api_call("DELETE", url, headers)
    
    # If successful, return a standardized response
    if "isError" not in result:
        return {"deleted": True, "contactId": cid}
    return result

def get_contact_fields(params: dict) -> dict:
    """
    List all available contact fields for this account.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            
    Returns:
        Dictionary with contact fields
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)

    headers = get_auth_headers(api_key)
    url = build_url(base_url, "v1/contacts/fields/")
    
    return api_call("GET", url, headers)

def find_duplicate_contacts(params: dict) -> List[str]:
    """
    Find all contacts with the same phone number.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - contact: Phone number to search for
            
    Returns:
        List of contact IDs that have the same phone number
    """
    account_name = params.get("accountName")
    phone = params.get("contact")
    if not phone:
        raise ValueError("'contact' (phone number) is required.")
        
    # Get all contacts and filter by phone
    search_params = params.copy()
    if "contact" in search_params:
        search_params["filters"] = {"contact": search_params.pop("contact")}
    search_params["allPages"] = True
    
    results = list_contacts(search_params)
    if "isError" in results:
        return []
        
    # Extract contact IDs
    contacts = results.get("results", [])
    return [contact["id"] for contact in contacts if "id" in contact]
