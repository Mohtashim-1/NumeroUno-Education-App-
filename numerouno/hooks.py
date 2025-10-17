app_name = "numerouno"
app_title = "Numerouno"
app_publisher = "mohtashim"
app_description = "Customization in Frappe Education Module"
app_email = "shoaibmohtashim973@gmail.com"
app_license = "mit"
# required_apps = []


website_route_rules = [
    {"from_route": "/assessment-result1", "to_route": "numerouno/assessment_result1"},
    {"from_route": "/quiz", "to_route": "numerouno/quiz_index"},
    {"from_route": "/quiz-attempt", "to_route": "numerouno/quiz_attempt"}
]

# Website pages accessible to guests
website_pages = [
    {"page_name": "quiz_attempt", "module": "Numerouno"}
]

# Website context
website_context = {
    "quiz_attempt": "numerouno.numerouno.page.quiz_attempt.quiz_attempt.get_context"
}

portal_menu_items = [
    {
        "title": "Assessment Results",
        "route": "/assessment-result1",
        "reference_doctype": "Assessment Result",
        "role": "Student"
    }
]




# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/numerouno/css/numerouno.css"
# app_include_js = "/assets/numerouno/js/CustomLessonContent.vue"

# include js, css files in header of web template
# web_include_css = "/assets/numerouno/css/numerouno.css"
# web_include_js = "/assets/numerouno/js/CustomLessonContent.vue"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "numerouno/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Student" : "public/js/student.js",
    "Student Group" : "public/js/student_group.js",
    "Student Attendance" : "public/js/student_attendance.js",
    "Student Card" : "public/js/student_card.js",
    "Sales Invoice" : "public/js/sales_invoice.js",
    # "Assessment Result" : "public/js/assesment_result.js",
    }
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "numerouno/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "numerouno.utils.jinja_methods",
# 	"filters": "numerouno.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "numerouno.install.before_install"
# after_install = "numerouno.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "numerouno.uninstall.before_uninstall"
# after_uninstall = "numerouno.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "numerouno.utils.before_app_install"
# after_app_install = "numerouno.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "numerouno.utils.before_app_uninstall"
# after_app_uninstall = "numerouno.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "numerouno.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
    "Student Attendance": "numerouno.numerouno.doctype.student_attendance.student_attendance.StudentAttendance"
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Student Group": {
		"before_save": "numerouno.numerouno.doctype.student_group.student_group.create_academic_term",
        "validate": ["numerouno.numerouno.doctype.student_group.student_group.validate_course_location",
                     "numerouno.numerouno.doctype.student_group.student_group.sync_children",
                     "numerouno.numerouno.doctype.student_group.student_group.create_sales_order_from_student_group",
                    # "numerouno.numerouno.doctype.student_group.student_group.create_sales_order_for_purchase_order",
                    # "numerouno.numerouno.doctype.student_group.student_group.create_sales_order_for_advance_payment",
                    # "numerouno.numerouno.doctype.student_group.student_group.create_sales_invoice_for_cash_payment"
                    ],
        "after_save": "numerouno.numerouno.doctype.student_group.student_group.check_and_send_unpaid_notifications",
        "after_insert": "numerouno.numerouno.notifications.event_handlers.handle_student_group_creation",
        "on_update": "numerouno.numerouno.notifications.event_handlers.handle_student_group_instructor_update"
	},
    "Student": {
        "validate": "numerouno.numerouno.doctype.student.student.validate_student_contact_type",
        "on_update": [
            "numerouno.numerouno.doctype.student.student.send_email_notification_to_accountant",
            "numerouno.numerouno.doctype.student.student.send_welcome_email_to_student"
        ],
        "after_insert": "numerouno.numerouno.notifications.event_handlers.handle_student_welcome"
    },
    "Sales Order": {
        "on_update": "numerouno.numerouno.notifications.event_handlers.handle_missing_po",
        "after_insert": "numerouno.numerouno.notifications.event_handlers.handle_sales_order_creation"
    },
    "Assessment Result": {
        "on_update": "numerouno.numerouno.notifications.event_handlers.handle_assessment_pending",
        "after_insert": "numerouno.numerouno.notifications.event_handlers.handle_assessment_creation"
    },
    "Student Attendance": {
        "after_insert": "numerouno.numerouno.notifications.event_handlers.handle_student_absence",
        "on_update": "numerouno.numerouno.notifications.event_handlers.handle_attendance_eligibility"
    },
    "Instructor Assignment": {
        "after_insert": "numerouno.numerouno.notifications.event_handlers.handle_instructor_assignment"
    },
    "Cash Assignment": {
        "after_insert": "numerouno.numerouno.notifications.event_handlers.handle_cash_assignment"
    },
    "Course Schedule": {
        "after_insert": "numerouno.numerouno.notifications.event_handlers.handle_course_schedule_creation"
    },
    "LMS Quiz Submission": {
        "validate": "numerouno.numerouno.doctype.lms_quiz_submission.lms_quiz_submission.on_submit"
    },
    "User": {
        "after_insert": "numerouno.numerouno.doctype.student.student.send_lms_welcome_email_to_user"
    },
    "Assessment Result": {
        "on_submit": "numerouno.numerouno.unified_assessment_system.trigger_assessment_result_events"
    }
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"numerouno.numerouno.doctype.student_group.student_group.send_daily_unpaid_notifications"
	]
}

# Testing
# -------

# before_tests = "numerouno.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "numerouno.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "numerouno.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["numerouno.utils.before_request"]
# after_request = ["numerouno.utils.after_request"]

# Job Events
# ----------
# before_job = ["numerouno.utils.before_job"]
# after_job = ["numerouno.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"numerouno.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

