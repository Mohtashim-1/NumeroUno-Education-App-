# Copyright (c) 2026, NumeroUNO and contributors
# License: MIT

"""Sync Theory Assessment print formats (summary + with questions) onto NUTC letterhead."""

from __future__ import annotations

from pathlib import Path

import frappe

MODULE = "Numerouno"
DOC_TYPE = "Assessment Result"

SUMMARY_NAME = "Theory Assessment Summary"
QUESTIONS_NAME = "Theory Assesment"  # existing name (legacy spelling)
QUIZ_ACTIVITY_PF = "Quiz Activity"

BASE = Path(__file__).resolve().parent / "print_format"


def _read(rel: str) -> str:
	path = BASE / rel
	return path.read_text(encoding="utf-8")


def _upsert_print_format(name: str, html: str, *, doc_type: str = DOC_TYPE):
	values = {
		"doctype": "Print Format",
		"name": name,
		"doc_type": doc_type,
		"module": MODULE,
		"standard": "No",
		"custom_format": 1,
		"print_format_type": "Jinja",
		"disabled": 0,
		"html": html,
		"margin_top": 10,
		"margin_bottom": 10,
		"margin_left": 10,
		"margin_right": 10,
		"font_size": 11,
		"page_number": "Hide",
		"pdf_generator": "chrome",
	}
	if frappe.db.exists("Print Format", name):
		doc = frappe.get_doc("Print Format", name)
		doc.update(values)
		doc.save(ignore_permissions=True)
	else:
		frappe.get_doc(values).insert(ignore_permissions=True)
	return name


def sync_theory_assessment_prints():
	"""Install / refresh both Theory Assessment print formats."""
	summary_html = _read("theory_assessment_summary/theory_assessment_summary.html")
	questions_html = _read("theory_assesment/theory_assesment.html")

	_upsert_print_format(SUMMARY_NAME, summary_html)
	_upsert_print_format(QUESTIONS_NAME, questions_html)

	# Keep Quiz Activity print aligned with summary (for direct QA print)
	if frappe.db.exists("Print Format", QUIZ_ACTIVITY_PF):
		qa_html = _quiz_activity_summary_html()
		frappe.db.set_value("Print Format", QUIZ_ACTIVITY_PF, {
			"html": qa_html,
			"disabled": 0,
			"custom_format": 1,
			"print_format_type": "Jinja",
		})

	frappe.db.commit()
	frappe.clear_cache()
	return {
		"summary": SUMMARY_NAME,
		"questions": QUESTIONS_NAME,
		"quiz_activity": QUIZ_ACTIVITY_PF,
	}


def _quiz_activity_summary_html() -> str:
	"""Summary table keyed off Quiz Activity doc (same look as Assessment Result summary)."""
	return """
<style>
@page { size: A4; margin: 10mm 10mm 9mm; }
.print-format { font-family: Arial, Helvetica, sans-serif; font-size: 11px; color: #222; padding: 0 !important; }
.print-heading, .print-format > .letter-head { display: none !important; }
.print-format * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
.ta-page { max-width: 190mm; margin: 0 auto; }
.ta-lh { text-align: center; margin: 0 0 8px; }
.ta-lh img { width: 100%; max-width: 100%; height: auto; display: block; margin: 0 auto; }
.ta-title { color: #c73636; font-size: 22px; font-weight: 800; margin: 6px 0 10px; }
.info-table, .result-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.info-table td, .result-table th, .result-table td { border: 1px solid #333; padding: 5px 6px; vertical-align: middle; }
.blue { background: #00589c !important; color: #fff !important; font-weight: 700; width: 18%; }
.orange { background: #e87522 !important; color: #fff !important; font-weight: 700; }
.section-bar { background: #e87522 !important; color: #fff !important; font-weight: 800; padding: 5px 7px; margin-top: 10px; }
.center { text-align: center; }
.pass { color: #0a7a2f; font-weight: 800; }
.fail { color: #c73636; font-weight: 800; }
.footer-acc { margin-top: 14px; }
.footer-acc img { width: 100%; height: auto; display: block; }
</style>
{% set student = frappe.get_doc("Student", doc.student) if doc.student and frappe.db.exists("Student", doc.student) else None %}
{% set candidate_name = (student.student_name if student else "") or doc.student or "" %}
{% set pass_fail = doc.status or "" %}
{% set total_score = doc.score or "" %}
<div class="ta-page">
	<div class="ta-lh"><img src="/files/IMAGE_NUTC.png" alt="NUTC" /></div>
	<h1 class="ta-title">THEORY ASSESSMENT</h1>
	<table class="info-table">
		<tr>
			<td class="blue">Candidate Name</td><td>{{ candidate_name }}</td>
			<td class="blue">Date</td><td>{{ frappe.utils.formatdate(doc.activity_date, "dd-MM-yyyy") if doc.activity_date else "" }}</td>
		</tr>
		<tr>
			<td class="blue">Student Group</td><td>{{ doc.custom_student_group or "" }}</td>
			<td class="blue">Assessment Plan</td><td>{{ doc.custom_assesment_plan or "" }}</td>
		</tr>
		<tr>
			<td class="blue">Assessment Result</td><td>{{ doc.custom_assesment_result or "" }}</td>
			<td class="blue">Total Score</td><td><b>{{ total_score }}</b></td>
		</tr>
		<tr>
			<td class="blue">Quiz</td><td>{{ doc.quiz or "" }}</td>
			<td class="blue">Pass / Fail</td>
			<td class="{% if (pass_fail or '')|lower == 'pass' %}pass{% elif (pass_fail or '')|lower in ['fail','failed','nyc'] %}fail{% endif %}"><b>{{ pass_fail }}</b></td>
		</tr>
	</table>
	<div class="section-bar">ASSESSMENT RESULT</div>
	<table class="result-table">
		<thead>
			<tr class="orange">
				<th style="width:6%;">No.</th>
				<th>Question</th>
				<th style="width:30%;">Selected Option</th>
				<th style="width:14%;">Result</th>
				<th style="width:10%;">Completed</th>
			</tr>
		</thead>
		<tbody>
			{% for row in doc.result %}
			<tr>
				<td class="center">{{ row.idx }}</td>
				<td>{{ row.question or "" }}</td>
				<td>{{ row.selected_option or "" }}</td>
				<td class="center">{{ row.quiz_result or "" }}</td>
				<td class="center">{% if row.quiz_result == "Correct" %}☑{% else %}☐{% endif %}</td>
			</tr>
			{% endfor %}
		</tbody>
	</table>
	<div class="section-bar">CANDIDATE’S RECORDS</div>
	<table class="result-table">
		<tr class="orange"><th>Quiz</th><th>Status</th><th>Score</th><th>Source of Evidence</th></tr>
		<tr>
			<td>{{ doc.quiz or "" }}</td>
			<td class="center">{{ pass_fail }}</td>
			<td class="center">{{ total_score }}</td>
			<td class="center">Q</td>
		</tr>
	</table>
	<br>
	<p><b>Learner Name:</b> {{ candidate_name }}</p>
	<div class="footer-acc"><img src="/files/FOOTER.png" alt="NUTC accreditations" /></div>
</div>
""".strip()
