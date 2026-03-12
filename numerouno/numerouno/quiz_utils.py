import frappe

def create_quiz_page():
    """Create the quiz attempt page in the database"""
    try:
        # Check if page already exists
        if frappe.db.exists("Page", "quiz_attempt"):
            print("Page already exists!")
            return
        
        # Create the page
        page = frappe.new_doc("Page")
        page.title = "Quiz Attempt"
        page.module = "Numerouno"
        page.page_name = "quiz_attempt"
        page.content_type = "Jinja Template"
        page.is_public = 1
        page.published = 1
        page.show_sidebar = 0
        page.show_title = 0
        page.insert(ignore_permissions=True)
        page.save()
        frappe.db.commit()
        
        print("Quiz attempt page created successfully!")
        return page.name
        
    except Exception as e:
        print(f"Error creating page: {str(e)}")
        frappe.log_error(f"Error creating quiz page: {str(e)}")
        return None

if __name__ == "__main__":
    create_quiz_page()
