import frappe
from frappe.utils import getdate, add_days, nowdate, get_url
from frappe import _
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue
from numerouno.numerouno.doctype.sales_invoice.sales_invoice import fetch_students_from_sg


def get_default_receivable_account():
    """Get the default receivable account for the company"""
    try:
        company = frappe.defaults.get_global_default("company")
        if company:
            return frappe.db.get_value("Company", company, "default_receivable_account")
        return None
    except Exception:
        return None


def get_default_cash_account():
    """Get the default cash account for the company"""
    try:
        company = frappe.defaults.get_global_default("company")
        if company:
            return frappe.db.get_value("Company", company, "default_cash_account")
        return None
    except Exception:
        return None



def validate_course_location(doc, method):
    """Validate and copy custom_course_location to custom_coarse_location if exists"""
    
    # Check if custom_course_location field exists and has a value
    if hasattr(doc, 'custom_course_location') and doc.custom_course_location:
        # Copy the value to custom_coarse_location
        doc.custom_coarse_location = doc.custom_course_location
        # frappe.msgprint(_("Course location copied to coarse location: {0}").format(doc.custom_course_location))

    if hasattr(doc, 'from_date') and doc.from_date:
        doc.custom_from_date = doc.from_date

    if hasattr(doc, 'to_date') and doc.to_date:   
        doc.custom_to_date = doc.to_date

    if hasattr(doc, 'end_date') and doc.end_date:   
        doc.custom_end_date = doc.end_date


def sync_children(doc, method):
    for row in doc.students:
        # 1) always store the link back to this parent
        row.custom_student_group = doc.name

        # 2) mirror your parent's date fields
        row.custom_start_date = doc.from_date
        row.custom_end_date   = doc.to_date

        # 3) mirror the course name
        row.custom_course_name = doc.course

        # 4) mirror the invoice if one exists
        row.custom_sales_invoice = doc.custom_sales_invoice or ""

        # 5) flag "invoiced" if you've actually set an invoice
        row.custom_invoiced = 1 if doc.custom_sales_invoice else 0


@frappe.whitelist()
def create_coarse_schedule(student_group, from_time, to_time):
    try:
        if not student_group:
            frappe.throw(_("❌ Student Group is missing"))

        doc = frappe.get_doc("Student Group", student_group)

        if not doc.from_date or not doc.to_date:
            frappe.throw(_("❌ Please set both 'From Date' and 'To Date' in the Student Group."))

        if not doc.custom_coarse_location:
            frappe.throw(_(" ❌ Please set the 'Room' (Coarse Location) in the Student Group."))

        if not doc.instructors:
            frappe.throw(_("❌ No instructors found in this Student Group."))

        # Ensure every instructor child row has instructor selected
        for i in doc.instructors:
            if not i.instructor:
                frappe.throw(_(" ❌ Each row in 'Instructors' must have an Instructor selected."))

        if not doc.students:
            frappe.throw(_("❌ No students found in this Student Group."))

        from_date = getdate(doc.from_date)
        to_date = getdate(doc.to_date)
        today = getdate(nowdate())

        for i in doc.instructors:
            instructor = i.instructor
            current_date = from_date

            while current_date <= to_date:
                # Create Course Schedule
                cs = frappe.new_doc("Course Schedule")
                cs.student_group = doc.name
                cs.course = doc.course
                cs.program = doc.program
                cs.instructor = instructor
                cs.schedule_date = current_date
                cs.room = doc.custom_coarse_location
                cs.from_time = from_time
                cs.to_time = to_time
                cs.flags.ignore_permissions = True
                cs.insert()

                # Create attendance for ALL dates (including future dates)
                for s in doc.students:
                    student = s.student

                    # Student Attendance - for all dates (past, present, and future)
                    try:
                        sa = frappe.new_doc("Student Attendance")
                        sa.student = student
                        sa.date = current_date
                        sa.course_schedule = cs.name
                        sa.student_group = doc.name
                        sa.status = "Present"
                        sa.flags.ignore_permissions = True
                        sa.insert()
                        print(f"✅ Created attendance for student {student} on {current_date}")
                    except Exception as attendance_error:
                        print(f"❌ Failed to create attendance for student {student} on {current_date}: {str(attendance_error)}")
                        frappe.log_error(f"Attendance creation failed for {student} on {current_date}: {str(attendance_error)}", "Attendance Creation Error")

                # Create Student Cards once per student (outside the date loop)
                if current_date == from_date:  # Only create cards on the first iteration
                    for s in doc.students:
                        student = s.student
                        # Student Card - only once per student
                        if not frappe.db.exists("Student Card", {"student": student, "student_group": doc.name}):
                            sc = frappe.new_doc("Student Card")
                            sc.student = student
                            sc.student_group = doc.name
                            sc.flags.ignore_permissions = True
                            sc.insert()

                frappe.db.commit()
                current_date = add_days(current_date, 1)

        frappe.msgprint(_("✅ Course Schedules and Student Attendance created from {0} to {1} (including future dates). Student Cards created.").format(from_date, to_date))

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "❌ Error in create_coarse_schedule")
        frappe.throw(_("An error occurred while creating schedule. Please check error logs."))


def create_academic_term(doc, method):
    if not (doc.from_date and doc.to_date and doc.academic_year):
        return  # Exit silently if any required field is missing

    if not doc.academic_term:
        existing_term = frappe.get_value(
            "Academic Term",
            {
                "term_start_date": doc.from_date,
                "term_end_date": doc.to_date,
                "academic_year": doc.academic_year
            }
        )

        if existing_term:
            doc.academic_term = existing_term
            return

        term_name = f"{doc.from_date} to {doc.to_date}"
        at = frappe.new_doc("Academic Term")
        at.academic_year = doc.academic_year
        at.term_name = term_name
        at.term_start_date = doc.from_date
        at.term_end_date = doc.to_date
        at.save()

        doc.academic_term = at.name

@frappe.whitelist()
def create_sales_order(student_group, item_code, rate):
    student_group_doc = frappe.get_doc("Student Group", student_group)
    students = student_group_doc.students

    if not students:
        frappe.throw("No students in the group")

    qty = len(students)

    sales_order = frappe.new_doc("Sales Order")
    sales_order.customer = student_group_doc.custom_customer
    sales_order.delivery_date = add_days(nowdate(), 7)

    sales_order.append("items", {
        "item_code": item_code,
        "qty": qty,
        "rate": rate
    })

    sales_order.insert()
    sales_order.submit()

    # ✅ Update custom field in Student Group
    student_group_doc.custom_sales_order = sales_order.name
    student_group_doc.save(ignore_permissions=True)

    frappe.db.commit()
    return sales_order.name

# there are three casees for the payment in first case company raised purchase order and we create sales order for its recording 

@frappe.whitelist()
def create_sales_invoice(student_group, sales_order):
    # 1) Load Student Group & validate
    sg = frappe.get_doc("Student Group", student_group)
    if not sg.students:
        frappe.throw(_("No students in the group"))

    # 2) Load the Sales Order and ensure it's submitted
    so = frappe.get_doc("Sales Order", sales_order)
    if so.docstatus == 0:
        so.submit()

    # 3) Build a new Sales Invoice manually (so items + sales_order link are present)
    si = frappe.new_doc("Sales Invoice")
    si.customer = so.customer
    si.select_student_group = sg.name
    si.due_date = add_days(nowdate(), 7)
    # copy each item, including the sales_order link
    for row in so.get("items"):
        si.append("items", {
            "item_code":      row.item_code,
            "qty":            row.qty,
            "rate":           row.rate,
            "uom":            row.uom,
            "sales_order":    so.name,
            "description":    row.description,
            # add any other fields you need
        })

    # Fetch students as the button would do
    students_data = fetch_students_from_sg(so.customer, [sg.name])

    # If fetch_students_from_sg returns a Frappe Response object, get the data
    if hasattr(students_data, 'get') and callable(students_data.get):
        students_data = students_data.get('message', students_data)

    # Add students to the child table
    for student in students_data:
        si.append("student", {
            "student": student["student"],
            "student_name": student["student_name"],
            # add other fields as needed
        })
    print(f"Fetched and added {len(students_data)} students to Sales Invoice")

    # 4) insert & submit
    si.insert()
    print(f"Sales Invoice {si.name} inserted.")
    si.submit()
    print(f"Sales Invoice {si.name} submitted.")

    # 5) write back to Student Group
    sg.custom_sales_invoice = si.name
    sg.save(ignore_permissions=True)

    # Add Student Group to the select_student_group MultiSelect Table field
    # si.append("select_student_group", {
    #     "student_group": sg.name
    # })
    # frappe.logger().info(f"Appended Student Group {sg.name} to select_student_group table")

    return si.name


@frappe.whitelist()
def create_sales_invoice_from_sales_order(sales_order):
    from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

    if not sales_order:
        frappe.throw("Sales Order is required")

    sales_order_doc = frappe.get_doc("Sales Order", sales_order)

    # ✅ Submit Sales Order if not submitted
    if sales_order_doc.docstatus == 0:
        sales_order_doc.submit()

    # ✅ Create Invoice from Sales Order
    invoice = make_sales_invoice(sales_order)
    invoice.due_date = add_days(nowdate(), 7)

    # 🛑 Handle missing income_account or other required fields if needed
    for item in invoice.items:
        if not item.income_account:
            item.income_account = frappe.db.get_value(
                "Item Default",
                {"parent": item.item_code},
                "income_account"
            ) or frappe.db.get_single_value("Company", invoice.company, "default_income_account")

    # ✅ Insert and Submit Invoice
    invoice.insert()
    invoice.submit()

    # ✅ Update Student Group with Sales Invoice reference
    student_group = sales_order_doc.get("custom_student_group")

    if student_group:
        sg_doc = frappe.get_doc("Student Group", student_group)
        sg_doc.custom_sales_invoice = invoice.name
        sg_doc.save(ignore_permissions=True)
        frappe.db.commit()

        # Add Student Group to the select_student_group MultiSelect Table field
        invoice.append("select_student_group", {
            "student_group": sg_doc.name
        })
        frappe.logger().info(f"Appended Student Group {sg_doc.name} to select_student_group table")
    else:
        frappe.log_error(f"❌ Sales Order {sales_order} has no custom_student_group", "Sales Invoice Link Failure")

    frappe.db.commit()
    return invoice.name

@frappe.whitelist()
def send_unpaid_student_notification(student_group_name, student_group_title, unpaid_students):
	"""Send email notification to Accounts User and Accounts Manager roles for unpaid students"""
	
	# Get users with Accounts User and Accounts Manager roles
	accounts_users = frappe.get_all(
		"Has Role",
		filters={"role": ["in", ["Accounts User", "Accounts Manager"]]},
		fields=["parent"]
	)
	
	if not accounts_users:
		return
	
	# Get email addresses
	email_addresses = []
	for user in accounts_users:
		email = frappe.db.get_value("User", user.parent, "email")
		if email:
			email_addresses.append(email)
	
	if not email_addresses:
		return
	
	# Prepare email content
	subject = f"Unpaid Students Alert - {student_group_title}"
	
	# Create HTML table for unpaid students
	unpaid_table = """
	<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
		<thead>
			<tr style="background-color: #f8f9fa;">
				<th>Roll Number</th>
				<th>Student ID</th>
				<th>Student Name</th>
			</tr>
		</thead>
		<tbody>
	"""
	
	for student in unpaid_students:
		unpaid_table += f"""
			<tr>
				<td>{student.get('group_roll_number', '')}</td>
				<td>{student.get('student', '')}</td>
				<td>{student.get('student_name', '')}</td>
			</tr>
		"""
	
	unpaid_table += """
		</tbody>
	</table>
	"""
	
	# Email body
	body = f"""
	<p>Dear Accounts Team,</p>
	
	<p>This is an automated notification regarding unpaid students in the Student Group: <strong>{student_group_title}</strong></p>
	
	<p>The following students have not been marked as invoiced:</p>
	
	{unpaid_table}
	
	<p><strong>Total Unpaid Students:</strong> {len(unpaid_students)}</p>
	
	<p>Please review and take necessary action to ensure proper invoicing.</p>
	
	<p>You can view the Student Group details by clicking the link below:</p>
	<p><a href="{get_url('/app/student-group/{0}'.format(student_group_name))}">View Student Group</a></p>
	
	<p>Best regards,<br>
	Numero Uno System</p>
	"""
	
	# Send email
	try:
		frappe.sendmail(
			recipients=email_addresses,
			subject=subject,
			message=body,
			now=True
		)
		
		# Log the notification
		frappe.logger().info(f"Unpaid student notification sent for Student Group: {student_group_name}")
		
	except Exception as e:
		frappe.logger().error(f"Failed to send unpaid student notification: {str(e)}")


def check_and_send_unpaid_notifications(doc, method):
	"""Check for unpaid students and send email notifications"""
	try:
		unpaid_students = []
		
		# Check if students exist and have the custom_invoiced field
		if hasattr(doc, 'students') and doc.students:
			for student in doc.students:
				# Check if custom_invoiced is False, 0, or None
				if not student.get("custom_invoiced"):
					unpaid_students.append({
						"student": student.student,
						"student_name": student.student_name,
						"group_roll_number": student.group_roll_number
					})
		
		if unpaid_students:
			# Log the event
			frappe.logger().info(f"Found {len(unpaid_students)} unpaid students in Student Group: {doc.name}")
			
			# Send email notification in background
			enqueue(
				"numerouno.numerouno.doctype.student_group.student_group.send_unpaid_student_notification",
				student_group_name=doc.name,
				student_group_title=doc.student_group_name,
				unpaid_students=unpaid_students,
				queue="short"
			)
			
			frappe.logger().info(f"Email notification queued for Student Group: {doc.name}")
		else:
			frappe.logger().info(f"No unpaid students found in Student Group: {doc.name}")
			
	except Exception as e:
		frappe.logger().error(f"Error in check_and_send_unpaid_notifications: {str(e)}")
		# Don't raise the exception to avoid breaking the save process


@frappe.whitelist()
def send_daily_unpaid_notifications():
	"""Send daily consolidated report of all unpaid students across all Student Groups"""
	
	# Ensure frappe is properly imported
	import frappe
	from frappe.utils import nowdate
	
	print("🔍 Starting send_daily_unpaid_notifications function")
	
	# Get all Student Groups with unpaid students
	unpaid_data = frappe.db.sql("""
		SELECT 
			sg.name as student_group_name,
			sg.student_group_name as student_group_title,
			sgs.student,
			sgs.student_name,
			sgs.group_roll_number,
			sg.program,
			sg.course
		FROM `tabStudent Group` sg
		JOIN `tabStudent Group Student` sgs ON sgs.parent = sg.name
		WHERE sgs.custom_invoiced = 0 OR sgs.custom_invoiced IS NULL
		ORDER BY sg.student_group_name, sgs.group_roll_number
	""", as_dict=True)
	
	print(f"📊 Found {len(unpaid_data)} unpaid students")
	
	if not unpaid_data:
		print("❌ No unpaid data found, returning early")
		return
	
	# Get users with Accounts User and Accounts Manager roles
	accounts_users = frappe.get_all(
		"Has Role",
		filters={"role": ["in", ["Accounts User", "Accounts Manager"]]},
		fields=["parent"]
	)
	
	print(f"👥 Found {len(accounts_users)} users with Accounts roles")
	
	if not accounts_users:
		print("❌ No accounts users found, returning early")
		return
	
	# Get email addresses
	email_addresses = []
	for user in accounts_users:
		email = frappe.db.get_value("User", user.parent, "email")
		if email:
			email_addresses.append(email)
	
	print(f"📧 Found {len(email_addresses)} email addresses: {email_addresses}")
	
	if not email_addresses:
		print("❌ No email addresses found, returning early")
		return
	
	# Prepare email content
	subject = f"Daily Unpaid Students Report - {nowdate()}"

	# Create summary
	total_unpaid = len(unpaid_data)
	unique_groups = len(set([row.student_group_name for row in unpaid_data]))

	print(f"📋 Preparing email with {total_unpaid} unpaid students from {unique_groups} groups")

	# Build HTML table for unpaid students (limit to first 100 for email size)
	table_rows = ""
	for i, row in enumerate(unpaid_data[:100]):  # Limit to first 100 rows
		table_rows += f"""
		<tr>
			<td>{row['student_group_title']}</td>
			<td>{row['student']}</td>
			<td>{row['student_name']}</td>
			<td>{row['program']}</td>
			<td>{row['course']}</td>
			<td>{row['group_roll_number']}</td>
			<td><a href="{frappe.utils.get_url('/app/student-group/' + row['student_group_name'])}">View Group</a></td>
		</tr>
		"""

	# Add note if there are more records
	additional_note = ""
	if total_unpaid > 100:
		additional_note = f"<p><em>Note: Showing first 100 records. Total unpaid students: {total_unpaid}</em></p>"

	body = f"""
	<p>Dear Accounts Team,</p>

	<p>This is your daily automated report of unpaid students across all Student Groups.</p>

	<div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
		<h3>Summary</h3>
		<p><strong>Total Student Groups with Unpaid Students:</strong> {unique_groups}</p>
		<p><strong>Total Unpaid Students:</strong> {total_unpaid}</p>
	</div>

	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%; margin-bottom: 20px;">
		<thead style="background-color: #e9ecef;">
			<tr>
				<th>Student Group</th>
				<th>Student ID</th>
				<th>Student Name</th>
				<th>Program</th>
				<th>Course</th>
				<th>Roll Number</th>
				<th>Link</th>
			</tr>
		</thead>
		<tbody>
			{table_rows}
		</tbody>
	</table>

	{additional_note}

	<p>Please review and take necessary action to ensure proper invoicing for all students.</p>

	<p>Best regards,<br>
	Numero Uno System</p>
	"""
	
	# Send email using multiple methods for reliability
	try:
		print(f"📤 Attempting to send email to: {email_addresses}")
		
		# Method 1: Try frappe.sendmail with now=True
		try:
			frappe.sendmail(
				recipients=email_addresses,
				subject=subject,
				message=body,
				now=True
			)
			print("✅ Email sent successfully using frappe.sendmail!")
			
		except Exception as e1:
			print(f"❌ frappe.sendmail failed: {str(e1)}")
			
			# Method 2: Try using Email Queue directly
			try:
				from frappe.email.doctype.email_queue.email_queue import QueueBuilder
				
				email_queue = frappe.new_doc("Email Queue")
				email_queue.recipients = ",".join(email_addresses)
				email_queue.subject = subject
				email_queue.message = body
				email_queue.status = "Not Sent"
				email_queue.insert()
				
				print(f"✅ Email queued successfully: {email_queue.name}")
				
			except Exception as e2:
				print(f"❌ Email queue method failed: {str(e2)}")
				
				# Method 3: Try using frappe.utils.email_lib
				try:
					import frappe.utils.email_lib
					
					frappe.utils.email_lib.sendmail(
						recipients=email_addresses,
						subject=subject,
						message=body
					)
					print("✅ Email sent successfully using frappe.utils.email_lib!")
					
				except Exception as e3:
					print(f"❌ frappe.utils.email_lib failed: {str(e3)}")
					raise Exception(f"All email methods failed. Last error: {str(e3)}")
		
		# Log the notification
		frappe.log_error(f"Daily unpaid student notification sent for {unique_groups} groups with {total_unpaid} unpaid students")
		
	except Exception as e:
		print(f"❌ Failed to send email: {str(e)}")
		frappe.log_error(f"Failed to send daily unpaid student notification: {str(e)}")
		
		# Try to flush email queue
		try:
			import frappe.utils.email_lib
			frappe.utils.email_lib.flush(from_test=True)
			print("📧 Email queue flushed")
		except Exception as flush_error:
			print(f"❌ Failed to flush email queue: {str(flush_error)}")


@frappe.whitelist()
def create_sales_order_for_purchase_order(doc, method):
    # Add debugging information
    frappe.logger().info(f"create_sales_order_from_student_group called for {doc.name}")
    frappe.logger().info(f"custom_mode_of_payment: {doc.custom_mode_of_payment}")
    frappe.logger().info(f"custom_sales_order: {doc.custom_sales_order}")
    frappe.logger().info(f"custom_customer_po_number: {doc.custom_customer_po_number}")
    
    sales_order_name = None
    if doc.custom_mode_of_payment == "PO":
        # Check if we need to create a new Sales Order
        should_create_so = False
        
        # Case 1: No existing Sales Order and has PO number
        if doc.custom_sales_order is None and doc.custom_customer_po_number is not None:
            should_create_so = True
            frappe.logger().info("Creating new Sales Order - no existing SO and has PO number")
        
        # Case 2: Has existing Sales Order but it doesn't exist in database (was deleted)
        elif doc.custom_sales_order is not None:
            try:
                existing_so = frappe.get_doc("Sales Order", doc.custom_sales_order)
                if not existing_so:
                    should_create_so = True
                    frappe.logger().info("Creating new Sales Order - existing SO was deleted")
            except frappe.DoesNotExistError:
                should_create_so = True
                frappe.logger().info("Creating new Sales Order - existing SO doesn't exist")
        
        if should_create_so and doc.custom_customer_po_number is not None:
            try:
                course_rate = frappe.db.get_value("Course", doc.course, "custom_course_rate")
                if not course_rate:
                    frappe.logger().error(f"No course rate found for course: {doc.course}")
                    return
                
                # create a sales order from the student group
                sales_order = frappe.new_doc("Sales Order")
                sales_order.customer = doc.custom_customer
                sales_order.delivery_date = doc.to_date
                sales_order.po_no = doc.custom_customer_po_number
                
                # Add link back to Student Group
                sales_order.custom_student_group = doc.name
                
                sales_order.append("items", {
                    "item_code": doc.course,
                    "qty": len(doc.students),
                    "rate": course_rate
                })

                sales_order.append("taxes",{
                     "charge_type":"On Net Total",
                     "account_head":"VAT 5% - NUTC",
                     "description":"VAT 5%",
                     "rate":5,
                     "cost_center":"Main - NUTC",
                })
                
                # Insert the Sales Order
                sales_order.insert()
                sales_order.submit()
                frappe.logger().info(f"Sales Order inserted: {sales_order.name}")
                
                # Set the field value directly instead of calling doc.save()
                doc.custom_sales_order = sales_order.name
                frappe.logger().info(f"Set custom_sales_order to: {sales_order.name}")
                
                # Verify the Sales Order exists
                try:
                    verify_so = frappe.get_doc("Sales Order", sales_order.name)
                    frappe.logger().info(f"Verified Sales Order exists: {verify_so.name}")
                except Exception as verify_error:
                    frappe.logger().error(f"Failed to verify Sales Order: {str(verify_error)}")
                sales_order_name = sales_order.name
            except Exception as e:
                frappe.logger().error(f"Error creating Sales Order: {str(e)}")
                frappe.throw(f"Error creating Sales Order: {str(e)}")
        else:
            # Use the existing sales order if it exists
            sales_order_name = doc.custom_sales_order
            frappe.logger().info(f"Using existing Sales Order: {sales_order_name}")

    # Now, only call the invoice/payment function if you have a valid sales_order_name
    if getattr(doc, "custom_create_payment", 0) == 1 and sales_order_name:
        create_sales_invoice_for_purchase_order(doc, sales_order_name)


def create_sales_invoice_for_purchase_order(doc, sales_order_name):
    if doc.custom_create_payment == 1:
        # Create Sales Invoice from Sales Order
        from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
        sales_invoice = make_sales_invoice(sales_order_name)
        sales_invoice.due_date = doc.to_date
        sales_invoice.posting_date = frappe.utils.today()
        # Fetch students as the button would do
        students_data = fetch_students_from_sg(sales_invoice.customer, [doc.name])

        # If fetch_students_from_sg returns a Frappe Response object, get the data
        if hasattr(students_data, 'get') and callable(students_data.get):
            students_data = students_data.get('message', students_data)

        # Add students to the child table
        for student in students_data:
            sales_invoice.append("student", {
                "student": student["student"],
                "student_name": student["student_name"],
                # add other fields as needed
            })
        print(f"Fetched and added {len(students_data)} students to Sales Invoice")
        sales_invoice.insert()
        sales_invoice.submit()
        # SAVE THE SALES INVOICE NAME TO THE STUDENT GROUP FIELD custom_sales_invoice
        frappe.logger().info(f"Sales Invoice {sales_invoice.name} created and submitted.")
        doc.custom_sales_invoice = sales_invoice.name

        # Create Payment Entry against the Sales Invoice
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
        try:
            payment_entry = get_payment_entry("Sales Invoice", sales_invoice.name)
            payment_entry.posting_date = frappe.utils.today()
            payment_entry.reference_no = f"PO-{doc.name}"
            payment_entry.reference_date = frappe.utils.today()
            payment_entry.custom_student_group = doc.name  # if you have this custom field

            payment_entry.insert()
            payment_entry.submit()
            frappe.logger().info(f"Payment Entry {payment_entry.name} created and submitted against Sales Invoice {sales_invoice.name}")

            # Optionally, link the Payment Entry to the Student Group
            doc.custom_payment_entry = payment_entry.name

        except Exception as e:
            print(f"Error creating Payment Entry: {str(e)}")


@frappe.whitelist()
def create_sales_order_for_advance_payment(doc, method):
    sales_order_name = None

    if doc.custom_mode_of_payment == "PO (Advance Payment)":
        should_create_so = False

        # Case 1: No existing Sales Order and has PO number
        if doc.custom_sales_order is None and doc.custom_customer_po_number is not None:
            should_create_so = True

        # Case 2: Has existing Sales Order but it doesn't exist in database (was deleted)
        elif doc.custom_sales_order is not None:
            try:
                existing_so = frappe.get_doc("Sales Order", doc.custom_sales_order)
                if not existing_so:
                    should_create_so = True
                    frappe.logger().info("Creating new Sales Order - existing SO was deleted")
            except frappe.DoesNotExistError:
                should_create_so = True
                frappe.logger().info("Creating new Sales Order - existing SO doesn't exist")

        if should_create_so and doc.custom_customer_po_number is not None:
            try:
                course_rate = frappe.db.get_value("Course", doc.course, "custom_course_rate")
                if not course_rate:
                    frappe.logger().error(f"No course rate found for course: {doc.course}")
                    return

                # create a sales order from the student group
                sales_order = frappe.new_doc("Sales Order")
                sales_order.customer = doc.custom_customer
                sales_order.delivery_date = doc.to_date
                sales_order.po_no = doc.custom_customer_po_number
                sales_order.custom_student_group = doc.name
                sales_order.append("items", {
                    "item_code": doc.course,
                    "qty": len(doc.students),
                    "rate": course_rate
                })
                sales_order.append("taxes", {
                    "charge_type": "On Net Total",
                    "account_head": "VAT 5% - NUTC",
                    "description": "VAT 5%",
                    "rate": 5,
                    "cost_center": "Main - NUTC",
                })
                sales_order.insert()
                sales_order.submit()
                frappe.logger().info(f"Sales Order inserted: {sales_order.name}")
                doc.custom_sales_order = sales_order.name
                sales_order_name = sales_order.name
            except Exception as e:
                frappe.logger().error(f"Error creating Sales Order: {str(e)}")
                frappe.throw(f"Error creating Sales Order: {str(e)}")
        else:
            sales_order_name = doc.custom_sales_order
            frappe.logger().info(f"Using existing Sales Order: {sales_order_name}")

    # Now, only call the payment/invoice function if you have a valid sales_order_name
    if getattr(doc, "custom_create_payment", 0) == 1 and sales_order_name:
        create_advance_payment_and_invoice(doc, sales_order_name)


def create_advance_payment_and_invoice(doc, sales_order_name):
    # 1. Create Payment Entry against the Sales Order
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    try:
        payment_entry = get_payment_entry("Sales Order", sales_order_name)
        payment_entry.posting_date = frappe.utils.today()
        payment_entry.reference_no = f"ADV-{doc.name}"
        payment_entry.reference_date = frappe.utils.today()
        payment_entry.custom_student_group = doc.name  # if you have this custom field

        payment_entry.insert()
        payment_entry.submit()
        frappe.logger().info(f"Payment Entry {payment_entry.name} created and submitted against Sales Order {sales_order_name}")
        doc.custom_payment_entry = payment_entry.name
    except Exception as e:
        frappe.logger().error(f"Error creating Payment Entry: {str(e)}")
        return

    # 2. Create Sales Invoice from Sales Order
    from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
    sales_invoice = make_sales_invoice(sales_order_name)
    sales_invoice.due_date = doc.to_date
    sales_invoice.posting_date = frappe.utils.today()

    # Fetch students as the button would do
    students_data = fetch_students_from_sg(sales_invoice.customer, [doc.name])
    if hasattr(students_data, 'get') and callable(students_data.get):
        students_data = students_data.get('message', students_data)
    for student in students_data:
        sales_invoice.append("student", {
            "student": student["student"],
            "student_name": student["student_name"],
        })
    sales_invoice.allocate_advances_automatically = 1
    sales_invoice.only_include_allocated_payments = 1
    print(f"Fetched and added {len(students_data)} students to Sales Invoice")

    sales_invoice.insert()
    sales_invoice.submit()
    frappe.logger().info(f"Sales Invoice {sales_invoice.name} created and submitted.")
    doc.custom_sales_invoice = sales_invoice.name


@frappe.whitelist()
def create_sales_invoice_for_cash_payment(doc, method):

    if doc.custom_mode_of_payment == "Cash Payment" and doc.custom_create_payment == 1:
        # Check if we need to create a new Sales Invoice
        should_create_si = False
        
        # Case 1: No existing Sales Invoice
        if doc.custom_sales_invoice is None:
            should_create_si = True
            frappe.logger().info("Creating new Sales Invoice for Cash Payment")
        
        # Case 2: Has existing Sales Invoice but it doesn't exist in database (was deleted)
        elif doc.custom_sales_invoice is not None:
            try:
                existing_si = frappe.get_doc("Sales Invoice", doc.custom_sales_invoice)
                if not existing_si:
                    should_create_si = True
                    frappe.logger().info("Creating new Sales Invoice - existing SI was deleted")
            except frappe.DoesNotExistError:
                should_create_si = True
                frappe.logger().info("Creating new Sales Invoice - existing SI doesn't exist")
        
        if should_create_si:
            try:
                # First, ensure the Student Group is saved to get a proper name
                if not doc.name or doc.name.startswith('New'):
                    frappe.logger().info("Student Group not yet saved, saving first...")
                    doc.save()
                    frappe.logger().info(f"Student Group saved with name: {doc.name}")
                
                course_rate = frappe.db.get_value("Course", doc.course, "custom_course_rate")
                if not course_rate:
                    frappe.logger().error(f"No course rate found for course: {doc.course}")
                    return
                
                # First create a Sales Order (required for items that mandate Sales Order)
                sales_order = frappe.new_doc("Sales Order")
                sales_order.customer = doc.custom_customer
                sales_order.delivery_date = doc.to_date
                sales_order.posting_date = frappe.utils.today()
                
                # Add link back to Student Group (now it has a proper name)
                sales_order.custom_student_group = doc.name
                
                # Add items
                sales_order.append("items", {
                    "item_code": doc.course,
                    "qty": len(doc.students),
                    "rate": course_rate
                })
                
                # Add taxes
                sales_order.append("taxes", {
                    "charge_type": "On Net Total",
                    "account_head": "VAT 5% - NUTC",
                    "description": "VAT 5%",
                    "rate": 5,
                    "cost_center": "Main - NUTC",
                })
                
                # Insert and submit the Sales Order
                sales_order.insert()
                sales_order.submit()
                frappe.logger().info(f"Sales Order inserted: {sales_order.name}")
                
                # Set the Sales Order field
                doc.custom_sales_order = sales_order.name
                frappe.logger().info(f"Set custom_sales_order to: {sales_order.name}")
                
                # Now create Sales Invoice from the Sales Order
                from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
                
                sales_invoice = make_sales_invoice(sales_order.name)
                sales_invoice.due_date = doc.to_date
                sales_invoice.posting_date = frappe.utils.today()
                sales_invoice.append("select_student_group", {
                    "student_group": doc.name
                })
                print(f"Added {doc.name} to select_student_group child table")
                
                # Fetch students as the button would do
                students_data = fetch_students_from_sg(sales_invoice.customer, [doc.name])

                # If fetch_students_from_sg returns a Frappe Response object, get the data
                if hasattr(students_data, 'get') and callable(students_data.get):
                    students_data = students_data.get('message', students_data)

                # Add students to the child table
                for student in students_data:
                    sales_invoice.append("student", {
                        "student": student["student"],
                        "student_name": student["student_name"],
                        # add other fields as needed
                    })
                print(f"Fetched and added {len(students_data)} students to Sales Invoice")
                
                # Insert the Sales Invoice (don't submit for now)
                sales_invoice.insert()
                sales_invoice.submit()
                print(f"Sales Invoice {sales_invoice.name} inserted and submitted.")

                # Create Payment Entry against the Sales Invoice
                from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

                try:
                    payment_entry = get_payment_entry("Sales Invoice", sales_invoice.name)
                    payment_entry.posting_date = frappe.utils.today()
                    payment_entry.reference_no = f"CASH-{doc.name}"
                    payment_entry.reference_date = frappe.utils.today()
                    payment_entry.custom_student_group = doc.name  # if you have this custom field

                    # Insert and submit the Payment Entry
                    payment_entry.insert()
                    payment_entry.submit()
                    print(f"Payment Entry {payment_entry.name} created and submitted against Sales Invoice {sales_invoice.name}")

                    # Optionally, link the Payment Entry to the Student Group
                    doc.custom_payment_entry = payment_entry.name

                except Exception as e:
                    print(f"Error creating Payment Entry: {str(e)}")
                
                # Set the Sales Invoice field
                doc.custom_sales_invoice = sales_invoice.name
                frappe.logger().info(f"Set custom_sales_invoice to: {sales_invoice.name}")
                
                # Don't create Payment Entry for now
                frappe.logger().info("Skipping Payment Entry creation as requested")
                
            except Exception as e:
                frappe.logger().error(f"Error creating Sales Invoice: {str(e)}")
                frappe.throw(f"Error creating Sales Invoice: {str(e)}")
        else:
            frappe.logger().info("No Sales Invoice created - conditions not met")


def create_payment_entry_for_sales_invoice(sales_invoice, student_group_doc):
    """Create a Payment Entry against a Sales Invoice"""
    try:
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
        
        # Get the payment entry template
        payment_entry = get_payment_entry("Sales Invoice", sales_invoice.name)
        
        # Get default accounts
        paid_from = get_default_receivable_account()
        paid_to = get_default_cash_account()
        
        if not paid_from or not paid_to:
            frappe.logger().error("Default accounts not found. Cannot create Payment Entry.")
            frappe.throw("Default accounts not configured. Please set up default receivable and cash accounts in Company settings.")
        
        # Set payment details
        payment_entry.payment_type = "Receive"
        payment_entry.party_type = "Customer"
        payment_entry.party = sales_invoice.customer
        payment_entry.paid_amount = sales_invoice.grand_total
        payment_entry.received_amount = sales_invoice.grand_total
        payment_entry.paid_from = paid_from
        payment_entry.paid_to = paid_to
        payment_entry.reference_no = f"CASH-{student_group_doc.name}"
        payment_entry.reference_date = frappe.utils.today()
        
        # Set posting date
        payment_entry.posting_date = frappe.utils.today()
        
        # Add reference to Student Group
        payment_entry.custom_student_group = student_group_doc.name
        
        # Insert and submit the Payment Entry
        payment_entry.insert()
        payment_entry.submit()
        
        frappe.logger().info(f"Payment Entry {payment_entry.name} created and submitted")
        return payment_entry.name
        
    except Exception as e:
        frappe.logger().error(f"Error creating Payment Entry: {str(e)}")
        frappe.throw(f"Error creating Payment Entry: {str(e)}")
        return None


def create_manual_payment_entry_for_draft_invoice(sales_invoice, student_group_doc):
    """Create a manual Payment Entry for a draft Sales Invoice"""
    try:
        # Get default accounts
        paid_from = get_default_receivable_account()
        paid_to = get_default_cash_account()
        
        if not paid_from or not paid_to:
            frappe.logger().error("Default accounts not found. Cannot create Payment Entry.")
            frappe.throw("Default accounts not configured. Please set up default receivable and cash accounts in Company settings.")
        
        # Create a new Payment Entry
        payment_entry = frappe.new_doc("Payment Entry")
        
        # Set payment details
        payment_entry.payment_type = "Receive"
        payment_entry.party_type = "Customer"
        payment_entry.party = sales_invoice.customer
        payment_entry.paid_amount = sales_invoice.grand_total
        payment_entry.received_amount = sales_invoice.grand_total
        payment_entry.paid_from = paid_from
        payment_entry.paid_to = paid_to
        payment_entry.reference_no = f"CASH-{student_group_doc.name}"
        payment_entry.reference_date = frappe.utils.today()
        
        # Set posting date
        payment_entry.posting_date = frappe.utils.today()
        
        # Add reference to Student Group
        payment_entry.custom_student_group = student_group_doc.name
        
        # Add reference to Sales Invoice (even though it's draft)
        payment_entry.append("references", {
            "reference_doctype": "Sales Invoice",
            "reference_name": sales_invoice.name,
            "total_amount": sales_invoice.grand_total,
            "outstanding_amount": sales_invoice.grand_total,
            "allocated_amount": sales_invoice.grand_total
        })
        
        # Insert and submit the Payment Entry
        payment_entry.insert()
        payment_entry.submit()
        
        frappe.logger().info(f"Manual Payment Entry {payment_entry.name} created and submitted")
        return payment_entry.name
        
    except Exception as e:
        frappe.logger().error(f"Error creating manual Payment Entry: {str(e)}")
        frappe.throw(f"Error creating manual Payment Entry: {str(e)}")
        return None
    

@frappe.whitelist()
def create_sales_order_from_student_group(doc, method):
    """
    Create separate sales orders for each customer and mode of payment combination.
    If there are 2 customers, create 2 sales orders.
    If a customer has multiple payment modes, create separate orders for each mode.
    """
    try:
        print(f"=== Starting create_sales_order_from_student_group for {doc.name} ===")
        
        if not doc.students:
            frappe.msgprint(_("No students found in this Student Group"))
        
        print(f"Found {len(doc.students)} students in Student Group")
        
        # Get course rate
        course_rate = frappe.db.get_value("Course", doc.course, "custom_course_rate")
        if not course_rate:
            frappe.msgprint(_("No course rate found for course: {0}").format(doc.course))
        
        print(f"Course rate: {course_rate}")
        
        # Group students by customer and payment mode
        customer_payment_groups = {}
        students_with_orders = 0
        students_without_orders = 0
        
        for row in doc.students:
            print(f"Processing student: {row.student}, custom_sales_order: {row.custom_sales_order}")
            
            if not row.custom_sales_order:  # Only process students without sales orders
                students_without_orders += 1
                customer = row.customer_name or doc.custom_customer
                payment_mode = row.custom_mode_of_payment or "Cash Payment"  # Default to Cash Payment
                
                print(f"Student {row.student}: customer={customer}, payment_mode={payment_mode}")
                
                if not customer:
                    frappe.msgprint(f"Student {row.student} has no customer assigned")
                    continue
                
                # Create key for grouping: (customer, payment_mode)
                group_key = (customer, payment_mode)
                
                if group_key not in customer_payment_groups:
                    customer_payment_groups[group_key] = {
                        'customer': customer,
                        'payment_mode': payment_mode,
                        'students': [],
                        'po_numbers': set()  # Track unique PO numbers
                    }
                
                customer_payment_groups[group_key]['students'].append(row)
                
                # Collect PO numbers if available
                if row.customer_purchase_order:
                    customer_payment_groups[group_key]['po_numbers'].add(row.customer_purchase_order)
            else:
                students_with_orders += 1
        
        print(f"Students with orders: {students_with_orders}, Students without orders: {students_without_orders}")
        print(f"Customer payment groups: {len(customer_payment_groups)}")
        
        created_orders = []
        
        # Create sales order for each customer-payment mode combination
        for (customer, payment_mode), group_data in customer_payment_groups.items():
            try:
                print(f"Creating Sales Order for customer: {customer}, payment_mode: {payment_mode}, students: {len(group_data['students'])}")
                
                # Try to find an existing Sales Order for this group, customer, payment mode, and course
                existing_so = frappe.get_all(
                    "Sales Order",
                    filters={
                        "customer": customer,
                        "custom_mode_of_payment": payment_mode,
                        "custom_student_group": doc.name,
                        "docstatus": ["!=", 2],  # not cancelled
                    },
                    fields=["name"]
                )

                if existing_so:
                    # Update the existing Sales Order
                    so = frappe.get_doc("Sales Order", existing_so[0].name)
                    so.custom_mode_of_payment = payment_mode  # <-- Add this line to ensure it is updated!
                    # Find the item row for this course
                    for item in so.items:
                        if item.item_code == doc.course:
                            item.qty += len(group_data['students'])
                            item.description = f"Course: {doc.course} for {item.qty} students"
                            break
                    else:
                        # If not found, add a new item row
                        so.append("items", {
                            "item_code": doc.course,
                            "qty": len(group_data['students']),
                            "rate": course_rate,
                            "description": f"Course: {doc.course} for {len(group_data['students'])} students"
                        })
                    so.save()
                    sales_order = so
                else:
                    # ... your existing code to create a new Sales Order ...
                    sales_order = frappe.new_doc("Sales Order")
                    # ... rest of your creation logic ...
                    sales_order.customer = customer
                    sales_order.delivery_date = doc.to_date
                    sales_order.posting_date = frappe.utils.today()
                    sales_order.custom_mode_of_payment = payment_mode  # <-- Make sure this line is present!
                    
                    # Set PO number if available (use first one if multiple)
                    if group_data['po_numbers']:
                        sales_order.po_no = list(group_data['po_numbers'])[0]
                    
                    # Add link back to Student Group
                    sales_order.custom_student_group = doc.name
                    
                    # Add item details
                    sales_order.append("items", {
                        "item_code": doc.course,
                        "qty": len(group_data['students']),
                        "rate": course_rate,
                        "description": f"Course: {doc.course} for {len(group_data['students'])} students"
                    })
                    
                    # Add taxes
                    sales_order.append("taxes", {
                        "charge_type": "On Net Total",
                        "account_head": "VAT 5% - NUTC",
                        "description": "VAT 5%",
                        "rate": 5,
                        "cost_center": "Main - NUTC",
                    })
                    
                    # Insert and submit the Sales Order
                    sales_order.insert()
                
                print(f"Sales Order {sales_order.name} created for customer {customer} with payment mode {payment_mode}")
                created_orders.append({
                    'sales_order': sales_order.name,
                    'customer': customer,
                    'payment_mode': payment_mode,
                    'student_count': len(group_data['students'])
                })
                
                # Update student records with the sales order reference
                for student_row in group_data['students']:
                    # Update the student row in the child table
                    frappe.db.set_value(
                        "Student Group Student",
                        student_row.name,
                        "custom_sales_order",
                        sales_order.name
                    )
                    # Update in-memory doc for immediate UI feedback (if returned)
                    student_row.custom_sales_order = sales_order.name
                
                # Commit the changes to ensure they are saved
                frappe.db.commit()
                
            except Exception as e:
                print(f"Error creating Sales Order for customer {customer}, payment mode {payment_mode}: {str(e)}")
                frappe.throw(f"Error creating Sales Order for customer {customer}: {str(e)}")
        
        # Show success message
        if created_orders:
            message = f"✅ Created {len(created_orders)} Sales Order(s):\n"
            for order in created_orders:
                message += f"• {order['sales_order']} for {order['customer']} ({order['payment_mode']}) - {order['student_count']} students\n"
            
            frappe.msgprint(message)
            print(f"Successfully created {len(created_orders)} sales orders")
        else:
            frappe.msgprint("No Sales Orders created - all students already have sales orders")
            print("No sales orders created - all students already have sales orders")
            
    except Exception as e:
        print(f"Error in create_sales_order_from_student_group: {str(e)}")
        frappe.throw(f"Error creating Sales Orders: {str(e)}")


@frappe.whitelist()
def check_email_configuration():
	"""Check and fix email configuration"""
	
	print("🔧 Checking Email Configuration...")
	
	try:
		# Check Email Settings
		email_settings = frappe.get_doc("Email Settings")
		print(f"   - SMTP Server: {email_settings.smtp_server}")
		print(f"   - SMTP Port: {email_settings.smtp_port}")
		print(f"   - Login: {email_settings.login}")
		print(f"   - Use SSL: {email_settings.use_ssl}")
		print(f"   - Always use account settings: {email_settings.always_use_account_settings}")
		
		# Check System Settings
		system_settings = frappe.get_doc("System Settings")
		print(f"   - System email: {system_settings.mail_login}")
		print(f"   - System email password: {'Set' if system_settings.mail_password else 'Not set'}")
		
		# Check if email is properly configured
		if not email_settings.smtp_server:
			print("❌ SMTP server not configured")
			return False
		
		if not email_settings.login:
			print("❌ Email login not configured")
			return False
		
		# Test email sending
		print("🧪 Testing email sending...")
		try:
			frappe.sendmail(
				recipients=["test@example.com"],
				subject="Test Email",
				message="This is a test email",
				now=True
			)
			print("✅ Test email sent successfully!")
			return True
		except Exception as e:
			print(f"❌ Test email failed: {str(e)}")
			return False
			
	except Exception as e:
		print(f"❌ Error checking email configuration: {str(e)}")
		return False


@frappe.whitelist()
def flush_email_queue():
	"""Flush the email queue to send pending emails"""
	
	print("📧 Flushing Email Queue...")
	
	try:
		import frappe.utils.email_lib
		frappe.utils.email_lib.flush(from_test=True)
		print("✅ Email queue flushed successfully!")
		
		# Check remaining emails
		pending_emails = frappe.db.sql("""
			SELECT COUNT(*) as count 
			FROM `tabEmail Queue` 
			WHERE status = 'Not Sent'
		""", as_dict=True)
		
		print(f"📊 Remaining pending emails: {pending_emails[0]['count'] if pending_emails else 0}")
		
		return True
		
	except Exception as e:
		print(f"❌ Failed to flush email queue: {str(e)}")
		return False


@frappe.whitelist()
def send_test_email(recipient_email):
	"""Send a test email to verify email configuration"""
	
	print(f"🧪 Sending test email to: {recipient_email}")
	
	try:
		frappe.sendmail(
			recipients=[recipient_email],
			subject="Test Email from Numero Uno System",
			message="""
			<p>This is a test email from the Numero Uno System.</p>
			<p>If you receive this email, the email configuration is working correctly.</p>
			<p>Best regards,<br>Numero Uno System</p>
			""",
			now=True
		)
		
		print("✅ Test email sent successfully!")
		return {"status": "success", "message": "Test email sent successfully!"}
		
	except Exception as e:
		print(f"❌ Test email failed: {str(e)}")
		return {"status": "error", "message": str(e)}