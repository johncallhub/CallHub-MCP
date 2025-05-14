#!/usr/bin/env python3
"""
Migrate CallHub credentials from .callhub_credentials.json to .env

This script converts existing CallHub credentials from JSON format to the new .env format.
It preserves all existing accounts and credentials.
"""

import os
import json
import sys
from dotenv import load_dotenv, set_key

def main():
    # Find the credentials files
    home_dir = os.path.expanduser('~')
    project_dir = os.getcwd()
    
    # Check project directory first, then home directory
    json_paths = [
        os.path.join(project_dir, '.callhub_credentials.json'),
        os.path.join(home_dir, '.callhub_credentials.json')
    ]
    
    json_path = None
    for path in json_paths:
        if os.path.exists(path):
            json_path = path
            break
    
    if not json_path:
        print("No .callhub_credentials.json file found in project directory or home directory.")
        return 1
    
    # Find or create .env file
    env_paths = [
        os.path.join(project_dir, '.env'),
        os.path.join(home_dir, '.env')
    ]
    
    env_path = None
    for path in env_paths:
        if os.path.exists(path):
            env_path = path
            break
    
    if not env_path:
        # Create .env in project directory if it doesn't exist
        env_path = os.path.join(project_dir, '.env')
        with open(env_path, 'w') as f:
            f.write("# CallHub API Credentials\n\n")
        print(f"Created new .env file at {env_path}")
    
    # Load existing credentials
    with open(json_path, 'r') as f:
        try:
            credentials = json.load(f)
            print(f"Loaded credentials for {len(credentials)} accounts from {json_path}")
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON file: {e}")
            return 1
    
    # Load existing .env file
    load_dotenv(env_path)
    
    # Migrate credentials to .env
    migrated_count = 0
    for account, config in credentials.items():
        account_upper = account.upper()
        api_key = config.get('api_key')
        base_url = config.get('base_url')
        
        if not api_key:
            print(f"Warning: No API key found for account '{account}', skipping...")
            continue
        
        # Add or update API key
        set_key(env_path, f"CALLHUB_{account_upper}_API_KEY", api_key)
        
        # Add or update base URL if present
        if base_url:
            set_key(env_path, f"CALLHUB_{account_upper}_BASE_URL", base_url)
        
        migrated_count += 1
    
    print(f"Successfully migrated {migrated_count} accounts to {env_path}")
    print("\nMigration complete!")
    print(f"You can now add the .callhub_credentials.json file to .gitignore")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
