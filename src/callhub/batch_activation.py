"""
Batch activation handler for CallHub.

This module provides functions for activating large numbers of agents in batches
with progress tracking and resumability when context window limits are reached.
"""

import os
import time
import json
import sys
import csv
import tempfile
from io import StringIO
from datetime import datetime
from typing import Dict, List, Union, Optional, Any, Tuple

from .browser_automation import activate_agents_with_password
from .auth import get_account_config

# Batch size - adjust based on CallHub API responsiveness
DEFAULT_BATCH_SIZE = 10

# State file path for tracking progress
def get_state_file_path(account_name: str):
    """Get the path to the state file for a specific account."""
    temp_dir = tempfile.gettempdir()
    safe_account = account_name.replace("/", "_").replace("\\", "_")
    return os.path.join(temp_dir, f"callhub_activation_state_{safe_account}.json")

def activate_agents_in_batches(
    activation_data: List[Dict], 
    password: str, 
    account_name: str, 
    batch_size: int = DEFAULT_BATCH_SIZE,
    resume_from_state: bool = True,
    update_callback: callable = None
) -> Dict:
    """
    Activate agents in batches with progress tracking and resumability.
    
    Args:
        activation_data: List of activation data entries (with url, username, email)
        password: Password to set for all activating agents
        account_name: CallHub account name
        batch_size: Number of agents to process in each batch
        resume_from_state: Whether to resume from saved state file
        update_callback: Optional callback function for real-time updates
        
    Returns:
        Dict with results of the activation process
    """
    if not activation_data:
        return {
            "isError": True,
            "content": [{"type": "text", "text": "No activation data provided. Please first upload a CSV with activation URLs."}]
        }
    
    # CallHub requires passwords of at least 8 characters
    if not password or len(password) < 8:
        return {
            "isError": True,
            "content": [{
                "type": "text", 
                "text": "Password must be at least 8 characters long. CallHub requires passwords of at least 8 characters."
            }]
        }
    
    # Load previous state if requested and available
    state_file = get_state_file_path(account_name)
    completed_urls = set()
    
    if resume_from_state and os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
                completed_urls = set(state.get('completed_urls', []))
                
            # Send initial update with loaded state
            total_count = len(activation_data)
            completed_count = len(completed_urls)
            
            progress_msg = f"Resuming activation: {completed_count}/{total_count} agents already activated."
            sys.stderr.write(f"[callhub] {progress_msg}\n")
            
            if update_callback:
                update_callback({
                    "type": "resume",
                    "message": progress_msg,
                    "total": total_count,
                    "completed": completed_count,
                    "percent": (completed_count / total_count * 100) if total_count > 0 else 0
                })
                
        except Exception as e:
            # If there's an error loading state, log it but continue without resuming
            error_msg = f"Error loading previous state: {str(e)}. Starting from beginning."
            sys.stderr.write(f"[callhub] {error_msg}\n")
            
            if update_callback:
                update_callback({
                    "type": "error",
                    "message": error_msg
                })
    
    # Filter out already completed activations
    pending_activations = [
        activation for activation in activation_data 
        if activation.get('url') not in completed_urls
    ]
    
    # Prepare result structure
    results = {
        "total_agents": len(activation_data),
        "successful_activations": len(completed_urls),  # Start with previously completed
        "failed_activations": 0,
        "details": []
    }
    
    # Calculate total batches
    total_batches = (len(pending_activations) + batch_size - 1) // batch_size
    
    # Send initial progress update
    if update_callback:
        start_message = f"Starting activation of {len(pending_activations)} agents in {total_batches} batches"
        sys.stderr.write(f"[callhub] {start_message}\n")
        
        update_callback({
            "type": "start",
            "message": start_message,
            "total": len(activation_data),
            "pending": len(pending_activations),
            "completed": len(completed_urls),
            "total_batches": total_batches
        })
    
    # Process in batches
    for batch_num, batch_start in enumerate(range(0, len(pending_activations), batch_size)):
        # Get the current batch
        batch = pending_activations[batch_start:batch_start + batch_size]
        
        # Send batch start update
        batch_msg = f"Processing batch {batch_num + 1}/{total_batches} ({len(batch)} agents)"
        sys.stderr.write(f"[callhub] {batch_msg}\n")
        
        # Ensure this update is properly logged and visible
        print(f"[CALLHUB-BATCH-START] {batch_msg}")
        sys.stderr.write(f"[callhub] *** BATCH {batch_num + 1}/{total_batches} STARTED - Processing {len(batch)} agents ***\n")
        
        if update_callback:
            update_callback({
                "type": "batch_start",
                "message": batch_msg,
                "batch_number": batch_num + 1,
                "total_batches": total_batches,
                "batch_size": len(batch)
            })
        
        # Process this batch
        start_time = time.time()
        batch_result = activate_agents_with_password(batch, password, account_name)
        
        # Handle errors at the batch level
        if batch_result.get("isError"):
            error_msg = batch_result.get("content", [{}])[0].get("text", "Unknown error")
            sys.stderr.write(f"[callhub] Batch error: {error_msg}\n")
            
            if update_callback:
                update_callback({
                    "type": "batch_error",
                    "message": f"Error processing batch {batch_num + 1}: {error_msg}"
                })
                
            # Continue with the next batch instead of failing completely
            continue
        
        # Update results with this batch
        batch_successful = batch_result.get("successful_activations", 0)
        batch_failed = batch_result.get("failed_activations", 0)
        batch_details = batch_result.get("details", [])
        
        results["successful_activations"] += batch_successful
        results["failed_activations"] += batch_failed
        results["details"].extend(batch_details)
        
        # Track successful activations for resume capability
        for detail in batch_details:
            if detail.get("success", False):
                # Find and add the URL to completed set
                for activation in batch:
                    if (activation.get("username") == detail.get("username") and 
                        activation.get("email") == detail.get("email")):
                        completed_urls.add(activation.get("url"))
                        break
        
        # Save state after each batch
        try:
            with open(state_file, 'w') as f:
                json.dump({
                    "completed_urls": list(completed_urls),
                    "last_updated": datetime.now().isoformat(),
                    "account": account_name
                }, f)
        except Exception as e:
            sys.stderr.write(f"[callhub] Error saving state: {str(e)}\n")
        
        # Calculate batch statistics
        batch_duration = time.time() - start_time
        per_agent_time = batch_duration / len(batch) if batch else 0
        success_rate = (batch_successful / len(batch) * 100) if batch else 0
        
        # Estimate remaining time
        remaining_agents = len(pending_activations) - (batch_num + 1) * batch_size
        estimated_time = remaining_agents * per_agent_time if per_agent_time > 0 else 0
        
        # Format estimated time as minutes and seconds
        if estimated_time > 0:
            est_minutes = int(estimated_time // 60)
            est_seconds = int(estimated_time % 60)
            time_estimate = f"{est_minutes}m {est_seconds}s"
        else:
            time_estimate = "less than 1 minute"
        
        # Send batch completion update
        completed_total = len(completed_urls)
        progress_percent = (completed_total / len(activation_data) * 100) if activation_data else 0
        
        batch_complete_msg = (
            f"Completed batch {batch_num + 1}/{total_batches}: "
            f"{batch_successful} successful, {batch_failed} failed. "
            f"Total progress: {completed_total}/{len(activation_data)} "
            f"({progress_percent:.1f}%). Estimated time remaining: {time_estimate}"
        )
        sys.stderr.write(f"[callhub] {batch_complete_msg}\n")
        
        # Ensure this update is properly logged and visible
        print(f"[CALLHUB-BATCH-COMPLETE] Batch {batch_num + 1}/{total_batches} complete: {batch_successful} successful, {batch_failed} failed. Progress: {progress_percent:.1f}%")
        sys.stderr.write(f"[callhub] *** BATCH {batch_num + 1}/{total_batches} COMPLETE - {batch_successful} successful, {batch_failed} failed. Total progress: {progress_percent:.1f}% ***\n")
        
        if update_callback:
            update_data = {
                "type": "batch_complete",
                "message": batch_complete_msg,
                "batch_number": batch_num + 1,
                "total_batches": total_batches,
                "batch_successful": batch_successful,
                "batch_failed": batch_failed,
                "total_successful": results["successful_activations"],
                "total_failed": results["failed_activations"],
                "total_completed": completed_total,
                "total_agents": len(activation_data),
                "progress_percent": progress_percent,
                "estimated_time_remaining": estimated_time,
                "time_estimate_formatted": time_estimate
            }
            update_callback(update_data)
            
            # Also print the update data for debugging
            print(f"[CALLHUB-UPDATE-CALLBACK] {json.dumps(update_data)}")
        
        # Reduced delay between batches to speed up the process (was 1 second)
        time.sleep(0.5)  # Reduced to 0.5 second
    
    # Process complete - calculate final success rate
    total = results["total_agents"]
    successful = results["successful_activations"]
    failed = results["failed_activations"]
    success_rate = (successful / total * 100) if total > 0 else 0
    
    # Add success rate and message to results
    results["success"] = True
    results["success_rate"] = f"{success_rate:.1f}%"
    results["message"] = f"Processed {total} agent activations with {successful} successful and {failed} failed"
    
    # Send completion update
    complete_msg = f"Activation complete! {successful}/{total} agents activated successfully ({results['success_rate']})"
    sys.stderr.write(f"[callhub] {complete_msg}\n")
    
    # Ensure the completion message is visible
    print(f"[CALLHUB-ACTIVATION-COMPLETE] {complete_msg}")
    sys.stderr.write(f"[callhub] **************************************\n")
    sys.stderr.write(f"[callhub] *** ACTIVATION COMPLETE! {successful}/{total} agents activated ({success_rate:.1f}%) ***\n")
    sys.stderr.write(f"[callhub] *** LOG MONITORING COMPLETE - CLOSE WINDOW ***\n")
    sys.stderr.write(f"[callhub] **************************************\n")
    
    if update_callback:
        final_update = {
            "type": "complete",
            "message": complete_msg,
            "results": results
        }
        update_callback(final_update)
        
        # Also print the final update for debugging
        print(f"[CALLHUB-FINAL-UPDATE] {json.dumps(final_update)}")
    
    # Clean up state file if all agents were processed
    if results["successful_activations"] + results["failed_activations"] >= results["total_agents"]:
        try:
            if os.path.exists(state_file):
                os.remove(state_file)
                sys.stderr.write(f"[callhub] Removed state file after successful completion\n")
        except Exception as e:
            sys.stderr.write(f"[callhub] Error removing state file: {str(e)}\n")
    
    return results

def get_activation_progress(account_name: str) -> Dict:
    """
    Get the current progress of an activation job.
    
    Args:
        account_name: CallHub account name
        
    Returns:
        Dict with progress information
    """
    state_file = get_state_file_path(account_name)
    
    if not os.path.exists(state_file):
        return {
            "exists": False,
            "message": "No activation job in progress for this account",
            "recent_updates": []
        }
    
    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
            
        completed_urls = state.get('completed_urls', [])
        last_updated = state.get('last_updated', 'Unknown')
        
        # Try to convert ISO format date to more readable format
        try:
            dt = datetime.fromisoformat(last_updated)
            last_updated = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass
            
        return {
            "exists": True,
            "completed_count": len(completed_urls),
            "last_updated": last_updated,
            "state": state,
            "recent_updates": []
        }
    except Exception as e:
        return {
            "exists": True,
            "error": str(e),
            "message": "Error reading activation progress state",
            "recent_updates": []
        }

def reset_activation_progress(account_name: str) -> Dict:
    """
    Reset the progress of an activation job by deleting the state file.
    
    Args:
        account_name: CallHub account name
        
    Returns:
        Dict with result information
    """
    state_file = get_state_file_path(account_name)
    
    if not os.path.exists(state_file):
        return {
            "success": True,
            "message": "No activation job in progress for this account"
        }
    
    try:
        os.remove(state_file)
        return {
            "success": True,
            "message": "Activation progress has been reset"
        }
    except Exception as e:
        return {
            "isError": True,
            "content": [{"type": "text", "text": f"Error resetting activation progress: {str(e)}"}]
        }

def parse_activation_csv_with_batch_support(csv_content: str) -> Dict:
    """
    Parse the CSV content with support for batch processing.
    This adds a unique identifier to each activation entry for tracking.
    
    Args:
        csv_content: CSV content as a string
        
    Returns:
        Dict with parsed activation data
    """
    if not csv_content:
        return {
            "isError": True, 
            "content": [{"type": "text", "text": "No CSV content to parse"}]
        }
    
    try:
        reader = csv.reader(StringIO(csv_content))
        
        # Extract the header row
        try:
            headers = next(reader)
        except StopIteration:
            return {
                "isError": True, 
                "content": [{"type": "text", "text": "CSV file is empty"}]
            }
        
        # Find the URL column index
        url_col = -1
        username_col = -1
        email_col = -1
        
        for i, header in enumerate(headers):
            h = header.lower()
            if "url" in h or "link" in h or "activation" in h:
                url_col = i
            elif "username" in h:
                username_col = i
            elif "email" in h:
                email_col = i
        
        if url_col == -1:
            return {
                "isError": True, 
                "content": [{"type": "text", "text": "Could not find URL column in CSV file"}]
            }
        
        # Extract activation data from each row
        activations = []
        
        for row in reader:
            if len(row) <= url_col:
                continue  # Skip incomplete rows
                
            activation = {
                "url": row[url_col].strip(),
                # Add a unique ID for tracking
                "id": f"act_{len(activations)}"
            }
            
            # Add username if available
            if username_col != -1 and len(row) > username_col:
                activation["username"] = row[username_col].strip()
                
            # Add email if available
            if email_col != -1 and len(row) > email_col:
                activation["email"] = row[email_col].strip()
                
            activations.append(activation)
        
        # Return the parsed activation data
        return {
            "success": True,
            "message": f"Successfully extracted {len(activations)} activation URLs",
            "activations": activations,
            "headers": headers,
            "raw_csv": csv_content  # Include the raw CSV in case direct parsing is needed
        }
        
    except Exception as e:
        sys.stderr.write(f"[callhub] Exception in parse_activation_csv: {str(e)}\n")
        return {"isError": True, "content": [{"type": "text", "text": str(e)}]}
