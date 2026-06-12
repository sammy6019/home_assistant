#!/usr/bin/env python3
"""Retrieve Anthropic API key from Vaultwarden"""

import json
import subprocess
import os

VAULTWARDEN_URL = "https://vaultwarden.ollamapi.com"
VAULTWARDEN_EMAIL = "stmcdonald76@gmail.com"  # Your login email
VAULTWARDEN_MASTER_PASSWORD = os.getenv("VAULTWARDEN_MASTER_PASSWORD")

def get_api_key():
    """Fetch API key from Vaultwarden vault"""
    try:
        # Use bitwarden CLI to access vault
        # First, unlock the vault
        cmd = f'bw unlock "{VAULTWARDEN_MASTER_PASSWORD}" --raw'
        session = subprocess.check_output(cmd, shell=True, text=True).strip()
        
        # Get the Anthropic API Key item
        cmd = f'bw get item "Anthropic API Key" --session {session}'
        item = json.loads(subprocess.check_output(cmd, shell=True, text=True))
        
        # Extract password field
        api_key = item['login']['password']
        return api_key
        
    except Exception as e:
        print(f"Error retrieving from Vaultwarden: {e}")
        return None

if __name__ == "__main__":
    key = get_api_key()
    if key:
        print(key)
    else:
        print("Failed to retrieve API key")
        exit(1)
