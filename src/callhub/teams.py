# teams.py
"""
Team management functions for CallHub API.
"""

import json
import sys
from typing import Dict, List, Union, Optional, Any

from .auth import get_account_config
from .utils import build_url, api_call, get_auth_headers, parse_input_fields

def list_teams(params: Dict) -> Dict:
    """
    List all teams in the CallHub account.
    
    Args:
        params (dict): Dictionary containing:
            - accountName (optional): The CallHub account name to use
    
    Returns:
        Dict: Response from the API with team list
    """
    account_name = params.get("accountName")
    account, api_key, base_url = get_account_config(account_name)
    
    url = build_url(base_url, "/v1/teams/")
    headers = get_auth_headers(api_key)
    
    return api_call("GET", url, headers)

def get_team(params: Dict) -> Dict:
    """
    Get details for a specific team by ID.
    
    Args:
        params (dict): Dictionary containing:
            - accountName (optional): The CallHub account name to use
            - teamId (required): The ID of the team to retrieve
    
    Returns:
        Dict: Response from the API with team details
    """
    account_name = params.get("accountName")
    team_id = params.get("teamId")
    
    if not team_id:
        return {"isError": True, "content": [{"type": "text", "text": "'teamId' is required"}]}
    
    account, api_key, base_url = get_account_config(account_name)
    
    url = build_url(base_url, "/v1/teams/{}/", team_id)
    headers = get_auth_headers(api_key)
    
    return api_call("GET", url, headers)

def create_team(params: Dict) -> Dict:
    """
    Create a new team.
    
    Args:
        params (dict): Dictionary containing:
            - accountName (optional): The CallHub account name to use
            - name (required): Name of the team to create
    
    Returns:
        Dict: Response from the API with the created team details
    """
    account_name = params.get("accountName")
    name = params.get("name")
    
    # Validate required fields
    if not name:
        return {
            "isError": True, 
            "content": [{"type": "text", "text": "Team 'name' is required"}]
        }
    
    account, api_key, base_url = get_account_config(account_name)
    
    url = build_url(base_url, "/v1/teams/")
    headers = get_auth_headers(api_key)
    
    # Use JSON payload as expected by the API
    payload = {"name": name}
    
    return api_call("POST", url, headers, json_data=payload)

def update_team(params: Dict) -> Dict:
    """
    Update a team's name by ID.
    
    Args:
        params (dict): Dictionary containing:
            - accountName (optional): The CallHub account name to use
            - teamId (required): The ID of the team to update
            - name (required): New name for the team
    
    Returns:
        Dict: Response from the API with the updated team details
    """
    account_name = params.get("accountName")
    team_id = params.get("teamId")
    name = params.get("name")
    
    # Validate required fields
    if not team_id:
        return {"isError": True, "content": [{"type": "text", "text": "'teamId' is required"}]}
    
    if not name:
        return {"isError": True, "content": [{"type": "text", "text": "Team 'name' is required"}]}
    
    account, api_key, base_url = get_account_config(account_name)
    
    url = build_url(base_url, "/v1/teams/{}/", team_id)
    headers = get_auth_headers(api_key)
    
    # Use JSON payload as expected by the API
    payload = {"name": name}
    
    return api_call("PUT", url, headers, json_data=payload)

def delete_team(params: Dict) -> Dict:
    """
    Delete a team by ID.
    
    Args:
        params (dict): Dictionary containing:
            - accountName (optional): The CallHub account name to use
            - teamId (required): The ID of the team to delete
    
    Returns:
        Dict: Response indicating success or failure
        
    Notes:
        This endpoint will unassign all agents associated with the team.
    """
    account_name = params.get("accountName")
    team_id = params.get("teamId")
    
    if not team_id:
        return {"isError": True, "content": [{"type": "text", "text": "'teamId' is required"}]}
    
    # First, let's check if the team has agents to provide a warning
    agents_response = get_team_agents({"accountName": account_name, "teamId": team_id})
    
    # If the team has agents, provide a warning but proceed with deletion
    if not agents_response.get("isError") and len(agents_response.get("results", [])) > 0:
        sys.stderr.write(f"[callhub] Warning: Team {team_id} has {len(agents_response.get('results', []))} agents that will be unassigned\n")
    
    account, api_key, base_url = get_account_config(account_name)
    
    url = build_url(base_url, "/v1/teams/{}/", team_id)
    headers = get_auth_headers(api_key)
    
    delete_response = api_call("DELETE", url, headers)
    
    # If deletion was successful and there were agents, add warning to response
    if not delete_response.get("isError") and not agents_response.get("isError") and len(agents_response.get("results", [])) > 0:
        agent_count = len(agents_response.get("results", []))
        if "content" not in delete_response:
            delete_response["content"] = []
        
        delete_response["content"].append({
            "type": "text", 
            "text": f"Warning: {agent_count} agents have been unassigned from this team"
        })
    
    return delete_response

def get_team_agents(params: Dict) -> Dict:
    """
    Get a list of all agents assigned to a specific team.
    
    Args:
        params (dict): Dictionary containing:
            - accountName (optional): The CallHub account name to use
            - teamId (required): The ID of the team
    
    Returns:
        Dict: Response from the API with the list of agents in the team
    """
    account_name = params.get("accountName")
    team_id = params.get("teamId")
    
    if not team_id:
        return {"isError": True, "content": [{"type": "text", "text": "'teamId' is required"}]}
    
    account, api_key, base_url = get_account_config(account_name)
    
    url = build_url(base_url, "/v1/teams/{}/agents/", team_id)
    headers = get_auth_headers(api_key)
    
    return api_call("GET", url, headers)

def get_team_agent_details(params: Dict) -> Dict:
    """
    Get details for a specific agent in a team.
    
    Args:
        params (dict): Dictionary containing:
            - accountName (optional): The CallHub account name to use
            - teamId (required): The ID of the team
            - agentId (required): The ID of the agent
    
    Returns:
        Dict: Response from the API with the agent details
    """
    account_name = params.get("accountName")
    team_id = params.get("teamId")
    agent_id = params.get("agentId")
    
    # Validate required fields
    if not team_id:
        return {"isError": True, "content": [{"type": "text", "text": "'teamId' is required"}]}
    
    if not agent_id:
        return {"isError": True, "content": [{"type": "text", "text": "'agentId' is required"}]}
    
    account, api_key, base_url = get_account_config(account_name)
    
    url = build_url(base_url, "/v1/teams/{}/agents/{}/", team_id, agent_id)
    headers = get_auth_headers(api_key)
    
    return api_call("GET", url, headers)

def add_agents_to_team(params: Dict) -> Dict:
    """
    Add one or more agents to a team.
    
    Args:
        params (dict): Dictionary containing:
            - accountName (optional): The CallHub account name to use
            - teamId (required): The ID of the team
            - agentIds (required): List of agent IDs to add to the team
    
    Returns:
        Dict: Response indicating success or failure
    """
    account_name = params.get("accountName")
    team_id = params.get("teamId")
    agent_ids = params.get("agentIds")
    
    # Validate required fields
    if not team_id:
        return {"isError": True, "content": [{"type": "text", "text": "'teamId' is required"}]}
    
    if not agent_ids or not isinstance(agent_ids, list) or len(agent_ids) == 0:
        return {"isError": True, "content": [{"type": "text", "text": "'agentIds' must be a non-empty list of agent IDs"}]}
    
    account, api_key, base_url = get_account_config(account_name)
    
    url = build_url(base_url, "/v1/teams/{}/agents/", team_id)
    headers = get_auth_headers(api_key)
    
    # Ensure all agent IDs are integers
    agent_ids = [int(agent_id) for agent_id in agent_ids]
    
    # Use JSON payload as expected by the API
    payload = {"agents": agent_ids}
    
    return api_call("POST", url, headers, json_data=payload)

def remove_agents_from_team(params: Dict) -> Dict:
    """
    Remove one or more agents from a team.
    
    Args:
        params (dict): Dictionary containing:
            - accountName (optional): The CallHub account name to use
            - teamId (required): The ID of the team
            - agentIds (required): List of agent IDs to remove from the team
    
    Returns:
        Dict: Response indicating success or failure
    """
    account_name = params.get("accountName")
    team_id = params.get("teamId")
    agent_ids = params.get("agentIds")
    
    # Validate required fields
    if not team_id:
        return {"isError": True, "content": [{"type": "text", "text": "'teamId' is required"}]}
    
    if not agent_ids or not isinstance(agent_ids, list) or len(agent_ids) == 0:
        return {"isError": True, "content": [{"type": "text", "text": "'agentIds' must be a non-empty list of agent IDs"}]}
    
    account, api_key, base_url = get_account_config(account_name)
    
    url = build_url(base_url, "/v1/teams/{}/agents/", team_id)
    headers = get_auth_headers(api_key)
    
    # Ensure all agent IDs are integers
    agent_ids = [int(agent_id) for agent_id in agent_ids]
    
    # Use JSON payload as expected by the API
    payload = {"agents": agent_ids}
    
    return api_call("DELETE", url, headers, json_data=payload)

# Team validation helper function (for agent creation validation)
def validate_team_exists(account_name: Optional[str], team_input: str) -> Dict:
    """
    Validate that a team exists by name or ID before creating an agent.
    
    Args:
        account_name: The CallHub account name to use
        team_input: Name or ID of the team to validate
        
    Returns:
        Dict: Response indicating whether the team exists
    """
    # First, get all teams
    teams_response = list_teams({"accountName": account_name})
    
    # Check if the API call failed
    if teams_response.get("isError"):
        return teams_response
    
    # Extract team objects from the response
    teams = teams_response.get("results", [])
    
    # Check if team_input is numeric (likely an ID)
    is_id_format = team_input.isdigit() or (team_input.startswith("2") or team_input.startswith("3"))
    
    # Look for a team with a matching name or ID
    for team in teams:
        # Check for team ID match
        if is_id_format and (str(team.get("id")) == team_input or team.get("pk_str") == team_input):
            return {
                "exists": True,
                "teamId": team.get("id"),
                "team": team
            }
        # Check for team name match
        elif not is_id_format and team.get("name") == team_input:
            return {
                "exists": True,
                "teamId": team.get("id"),
                "team": team
            }
    
    # If no team was found with that name or ID
    if is_id_format:
        return {
            "exists": False,
            "message": f"Team with ID '{team_input}' does not exist. Please create a team first or use an existing team ID."
        }
    else:
        return {
            "exists": False,
            "message": f"Team with name '{team_input}' does not exist. Please create it first or use an existing team."
        }
