#!/usr/bin/env python3
"""
IndiaMART Integration Diagnostic Script
This script helps diagnose common issues with the IndiaMART integration
"""

import requests
from datetime import datetime, timedelta

def test_api_connection(api_url):
    """Test the IndiaMART API connection"""
    print("=== Testing IndiaMART API Connection ===")
    
    # Clean URL and add test dates
    base_url = api_url.strip()
    if 'start_time=' in base_url:
        base_url = base_url.split('&start_time=')[0]
    if 'end_time=' in base_url:
        base_url = base_url.split('&end_time=')[0]
    
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    
    start_time = yesterday.strftime('%d-%b-%Y')
    end_time = now.strftime('%d-%b-%Y')
    
    final_url = f"{base_url}&start_time={start_time}&end_time={end_time}"
    
    print(f"Testing URL: {final_url}")
    
    try:
        response = requests.get(final_url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        status = data.get('STATUS')
        total_records = data.get('TOTAL_RECORDS', 0)
        message = data.get('MESSAGE', '')
        
        print(f"✅ API Response Status: {status}")
        print(f"📊 Total Records: {total_records}")
        print(f"💬 Message: {message}")
        
        if status == 'SUCCESS':
            print("✅ API connection is working!")
            return True
        else:
            print(f"❌ API returned error: {message}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API connection failed: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def main():
    print("IndiaMART Integration Diagnostics")
    print("=" * 50)
    print()
    
    print("1. Manual API Test")
    print("Enter your IndiaMART API URL (without dates):")
    api_url = input("> ")
    
    if api_url:
        test_api_connection(api_url)
    
    print()
    print("2. Common Issues Checklist:")
    print("□ Is auto mode enabled in the integration record?")
    print("□ Is the integration status 'active'?")
    print("□ Is the cron job active and running?")
    print("□ Check Odoo logs for any error messages")
    print("□ Verify API key is correct and not expired")
    print("□ Check if blocked_emails is blocking all leads")
    print("□ Ensure time zone settings are correct")
    
    print()
    print("3. Next Steps:")
    print("- Check the integration form in Odoo")
    print("- Click 'Test Auto Fetch' to manually test")
    print("- Check CRM → Leads for imported leads")
    print("- Review Odoo server logs")

if __name__ == "__main__":
    main()
