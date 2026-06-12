#!/usr/bin/env python3
import os
import requests
from datetime import datetime

# Your Anthropic Admin API Key (different from regular key)
ADMIN_KEY = "sk-ant-admin-YOUR_ADMIN_KEY_HERE"
ORG_ID = "your-org-id"

# Budget thresholds
DAILY_LIMIT = 3  # $3 per day = ~$90/month
WARNING_THRESHOLD = 0.75  # Alert at 75% of daily limit
CRITICAL_THRESHOLD = 0.95  # Alert at 95% of daily limit

def get_usage():
    """Fetch usage from Anthropic API"""
    url = f"https://api.anthropic.com/v1/organizations/usage_report/messages"
    headers = {
        "x-api-key": ADMIN_KEY,
        "anthropic-version": "2023-06-01"
    }
    
    today = datetime.now().strftime("%Y-%m-%dT00:00:00Z")
    tomorrow = datetime.now().strftime("%Y-%m-%dT23:59:59Z")
    
    params = {
        "starting_at": today,
        "ending_at": tomorrow,
        "bucket_width": "1d"
    }
    
    response = requests.get(url, headers=headers, params=params)
    return response.json()

def check_budget():
    """Monitor daily spend"""
    try:
        usage = get_usage()
        daily_spend = usage.get("data", [{}])[0].get("amount_usd", 0)
        
        if daily_spend > (CRITICAL_THRESHOLD * DAILY_LIMIT):
            print(f"🚨 CRITICAL: Daily spend ${daily_spend:.2f} exceeds 95% of limit!")
            # Send HA notification
            os.system('curl -X POST http://localhost:8123/api/webhook/api-spending-critical')
        elif daily_spend > (WARNING_THRESHOLD * DAILY_LIMIT):
            print(f"⚠️  WARNING: Daily spend ${daily_spend:.2f} at 75% of limit")
            # Send HA notification
            os.system('curl -X POST http://localhost:8123/api/webhook/api-spending-warning')
        else:
            print(f"✅ Daily spend: ${daily_spend:.2f}/{DAILY_LIMIT}")
            
    except Exception as e:
        print(f"Error checking budget: {e}")

if __name__ == "__main__":
    check_budget()
