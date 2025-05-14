"""
MCP tools for batch activation of CallHub agents.

These tools provide a way to activate agents in batches with progress updates
and resumability when context window limits are reached.
"""

import sys
import time
import json
import os
import datetime
import pickle
import tempfile
from typing import Dict, List, Optional, Any

# Global dictionary to store activation data temporarily
_activation_data_cache = {}

def _get_cache_file_path(account: str) -> str:
    """Get the path to the temporary activation data cache file"""
    temp_dir = tempfile.gettempdir()
    return os.path.join(temp_dir, f"callhub_activation_cache_{account}.pkl")

from ..batch_activation import (
    activate_agents_in_batches, 
    get_activation_progress, 
    reset_activation_progress,
    parse_activation_csv_with_batch_support
)
from ..csv_processor import process_uploaded_csv
from ..browser_automation import activate_agents_with_password

# Global state to track progress updates across calls
activation_progress = {
    "last_update": None,
    "updates": []
}

# Define log file path based on account name
def get_log_file_path(account: str) -> str:
    """Get the path to the log file for a specific account"""
    # Use home directory for logs
    home_dir = os.path.expanduser("~")
    log_dir = os.path.join(home_dir, "callhub_logs")
    
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Create a timestamped log file name
    timestamp = datetime.datetime.now().strftime("%Y%m%d")
    return os.path.join(log_dir, f"callhub_activation_{account}_{timestamp}.log")

def log_to_file(log_file: str, message: str):
    """Write a message to the log file with timestamp"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(log_file, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        sys.stderr.write(f"[callhub] Error writing to log file: {str(e)}\n")

def stream_updates_callback(update_data: Dict, log_file: str = None):
    """Callback function that stores updates and logs them to file"""
    global activation_progress
    
    timestamp = time.time()
    update = {
        "timestamp": timestamp,
        "data": update_data
    }
    
    # Keep only the last 20 updates to avoid excessive memory usage
    activation_progress["updates"].append(update)
    if len(activation_progress["updates"]) > 20:
        activation_progress["updates"] = activation_progress["updates"][-20:]
    
    activation_progress["last_update"] = timestamp
    
    # Handle special agent activation update from the browser automation
    if update_data.get('type') == 'agent_activated' and log_file:
        username = update_data.get('username', 'Unknown')
        email = update_data.get('email', 'Unknown')
        success = update_data.get('success', False)
        agent_num = update_data.get('agent_number', 0)
        total_agents = update_data.get('total_agents', 0)
        error = update_data.get('error', '')
        
        status = "SUCCESS" if success else "FAILED"
        log_message = f"Agent {agent_num}/{total_agents} '{username}' ({email}): {status}"
        if not success and error:
            log_message += f" - Error: {error}"
            
        log_to_file(log_file, log_message)
    
    # Log update to stderr for server logs
    message = f"{update_data.get('type')} - {update_data.get('message')}"
    sys.stderr.write(f"[callhub] Progress update: {message}\n")
    
    # Write to log file if provided
    if log_file:
        log_message = ""
        
        # Format message based on update type
        update_type = update_data.get('type')
        
        if update_type == "batch_start":
            batch_num = update_data.get('batch_number', 0)
            total_batches = update_data.get('total_batches', 0)
            batch_size = update_data.get('batch_size', 0)
            total_agents = update_data.get('total_agents', 0)
            log_message = f"*** BATCH {batch_num}/{total_batches} STARTED *** Processing {batch_size} agents ({total_agents} total)"
        
        elif update_type == "batch_complete":
            batch_num = update_data.get('batch_number', 0)
            total_batches = update_data.get('total_batches', 0)
            successful = update_data.get('batch_successful', 0)
            failed = update_data.get('batch_failed', 0)
            total_success = update_data.get('total_successful', 0)
            total_failed = update_data.get('total_failed', 0)
            progress = update_data.get('progress_percent', 0)
            
            log_message = (
                f"*** BATCH {batch_num}/{total_batches} COMPLETE *** "
                f"Results: {successful} successful, {failed} failed | "
                f"Overall progress: {total_success} successful, {total_failed} failed ({progress:.1f}%)"
            )
            
        elif update_type == "agent_complete":
            agent_num = update_data.get('agent_number', 0)
            total_agents = update_data.get('total_agents', 0)
            username = update_data.get('username', 'Unknown')
            email = update_data.get('email', 'Unknown')
            status = "SUCCESS" if update_data.get('success', False) else "FAILED"
            
            log_message = f"Agent {agent_num}/{total_agents} '{username}' ({email}): {status}"
            
            # Include error message if failed
            if not update_data.get('success', False) and update_data.get('error'):
                log_message += f" - Error: {update_data.get('error')}"
        
        else:
            # For other update types, just use the message
            log_message = message
        
        # Write to log file
        log_to_file(log_file, log_message)

# Process agent activation events from stdout events, mainly the CALLHUB-AGENT-ACTIVATED events
def process_agent_event(line: str, log_file: str = None):
    """Process an agent activation event line from stdout"""
    if line.startswith('[CALLHUB-AGENT-ACTIVATED]'):
        try:
            # Parse the event line, format: "[CALLHUB-AGENT-ACTIVATED] username (email): SUCCESS|FAILED - [error]"
            parts = line[len('[CALLHUB-AGENT-ACTIVATED]'):].strip().split(':')
            user_email_part = parts[0].strip()
            status_part = ':'.join(parts[1:]).strip()
            
            # Extract username and email
            username_email = user_email_part.split('(')
            username = username_email[0].strip()
            email = username_email[1].strip(')')
            
            # Extract status and error
            is_success = 'SUCCESS' in status_part
            error = status_part.split('-')[1].strip() if '-' in status_part and not is_success else ''
            
            # If we have a log file, log the agent activation
            if log_file:
                status = "SUCCESS" if is_success else "FAILED"
                log_message = f"Agent '{username}' ({email}): {status}"
                if not is_success and error:
                    log_message += f" - Error: {error}"
                    
                log_to_file(log_file, log_message)
            
            return {
                'type': 'agent_activated',
                'username': username,
                'email': email,
                'success': is_success,
                'error': error,
                'message': f"Agent {username} activation {'successful' if is_success else 'failed'}"
            }
            
        except Exception as e:
            sys.stderr.write(f"[callhub] Error parsing agent activation event: {str(e)}\n")
    
    return None

def activate_agents_with_progress(account: str, activation_data: List[Dict], password: str, batch_size: int = 10) -> Dict:
    """
    Activate a list of agents with real-time progress updates.
    
    Args:
        account: CallHub account name
        activation_data: List of activation data entries
        password: Password to set for all agents
        batch_size: Number of agents to process in each batch
    
    Returns:
        Dict with activation results and progress information
    """
    global activation_progress
    
    # Reset progress tracking
    activation_progress = {
        "last_update": time.time(),
        "updates": []
    }
    
    # Set up log file
    log_file = get_log_file_path(account)
    
    # Log the start of the activation process
    log_to_file(log_file, f"========================================")
    log_to_file(log_file, f"STARTING AGENT ACTIVATION PROCESS")
    log_to_file(log_file, f"Account: {account}")
    log_to_file(log_file, f"Agents to process: {len(activation_data)}")
    log_to_file(log_file, f"Batch size: {batch_size}")
    log_to_file(log_file, f"Log file: {log_file}")
    log_to_file(log_file, f"========================================")
    
    # Create a custom callback that includes the log file
    def custom_callback(update_data):
        return stream_updates_callback(update_data, log_file)
    
    # Start the activation process
    try:
        result = activate_agents_in_batches(
            activation_data=activation_data,
            password=password,
            account_name=account,
            batch_size=batch_size,
            resume_from_state=True,
            update_callback=custom_callback
        )
        
        # Add log file path to the result
        result["log_file"] = log_file
        
        # Log the completion of the activation process
        log_to_file(log_file, f"========================================")
        log_to_file(log_file, f"ACTIVATION PROCESS COMPLETE")
        log_to_file(log_file, f"Total successful: {result.get('successful_activations', 0)}")
        log_to_file(log_file, f"Total failed: {result.get('failed_activations', 0)}")
        log_to_file(log_file, f"Success rate: {result.get('success_rate', '0%')}")
        log_to_file(log_file, f"========================================")
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        sys.stderr.write(f"[callhub] Error in activate_agents_with_progress: {error_msg}\n")
        
        # Log the error
        log_to_file(log_file, f"ERROR: {error_msg}")
        log_to_file(log_file, f"ACTIVATION PROCESS FAILED")
        
        return {
            "isError": True,
            "content": [{"type": "text", "text": error_msg}],
            "log_file": log_file
        }

def process_uploaded_activation_csv(file_path: str) -> Dict:
    """
    Process an uploaded CSV file containing agent activation URLs.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        Dict with parsed activation data
    """
    try:
        # Process the uploaded CSV file
        csv_result = process_uploaded_csv(file_path)
        
        if csv_result.get("isError"):
            return csv_result
        
        # Parse the CSV data for activations
        raw_csv = csv_result.get("raw_csv", "")
        return parse_activation_csv_with_batch_support(raw_csv)
        
    except Exception as e:
        error_msg = str(e)
        sys.stderr.write(f"[callhub] Error in process_uploaded_activation_csv: {error_msg}\n")
        
        return {
            "isError": True,
            "content": [{"type": "text", "text": error_msg}]
        }

def prepare_agent_activation(account: str, password: str, activation_data: List[Dict], batch_size: int = 10) -> Dict:
    """
    Prepare for agent activation by setting up the log file and showing instructions.
    This must be called BEFORE actually activating agents to ensure the user knows
    where to look for progress updates.
    
    Args:
        account: CallHub account name
        password: Password to set for all agents
        activation_data: List of activation data entries
        batch_size: Number of agents to process in each batch
    
    Returns:
        Dict with log file path and instructions
    """
    if not account:
        return {
            "isError": True,
            "content": [{"type": "text", "text": "Account name is required"}]
        }
        
    if not password:
        return {
            "isError": True,
            "content": [{"type": "text", "text": "Password is required"}]
        }
        
    if not activation_data or not isinstance(activation_data, list):
        return {
            "isError": True,
            "content": [{"type": "text", "text": "Valid activation data is required"}]
        }
    
    # Validate password length
    if len(password) < 8:
        return {
            "isError": True,
            "content": [
                {"type": "text", "text": f"Password is too short. CallHub requires passwords to be at least 8 characters long."},
                {"type": "text", "text": "Please provide a longer password that meets the minimum requirements."}
            ]
        }
    
    # Validate batch size
    try:
        batch_size = int(batch_size)
        if batch_size < 1:
            batch_size = 10  # Default to 10 if invalid
    except:
        batch_size = 10  # Default to 10 if invalid
    
    # Store the activation data and password in a temporary file for later use
    cache_file = _get_cache_file_path(account)
    try:
        with open(cache_file, 'wb') as f:
            cache_data = {
                'activation_data': activation_data,
                'password': password,
                'batch_size': batch_size
            }
            pickle.dump(cache_data, f)
            sys.stderr.write(f"[callhub] Cached activation data for {len(activation_data)} agents\n")
    except Exception as e:
        sys.stderr.write(f"[callhub] Warning: Could not save activation data cache: {str(e)}\n")
    
    # Set up log file
    log_file = get_log_file_path(account)
    
    # Create an empty log file with initial header
    try:
        with open(log_file, "w") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] CallHub Agent Activation Log\n")
            f.write(f"[{timestamp}] Account: {account}\n")
            f.write(f"[{timestamp}] Agents to process: {len(activation_data)}\n")
            f.write(f"[{timestamp}] Batch size: {batch_size}\n")
            f.write(f"[{timestamp}] Log file created - Waiting for user confirmation to start\n")
    except Exception as e:
        sys.stderr.write(f"[callhub] Error creating log file: {str(e)}\n")
        
    # Create a clickable file URL
    file_url = f"file://{log_file}"
    
    # Prepare response with instructions
    return {
        "success": True,
        "message": f"Ready to activate {len(activation_data)} agents. Progress will be logged to file.",
        "total_agents": len(activation_data),
        "log_file": log_file,
        "log_file_url": file_url,  # Add clickable URL
        "instructions": [
            f"📊 Activation progress will be logged to: {log_file}",
            f"📝 You can open this file to monitor progress in real-time: <a href='{file_url}' target='_blank'>Open Log File</a>",
            f"⚠️ IMPORTANT: Please confirm you have access to this log file before proceeding.",
            f"🔄 Once activated, the process will continue in the background.",
            f"👍 Please respond with 'yes' to proceed with activation."
        ]
    }

def activate_agents_with_batch_password(account: str, password: str = None, activation_data: List[Dict] = None, batch_size: int = 10) -> Dict:
    """
    MCP tool for activating agents in batches with file-based logging.
    
    Args:
        account: CallHub account name
        password: Password to set for all agents (optional if cached)
        activation_data: List of activation data entries (optional if cached)
        batch_size: Number of agents to process in each batch
    
    Returns:
        Dict with activation results and log file path
    """
    if not account:
        return {
            "isError": True,
            "content": [{"type": "text", "text": "Account name is required"}]
        }
    
    # Try to load cached data if not provided
    cache_file = _get_cache_file_path(account)
    if (not password or not activation_data) and os.path.exists(cache_file):
        try:
            with open(cache_file, 'rb') as f:
                cached_data = pickle.load(f)
                if not password and 'password' in cached_data:
                    password = cached_data['password']
                    sys.stderr.write(f"[callhub] Using cached password\n")
                if not activation_data and 'activation_data' in cached_data:
                    activation_data = cached_data['activation_data']
                    sys.stderr.write(f"[callhub] Using cached activation data ({len(activation_data)} entries)\n")
                if not batch_size and 'batch_size' in cached_data:
                    batch_size = cached_data['batch_size']
                    sys.stderr.write(f"[callhub] Using cached batch size: {batch_size}\n")
        except Exception as e:
            sys.stderr.write(f"[callhub] Error loading cached activation data: {str(e)}\n")
    
    # Now check if we have the required data
    if not password:
        return {
            "isError": True,
            "content": [{"type": "text", "text": "Password is required"}]
        }
        
    if not activation_data or not isinstance(activation_data, list):
        return {
            "isError": True,
            "content": [{"type": "text", "text": "Valid activation data is required"}]
        }
    
    # Validate password length
    if len(password) < 8:
        return {
            "isError": True,
            "content": [
                {"type": "text", "text": f"Password is too short. CallHub requires passwords to be at least 8 characters long."},
                {"type": "text", "text": "Please provide a longer password that meets the minimum requirements."}
            ]
        }
    
    # Validate batch size
    try:
        batch_size = int(batch_size)
        if batch_size < 1:
            batch_size = 10  # Default to 10 if invalid
    except:
        batch_size = 10  # Default to 10 if invalid
    
    # Start the activation process
    result = activate_agents_with_progress(
        account=account,
        activation_data=activation_data,
        password=password,
        batch_size=batch_size
    )
    
    # Get the log file path
    log_file = result.get("log_file", get_log_file_path(account))
    
    # If there's an error, return it with the log file path
    if "isError" in result:
        result["log_file"] = log_file
        return result
    
    # Create a clickable file URL
    file_url = f"file://{log_file}"
    
    # Prepare a user-friendly response
    response = {
        "success": True,
        "message": f"Agent activation started. Real-time progress is being logged to a file.",
        "total_agents": len(activation_data),
        "log_file": log_file,
        "log_file_url": file_url,  # Add clickable URL
        "instructions": [
            f"📊 Activation progress is being logged to: {log_file}",
            f"📝 You can open this file to see real-time updates: <a href='{file_url}' target='_blank'>Open Log File</a>",
            f"🔄 The activation will continue in the background - no need to wait here!",
            f"📋 Check the log file periodically to monitor progress.",
            f"✅ When complete, the final results will be added to the log file."
        ]
    }
    
    # Add any initial results
    response.update({
        "initial_results": {
            "successful_activations": result.get("successful_activations", 0),
            "failed_activations": result.get("failed_activations", 0),
            "success_rate": result.get("success_rate", "0%")
        }
    })
    
    # Clean up the cache file if it exists
    cache_file = _get_cache_file_path(account)
    if os.path.exists(cache_file):
        try:
            os.remove(cache_file)
            sys.stderr.write(f"[callhub] Removed activation data cache file\n")
        except Exception as e:
            sys.stderr.write(f"[callhub] Error removing cache file: {str(e)}\n")
    
    return response

def get_activation_status(account: str = None) -> Dict:
    """
    MCP tool for retrieving current activation job status.
    
    Args:
        account: CallHub account name
        
    Returns:
        Dict with current activation status
    """
    if not account:
        return {
            "isError": True,
            "content": [{"type": "text", "text": "Account name is required"}]
        }
    
    # Get the current progress state
    progress = get_activation_progress(account)
    
    # Add log file path to the result
    log_file = get_log_file_path(account)
    progress["log_file"] = log_file
    
    # Create clickable file URL
    file_url = f"file://{log_file}"
    progress["log_file_url"] = file_url
    
    # Add a user-friendly summary
    if progress.get("exists", False):
        completed = progress.get("completed_count", 0)
        total = progress.get("total_count", 0)
        progress["status_message"] = f"Activation job in progress: {completed} of {total} agents processed."
        progress["instructions"] = [
            f"📊 Activation progress is being logged to: {log_file}",
            f"📝 You can open this file to see real-time updates: <a href='{file_url}' target='_blank'>Open Log File</a>",
            f"🔄 The activation is running in the background - no need to wait here!"
        ]
    else:
        progress["status_message"] = "No activation job in progress."
        # Check if log file exists
        if os.path.exists(log_file):
            progress["instructions"] = [
                f"📊 Previous activation log is available at: {log_file}",
                f"📝 You can open this file to see the results of the last activation: <a href='{file_url}' target='_blank'>Open Log File</a>"
            ]
    
    return progress

def reset_activation_state(account: str = None) -> Dict:
    """
    MCP tool for resetting the activation state (in case of errors or to restart).
    
    Args:
        account: CallHub account name
        
    Returns:
        Dict with reset result
    """
    if not account:
        return {
            "isError": True,
            "content": [{"type": "text", "text": "Account name is required"}]
        }
    
    # Reset the progress state
    result = reset_activation_progress(account)
    
    # Also reset the in-memory progress tracking
    global activation_progress
    activation_progress = {
        "last_update": time.time(),
        "updates": []
    }
    
    # Log the reset to the log file
    log_file = get_log_file_path(account)
    log_to_file(log_file, "Activation state reset. Starting fresh for next activation.")
    
    # Add log file path to the result
    result["log_file"] = log_file
    
    return result
