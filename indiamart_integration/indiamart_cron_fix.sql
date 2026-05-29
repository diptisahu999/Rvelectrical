-- IndiaMART Cron Job Fix Script
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
-- Go to Apps -> IndiaMART Integration -> Uninstall -> Install

-- Step 5: Verify fixes
SELECT 'After Fix - Cron Job:' as info;
SELECT id, name, active, nextcall, interval_number, interval_type 
FROM ir_cron 
WHERE name LIKE '%IndiaMART%';

SELECT 'After Fix - Integration:' as info;
SELECT id, name, auto_mode, status, last_auto_execution, auto_mode_active
FROM indiamart_integration;
