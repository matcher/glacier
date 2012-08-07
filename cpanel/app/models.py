# -*- coding: utf-8 -*-

""" 
cimri matcher control panel
---------------------------
date:                    01.31.2012
author:                  gun@alppay.com

description:
------------

revision history: 
-----------------
gun@alppay.com:          initial version

"""


import mongoengine
from mongoengine import *
import datetime
import json
import hashlib
import uuid

from cpanel.app.logger import Logger
from cpanel.config.config import Config
from cpanel.app.document import SerialDoc


#machine learning case 
class MLCase(Document,SerialDoc):
	STATUS_DRAFT="draft"
	STATUS_READY="ready"
	STATUS_PENDING="pending"
	STATUS_ACTIVE="active"
	STATUS_DEACTIVATED="deactivated"

	owner=ObjectIdField(required=True)
	label = StringField(max_length=100, required=True)
	uuid = StringField(max_length=100, required=True)
	module = StringField(max_length=100, required=True)
 	status = StringField(max_length=12, required=True)            
	op = StringField(max_length=20, required=True)
	history = ListField(DictField())
	target = DictField(required=True)
	data = ListField(required=True, default=[])
	created = DateTimeField(default=datetime.datetime.now)

	def create(self):
		try:
			#status
			self.status=MLCase.STATUS_DRAFT

			#uuid
			self.uuid=MLCase._get_guid()

			#connect to db
			SerialDoc.connectdb()

			#save
			self.save()

			return self

		except Exception as e:
			Logger.getlogger("test").info(e)
			return None


	def getstatusstring(self):
		lookup={MLCase.STATUS_DRAFT:		u"yeni",
			MLCase.STATUS_READY:		u"hazır",
			MLCase.STATUS_PENDING:		u"onay bekliyor",
        		MLCase.STATUS_ACTIVE:		u"kullanımda",
        		MLCase.STATUS_DEACTIVATED:	u"kullanım dışı"}

		return lookup[self.status]


	@classmethod
	def _get_guid(self):
		return str(uuid.uuid4())


#test case
class TestCase(Document,SerialDoc):
	STATUS_DRAFT="draft"
	STATUS_READY="ready"

	owner=ObjectIdField(required=True)
	label = StringField(max_length=100, required=True)
	uuid = StringField(max_length=100, required=True)
	module = StringField(max_length=100, required=True)
	op = StringField(max_length=20, required=True)
 	status = StringField(max_length=12, required=True)            
	target = DictField(required=True)
	data = ListField(required=True, default=[])
	batch = ListField(required=False, default=None)
	created = DateTimeField(default=datetime.datetime.now)

	def create(self):
		try:
			#status
			self.status=MLCase.STATUS_DRAFT

			#uuid
			self.uuid=TestCase._get_guid()

			#connect to db
			SerialDoc.connectdb()

			#save
			self.save()

			return self

		except Exception as e:
			Logger.getlogger("test").info(e)
			return None

	def getstatusstring(self):
		lookup={MLCase.STATUS_DRAFT:		u"yeni",
			MLCase.STATUS_READY:		u"hazır"}
		return lookup[self.status]

	@classmethod
	def _get_guid(self):
		return str(uuid.uuid4())


class TaskTemplate(Document,SerialDoc):
	owner=ObjectIdField(required=True)
	label = StringField(max_length=100, required=True)
	tasks = ListField(DictField(),required=True)
	schedule = StringField(max_length=1024, required=False, default="")
	schedule_log = DictField(required=True, default={})
	created = DateTimeField(default=datetime.datetime.now)

	def settasks(self,tasks):
		self.tasks=[]
		for task in tasks:
			data={}
			for key in task:
				if key=="meta":
					meta={}
					for metakey in task[key]:
						meta[metakey.replace(".","-")]=task[key][metakey]
					data[key]=meta
				else:
					data[key]=task[key]
			self.tasks.append(data)

	def gettasks(self):
		tasks=[]
		for task in self.tasks:
			data={}
			for key in task:
				if key=="meta":
					meta={}
					for metakey in task[key]:
						meta[metakey.replace("-",".")]=task[key][metakey]
					data[key]=meta
				else:
					data[key]=task[key]
			tasks.append(data)
		
		return tasks
