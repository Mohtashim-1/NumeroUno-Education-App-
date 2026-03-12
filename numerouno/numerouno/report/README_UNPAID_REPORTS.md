# Unpaid Students Reports System

## Overview
This system provides comprehensive reports for tracking and managing students with unmarked paid fields (`custom_invoiced = 0`) across all Student Groups. It includes both detailed reports and dashboard views with actionable insights.

## Reports Available

### 1. **Unpaid Students Report** (`unpaid_students`)
**Location**: `apps/numerouno/numerouno/numerouno/report/unpaid_students/`

**Features**:
- ✅ Complete list of all unpaid students
- ✅ Detailed information including Student Group, Program, Course, Instructor
- ✅ Sales Invoice and Sales Order tracking
- ✅ Summary statistics
- ✅ Bar chart showing unpaid students by Student Group
- ✅ Direct "Send Email Notifications" button
- ✅ Comprehensive filtering options

**Columns**:
- Student Group ID & Name
- Program & Course
- From/To Dates
- Roll Number
- Student ID & Name
- Invoiced Status
- Sales Invoice
- Instructor & Instructor Name
- Customer
- Sales Order

**Filters**:
- Student Group
- Program
- Course
- Instructor
- From Date
- To Date

### 2. **Unpaid Students Dashboard** (`unpaid_students_dashboard`)
**Location**: `apps/numerouno/numerouno/numerouno/report/unpaid_students_dashboard/`

**Features**:
- ✅ Visual dashboard with summary cards
- ✅ Priority-based categorization (High/Medium/Low)
- ✅ Multiple charts and visualizations
- ✅ Recent unpaid students table
- ✅ Quick action buttons
- ✅ Export functionality

**Dashboard Elements**:
1. **Summary Cards**:
   - Total Unpaid Students
   - Student Groups Affected
   - Unique Students
   - Average Days Unpaid

2. **Priority Levels**:
   - High Priority (>30 days)
   - Medium Priority (15-30 days)
   - Low Priority (<15 days)

3. **Charts**:
   - Unpaid Students by Student Group (Bar Chart)
   - Unpaid Students by Program (Pie Chart)
   - Unpaid Students by Days Unpaid (Bar Chart)

4. **Recent Data Table**:
   - Top 50 most urgent cases
   - Sorted by days unpaid (descending)

**Filters**:
- Program
- Course
- Priority Level

## Utility Functions

### Mark as Paid Functions (`mark_as_paid.py`)
**Location**: `apps/numerouno/numerouno/numerouno/doctype/student_group/mark_as_paid.py`

**Available Functions**:
1. `mark_student_as_paid(student_group, student)` - Mark individual student as paid
2. `mark_multiple_students_as_paid(student_data)` - Mark multiple students as paid
3. `mark_all_students_in_group_as_paid(student_group)` - Mark all students in a group as paid
4. `get_unpaid_students_summary()` - Get quick summary statistics

## How to Use

### Accessing the Reports
1. Go to **Reports** in the Frappe desk
2. Search for "Unpaid Students" or "Unpaid Students Dashboard"
3. Apply filters as needed
4. Generate the report

### Using the Dashboard
1. **View Summary**: Check the colored cards for quick overview
2. **Analyze Charts**: Use charts to identify patterns and priorities
3. **Review Recent Cases**: Check the table for most urgent cases
4. **Take Action**: Use the action buttons to send notifications or export data

### Marking Students as Paid
```python
# Mark individual student
from numerouno.numerouno.doctype.student_group.mark_as_paid import mark_student_as_paid
mark_student_as_paid("STUDENT-GROUP-001", "STUDENT-001")

# Mark all students in a group
from numerouno.numerouno.doctype.student_group.mark_as_paid import mark_all_students_in_group_as_paid
mark_all_students_in_group_as_paid("STUDENT-GROUP-001")
```

## Integration with Email System

Both reports integrate with the email notification system:
- **"Send Email Notifications"** button triggers the daily notification function
- Reports show the same data that email notifications are based on
- Consistent filtering and data sources

## Customization

### Adding New Filters
Edit the respective `.js` files to add new filter options:
```javascript
{
  fieldname: "new_filter",
  label: __("New Filter"),
  fieldtype: "Link",
  options: "Your DocType"
}
```

### Modifying Charts
Edit the chart data generation in the Python files:
```python
chart = {
    "data": {
        "labels": your_labels,
        "datasets": [{"name": "Your Data", "values": your_values}]
    },
    "type": "bar",
    "title": "Your Chart Title"
}
```

### Adding New Columns
Modify the `columns` list in the Python files:
```python
columns = [
    {"label": "New Column", "fieldname": "new_field", "fieldtype": "Data", "width": 150},
    # ... existing columns
]
```

## File Structure
```
apps/numerouno/numerouno/numerouno/report/
├── unpaid_students/
│   ├── unpaid_students.py
│   ├── unpaid_students.js
│   └── unpaid_students.json
├── unpaid_students_dashboard/
│   ├── unpaid_students_dashboard.py
│   ├── unpaid_students_dashboard.js
│   └── unpaid_students_dashboard.json
└── README_UNPAID_REPORTS.md

apps/numerouno/numerouno/numerouno/doctype/student_group/
└── mark_as_paid.py
```

## Permissions

Reports are accessible to users with these roles:
- **Accounts User**
- **Accounts Manager**
- **Academics User**
- **System Manager**

## Best Practices

1. **Regular Monitoring**: Run the dashboard daily to monitor unpaid students
2. **Priority Management**: Focus on high-priority cases (>30 days unpaid)
3. **Bulk Actions**: Use the utility functions for bulk updates
4. **Data Export**: Export data for external analysis when needed
5. **Email Integration**: Use the email notifications for automated alerts

## Troubleshooting

### Report Not Loading
1. Check if the custom field `custom_invoiced` exists
2. Verify user permissions
3. Clear cache: `bench clear-cache`

### No Data Showing
1. Ensure Student Groups have students with `custom_invoiced = 0`
2. Check filter settings
3. Verify database connections

### Charts Not Displaying
1. Check browser console for JavaScript errors
2. Ensure sufficient data for chart generation
3. Verify chart configuration in Python files

## Support

For issues with the reports:
1. Check error logs: `bench --site your-site.com logs`
2. Verify data integrity in Student Groups
3. Test with the provided utility functions
4. Review the email notification system integration 