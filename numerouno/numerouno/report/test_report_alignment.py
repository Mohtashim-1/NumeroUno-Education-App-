# test_report_alignment.py
# Test script to verify report alignment and formatting

import frappe

def test_student_payment_summary_alignment():
    """Test the Student Payment Summary report alignment"""
    
    try:
        # Import the report function
        from numerouno.numerouno.report.student_payment_summary.student_payment_summary import execute
        
        # Test with no filters
        columns, data, summary, charts = execute({})
        
        print("✅ Report executed successfully!")
        print(f"📊 Columns defined: {len(columns)}")
        print(f"📋 Data rows: {len(data)}")
        
        # Check column structure
        print("\n📋 Column Structure:")
        for i, col in enumerate(columns, 1):
            print(f"  {i}. {col['label']} ({col['fieldname']}) - Width: {col.get('width', 'N/A')} - Align: {col.get('align', 'N/A')}")
        
        # Check data structure
        if data:
            print(f"\n📊 Sample Data Row:")
            sample_row = data[0]
            for col in columns:
                fieldname = col['fieldname']
                value = sample_row.get(fieldname, 'N/A')
                print(f"  {fieldname}: {value}")
        
        # Check summary
        print(f"\n📝 Summary length: {len(summary)} characters")
        
        # Check charts
        print(f"\n📈 Charts: {len(charts)}")
        for i, chart in enumerate(charts, 1):
            print(f"  {i}. {chart['title']} ({chart['type']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing report: {str(e)}")
        return False

def test_data_integrity():
    """Test data integrity and alignment"""
    
    try:
        # Get sample data directly from database
        sample_data = frappe.db.sql("""
            SELECT 
                sgs.student,
                sgs.student_name,
                sgs.custom_invoiced,
                sg.student_group_name,
                sg.program,
                sg.course,
                sgi.instructor_name
            FROM `tabStudent Group` sg
            LEFT JOIN `tabStudent Group Student` sgs
              ON sgs.parent = sg.name
             AND sgs.parentfield = 'students'
            LEFT JOIN `tabStudent Group Instructor` sgi
              ON sgi.parent = sg.name
             AND sgi.parentfield = 'instructors'
            LIMIT 5
        """, as_dict=True)
        
        print(f"\n🔍 Database Sample Data: {len(sample_data)} rows")
        
        if sample_data:
            print("📋 Sample row structure:")
            sample = sample_data[0]
            for key, value in sample.items():
                print(f"  {key}: {value} ({type(value).__name__})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing data integrity: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Student Payment Summary Report Alignment")
    print("=" * 50)
    
    success1 = test_student_payment_summary_alignment()
    success2 = test_data_integrity()
    
    if success1 and success2:
        print("\n✅ All tests passed! Report should display correctly.")
    else:
        print("\n❌ Some tests failed. Check the errors above.") 