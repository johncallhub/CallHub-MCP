#!/usr/bin/env python3
"""
Cleanup Script for CallHub MCP

This script removes credential files and other sensitive information
to prepare the repository for public distribution.
"""

import os
import sys
import shutil

def main():
    """Main cleanup function."""
    print("\nCallHub MCP Cleanup Script")
    print("==========================\n")
    print("This script will remove credential files and sensitive information.")
    print("Use this before pushing to GitHub or sharing the code.\n")
    
    # Ask for confirmation
    confirm = input("Do you want to proceed? (y/n): ")
    if confirm.lower() != 'y':
        print("Cleanup canceled.")
        return
    
    # Files to remove
    files_to_remove = [
        ".env",
        ".callhub_credentials.json",
        "credentials.json"
    ]
    
    # Directories to clean
    dirs_to_clean = [
        "logs"
    ]
    
    # Current directory (should be project root)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Remove credential files
    for file in files_to_remove:
        file_path = os.path.join(current_dir, file)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"✓ Removed: {file}")
            except Exception as e:
                print(f"✗ Error removing {file}: {str(e)}")
        else:
            print(f"ℹ Not found: {file}")
    
    # Clean directories
    for directory in dirs_to_clean:
        dir_path = os.path.join(current_dir, directory)
        if os.path.exists(dir_path):
            try:
                # Remove all files in the directory but keep the directory
                for item in os.listdir(dir_path):
                    item_path = os.path.join(dir_path, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                print(f"✓ Cleaned: {directory}/")
            except Exception as e:
                print(f"✗ Error cleaning {directory}: {str(e)}")
        else:
            print(f"ℹ Not found: {directory}/")
    
    # Make sure .env.example exists
    env_example = os.path.join(current_dir, ".env.example")
    if not os.path.exists(env_example):
        try:
            with open(env_example, 'w') as f:
                f.write("""# Environment file example for CallHub MCP
# Copy this file to .env and fill in your actual credentials

# Default account (used when no account is specified)
CALLHUB_DEFAULT_USERNAME=your_username
CALLHUB_DEFAULT_API_KEY=your_api_key
CALLHUB_DEFAULT_BASE_URL=https://api-na1.callhub.io

# MCP Configuration
# LOG_LEVEL=INFO           # DEBUG, INFO, WARNING, ERROR, CRITICAL
# MAX_RETRIES=3            # Maximum number of retry attempts for API calls
""")
            print(f"✓ Created: .env.example")
        except Exception as e:
            print(f"✗ Error creating .env.example: {str(e)}")
    
    print("\nCleanup complete! Your repository is now ready for public distribution.")
    print("Remember to run setup.py after installation to configure credentials.")

if __name__ == "__main__":
    main()
