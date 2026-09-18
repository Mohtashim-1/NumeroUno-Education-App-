import frappe
from frappe import _
from frappe.utils import flt, getdate, today, add_days, date_diff
import json
from collections import defaultdict

RATING_FIELDS = [
	"joining_instructions_clear",
	"training_room_environment",
	"administration_support",
	"objectives_clearly_defined",
	"content_organization",
	"materials_aligned",
	"course_pace",
	"presentation_skills",
	"teaching_effectiveness",
	"knowledge_accessibility",
	"assignments_exercises",
	"handouts_tools_equipment",
	"technology_effectiveness",
]

LEGACY_RATING_SCORES = {"Excellent": 4, "Good": 3, "Average": 2, "Poor": 1}


def rating_to_score_4(value):
	if value is None or value == "":
		return None
	if isinstance(value, str):
		if value in LEGACY_RATING_SCORES:
			return float(LEGACY_RATING_SCORES[value])
		value = flt(value)
	else:
		value = flt(value)
	if value <= 0:
		return None
	if value <= 1:
		return flt(value * 4, 4)
	if value <= 5:
		return flt(value * 4 / 5, 4)
	return value


def rating_performance_bucket(value):
	score = rating_to_score_4(value)
	if score is None:
		return None
	if score >= 3.5:
		return "excellent"
	if score >= 2.5:
		return "good"
	if score >= 1.5:
		return "average"
	return "poor"


def document_average_rating_4(doc, fields=None):
	fields = fields or RATING_FIELDS
	scores = [rating_to_score_4(doc.get(field)) for field in fields]
	scores = [s for s in scores if s is not None]
	if not scores:
		return None
	return flt(sum(scores) / len(scores), 2)


@frappe.whitelist()
def get_course_evaluation_kpis():
	"""Get KPI data for Course Evaluation Dashboard"""
	
	# Total Evaluations
	total_evaluations = frappe.db.count("Course Evaluation", {"docstatus": ["!=", 2]})
	
	# Submitted Evaluations
	submitted_evaluations = frappe.db.count("Course Evaluation", {"docstatus": 1})
	
	# Draft Evaluations
	draft_evaluations = frappe.db.count("Course Evaluation", {"docstatus": 0})
	
	# Get all evaluation data for calculations
	evaluations = frappe.get_all(
		"Course Evaluation",
		filters={"docstatus": 1},
		fields=[
			"joining_instructions_clear", "training_room_environment", "administration_support",
			"objectives_clearly_defined", "content_organization", "materials_aligned", "course_pace",
			"presentation_skills", "teaching_effectiveness", "knowledge_accessibility", "assignments_exercises",
			"handouts_tools_equipment", "technology_effectiveness",
			"skills_improve_job_performance", "recommend_course", "course_duration"
		]
	)
	
	# Calculate average ratings
	rating_fields = [
		"joining_instructions_clear", "training_room_environment", "administration_support",
		"objectives_clearly_defined", "content_organization", "materials_aligned", "course_pace",
		"presentation_skills", "teaching_effectiveness", "knowledge_accessibility", "assignments_exercises",
		"handouts_tools_equipment", "technology_effectiveness"
	]
	
	total_ratings = 0
	total_score = 0
	excellent_count = 0
	good_count = 0
	average_count = 0
	poor_count = 0
	
	for eval in evaluations:
		for field in RATING_FIELDS:
			score = rating_to_score_4(eval.get(field))
			if score is None:
				continue
			total_score += score
			total_ratings += 1
			bucket = rating_performance_bucket(eval.get(field))
			if bucket == "excellent":
				excellent_count += 1
			elif bucket == "good":
				good_count += 1
			elif bucket == "average":
				average_count += 1
			elif bucket == "poor":
				poor_count += 1
	
	# Calculate averages
	average_rating = flt(total_score / total_ratings, 2) if total_ratings > 0 else 0
	excellent_percentage = flt((excellent_count / total_ratings * 100), 2) if total_ratings > 0 else 0
	good_percentage = flt((good_count / total_ratings * 100), 2) if total_ratings > 0 else 0
	
	# Unique courses evaluated
	unique_courses = frappe.db.sql("""
		SELECT COUNT(DISTINCT course_name) as count
		FROM `tabCourse Evaluation`
		WHERE docstatus = 1 AND course_name IS NOT NULL
	""", as_dict=True)[0].count or 0
	
	# Unique instructors evaluated
	unique_instructors = frappe.db.sql("""
		SELECT COUNT(DISTINCT instructor_name) as count
		FROM `tabCourse Evaluation`
		WHERE docstatus = 1 AND instructor_name IS NOT NULL
	""", as_dict=True)[0].count or 0
	
	# Training Impact Metrics
	improve_job_yes = frappe.db.count("Course Evaluation", {
		"skills_improve_job_performance": "Yes",
		"docstatus": 1
	})
	recommend_yes = frappe.db.count("Course Evaluation", {
		"recommend_course": "Yes",
		"docstatus": 1
	})
	
	improve_job_percentage = flt((improve_job_yes / submitted_evaluations * 100), 2) if submitted_evaluations > 0 else 0
	recommend_percentage = flt((recommend_yes / submitted_evaluations * 100), 2) if submitted_evaluations > 0 else 0
	
	# Recent evaluations (last 30 days)
	recent_evaluations = frappe.db.count("Course Evaluation", {
		"docstatus": 1,
		"creation": [">=", add_days(today(), -30)]
	})
	
	average_percentage = flt((average_count / total_ratings * 100), 2) if total_ratings > 0 else 0
	poor_percentage = flt((poor_count / total_ratings * 100), 2) if total_ratings > 0 else 0
	
	return {
		"total_evaluations": total_evaluations,
		"submitted_evaluations": submitted_evaluations,
		"draft_evaluations": draft_evaluations,
		"average_rating": average_rating,
		"excellent_percentage": excellent_percentage,
		"good_percentage": good_percentage,
		"unique_courses": unique_courses,
		"unique_instructors": unique_instructors,
		"improve_job_percentage": improve_job_percentage,
		"recommend_percentage": recommend_percentage,
		"recent_evaluations": recent_evaluations,
		"rating_distribution": {
			"excellent": excellent_count,
			"good": good_count,
			"average": average_count,
			"poor": poor_count
		}
	}


@frappe.whitelist()
def get_detailed_metrics():
	"""Get detailed breakdown metrics"""
	evaluations = frappe.get_all(
		"Course Evaluation",
		filters={"docstatus": 1},
		fields=[
			"joining_instructions_clear", "training_room_environment", "administration_support",
			"objectives_clearly_defined", "content_organization", "materials_aligned", "course_pace",
			"presentation_skills", "teaching_effectiveness", "knowledge_accessibility", "assignments_exercises",
			"handouts_tools_equipment", "technology_effectiveness",
			"skills_improve_job_performance", "recommend_course", "course_duration"
		]
	)
	
	rating_fields = [
		"joining_instructions_clear", "training_room_environment", "administration_support",
		"objectives_clearly_defined", "content_organization", "materials_aligned", "course_pace",
		"presentation_skills", "teaching_effectiveness", "knowledge_accessibility", "assignments_exercises",
		"handouts_tools_equipment", "technology_effectiveness"
	]
	
	excellent_count = 0
	good_count = 0
	average_count = 0
	poor_count = 0
	total_ratings = 0
	
	for eval in evaluations:
		for field in RATING_FIELDS:
			if rating_to_score_4(eval.get(field)) is None:
				continue
			total_ratings += 1
			bucket = rating_performance_bucket(eval.get(field))
			if bucket == "excellent":
				excellent_count += 1
			elif bucket == "good":
				good_count += 1
			elif bucket == "average":
				average_count += 1
			elif bucket == "poor":
				poor_count += 1
	
	excellent_percentage = flt((excellent_count / total_ratings * 100), 2) if total_ratings > 0 else 0
	good_percentage = flt((good_count / total_ratings * 100), 2) if total_ratings > 0 else 0
	average_percentage = flt((average_count / total_ratings * 100), 2) if total_ratings > 0 else 0
	poor_percentage = flt((poor_count / total_ratings * 100), 2) if total_ratings > 0 else 0
	
	# Training Impact
	improve_job_yes = sum(1 for e in evaluations if e.get("skills_improve_job_performance") == "Yes")
	improve_job_no = sum(1 for e in evaluations if e.get("skills_improve_job_performance") == "No")
	improve_job_maybe = sum(1 for e in evaluations if e.get("skills_improve_job_performance") == "Maybe")
	recommend_yes = sum(1 for e in evaluations if e.get("recommend_course") == "Yes")
	
	# Duration
	duration_about_right = sum(1 for e in evaluations if e.get("course_duration") == "About Right")
	duration_too_long = sum(1 for e in evaluations if e.get("course_duration") == "Too Long")
	duration_short = sum(1 for e in evaluations if e.get("course_duration") == "Short")
	
	return {
		"excellent_count": excellent_count,
		"good_count": good_count,
		"average_count": average_count,
		"poor_count": poor_count,
		"excellent_percentage": excellent_percentage,
		"good_percentage": good_percentage,
		"average_percentage": average_percentage,
		"poor_percentage": poor_percentage,
		"improve_job_yes": improve_job_yes,
		"improve_job_no": improve_job_no,
		"improve_job_maybe": improve_job_maybe,
		"recommend_yes": recommend_yes,
		"duration_about_right": duration_about_right,
		"duration_too_long": duration_too_long,
		"duration_short": duration_short
	}


@frappe.whitelist()
def get_rating_distribution():
	"""Get rating distribution data for chart"""
	rating_fields = [
		"joining_instructions_clear", "training_room_environment", "administration_support",
		"objectives_clearly_defined", "content_organization", "materials_aligned", "course_pace",
		"presentation_skills", "teaching_effectiveness", "knowledge_accessibility", "assignments_exercises",
		"handouts_tools_equipment", "technology_effectiveness"
	]
	
	evaluations = frappe.get_all(
		"Course Evaluation",
		filters={"docstatus": 1},
		fields=rating_fields
	)
	
	excellent = 0
	good = 0
	average = 0
	poor = 0
	
	for eval in evaluations:
		for field in RATING_FIELDS:
			bucket = rating_performance_bucket(eval.get(field))
			if bucket == "excellent":
				excellent += 1
			elif bucket == "good":
				good += 1
			elif bucket == "average":
				average += 1
			elif bucket == "poor":
				poor += 1
	
	return {
		"labels": ["Excellent", "Good", "Average", "Poor"],
		"datasets": [{
			"name": "Ratings",
			"values": [excellent, good, average, poor]
		}]
	}


@frappe.whitelist()
def get_evaluations_over_time():
	"""Get evaluations over time for time series chart"""
	from frappe.utils import get_first_day, get_last_day, add_months
	
	# Get last 12 months
	data = []
	labels = []
	
	for i in range(11, -1, -1):
		month_start = get_first_day(add_months(today(), -i))
		month_end = get_last_day(add_months(today(), -i))
		
		count = frappe.db.count("Course Evaluation", {
			"docstatus": 1,
			"creation": ["between", [month_start, month_end]]
		})
		
		labels.append(month_start.strftime("%b %Y"))
		data.append(count)
	
	return {
		"labels": labels,
		"datasets": [{
			"name": "Evaluations",
			"values": data
		}]
	}


@frappe.whitelist()
def get_course_performance():
	"""Get top performing courses"""
	evaluations = frappe.get_all(
		"Course Evaluation",
		filters={"docstatus": 1, "course_name": ["is", "set"]},
		fields=["course_name", *RATING_FIELDS],
	)
	by_course = defaultdict(list)
	for row in evaluations:
		avg = document_average_rating_4(row)
		if avg is not None:
			by_course[row.course_name].append(avg)
	courses = sorted(
		[(name, flt(sum(scores) / len(scores), 2)) for name, scores in by_course.items()],
		key=lambda item: item[1],
		reverse=True,
	)[:10]
	labels = [c[0] or "Unknown" for c in courses]
	values = [c[1] for c in courses]
	
	return {
		"labels": labels,
		"datasets": [{
			"name": "Average Rating",
			"values": values
		}]
	}


@frappe.whitelist()
def get_instructor_performance():
	"""Get instructor performance ratings"""
	evaluations = frappe.get_all(
		"Course Evaluation",
		filters={"docstatus": 1, "instructor_name": ["is", "set"]},
		fields=["instructor_name", "presentation_skills", "teaching_effectiveness"],
	)
	stats = defaultdict(lambda: {"presentation": [], "teaching": []})
	for row in evaluations:
		name = row.instructor_name
		pres = rating_to_score_4(row.get("presentation_skills"))
		teach = rating_to_score_4(row.get("teaching_effectiveness"))
		if pres is not None:
			stats[name]["presentation"].append(pres)
		if teach is not None:
			stats[name]["teaching"].append(teach)
	instructors = []
	for name, data in stats.items():
		pres = data["presentation"]
		teach = data["teaching"]
		avg_p = flt(sum(pres) / len(pres), 2) if pres else 0
		avg_t = flt(sum(teach) / len(teach), 2) if teach else 0
		instructors.append({"name": name, "avg_p": avg_p, "avg_t": avg_t, "avg_c": flt((avg_p + avg_t) / 2, 2)})
	instructors.sort(key=lambda x: x["avg_c"], reverse=True)
	instructors = instructors[:10]
	labels = [i["name"] or "Unknown" for i in instructors]
	presentation_scores = [i["avg_p"] for i in instructors]
	teaching_scores = [i["avg_t"] for i in instructors]
	
	return {
		"labels": labels,
		"datasets": [
			{
				"name": "Presentation Skills",
				"values": presentation_scores
			},
			{
				"name": "Teaching Effectiveness",
				"values": teaching_scores
			}
		]
	}


@frappe.whitelist()
def get_training_impact_metrics():
	"""Get training impact metrics"""
	evaluations = frappe.get_all(
		"Course Evaluation",
		filters={"docstatus": 1},
		fields=["skills_improve_job_performance", "recommend_course", "course_duration"]
	)
	
	improve_job = {"Yes": 0, "No": 0, "Maybe": 0}
	recommend = {"Yes": 0, "No": 0, "Maybe": 0}
	duration = {"Too Long": 0, "About Right": 0, "Short": 0}
	
	for eval in evaluations:
		if eval.get("skills_improve_job_performance"):
			improve_job[eval.skills_improve_job_performance] = improve_job.get(eval.skills_improve_job_performance, 0) + 1
		if eval.get("recommend_course"):
			recommend[eval.recommend_course] = recommend.get(eval.recommend_course, 0) + 1
		if eval.get("course_duration"):
			duration[eval.course_duration] = duration.get(eval.course_duration, 0) + 1
	
	return {
		"improve_job": {
			"labels": list(improve_job.keys()),
			"values": list(improve_job.values())
		},
		"recommend": {
			"labels": list(recommend.keys()),
			"values": list(recommend.values())
		},
		"duration": {
			"labels": list(duration.keys()),
			"values": list(duration.values())
		}
	}


@frappe.whitelist()
def get_category_ratings():
	"""Get average ratings by category"""
	categories = {
		"Training Environment": ["joining_instructions_clear", "training_room_environment", "administration_support"],
		"Course Content": ["objectives_clearly_defined", "content_organization", "materials_aligned", "course_pace"],
		"Instructor": ["presentation_skills", "teaching_effectiveness", "knowledge_accessibility", "assignments_exercises"],
		"Resources": ["handouts_tools_equipment", "technology_effectiveness"]
	}
	
	evaluations = frappe.get_all(
		"Course Evaluation",
		filters={"docstatus": 1},
		fields=[
			"joining_instructions_clear", "training_room_environment", "administration_support",
			"objectives_clearly_defined", "content_organization", "materials_aligned", "course_pace",
			"presentation_skills", "teaching_effectiveness", "knowledge_accessibility", "assignments_exercises",
			"handouts_tools_equipment", "technology_effectiveness"
		]
	)
	
	category_ratings = {}
	
	for category, fields in categories.items():
		total_score = 0
		total_count = 0
		for eval in evaluations:
			for field in fields:
				score = rating_to_score_4(eval.get(field))
				if score is not None:
					total_score += score
					total_count += 1
		category_ratings[category] = flt(total_score / total_count, 2) if total_count > 0 else 0
	
	labels = list(category_ratings.keys())
	values = list(category_ratings.values())
	
	return {
		"labels": labels,
		"datasets": [{
			"name": "Average Rating",
			"values": values
		}]
	}


@frappe.whitelist()
def get_company_evaluations():
	"""Get evaluation count by company"""
	companies = frappe.db.sql("""
		SELECT 
			ce.company,
			COUNT(*) as evaluation_count
		FROM `tabCourse Evaluation` ce
		WHERE ce.docstatus = 1 
			AND ce.company IS NOT NULL
		GROUP BY ce.company
		ORDER BY evaluation_count DESC
		LIMIT 10
	""", as_dict=True)
	
	labels = [c.company or "Unknown" for c in companies]
	values = [c.evaluation_count for c in companies]
	
	return {
		"labels": labels,
		"datasets": [{
			"name": "Evaluations",
			"values": values
		}]
	}


@frappe.whitelist()
def get_dashboard_data(filters=None):
	"""Get comprehensive dashboard data with filters"""
	
	try:
		if isinstance(filters, str):
			filters = json.loads(filters)
		
		# If no filters or empty filters, use the original KPI function
		if not filters or (not filters.get('from_date') and not filters.get('to_date') and 
			not filters.get('course') and not filters.get('instructor') and 
			not filters.get('company') and not filters.get('status')):
			# Use original function for better performance and reliability
			summary = get_course_evaluation_kpis()
		else:
			# Get summary/KPI data with filters
			summary = get_filtered_kpis(filters)
		
		return {
			"summary": summary
		}
	except Exception as e:
		frappe.log_error(f"Error in get_dashboard_data: {str(e)}", "Course Evaluation Dashboard Error")
		# Fallback to original function
		try:
			summary = get_course_evaluation_kpis()
			return {
				"summary": summary
			}
		except:
			return {
				"summary": {
					"total_evaluations": 0,
					"submitted_evaluations": 0,
					"draft_evaluations": 0,
					"average_rating": 0,
					"excellent_percentage": 0,
					"unique_courses": 0,
					"unique_instructors": 0,
					"improve_job_percentage": 0,
					"recommend_percentage": 0,
					"recent_evaluations": 0
				},
				"error": str(e)
			}


def build_filter_conditions(filters):
	"""Build SQL filter conditions from filters dict - returns tuple (conditions_string, values_dict)"""
	conditions = []
	values = {}
	
	if not filters:
		return ("1=1", {})
	
	if filters.get('from_date'):
		conditions.append("DATE(ce.creation) >= %(from_date)s")
		values['from_date'] = filters['from_date']
	
	if filters.get('to_date'):
		conditions.append("DATE(ce.creation) <= %(to_date)s")
		values['to_date'] = filters['to_date']
	
	if filters.get('course'):
		conditions.append("ce.course_name LIKE %(course)s")
		values['course'] = f"%{filters['course']}%"
	
	if filters.get('instructor'):
		conditions.append("ce.instructor_name LIKE %(instructor)s")
		values['instructor'] = f"%{filters['instructor']}%"
	
	if filters.get('company'):
		conditions.append("ce.company LIKE %(company)s")
		values['company'] = f"%{filters['company']}%"
	
	if filters.get('status'):
		if filters['status'] == '1':
			conditions.append("ce.docstatus = 1")
		elif filters['status'] == '0':
			conditions.append("ce.docstatus = 0")
	
	if not conditions:
		return ("1=1", {})
	
	return (" AND ".join(conditions), values)


def get_filtered_kpis(filters):
	"""Get KPI data with filters applied using frappe.get_all"""
	
	# Build base filters
	base_filters = {}
	
	# Handle date range properly
	if filters.get('from_date') and filters.get('to_date'):
		base_filters['creation'] = ['between', [filters['from_date'], filters['to_date']]]
	elif filters.get('from_date'):
		base_filters['creation'] = ['>=', filters['from_date']]
	elif filters.get('to_date'):
		base_filters['creation'] = ['<=', filters['to_date']]
	
	if filters.get('course'):
		base_filters['course_name'] = ['like', f"%{filters['course']}%"]
	
	if filters.get('instructor'):
		base_filters['instructor_name'] = ['like', f"%{filters['instructor']}%"]
	
	if filters.get('company'):
		base_filters['company'] = ['like', f"%{filters['company']}%"]
	
	# Total Evaluations (all docstatuses except cancelled)
	total_filters = base_filters.copy()
	total_filters['docstatus'] = ['!=', 2]
	total_evaluations = len(frappe.get_all("Course Evaluation", filters=total_filters, pluck="name"))
	
	# Submitted Evaluations
	submitted_filters = base_filters.copy()
	submitted_filters['docstatus'] = 1
	submitted_evaluations = len(frappe.get_all("Course Evaluation", filters=submitted_filters, pluck="name"))
	
	# Draft Evaluations
	draft_filters = base_filters.copy()
	draft_filters['docstatus'] = 0
	draft_evaluations = len(frappe.get_all("Course Evaluation", filters=draft_filters, pluck="name"))
	
	# Get evaluation data for calculations (only submitted)
	evaluations = frappe.get_all(
		"Course Evaluation",
		filters=submitted_filters,
		fields=[
			"joining_instructions_clear", "training_room_environment", "administration_support",
			"objectives_clearly_defined", "content_organization", "materials_aligned", "course_pace",
			"presentation_skills", "teaching_effectiveness", "knowledge_accessibility", "assignments_exercises",
			"handouts_tools_equipment", "technology_effectiveness",
			"skills_improve_job_performance", "recommend_course", "course_duration"
		]
	)
	
	# Calculate average ratings
	rating_fields = [
		"joining_instructions_clear", "training_room_environment", "administration_support",
		"objectives_clearly_defined", "content_organization", "materials_aligned", "course_pace",
		"presentation_skills", "teaching_effectiveness", "knowledge_accessibility", "assignments_exercises",
		"handouts_tools_equipment", "technology_effectiveness"
	]
	
	total_ratings = 0
	total_score = 0
	excellent_count = 0
	good_count = 0
	
	for eval in evaluations:
		for field in RATING_FIELDS:
			score = rating_to_score_4(eval.get(field))
			if score is None:
				continue
			total_score += score
			total_ratings += 1
			bucket = rating_performance_bucket(eval.get(field))
			if bucket == "excellent":
				excellent_count += 1
			elif bucket == "good":
				good_count += 1
	
	# Calculate averages
	average_rating = flt(total_score / total_ratings, 2) if total_ratings > 0 else 0
	excellent_percentage = flt((excellent_count / total_ratings * 100), 2) if total_ratings > 0 else 0
	
	# Unique courses evaluated
	course_filters = submitted_filters.copy()
	course_filters['course_name'] = ['is', 'set']
	unique_courses_list = frappe.get_all("Course Evaluation", filters=course_filters, pluck="course_name", distinct=True)
	unique_courses = len([c for c in unique_courses_list if c]) or 0
	
	# Unique instructors evaluated
	instructor_filters = submitted_filters.copy()
	instructor_filters['instructor_name'] = ['is', 'set']
	unique_instructors_list = frappe.get_all("Course Evaluation", filters=instructor_filters, pluck="instructor_name", distinct=True)
	unique_instructors = len([i for i in unique_instructors_list if i]) or 0
	
	# Training Impact Metrics
	improve_job_filters = submitted_filters.copy()
	improve_job_filters['skills_improve_job_performance'] = 'Yes'
	improve_job_yes = len(frappe.get_all("Course Evaluation", filters=improve_job_filters, pluck="name"))
	
	recommend_filters = submitted_filters.copy()
	recommend_filters['recommend_course'] = 'Yes'
	recommend_yes = len(frappe.get_all("Course Evaluation", filters=recommend_filters, pluck="name"))
	
	improve_job_percentage = flt((improve_job_yes / submitted_evaluations * 100), 2) if submitted_evaluations > 0 else 0
	recommend_percentage = flt((recommend_yes / submitted_evaluations * 100), 2) if submitted_evaluations > 0 else 0
	
	# Recent evaluations (last 30 days)
	recent_filters = submitted_filters.copy()
	recent_filters['creation'] = ['>=', add_days(today(), -30)]
	recent_evaluations = len(frappe.get_all("Course Evaluation", filters=recent_filters, pluck="name"))
	
	return {
		"total_evaluations": total_evaluations,
		"submitted_evaluations": submitted_evaluations,
		"draft_evaluations": draft_evaluations,
		"average_rating": average_rating,
		"excellent_percentage": excellent_percentage,
		"unique_courses": unique_courses,
		"unique_instructors": unique_instructors,
		"improve_job_percentage": improve_job_percentage,
		"recommend_percentage": recommend_percentage,
		"recent_evaluations": recent_evaluations
	}

