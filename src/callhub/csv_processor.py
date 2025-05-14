""" 
CSV processing helper functions for CallHub.

This module provides functions for handling and processing CSV files that are
uploaded to the conversation, particularly for agent activation URLs.
"""

import os
import glob
import csv
import sys
from io import StringIO
from typing import Dict, List, Union, Optional, Any, Tuple

def find_file(filename: str, search_paths: Optional[List[str]] = None) -> Optional[str]:
    """
    Find a file by searching in common locations and provided search paths.
    
    Args:
        filename: The name of the file to find
        search_paths: Optional list of paths to search in addition to default locations
        
    Returns:
        Full path to the file if found, None otherwise
    """
    # Set up default search paths
    default_paths = [
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~")
    ]
    
    # Add user-provided search paths
    if search_paths:
        all_paths = search_paths + default_paths
    else:
        all_paths = default_paths
    
    # Check for exact filename match in each location
    for path in all_paths:
        full_path = os.path.join(path, filename)
        if os.path.isfile(full_path):
            sys.stderr.write(f"[callhub] Found file at: {full_path}\n")
            return full_path
    
    # If not found, try partial matching in case the full filename isn't exact
    for path in all_paths:
        # Search with glob pattern
        pattern = os.path.join(path, f"*{filename}*")
        matches = glob.glob(pattern)
        # Filter for CSV files
        csv_matches = [m for m in matches if m.lower().endswith('.csv')]
        if csv_matches:
            # Sort by modification time (newest first)
            csv_matches.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            sys.stderr.write(f"[callhub] Found similar file at: {csv_matches[0]}\n")
            return csv_matches[0]
    
    # Not found
    return None

def smart_file_process(filename: str, processor_func: callable, search_paths: Optional[List[str]] = None) -> Dict:
    """
    Smart file processing with auto-location capabilities.
    
    This function will:
    1. Try to find the file in common locations
    2. If found, process it with the provided processor function
    3. If not found, return a user-friendly error with guidance
    
    Args:
        filename: Name of the file to process
        processor_func: Function to use for processing the file once found
        search_paths: Optional additional paths to search
        
    Returns:
        Result of the processor function or error information
    """
    # First try to handle the case where the input is already a full path
    if os.path.isfile(filename):
        return processor_func(filename)
    
    # Otherwise, try to find the file
    full_path = find_file(filename, search_paths)
    
    if full_path:
        return processor_func(full_path)
    else:
        # Prepare a helpful error message
        default_paths_str = "\n - ".join(["Downloads folder", "Desktop", "Documents folder", "Home directory"])
        return {
            "isError": True,
            "content": [
                {"type": "text", "text": f"Could not find file '{filename}'."},
                {"type": "text", "text": f"I looked in these locations:\n - {default_paths_str}"},
                {"type": "text", "text": "Please provide the full path to the file or move it to one of these locations."}
            ]
        }

def process_uploaded_csv(file_path: str) -> Dict:
    """
    Process a CSV file from a specific file path.
    
    Intended to be used with files that have been uploaded to the conversation.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        Dict with the parsed data or error message
    """
    return smart_file_process(file_path, _process_csv_file)

def _process_csv_file(file_path: str) -> Dict:
    """
    Internal function to process a CSV file given a valid path.
    
    Args:
        file_path: Path to an existing CSV file
        
    Returns:
        Dict with the parsed data or error message
    """
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as file:
            csv_content = file.read()
        
        # Parse the CSV content
        return process_csv_content(csv_content)
    
    except Exception as e:
        sys.stderr.write(f"[callhub] Error processing CSV file: {str(e)}\n")
        return {
            "isError": True,
            "content": [{"type": "text", "text": f"Error processing CSV file: {str(e)}"}]
        }

def process_csv_content(csv_content: str) -> Dict:
    """
    Process CSV content as a string.
    
    Args:
        csv_content: CSV content as a string
        
    Returns:
        Dict with the parsed data or error message
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
        
        # Process rows
        rows = list(reader)
        
        # Return the parsed data
        return {
            "success": True,
            "headers": headers,
            "rows": rows,
            "row_count": len(rows),
            "column_count": len(headers),
            "raw_csv": csv_content
        }
    
    except Exception as e:
        sys.stderr.write(f"[callhub] Error parsing CSV content: {str(e)}\n")
        return {
            "isError": True,
            "content": [{"type": "text", "text": f"Error parsing CSV content: {str(e)}"}]
        }

def process_agent_activation_csv_from_file(file_path: str) -> Dict:
    """
    Process an agent activation CSV file from a specific file path.
    
    Args:
        file_path: Path to the CSV file containing agent activation URLs
        
    Returns:
        Dict with the parsed activation data or error message
    """
    return smart_file_process(file_path, _process_agent_activation_file)

def _process_agent_activation_file(file_path: str) -> Dict:
    """
    Internal function to process an agent activation CSV file.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        Dict with the parsed activation data
    """
    try:
        # First read the file
        with open(file_path, 'r', encoding='utf-8') as file:
            csv_content = file.read()
        
        # Then process using the existing function
        from .agent_activation_manual import process_activation_csv
        return process_activation_csv(csv_content)
    
    except Exception as e:
        sys.stderr.write(f"[callhub] Error processing agent activation CSV file: {str(e)}\n")
        return {
            "isError": True,
            "content": [{"type": "text", "text": f"Error processing agent activation CSV file: {str(e)}"}]
        }
