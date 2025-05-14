#!/usr/bin/env python3

"""
Agent Activation Flow Example

This script demonstrates the complete flow for automating agent activations:
1. Export pending agent activation URLs using browser automation
2. Parse the CSV for activation URLs
3. Automate the activation process with a set password

Usage:
python agent_activation_flow.py [account_name] [password]

Arguments:
  account_name - Optional CallHub account name (defaults to "default")
  password - Password to set for all activated agents (defaults to "Password123!")
"""

import sys
import os
import time
import argparse
from src.callhub.browser_automation import (
    export_agent_activation_urls_browser,
    activate_agents_with_password
)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Automate agent activation flow")
    parser.add_argument("account", nargs="?", default="default", help="CallHub account name")
    parser.add_argument("password", nargs="?", default="Password123!", help="Password to set for all agents")
    args = parser.parse_args()

    account_name = args.account
    password = args.password
    
    # Validate password
    if len(password) < 6:
        print("Error: Password must be at least 6 characters long")
        return
    
    print(f"Starting agent activation flow for account '{account_name}'...")
    print(f"Will set password: {password}")
    
    # Step 1: Export pending agent activation URLs
    print("\n== Step 1: Exporting activation URLs ==")
    export_result = export_agent_activation_urls_browser(account_name)
    
    if export_result.get("isError"):
        print(f"Error exporting activation URLs: {export_result.get('content', [{}])[0].get('text')}")
        return
    
    # Step 2: Check if we have any activations to process
    activations = export_result.get("activations", [])
    activation_count = len(activations)
    
    if activation_count == 0:
        print("No pending agent activations found. Process complete.")
        return
    
    print(f"Found {activation_count} pending agent activations:")
    for i, activation in enumerate(activations[:5]):  # Print first 5 for visibility
        print(f"  {i+1}. Username: {activation.get('username', 'Unknown')}, Email: {activation.get('email', 'Unknown')}")
    
    if activation_count > 5:
        print(f"  ... and {activation_count - 5} more")
    
    # Step 3: Prompt for confirmation
    confirm = input(f"\nDo you want to activate {activation_count} agents with password '{password}'? (y/n): ")
    if confirm.lower() != 'y':
        print("Operation cancelled by user.")
        return
    
    # Step 4: Activate agents
    print("\n== Step 4: Activating agents ==")
    start_time = time.time()
    
    activation_result = activate_agents_with_password(activations, password, account_name)
    
    if activation_result.get("isError"):
        print(f"Error during activation: {activation_result.get('content', [{}])[0].get('text')}")
        return
    
    # Step 5: Display results
    successful = activation_result.get("successful_activations", 0)
    failed = activation_result.get("failed_activations", 0)
    success_rate = activation_result.get("success_rate", "0%")
    duration = time.time() - start_time
    
    print(f"\n== Activation Complete ==")
    print(f"Total agents processed: {activation_count}")
    print(f"Successful activations: {successful}")
    print(f"Failed activations: {failed}")
    print(f"Success rate: {success_rate}")
    print(f"Processing time: {duration:.2f} seconds ({duration/activation_count:.2f} seconds per agent)")
    
    # Print details of failed activations
    if failed > 0:
        print("\nFailed activations details:")
        for i, result in enumerate(activation_result.get("details", [])):
            if not result.get("success"):
                print(f"  Username: {result.get('username', 'Unknown')}")
                print(f"  Email: {result.get('email', 'Unknown')}")
                print(f"  Error: {result.get('message', 'Unknown error')}")
                print("")
    
    print("Agent activation flow complete!")

if __name__ == "__main__":
    main()
