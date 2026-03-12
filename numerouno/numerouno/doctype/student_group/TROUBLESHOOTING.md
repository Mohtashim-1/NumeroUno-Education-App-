# Email Notification System Troubleshooting Guide

## Quick Fix Steps

### Step 1: Run the Debug Script
```bash
bench --site your-site.com console
```
Then execute:
```python
exec(open('apps/numerouno/numerouno/numerouno/doctype/student_group/debug_email_notification.py').read())
```

### Step 2: Run the Manual Test
```python
exec(open('apps/numerouno/numerouno/numerouno/doctype/student_group/manual_test.py').read())
```

## Common Issues and Solutions

### Issue 1: "No users found with required roles"
**Solution:**
1. Create a user with "Accounts User" or "Accounts Manager" role:
   - Go to **User** doctype
   - Create new user with email address
   - Add role: "Accounts User" or "Accounts Manager"

### Issue 2: "SMTP Server not configured"
**Solution:**
1. Go to **Setup > Email Settings**
2. Configure SMTP settings:
   - SMTP Server (e.g., smtp.gmail.com)
   - SMTP Port (usually 587 or 465)
   - Login credentials
3. Test email configuration

### Issue 3: "No Student Groups found with unpaid students"
**Solution:**
1. Create a Student Group with students
2. Ensure students have `custom_invoiced = 0` (unchecked)
3. Or run the test script which will create test data

### Issue 4: "custom_invoiced field not found"
**Solution:**
```bash
bench migrate
bench --site your-site.com migrate
```

### Issue 5: "Hooks not found"
**Solution:**
1. Clear cache:
```bash
bench clear-cache
bench --site your-site.com clear-cache
```

2. Restart the server:
```bash
bench restart
```

### Issue 6: "Background jobs not running"
**Solution:**
1. Start the scheduler:
```bash
bench start --scheduler
```

2. Or run in background:
```bash
bench schedule
```

### Issue 7: "Import errors"
**Solution:**
1. Check if all imports are correct in `student_group.py`
2. Ensure the file path is correct
3. Restart the server after changes

## Testing the System

### Test 1: Quick Email Test
```python
# In bench console
exec(open('apps/numerouno/numerouno/numerouno/doctype/student_group/manual_test.py').read())
```

### Test 2: Create Test Data and Test
```python
# This will create test data and send emails
from numerouno.numerouno.doctype.student_group.manual_test import test_step_by_step
test_step_by_step()
```

### Test 3: Manual Trigger
```python
# Manually trigger email notification
from numerouno.numerouno.doctype.student_group.student_group import send_daily_unpaid_notifications
send_daily_unpaid_notifications()
```

## Checking Logs

### View Error Logs
```bash
bench --site your-site.com logs
```

### View Scheduler Logs
```bash
bench --site your-site.com logs --scheduler
```

### View Email Logs
```bash
bench --site your-site.com logs --email
```

## Verification Checklist

- [ ] Users exist with "Accounts User" or "Accounts Manager" roles
- [ ] Email settings are configured correctly
- [ ] Student Groups exist with students having `custom_invoiced = 0`
- [ ] `custom_invoiced` field exists in database
- [ ] Hooks are properly configured
- [ ] Scheduler is running
- [ ] No import errors in console
- [ ] Test emails are being sent

## Emergency Fix

If nothing works, try this complete reset:

```python
# In bench console
import frappe

# 1. Clear all caches
frappe.clear_cache()

# 2. Reload hooks
frappe.reload_doc('numerouno', 'hooks')

# 3. Test email sending
frappe.sendmail(
    recipients=['your-email@example.com'],
    subject='Test Email',
    message='Test message',
    now=True
)

# 4. Test the notification function
from numerouno.numerouno.doctype.student_group.student_group import send_daily_unpaid_notifications
send_daily_unpaid_notifications()
```

## Still Not Working?

1. **Check the error logs** for specific error messages
2. **Verify email configuration** with a simple test email
3. **Ensure the scheduler is running** for background jobs
4. **Check user permissions** and roles
5. **Verify the custom field exists** in the database

## Support

If you're still having issues:
1. Check the error logs for specific messages
2. Verify all prerequisites are met
3. Test with the provided scripts
4. Check Frappe documentation for email and scheduling 