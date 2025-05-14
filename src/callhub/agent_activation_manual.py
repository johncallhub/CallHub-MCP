"""
Agent activation helper functions using a hybrid approach with manual download.

These functions help generate direct URLs for exporting agent activation data
and then process the downloaded CSV once uploaded by the user.
"""

import csv
import sys
from io import StringIO
from typing import Dict, List, Union, Optional, Any, Tuple

from .auth import get_account_config

def generate_export_url(account_name: Optional[str] = None) -> Dict:
    """
    Generate a direct URL for exporting agent activation URLs.
    
    Args:
        account_name: The CallHub account name to use
        
    Returns:
        Dict with the direct export URL and instructions
    """
    # Get the account configuration
    account, api_key, base_url = get_account_config(account_name)
    
    if not base_url:
        return {
            "isError": True,
            "content": [{"type": "text", "text": f"Invalid account configuration for '{account}'"}]
        }
    
    # Extract the domain from the base_url
    if '://' in base_url:
        domain = base_url.split('://')[1].split('/')[0]  # Get the domain part
    else:
        domain = base_url.split('/')[0]
    
    # Remove 'api-' prefix if present
    if domain.startswith('api-'):
        domain = domain[4:]  # Remove 'api-'
    
    # Construct the direct export URL - always using HTTPS
    export_url = f"https://{domain}/agent/#export"
    
    # Return the URL with instructions
    return {
        "success": True,
        "export_url": export_url,
        "instructions": [
            "1. Click the link below to open the Agents page in your browser:",
            f"   {export_url}",
            "2. If prompted, log in with your CallHub credentials",
            "3. Look for the 'Export Pending Activations' button on the page",
            "4. Click this button to start the export process",
            "5. Once complete, download the CSV file",
            "6. Upload the downloaded CSV file back to this conversation",
            "7. We'll automatically process the file and show you the activation data"
        ]
    }

def process_activation_csv(csv_content: str) -> Dict:
    """
    Process the CSV file uploaded by the user to extract activation URLs.
    
    Args:
        csv_content: CSV content as a string
        
    Returns:
        Dict with the parsed activation data
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
                "url": row[url_col].strip()
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
            "raw_csv": csv_content  # Include the raw CSV in case further processing is needed
        }
        
    except Exception as e:
        sys.stderr.write(f"[callhub] Exception in parse_activation_csv: {str(e)}\n")
        return {"isError": True, "content": [{"type": "text", "text": str(e)}]}
