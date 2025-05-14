# File: src/callhub/dnc.py

from .auth import get_account_config
from .utils import build_url, api_call

def create_dnc_contact(account=None, dnc=None, phone_number=None, category=3):
    """
    Create a new DNC contact.
    
    Args:
        account (str, optional): The CallHub account name to use. Defaults to 'default'.
        dnc (str, required): URL of the DNC list that the phone number belongs to.
                             Format: 'https://api.callhub.io/v1/dnc_lists/{id}/'
        phone_number (str, required): Phone number of the contact in E.164 format.
        category (int, optional): 1 for call opt-out only, 2 for text opt-out only,
                                 3 for both call and text opt-out. Defaults to 3.
        
    Returns:
        dict: API response containing the created DNC contact information.
    """
    try:
        _, api_key, base_url = get_account_config(account)
    except Exception as e:
        return {"isError": True, "content": [{"text": str(e)}]}
    
    if not dnc:
        return {"isError": True, "content": [{"text": "'dnc' is required. Format: 'https://api.callhub.io/v1/dnc_lists/{id}/'"}]}
    
    if not phone_number:
        return {"isError": True, "content": [{"text": "'phone_number' is required."}]}
    
    url = build_url(base_url, "v1/dnc_contacts/")
    headers = {"Authorization": f"Token {api_key}"}
    
    data = {
        "dnc": dnc,
        "phone_number": phone_number,
        "category": category
    }
    
    result = api_call("POST", url, headers, data=data)
    return result


def list_dnc_contacts(account=None, page=None, pageSize=None, allPages=False):
    """
    Retrieve a list of DNC contacts with optional pagination.
    
    Args:
        account (str, optional): The CallHub account name to use. Defaults to 'default'.
        page (int, optional): Page number for pagination. Defaults to 1.
        pageSize (int, optional): Number of items per page. Defaults to 10.
        allPages (bool, optional): If True, fetch all pages. Defaults to False.
        
    Returns:
        dict: API response containing DNC contacts with url, dnc, and phone_number fields.
    """
    try:
        _, api_key, base_url = get_account_config(account)
    except Exception as e:
        return {"isError": True, "content": [{"text": str(e)}]}
    
    url = build_url(base_url, "v1/dnc_contacts/")
    headers = {"Authorization": f"Token {api_key}"}
    
    params = {}
    if page:
        params["page"] = page
    if pageSize:
        params["page_size"] = pageSize
    
    if not allPages:
        result = api_call("GET", url, headers, params=params)
        return result
    
    # Handle fetching all pages
    all_results = []
    current_page = 1
    
    while True:
        params["page"] = current_page
        result = api_call("GET", url, headers, params=params)
        
        if "isError" in result:
            return result
        
        if "results" in result:
            all_results.extend(result["results"])
            
            if not result.get("next"):
                break
            
            current_page += 1
        else:
            break
    
    return {"count": len(all_results), "results": all_results}


def update_dnc_contact(account=None, contactId=None, dnc=None, phone_number=None):
    """
    Update an existing DNC contact by ID.
    
    Args:
        account (str, optional): The CallHub account name to use. Defaults to 'default'.
        contactId (str, required): The ID of the DNC contact to update.
        dnc (str, required): URL of the DNC list that the contact belongs to.
                            Format: 'https://api.callhub.io/v1/dnc_lists/{id}/'
        phone_number (str, required): Phone number of the contact in E.164 format.
        
    Returns:
        dict: API response containing the updated DNC contact information.
        
    Note:
        Both 'dnc' and 'phone_number' fields are required by the CallHub API.
        Omitting either field will result in a 400 Bad Request error.
    """
    try:
        _, api_key, base_url = get_account_config(account)
    except Exception as e:
        return {"isError": True, "content": [{"text": str(e)}]}
    
    if not contactId:
        return {"isError": True, "content": [{"text": "'contactId' is required."}]}
    
    if not dnc:
        return {"isError": True, "content": [{"text": "'dnc' is required. Format: 'https://api.callhub.io/v1/dnc_lists/{id}/'"}]}
    
    if not phone_number:
        return {"isError": True, "content": [{"text": "'phone_number' is required."}]}
    
    url = build_url(base_url, "v1/dnc_contacts/{}/", contactId)
    headers = {"Authorization": f"Token {api_key}"}
    
    data = {
        "dnc": dnc,
        "phone_number": phone_number
    }
    
    result = api_call("PUT", url, headers, data=data)
    return result


def delete_dnc_contact(account=None, contactId=None):
    """
    Delete a DNC contact by ID.
    
    Args:
        account (str, optional): The CallHub account name to use. Defaults to 'default'.
        contactId (str, required): The ID of the DNC contact to delete.
        
    Returns:
        dict: API response indicating success or failure.
    """
    try:
        _, api_key, base_url = get_account_config(account)
    except Exception as e:
        return {"isError": True, "content": [{"text": str(e)}]}
    
    if not contactId:
        return {"isError": True, "content": [{"text": "'contactId' is required."}]}
    
    url = build_url(base_url, "v1/dnc_contacts/{}/", contactId)
    headers = {"Authorization": f"Token {api_key}"}
    
    result = api_call("DELETE", url, headers)
    return result


def create_dnc_list(account=None, name=None):
    """
    Create a new DNC list.
    
    Args:
        account (str, optional): The CallHub account name to use. Defaults to 'default'.
        name (str, required): Name of the DNC list to be created.
        
    Returns:
        dict: API response containing the created DNC list information.
    """
    try:
        _, api_key, base_url = get_account_config(account)
    except Exception as e:
        return {"isError": True, "content": [{"text": str(e)}]}
    
    if not name:
        return {"isError": True, "content": [{"text": "'name' is required."}]}
    
    url = build_url(base_url, "v1/dnc_lists/")
    headers = {"Authorization": f"Token {api_key}"}
    
    data = {"name": name}
    
    result = api_call("POST", url, headers, data=data)
    return result


def list_dnc_lists(account=None, page=None, pageSize=None, allPages=False):
    """
    Retrieve a list of DNC lists with optional pagination.
    
    Args:
        account (str, optional): The CallHub account name to use. Defaults to 'default'.
        page (int, optional): Page number for pagination. Defaults to 1.
        pageSize (int, optional): Number of items per page. Defaults to 10.
        allPages (bool, optional): If True, fetch all pages. Defaults to False.
        
    Returns:
        dict: API response containing DNC lists with url, owner, and name fields.
    """
    try:
        _, api_key, base_url = get_account_config(account)
    except Exception as e:
        return {"isError": True, "content": [{"text": str(e)}]}
    
    url = build_url(base_url, "v1/dnc_lists/")
    headers = {"Authorization": f"Token {api_key}"}
    
    params = {}
    if page:
        params["page"] = page
    if pageSize:
        params["page_size"] = pageSize
    
    if not allPages:
        result = api_call("GET", url, headers, params=params)
        return result
    
    # Handle fetching all pages
    all_results = []
    current_page = 1
    
    while True:
        params["page"] = current_page
        result = api_call("GET", url, headers, params=params)
        
        if "isError" in result:
            return result
        
        if "results" in result:
            all_results.extend(result["results"])
            
            if not result.get("next"):
                break
            
            current_page += 1
        else:
            break
    
    return {"count": len(all_results), "results": all_results}


def update_dnc_list(account=None, listId=None, name=None):
    """
    Update an existing DNC list by ID.
    
    Args:
        account (str, optional): The CallHub account name to use. Defaults to 'default'.
        listId (str, required): The ID of the DNC list to update.
        name (str, required): The new name for the DNC list.
        
    Returns:
        dict: API response containing the updated DNC list information.
    """
    try:
        _, api_key, base_url = get_account_config(account)
    except Exception as e:
        return {"isError": True, "content": [{"text": str(e)}]}
    
    if not listId:
        return {"isError": True, "content": [{"text": "'listId' is required."}]}
    
    if not name:
        return {"isError": True, "content": [{"text": "'name' is required."}]}
    
    url = build_url(base_url, "v1/dnc_lists/{}/", listId)
    headers = {"Authorization": f"Token {api_key}"}
    
    data = {"name": name}
    
    result = api_call("PUT", url, headers, data=data)
    return result


def delete_dnc_list(account=None, listId=None):
    """
    Delete a DNC list by ID.
    
    Args:
        account (str, optional): The CallHub account name to use. Defaults to 'default'.
        listId (str, required): The ID of the DNC list to delete.
        
    Returns:
        dict: API response indicating success or failure.
    """
    try:
        _, api_key, base_url = get_account_config(account)
    except Exception as e:
        return {"isError": True, "content": [{"text": str(e)}]}
    
    if not listId:
        return {"isError": True, "content": [{"text": "'listId' is required."}]}
    
    url = build_url(base_url, "v1/dnc_lists/{}/", listId)
    headers = {"Authorization": f"Token {api_key}"}
    
    result = api_call("DELETE", url, headers)
    return result
