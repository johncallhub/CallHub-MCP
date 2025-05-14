# File: src/callhub/users.py

from .auth import get_account_config
from .utils import api_call, build_url

def list_users(params):
    """
    Retrieve a list of all users in the CallHub account.
    
    Args:
        params (dict): Dictionary containing the following keys:
            - accountName (str, optional): The account name to use
    
    Returns:
        dict: A dictionary containing the API response with user data
    """
    _, api_key, base_url = get_account_config(params.get("accountName"))
    headers = {"Authorization": f"Token {api_key}"}
    url = build_url(base_url, "v1/users/")
    
    result = api_call("GET", url, headers)
    return result

def get_credit_usage(params):
    """
    Retrieve credit usage details for the CallHub account.
    
    Args:
        params (dict): Dictionary containing the following keys:
            - accountName (str, optional): The account name to use
            - start_date (str, optional): Start date in MM/DD/YYYY format
            - end_date (str, optional): End date in MM/DD/YYYY format
            - generate_csv (bool, optional): Whether to output in CSV (True) or JSON (False)
            - campaign_type (int, optional): Filter by campaign type (1=SMS, 3=Text2Join, 4=P2P, 5=CallCentre, 6=Voice)
    
    Returns:
        dict: A dictionary containing the API response with credit usage data
    """
    _, api_key, base_url = get_account_config(params.get("accountName"))
    headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}
    url = build_url(base_url, "v2/credits_usage/")
    
    # Prepare the request payload
    payload = {}
    
    # Add parameters - start_date is required in mm/dd/yyyy format
    if params.get("start_date"):
        payload["start_date"] = params.get("start_date")
    else:
        # Default to current date if not provided
        from datetime import datetime
        today = datetime.now()
        payload["start_date"] = today.strftime("%m/%d/%Y")
    
    # Add end_date if provided (also in mm/dd/yyyy format)
    if params.get("end_date"):
        payload["end_date"] = params.get("end_date")
    
    # Campaign type is optional
    if params.get("campaign_type") is not None:
        payload["campaign_type"] = params.get("campaign_type")
        
    # generate_csv is required (whether output is CSV or JSON)
    generate_csv = False
    if params.get("generate_csv") is not None:
        generate_csv = params.get("generate_csv")
        payload["generate_csv"] = generate_csv
    else:
        # Default to JSON (False) if not specified
        payload["generate_csv"] = False
    
    # Make the API call without using the util function for more control
    import requests
    import sys
    
    try:
        sys.stderr.write(f"[callhub] POST request to {url}\n")
        sys.stderr.write(f"[callhub] Payload: {payload}\n")
        
        response = requests.post(url, headers=headers, json=payload)
        
        # Handle error responses
        if response.status_code >= 400:
            sys.stderr.write(f"[callhub] API error: {response.status_code} {response.reason}\n")
            try:
                sys.stderr.write(f"[callhub] Response body: {response.text}\n")
            except:
                pass
            response.raise_for_status()
        
        # Handle CSV response
        if generate_csv and response.text:
            # Return CSV data as is
            return {
                "format": "csv",
                "data": response.text,
                "success": True
            }
        # Handle JSON response
        elif response.text:
            try:
                return response.json()
            except Exception as e:
                # If can't parse as JSON but has content, return text
                return {
                    "format": "text",
                    "data": response.text,
                    "success": True
                }
        else:
            # Empty response
            return {"success": True, "message": "Operation successful but no data returned"}
            
    except requests.exceptions.RequestException as e:
        # Build a user-friendly error response
        status_code = e.response.status_code if hasattr(e, 'response') and e.response else None
        
        # Special handling for rate limiting errors
        if status_code == 429:
            return {
                "isError": True, 
                "content": [{
                    "type": "text", 
                    "text": f"Rate limit exceeded (429). The API has a limit of calls per minute."
                }]
            }
        
        # Generic error response
        sys.stderr.write(f"[callhub] Request exception: {str(e)}\n")
        return {"isError": True, "content": [{"type": "text", "text": str(e)}]}
        
    except Exception as e:
        sys.stderr.write(f"[callhub] Unexpected error: {str(e)}\n")
        return {"isError": True, "content": [{"type": "text", "text": str(e)}]}
