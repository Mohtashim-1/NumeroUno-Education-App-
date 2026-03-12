# Email Notification System for Unpaid Students

## Overview
This system automatically sends email notifications to Accounts User and Accounts Manager roles when students in Student Groups are not marked as invoiced (custom_invoiced field is unchecked).

## Features

### 1. Real-time Notifications
- **Trigger**: When a Student Group is saved/updated
- **Condition**: If any student in the group has `custom_invoiced = 0` or `NULL`
- **Recipients**: All users with "Accounts User" or "Accounts Manager" roles
- **Content**: Detailed table showing unpaid students with roll numbers, student IDs, and names

### 2. Daily Consolidated Reports
- **Trigger**: Daily scheduled task (runs automatically)
- **Content**: Summary of all unpaid students across all Student Groups
- **Recipients**: Same as real-time notifications
- **Frequency**: Once per day

## How It Works

### Event Triggers
1. **Document Save Event**: When a Student Group is saved, the system checks all students in the group
2. **Scheduled Task**: Daily background job that scans all Student Groups for unpaid students

### Email Content
- **Subject**: "Unpaid Students Alert - [Student Group Name]" or "Daily Unpaid Students Report - [Date]"
- **Body**: 
  - Professional greeting
  - Summary of unpaid students
  - HTML table with student details
  - Direct link to the Student Group
  - Call to action for review

### Technical Implementation

#### Files Modified:
1. **`student_group.py`**: Contains the notification functions
2. **`hooks.py`**: Registers event handlers and scheduled tasks

#### Key Functions:
- `send_unpaid_student_notification()`: Sends individual group notifications
- `check_and_send_unpaid_notifications()`: Event handler for document save
- `send_daily_unpaid_notifications()`: Daily consolidated report

#### Background Processing:
- Uses Frappe's `enqueue()` function for background email sending
- Prevents blocking the UI during email processing
- Includes error handling and logging

## Configuration

### Required Roles
Ensure users have one of these roles to receive notifications:
- **Accounts User**
- **Accounts Manager**

### Email Settings
Make sure your Frappe system has proper email configuration:
1. Go to **Setup > Email Settings**
2. Configure SMTP settings
3. Test email functionality

### Custom Field
The system relies on the `custom_invoiced` field in the Student Group Student child table:
- **Field Type**: Check (Boolean)
- **Default**: 0 (unchecked)
- **Purpose**: Indicates if the student has been invoiced

## Testing

### Manual Test
Run the test script to verify the system:
```bash
bench --site your-site.com console
```
Then execute:
```python
exec(open('apps/numerouno/numerouno/numerouno/doctype/student_group/test_email_notification.py').read())
```

### Real-time Test
1. Create or edit a Student Group
2. Ensure some students have `custom_invoiced` unchecked
3. Save the document
4. Check email inboxes of Accounts users

### Daily Report Test
1. Manually trigger the daily notification:
```python
from numerouno.numerouno.doctype.student_group.student_group import send_daily_unpaid_notifications
send_daily_unpaid_notifications()
```

## Troubleshooting

### Common Issues:
1. **No emails received**: Check email configuration and user roles
2. **Background jobs not running**: Ensure scheduler is active
3. **Permission errors**: Verify user permissions for Student Group access

### Logs:
Check the following logs for errors:
- **Error Logs**: `bench --site your-site.com logs`
- **Scheduler Logs**: Monitor background job execution
- **Email Logs**: Check email delivery status

## Customization

### Modify Email Template
Edit the email body in the notification functions to customize:
- Email format and styling
- Content and messaging
- Additional information to include

### Add More Recipients
Modify the role filter in the notification functions:
```python
filters={"role": ["in", ["Accounts User", "Accounts Manager", "Additional Role"]]}
```

### Change Frequency
Modify the scheduler in `hooks.py`:
```python
scheduler_events = {
    "hourly": ["numerouno.numerouno.doctype.student_group.student_group.send_daily_unpaid_notifications"]
}
```

## Security Considerations
- Only users with appropriate roles receive notifications
- Email content is sanitized and doesn't expose sensitive data
- Background processing prevents system overload
- Error handling prevents system crashes

## Support
For issues or questions about this email notification system, please check:
1. Frappe documentation on email and scheduling
2. System logs for error details
3. Email configuration settings 