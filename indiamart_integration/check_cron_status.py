#!/usr/bin/env python3
"""
Script to check IndiaMART cron job status in Odoo
Run this script to verify if the cron job is active and when it last ran
"""

print("=== IndiaMART Cron Job Checker ===")
print()
print("To check your cron job status, please run these SQL queries in your Odoo database:")
print()
print("1. Check if the cron job exists:")
print("   SELECT id, name, active, nextcall, numbercall, interval_number, interval_type")
print("   FROM ir_cron") 
print("   WHERE name LIKE '%IndiaMART%' OR name LIKE '%indiamart%';")
print()
print("2. Check cron job execution history:")
print("   SELECT * FROM ir_cron")
print("   WHERE name = 'IndiaMART: Auto-fetch Leads (Real-time)'")
print("   ORDER BY nextcall DESC;")
print()
print("3. Check integration records:")
print("   SELECT id, name, auto_mode, status, last_auto_execution, auto_execution_count, leads_count")
print("   FROM indiamart_integration")
print("   WHERE auto_mode = true;")
print()
print("Expected Results:")
print("- Cron job should be active=true")  
print("- nextcall should be updated every 5 minutes")
print("- Integration status should be 'active'")
print("- last_auto_execution should be recent (within 5 minutes)")
