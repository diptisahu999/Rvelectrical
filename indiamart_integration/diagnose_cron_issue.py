#!/usr/bin/env python3
"""
IndiaMART Cron Job Diagnostic Script
This script helps identify why the cron job is not working
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def print_diagnostic_queries():
    """Print SQL queries to diagnose the cron job issue"""
    print("=" * 60)
    print("🔍 INDIAMART CRON JOB DIAGNOSTICS")
    print("=" * 60)
    print()
    
    print("1️⃣ CHECK CRON JOB STATUS:")
    print("Run this query in your Odoo database to check if cron job exists:")
    print()
    print("SELECT id, name, active, nextcall, numbercall, interval_number, interval_type, state, code")
    print("FROM ir_cron") 
    print("WHERE name LIKE '%IndiaMART%' OR name LIKE '%indiamart%';")
    print()
    print("Expected result:")
    print("- name: 'IndiaMART: Auto-fetch Leads (Real-time)'")
    print("- active: true")
    print("- interval_number: 5")
    print("- interval_type: 'minutes'")
    print("- state: 'code'")
    print("- code: 'model.cron_fetch_leads_auto_mode()'")
    print()
    
    print("2️⃣ CHECK INTEGRATION STATUS:")
    print("Run this query to check integration configuration:")
    print()
    print("SELECT id, name, auto_mode, status, last_auto_execution, auto_execution_count,")
    print("       leads_count, error_message, auto_mode_active")
    print("FROM indiamart_integration")
    print("WHERE auto_mode = true;")
    print()
    print("Expected result:")
    print("- auto_mode: true")
    print("- status: 'active'")
    print("- auto_mode_active: true")
    print("- last_auto_execution: should be recent (within 5-10 minutes)")
    print()
    
    print("3️⃣ CHECK RECENT CRON EXECUTIONS:")
    print("Run this query to see recent cron activity:")
    print()
    print("SELECT id, name, nextcall, lastcall, active, numbercall")
    print("FROM ir_cron")
    print("WHERE name = 'IndiaMART: Auto-fetch Leads (Real-time)'")
    print("ORDER BY nextcall DESC;")
    print()
    
    print("4️⃣ CHECK FOR ERROR LOGS:")
    print("Look in your Odoo server logs for these patterns:")
    print("- '🚀 CRON JOB STARTED: IndiaMart real-time lead fetch'")
    print("- '❌ CRON ERROR'")
    print("- 'IndiaMART'")
    print("- 'cron_fetch_leads_auto_mode'")
    print()
    
    print("=" * 60)
    print("🚨 COMMON ISSUES AND SOLUTIONS:")
    print("=" * 60)
    print()
    
    print("ISSUE 1: Cron job doesn't exist")
    print("SOLUTION: Module installation failed. Reinstall the module.")
    print()
    
    print("ISSUE 2: Cron job exists but active=false")
    print("SOLUTION: Update query:")
    print("UPDATE ir_cron SET active=true WHERE name='IndiaMART: Auto-fetch Leads (Real-time)';")
    print()
    
    print("ISSUE 3: Integration auto_mode=false")
    print("SOLUTION: Enable auto mode in the integration form or update query:")
    print("UPDATE indiamart_integration SET auto_mode=true, status='active', auto_mode_active=true;")
    print()
    
    print("ISSUE 4: nextcall is in the past and not updating")
    print("SOLUTION: Reset the cron job next call time:")
    print("UPDATE ir_cron SET nextcall=NOW() + INTERVAL '5 minutes'")
    print("WHERE name='IndiaMART: Auto-fetch Leads (Real-time)';")
    print()
    
    print("ISSUE 5: API errors preventing execution")
    print("SOLUTION: Check the error_message field in indiamart_integration table")
    print("and fix API configuration issues.")
    print()
    
    print("=" * 60)
    print("🔧 QUICK FIX COMMANDS:")
    print("=" * 60)
    print()
    
    print("1. Activate cron job:")
    print("UPDATE ir_cron SET active=true WHERE name LIKE '%IndiaMART%';")
    print()
    
    print("2. Reset cron job timing:")
    print("UPDATE ir_cron SET nextcall=NOW() + INTERVAL '5 minutes'")
    print("WHERE name LIKE '%IndiaMART%';")
    print()
    
    print("3. Enable integration auto mode:")
    print("UPDATE indiamart_integration SET auto_mode=true, status='active',")
    print("       auto_mode_active=true WHERE id=1;")
    print()
    
    print("4. Clear integration errors:")
    print("UPDATE indiamart_integration SET error_message=NULL, status='active'")
    print("WHERE auto_mode=true;")
    print()
    
    print("=" * 60)
    print("📝 NEXT STEPS:")
    print("=" * 60)
    print()
    print("1. Run the diagnostic queries above")
    print("2. Apply the appropriate fix based on findings")
    print("3. Monitor the system for 10-15 minutes")
    print("4. Check if last_auto_execution updates")
    print("5. Verify new leads appear in CRM → Leads")
    print()

def create_fix_script():
    """Create a comprehensive fix script"""
    fix_script = '''-- IndiaMART Cron Job Fix Script
-- Run these SQL commands in your Odoo database

-- Step 1: Check current state
SELECT 'Current Cron Job State:' as info;
SELECT id, name, active, nextcall, interval_number, interval_type 
FROM ir_cron 
WHERE name LIKE '%IndiaMART%';

SELECT 'Current Integration State:' as info;
SELECT id, name, auto_mode, status, last_auto_execution, auto_mode_active
FROM indiamart_integration;

-- Step 2: Fix cron job if it exists but is inactive
UPDATE ir_cron 
SET active=true, 
    nextcall=NOW() + INTERVAL '2 minutes'
WHERE name LIKE '%IndiaMART%' AND active=false;

-- Step 3: Fix integration settings
UPDATE indiamart_integration 
SET auto_mode=true, 
    status='active',
    auto_mode_active=true,
    error_message=NULL
WHERE auto_mode=false OR status != 'active';

-- Step 4: If cron job doesn't exist, you need to reinstall the module
-- Go to Apps → IndiaMART Integration → Uninstall → Install

-- Step 5: Verify fixes
SELECT 'After Fix - Cron Job:' as info;
SELECT id, name, active, nextcall, interval_number, interval_type 
FROM ir_cron 
WHERE name LIKE '%IndiaMART%';

SELECT 'After Fix - Integration:' as info;
SELECT id, name, auto_mode, status, last_auto_execution, auto_mode_active
FROM indiamart_integration;
'''
    
    with open('indiamart_cron_fix.sql', 'w') as f:
        f.write(fix_script)
    
    print(f"📄 Fix script saved to: indiamart_cron_fix.sql")
    print("Run this SQL script in your Odoo database to apply fixes.")
    print()

def main():
    """Main diagnostic function"""
    print_diagnostic_queries()
    create_fix_script()
    
    print("=" * 60)
    print("🎯 IMMEDIATE ACTION REQUIRED:")
    print("=" * 60)
    print()
    print("1. Connect to your Odoo database")
    print("2. Run the diagnostic queries above")
    print("3. Based on results, run the appropriate fix commands")
    print("4. Wait 5-10 minutes and check if cron starts working")
    print("5. Test with 'Test Auto Fetch' button in integration form")
    print()
    print("If issue persists, check Odoo server logs for detailed error messages.")

if __name__ == "__main__":
    main()
