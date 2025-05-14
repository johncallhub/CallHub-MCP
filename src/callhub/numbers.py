# numbers.py
"""
Phone number management operations for CallHub API.
"""

import sys
from typing import Dict, List, Union, Optional, Any

from .utils import build_url, api_call, get_auth_headers
from .auth import get_account_config

def list_rented_numbers(params: Dict) -> Dict:
    """
    List all rented calling numbers (caller IDs) for the account.
    
    Args:
        params: Dictionary containing the following keys:
            accountName (str, optional): The account name to use
    
    Returns:
        dict: API response containing rented number data or error information
    """
    try:
        # Get account configuration
        account_name, api_key, base_url = get_account_config(params.get("accountName"))
        
        # Build URL and headers
        url = build_url(base_url, "v1/numbers/rented_calling_numbers/")
        headers = get_auth_headers(api_key)
        
        # Make API call
        return api_call("GET", url, headers)
        
    except Exception as e:
        sys.stderr.write(f"[callhub] Error listing rented numbers: {str(e)}\n")
        return {"isError": True, "content": [{"type": "text", "text": str(e)}]}

def list_validated_numbers(params: Dict) -> Dict:
    """
    List all validated personal phone numbers that can be used as caller IDs.
    
    Args:
        params: Dictionary containing the following keys:
            accountName (str, optional): The account name to use
    
    Returns:
        dict: API response containing validated number data or error information
    """
    try:
        # Get account configuration
        account_name, api_key, base_url = get_account_config(params.get("accountName"))
        
        # Build URL and headers
        url = build_url(base_url, "v1/numbers/validated_numbers/")
        headers = get_auth_headers(api_key)
        
        # Make API call
        return api_call("GET", url, headers)
        
    except Exception as e:
        sys.stderr.write(f"[callhub] Error listing validated numbers: {str(e)}\n")
        return {"isError": True, "content": [{"type": "text", "text": str(e)}]}

def rent_number(params: Dict) -> Dict:
    """
    Rent a new phone number to use as a caller ID.
    
    Args:
        params: Dictionary containing the following keys:
            accountName (str, optional): The account name to use
            country_iso (str): The country ISO code for the number (e.g., "US")
            country_code (str): Alternative way to specify country (legacy parameter)
            phone_number_prefix (str, optional): The area code for the number
            area_code (str, optional): Alternative way to specify area code (legacy parameter)
            prefix (str, optional): The prefix for the number
            setup_fee (bool, optional): Whether to pay setup fee (default: True)
    
    Returns:
        dict: API response containing the newly rented number or error information
    """
    try:
        # Get account configuration
        account_name, api_key, base_url = get_account_config(params.get("accountName"))
        
        # Required parameter validation
        country_iso = params.get("country_iso") or params.get("country_code")
        if not country_iso:
            return {"isError": True, "content": [{"type": "text", "text": "Either 'country_iso' or 'country_code' is required."}]}
        
        # Build URL and headers
        url = build_url(base_url, "v1/numbers/rent/")
        headers = get_auth_headers(api_key, "application/json")
        
        # Prepare data
        data = {"country_iso": country_iso}
        
        # Add optional parameters
        if params.get("area_code") or params.get("phone_number_prefix"):
            data["phone_number_prefix"] = params.get("area_code") or params.get("phone_number_prefix")
        if params.get("prefix"):
            data["prefix"] = params["prefix"]
        if "setup_fee" in params:
            data["setup_fee"] = params["setup_fee"]
        
        # Make API call
        return api_call("POST", url, headers, json_data=data)
        
    except Exception as e:
        sys.stderr.write(f"[callhub] Error renting number: {str(e)}\n")
        return {"isError": True, "content": [{"type": "text", "text": str(e)}]}
