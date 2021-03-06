# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.desk.doctype.auto_repeat.auto_repeat import make_auto_repeat_entry, disable_auto_repeat
from frappe.utils import today, add_days, getdate


def add_custom_fields():
	df = dict(
		fieldname='auto_repeat', label='Auto Repeat', fieldtype='Link', insert_after='sender',
		options='Auto Repeat')
	create_custom_field('ToDo', df)


class TestAutoRepeat(unittest.TestCase):
	def setUp(self):
		if not frappe.db.sql('select name from `tabCustom Field` where name="auto_repeat"'):
			add_custom_fields()

	def test_daily_auto_repeat(self):
		todo = frappe.get_doc(
			dict(doctype='ToDo', description='test recurring todo', assigned_by='Administrator')).insert()

		doc = make_auto_repeat(reference_document=todo.name)
		self.assertEqual(doc.next_schedule_date, today())
		make_auto_repeat_entry()
		frappe.db.commit()

		todo = frappe.get_doc(doc.reference_doctype, doc.reference_document)
		self.assertEqual(todo.auto_repeat, doc.name)

		new_todo = frappe.db.get_value('ToDo',
			{'auto_repeat': doc.name, 'name': ('!=', todo.name)}, 'name')

		new_todo = frappe.get_doc('ToDo', new_todo)

		self.assertEqual(todo.get('description'), new_todo.get('description'))

	def test_monthly_auto_repeat(self):
		start_date = '2018-01-01'
		end_date = '2018-12-31'

		todo = frappe.get_doc(
			dict(doctype='ToDo', description='test recurring todo', assigned_by='Administrator')).insert()

		self.monthly_auto_repeat('ToDo', todo.name, start_date, end_date)

	def monthly_auto_repeat(self, doctype, docname, start_date, end_date):
		def get_months(start, end):
			diff = (12 * end.year + end.month) - (12 * start.year + start.month)
			return diff + 1

		doc = make_auto_repeat(
			reference_doctype=doctype, frequency='Monthly',	reference_document=docname, start_date=start_date,
			end_date=end_date)

		disable_auto_repeat(doc)

		make_auto_repeat_entry()
		docnames = frappe.get_all(doc.reference_doctype, {'auto_repeat': doc.name})
		self.assertEqual(len(docnames), 1)

		doc = frappe.get_doc('Auto Repeat', doc.name)
		doc.db_set('disabled', 0)

		months = get_months(getdate(start_date), getdate(today()))
		make_auto_repeat_entry()

		docnames = frappe.get_all(doc.reference_doctype, {'auto_repeat': doc.name})
		self.assertEqual(len(docnames), months)


def make_auto_repeat(**args):
	args = frappe._dict(args)
	doc = frappe.get_doc({
		'doctype': 'Auto Repeat',
		'reference_doctype': args.reference_doctype or 'ToDo',
		'reference_document': args.reference_document or frappe.db.get_value('ToDo', {'docstatus': 1}, 'name'),
		'frequency': args.frequency or 'Daily',
		'start_date': args.start_date or add_days(today(), -1),
		'end_date': args.end_date or add_days(today(), 1),
		'submit_on_creation': args.submit_on_creation or 0
	}).insert(ignore_permissions=True)

	if not args.do_not_submit:
		doc.submit()

	return doc
