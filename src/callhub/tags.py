# tags.py
"""
Tag management functions for CallHub API.
"""

import sys
import json
from typing import Dict, List, Union, Optional, Any

from .auth import get_account_config
from .utils import build_url, api_call, get_auth_headers

def list_tags(params: dict) -> dict:
    """
    List all tags for the account.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - page (optional): Page number for pagination
            - pageSize (optional): Number of results per page
            
    Returns:
        Dictionary with tag results
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)

    headers = get_auth_headers(api_key)
    query = {}
    if params.get("page"):
        query["page"] = params["page"]
    if params.get("pageSize"):
        query["page_size"] = params["pageSize"]

    url = build_url(base_url, "v1/tags/")
    return api_call("GET", url, headers, params=query)

def get_tag(params: dict) -> dict:
    """
    Retrieve a single tag by ID.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - tagId: ID of the tag to retrieve
            
    Returns:
        Dictionary with tag details
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)

    tag_id = params.get("tagId")
    if not tag_id:
        raise ValueError("'tagId' is required.")

    headers = get_auth_headers(api_key)
    url = build_url(base_url, "v1/tags/{}/", tag_id)
    
    return api_call("GET", url, headers)

def create_tag(params: dict) -> dict:
    """
    Create a new tag.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - name: Name of the tag (required)
            - description (optional): Description of the tag
            
    Returns:
        Dictionary with created tag details
    """
    account_name = params.pop("accountName", None)
    _, api_key, base_url = get_account_config(account_name)

    # Ensure name is provided
    if "name" not in params:
        raise ValueError("'name' field is required to create a tag")

    # Debug output to help troubleshoot
    sys.stderr.write(f"[callhub] Creating tag with params: {params}\n")

    # Format for CallHub API expects "tag" field
    request_data = {"tag": params["name"]}

    headers = get_auth_headers(api_key)
    url = build_url(base_url, "v2/tags/")
    
    return api_call("POST", url, headers, json_data=request_data)

def update_tag(params: dict) -> dict:
    """
    Update an existing tag by ID.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - tagId: ID of the tag to update
            - name (optional): New name for the tag
            - description (optional): New description for the tag
            
    Returns:
        Dictionary with updated tag details
    """
    account_name = params.pop("accountName", None)
    _, api_key, base_url = get_account_config(account_name)

    tag_id = params.pop("tagId", None)
    if not tag_id:
        raise ValueError("'tagId' is required.")

    update_data = {}
    if "name" in params:
        update_data["name"] = params["name"]
    if "description" in params:
        update_data["description"] = params["description"]

    # Debug output to help troubleshoot
    sys.stderr.write(f"[callhub] Updating tag {tag_id} with params: {update_data}\n")

    headers = get_auth_headers(api_key)
    url = build_url(base_url, "v1/tags/{}/", tag_id)
    
    return api_call("PATCH", url, headers, json_data=update_data)

def delete_tag(params: dict) -> dict:
    """
    Delete a tag by ID.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - tagId: ID of the tag to delete
            
    Returns:
        Dictionary with deletion status
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)

    tag_id = params.get("tagId")
    if not tag_id:
        raise ValueError("'tagId' is required.")

    headers = get_auth_headers(api_key)
    url = build_url(base_url, "v1/tags/{}/", tag_id)
    
    result = api_call("DELETE", url, headers)
    
    # If successful, return a standardized response
    if "isError" not in result:
        return {"deleted": True, "tagId": tag_id}
    return result

def add_tag_to_contact(params: dict) -> dict:
    """
    Add tag(s) to a contact.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - contactId: ID of the contact
            - tagNames: List of tag names to add
            
    Returns:
        Dictionary with operation status
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)

    contact_id = params.get("contactId")
    tag_names = params.get("tagNames")
    
    if not contact_id:
        raise ValueError("'contactId' is required.")
        
    if not tag_names or not isinstance(tag_names, list):
        raise ValueError("'tagNames' must be a non-empty list of tag names.")

    # First, get the contact details and its existing tags
    headers = get_auth_headers(api_key)
    contact_url = build_url(base_url, "v1/contacts/{}/", contact_id)
    contact_result = api_call("GET", contact_url, headers)
    
    if "isError" in contact_result:
        return contact_result
    
    # Extract the phone number and existing tags
    if "contact" not in contact_result:
        return {
            "isError": True,
            "content": [{"type": "text", "text": "The contact doesn't have a phone number"}]
        }
    
    phone_number = contact_result["contact"]
    existing_tags = contact_result.get("tags", [])
    
    # Build a list of existing tag IDs and names
    existing_tag_ids = [tag["id"] for tag in existing_tags]
    existing_tag_names = [tag["name"] for tag in existing_tags]
    
    # Check if all the requested tags already exist on the contact
    all_exist = True
    for tag_name in tag_names:
        if tag_name not in existing_tag_names:
            all_exist = False
            break
    
    # If all tags already exist, return success
    if all_exist:
        return {
            "success": True,
            "message": f"All tags already exist on contact {contact_id}",
            "contactId": contact_id,
            "phone": phone_number,
            "tagNames": tag_names
        }
    
    # Add the existing tag names to maintain them (since API replaces rather than adds)
    # Create a set of all the tag names (existing + new)
    all_tag_names = set(existing_tag_names + tag_names)
    
    # Let's try the direct approach of updating the contact with the PATCH api
    taggings_url = build_url(base_url, "v2/contacts/{}/taggings/", contact_id)
    
    # For this simplified approach, we'll use the existing tag IDs and create any missing ones
    # First, get the tag IDs for the tags we want to add
    tag_id_map = {}
    for tag_name in tag_names:
        if tag_name in existing_tag_names:
            # If it already exists on the contact, find its ID
            for tag in existing_tags:
                if tag["name"] == tag_name:
                    tag_id_map[tag_name] = str(tag["id"])
                    break
        else:
            # If it doesn't exist, search for it or create it
            # First try to get the tag directly
            tags_url = build_url(base_url, "v1/tags/")
            tags_result = api_call("GET", tags_url, headers, params={"page_size": 100})
            
            if "isError" in tags_result:
                return tags_result
            
            # Look for the tag in the results
            found = False
            if "results" in tags_result:
                for tag in tags_result["results"]:
                    if tag["name"] == tag_name:
                        tag_id_map[tag_name] = str(tag["id"])
                        found = True
                        break
            
            # If not found, create it
            if not found:
                sys.stderr.write(f"[callhub] Tag '{tag_name}' not found, attempting to create it\n")
                create_result = create_tag({"accountName": account_name, "name": tag_name})
                
                if "isError" in create_result:
                    return {
                        "isError": True,
                        "content": [{"type": "text", "text": f"Failed to create tag '{tag_name}': {create_result}"}]
                    }
                
                # If creation was successful, get the ID
                if "id" in create_result:
                    tag_id_map[tag_name] = str(create_result["id"])
                else:
                    return {
                        "isError": True,
                        "content": [{"type": "text", "text": f"Created tag '{tag_name}' but couldn't retrieve its ID: {create_result}"}]
                    }
    
    # Now build the final list of all tag IDs (existing + new)
    all_tag_ids = existing_tag_ids.copy()
    
    # Add any new tag IDs not already in the list
    for tag_name, tag_id in tag_id_map.items():
        if tag_id not in all_tag_ids:
            all_tag_ids.append(tag_id)
    
    # Make the API call to set all tags
    headers["Content-Type"] = "application/json"  # Ensure proper content type
    payload = {"tags": [str(tag_id) for tag_id in all_tag_ids]}
    
    # Debug output
    sys.stderr.write(f"[callhub] Setting tags for contact {contact_id}\n")
    sys.stderr.write(f"[callhub] Request URL: {taggings_url}\n")
    sys.stderr.write(f"[callhub] Request payload: {json.dumps(payload)}\n")
    
    result = api_call("PATCH", taggings_url, headers, json_data=payload)
    
    if "isError" not in result:
        return {
            "success": True,
            "message": f"Tags successfully set for contact {contact_id}",
            "contactId": contact_id,
            "phone": phone_number,
            "addedTags": tag_names,
            "allTagIds": all_tag_ids,
            "taggingsResult": result
        }
    
    # If PATCH failed, try a direct PUT to update the contact
    sys.stderr.write(f"[callhub] PATCH attempt failed, trying PUT to the contact endpoint\n")
    
    # Try updating the contact directly
    contact_update_url = build_url(base_url, "v1/contacts/{}/", contact_id)
    
    # The PUT request needs the full tag objects, not just IDs
    tag_objects = []
    for tag_id in all_tag_ids:
        # Find the name for existing tags
        tag_name = None
        for tag in existing_tags:
            if str(tag["id"]) == str(tag_id):
                tag_name = tag["name"]
                break
        
        # If not found, check our newly created/found tags
        if not tag_name:
            for name, id_val in tag_id_map.items():
                if str(id_val) == str(tag_id):
                    tag_name = name
                    break
        
        # Add the tag object
        if tag_name:
            tag_objects.append({
                "id": tag_id,
                "name": tag_name
            })
    
    update_payload = {
        "tags": tag_objects
    }
    
    sys.stderr.write(f"[callhub] Request URL: {contact_update_url}\n")
    sys.stderr.write(f"[callhub] Request payload: {json.dumps(update_payload)}\n")
    
    result2 = api_call("PUT", contact_update_url, headers, json_data=update_payload)
    
    if "isError" not in result2:
        return {
            "success": True,
            "message": f"Tags successfully set for contact {contact_id} via PUT",
            "contactId": contact_id,
            "phone": phone_number,
            "addedTags": tag_names,
            "tagsSet": [obj["name"] for obj in tag_objects],
            "updateResult": result2
        }
    
    # If all attempts failed, return details of all failures
    return {
        "isError": True,
        "content": [
            {"type": "text", "text": "All attempts to add tags failed. Errors:"}, 
            {"type": "text", "text": f"PATCH to taggings: {result}"},
            {"type": "text", "text": f"PUT to contact: {result2}"}
        ]
    }

def remove_tag_from_contact(params: dict) -> dict:
    """
    Remove a tag from a contact.
    
    Args:
        params: Dictionary with:
            - accountName (optional): The account to use
            - contactId: ID of the contact
            - tagId: ID of the tag to remove
            
    Returns:
        Dictionary with operation status
    """
    account_name = params.get("accountName")
    _, api_key, base_url = get_account_config(account_name)

    contact_id = params.get("contactId")
    tag_id = params.get("tagId")
    
    if not contact_id or not tag_id:
        raise ValueError("Both 'contactId' and 'tagId' are required.")

    headers = get_auth_headers(api_key)
    url = build_url(base_url, "v1/contacts/{}/tags/{}/", contact_id, tag_id)
    
    # Debug output
    sys.stderr.write(f"[callhub] Removing tag {tag_id} from contact {contact_id}\n")
    
    result = api_call("DELETE", url, headers)
    
    # If successful, standardize the response
    if "isError" not in result:
        return {
            "success": True,
            "message": f"Tag {tag_id} removed from contact {contact_id}",
            "contactId": contact_id,
            "tagId": tag_id
        }
    
    return result
