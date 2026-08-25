from numerouno.numerouno.page.habc2_examination_form.habc2_examination_form import (
	get_form_data,
	get_form_html,
	save_form_data,
	submit_form,
)


def get_form(docname=None, student_group=None):
	return get_form_html(docname=docname, student_group=student_group)


def save_form(data):
	return save_form_data(data)


def submit(docname):
	return submit_form(docname)
