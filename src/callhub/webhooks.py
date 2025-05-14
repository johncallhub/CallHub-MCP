# webhooks.py
"""
Webhook operations for CallHub API.
"""

import sys
from typing import Dict, List, Union, Optional, Any

from .utils import build_url, api_call, get_auth_headers
from .auth import get_account_config

def list_webhooks(params: Dict) -> Dict:
    """
    List all webhooks with optional pagination.
    
    Args:
        params: Dictionary containing the following keys:
            accountName (str, optional): The account name to use
            page (int, optional): Page number for pagination
            pageSize (int, optional): Number of items per page
    
    Returns:
        dict: API response containing webhook data or error information
    """
    try:
        # Get account configuration
        account_name, api_key, base_url = get_account_config(params.get("accountName"))
        
        # Build URL and headers
        url = build_url(base_url, "v1/webhooks/")
        headers = get_auth_headers(api_key)
        
        # Prepare query parameters
        query_params = {}
        if params.get("page") is not None:
            query_params["page"] = params["page"]
        if params.get("pageSize") is not None:
            query_params["page_size"] = params["pageSize"]
        
        # Make API call
        return api_call("GET", url, headers, params=query_params)
        
    except Exception as e:
        sys.stderr.write(f"[callhub] Error listing webhooks: {str(e)}\n")
        return {"isError": True, "content": [{"type": "text", "text": str(e)}]}

def get_webhook(params: Dict) -> Dict:
    """
    Retrieve a single webhook by ID. Since the API doesn't have a dedicated endpoint
    for retrieving a single webhook, this function gets all webhooks and filters them.
    
    Args:
        params: Dictionary containing the following keys:
            accountName (str, optional): The account name to use
            webhookId (str): The ID of the webhook to retrieve
    
    Returns:
        dict: API response containing webhook data or error information
    """
    # Validate required parameters
    webhook_id = params.get("webhookId")
    if not webhook_id:
        return {"isError": True, "content": [{"type": "text", "text": "'webhookId' is required."}]}
    
    try:
        # Get account configuration
        account_name, api_key, base_url = get_account_config(params.get("accountName"))
        
        # Get all webhooks
        list_params = {"accountName": account_name}
        all_webhooks_response = list_webhooks(list_params)
        
        # Check if there was an error getting all webhooks
        if "isError" in all_webhooks_response:
            return all_webhooks_response
        
        # Extract the webhooks from the response
        all_webhooks = all_webhooks_response.get("results", [])
        
        # Find the webhook with the matching ID
        for webhook in all_webhooks:
            if str(webhook.get("id")) == str(webhook_id):
                return {"result": webhook, "status": "success"}
        
        # If no webhook found with that ID
        return {
            "isError": True, 
            "content": [{"type": "text", "text": f"No webhook found with ID '{webhook_id}'"}]
        }
        
    except Exception as e:
        sys.stderr.write(f"[callhub] Error getting webhook: {str(e)}\n")
        return {"isError": True, "content": [{"type": "text", "text": str(e)}]}

def create_webhook(params: Dict) -> Dict:
    """
    Create a new webhook.
    
    Args:
        params: Dictionary containing the following keys:
            accountName (str, optional): The account name to use
            event (str): The event type to listen for (e.g., 'vb.transfer', 'sb.reply', 'cc.notes', 'agent.activation')
            target (str): The URL that will receive webhook events
    
    Returns:
        dict: API response containing the created webhook data or error information
    """
    # Validate required parameters
    event = params.get("event_name") or params.get("event")
    target = params.get("target_url") or params.get("target")
    
    if not event:
        return {"isError": True, "content": [{"type": "text", "text": "'event' is required."}]}
    if not target:
        return {"isError": True, "content": [{"type": "text", "text": "'target' is required."}]}
    
    # Validate event type
    valid_events = ['vb.transfer', 'sb.reply', 'cc.notes', 'agent.activation']
    if event not in valid_events:
        return {
            "isError": True, 
            "content": [{"type": "text", "text": f"'event' must be one of: {', '.join(valid_events)}"}]
        }
    
    try:
        # Get account configuration
        account_name, api_key, base_url = get_account_config(params.get("accountName"))
        
        # Build URL and headers - using application/x-www-form-urlencoded since the API example does
        url = build_url(base_url, "v1/webhooks/")
        headers = get_auth_headers(api_key, "application/x-www-form-urlencoded")
        
        # Prepare payload
        data = {
            "event": event,  # API expects 'event' and 'target' based on documentation
            "target": target
        }
        
        # Make API call - use data parameter for form-encoded
        return api_call("POST", url, headers, data=data)
        
    except Exception as e:
        sys.stderr.write(f"[callhub] Error creating webhook: {str(e)}\n")
        return {"isError": True, "content": [{"type": "text", "text": str(e)}]}

def delete_webhook(params: Dict) -> Dict:
    """
    Delete a webhook by ID.
    
    Args:
        params: Dictionary containing the following keys:
            accountName (str, optional): The account name to use
            webhookId (str): The ID of the webhook to delete
    
    Returns:
        dict: API response or error information
    """
    # Validate required parameters
    webhook_id = params.get("webhookId")
    if not webhook_id:
        return {"isError": True, "content": [{"type": "text", "text": "'webhookId' is required."}]}
    
    try:
        # Get account configuration
        account_name, api_key, base_url = get_account_config(params.get("accountName"))
        
        # Build URL and headers
        url = build_url(base_url, "v1/webhooks/{}/", webhook_id)
        headers = get_auth_headers(api_key)
        
        # Make API call
        return api_call("DELETE", url, headers)
        
    except Exception as e:
        sys.stderr.write(f"[callhub] Error deleting webhook: {str(e)}\n")
        return {"isError": True, "content": [{"type": "text", "text": str(e)}]}
