# Copyright (c) 2026, mohtashim and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import strip_html


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = get_columns()
	raw_rows = get_raw_rows(filters)
	correct_answer_counts = get_correct_answer_counts(filters)
	data = get_aggregated_rows(raw_rows, correct_answer_counts)
	chart = get_chart(data)
	report_summary = get_report_summary(data)

	return columns, data, None, chart, report_summary


def get_columns():
	return [
		{
			"label": _("Quiz"),
			"fieldname": "quiz",
			"fieldtype": "Link",
			"options": "Quiz",
			"width": 180,
		},
		{
			"label": _("Course"),
			"fieldname": "course",
			"fieldtype": "Link",
			"options": "Course",
			"width": 160,
		},
		{
			"label": _("Question ID"),
			"fieldname": "question",
			"fieldtype": "Link",
			"options": "Question",
			"width": 140,
		},
		{
			"label": _("Question"),
			"fieldname": "question_title",
			"fieldtype": "Data",
			"width": 320,
		},
		{
			"label": _("Wrong Answer Attempted"),
			"fieldname": "wrong_answer_attempted",
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"label": _("Correct Answer"),
			"fieldname": "correct_answer",
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"label": _("Wrong Attempts"),
			"fieldname": "wrong_attempts",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": _("Candidates"),
			"fieldname": "candidate_count",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"label": _("Correct Answer Count"),
			"fieldname": "correct_answer_count",
			"fieldtype": "Int",
			"width": 150,
		},
		{
			"label": _("Question Rank"),
			"fieldname": "question_rank",
			"fieldtype": "Int",
			"width": 110,
		},
		{
			"label": _("Latest Attempt"),
			"fieldname": "latest_attempt",
			"fieldtype": "Datetime",
			"width": 160,
		},
	]


def get_raw_rows(filters):
	conditions = ["qr.quiz_result = 'Wrong'", "IFNULL(qr.selected_option, '') NOT IN ('', 'Unattempted')"]
	values = {}

	for field in ("quiz", "course", "student"):
		if filters.get(field):
			conditions.append(f"qa.{field} = %({field})s")
			values[field] = filters.get(field)

	if filters.get("question"):
		conditions.append("qr.question = %(question)s")
		values["question"] = filters.get("question")

	if filters.get("from_date"):
		conditions.append("DATE(qa.activity_date) >= %(from_date)s")
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("DATE(qa.activity_date) <= %(to_date)s")
		values["to_date"] = filters.get("to_date")

	conditions_sql = " AND ".join(conditions)

	return frappe.db.sql(
		f"""
		SELECT
			qa.quiz,
			qa.course,
			qa.student,
			qa.activity_date,
			qr.question,
			q.question AS question_title,
			qr.selected_option AS wrong_answer_attempted,
			(
				SELECT GROUP_CONCAT(opt.option ORDER BY opt.idx SEPARATOR ', ')
				FROM `tabOptions` opt
				WHERE opt.parent = qr.question
					AND opt.parenttype = 'Question'
					AND opt.parentfield = 'options'
					AND opt.is_correct = 1
			) AS correct_answer
		FROM `tabQuiz Activity` qa
		INNER JOIN `tabQuiz Result` qr
			ON qr.parent = qa.name
			AND qr.parenttype = 'Quiz Activity'
		LEFT JOIN `tabQuestion` q
			ON q.name = qr.question
		WHERE {conditions_sql}
		""",
		values,
		as_dict=True,
	)


def get_correct_answer_counts(filters):
	conditions = ["qr.quiz_result = 'Correct'"]
	values = {}

	for field in ("quiz", "course", "student"):
		if filters.get(field):
			conditions.append(f"qa.{field} = %({field})s")
			values[field] = filters.get(field)

	if filters.get("question"):
		conditions.append("qr.question = %(question)s")
		values["question"] = filters.get("question")

	if filters.get("from_date"):
		conditions.append("DATE(qa.activity_date) >= %(from_date)s")
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("DATE(qa.activity_date) <= %(to_date)s")
		values["to_date"] = filters.get("to_date")

	conditions_sql = " AND ".join(conditions)

	rows = frappe.db.sql(
		f"""
		SELECT
			qa.quiz,
			qa.course,
			qr.question,
			COUNT(*) AS correct_answer_count
		FROM `tabQuiz Activity` qa
		INNER JOIN `tabQuiz Result` qr
			ON qr.parent = qa.name
			AND qr.parenttype = 'Quiz Activity'
		WHERE {conditions_sql}
		GROUP BY qa.quiz, qa.course, qr.question
		""",
		values,
		as_dict=True,
	)

	return {(row.quiz, row.course, row.question): row.correct_answer_count for row in rows}


def get_aggregated_rows(raw_rows, correct_answer_counts):
	grouped_rows = {}

	for row in raw_rows:
		question_title = strip_html(row.question_title or "")
		key = (
			row.quiz,
			row.course,
			row.question,
			question_title,
			row.wrong_answer_attempted,
			row.correct_answer,
		)

		if key not in grouped_rows:
			grouped_rows[key] = {
				"quiz": row.quiz,
				"course": row.course,
				"question": row.question,
				"question_title": question_title,
				"wrong_answer_attempted": row.wrong_answer_attempted,
				"correct_answer": row.correct_answer,
				"wrong_attempts": 0,
				"candidate_count": 0,
				"correct_answer_count": correct_answer_counts.get((row.quiz, row.course, row.question), 0),
				"question_rank": 0,
				"latest_attempt": row.activity_date,
				"_students": set(),
			}

		grouped_rows[key]["wrong_attempts"] += 1
		grouped_rows[key]["latest_attempt"] = max(grouped_rows[key]["latest_attempt"], row.activity_date)

		if row.student:
			grouped_rows[key]["_students"].add(row.student)

	data = list(grouped_rows.values())

	for row in data:
		row["candidate_count"] = len(row.pop("_students"))

	data.sort(
		key=lambda row: (
			row["quiz"] or "",
			row["question_title"] or "",
			-row["wrong_attempts"],
			-row["candidate_count"],
			row["wrong_answer_attempted"] or "",
		)
	)

	current_question = None
	current_rank = 0
	for row in data:
		question_key = (row["quiz"], row["question"])
		if question_key != current_question:
			current_question = question_key
			current_rank = 1
		else:
			current_rank += 1
		row["question_rank"] = current_rank

	data.sort(
		key=lambda row: (
			row["question_rank"],
			-row["wrong_attempts"],
			-row["candidate_count"],
			row["quiz"] or "",
			row["question_title"] or "",
		)
	)

	return data


def get_chart(data):
	top_rows = data[:10]
	if not top_rows:
		return None

	return {
		"data": {
			"labels": [row["wrong_answer_attempted"][:40] for row in top_rows],
			"datasets": [
				{
					"name": _("Wrong Attempts"),
					"values": [row["wrong_attempts"] for row in top_rows],
				}
			],
		},
		"type": "bar",
		"colors": ["#d9485f"],
	}


def get_report_summary(data):
	if not data:
		return []

	total_wrong_attempts = sum(row["wrong_attempts"] for row in data)
	total_questions = len({(row["quiz"], row["question"]) for row in data})
	top_row = max(data, key=lambda row: (row["wrong_attempts"], row["candidate_count"]))

	return [
		{
			"value": total_wrong_attempts,
			"label": _("Total Wrong Attempts"),
			"datatype": "Int",
		},
		{
			"value": total_questions,
			"label": _("Questions With Wrong Attempts"),
			"datatype": "Int",
		},
		{
			"value": top_row["wrong_answer_attempted"],
			"label": _("Most Attempted Wrong Answer"),
			"datatype": "Data",
		},
	]
