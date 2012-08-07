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

from cpanel.config.config import Config
from cpanel.app.logger import Logger

class SerialDoc(object):
	def todict(self):
		obj={}
		
		for field in self._fields.keys():
			t=type(self._fields[field])
			if t==mongoengine.base.ObjectIdField:
				val=getattr(self,field)	
				obj[field]=None if val==None else str(val)	
				
			elif t in (mongoengine.fields.StringField, mongoengine.fields.EmailField):
				val=getattr(self,field)	
				obj[field]=None if val==None else val
				
			elif t==mongoengine.fields.DateTimeField:
				val=getattr(self,field)	
				obj[field]=None if val==None else str(val)	
				
			elif t==mongoengine.fields.ListField:
				list=getattr(self,field)	
				obj[field]=None if list==None else [elmt for elmt in list]

			else:
				obj[field]=getattr(self,field)

		return obj
		
	def tojson(self):
		return json.dumps(self.todict())


	def fromjson(self,str):
		pass
	
	@classmethod
	def connectdb(self):
		connect(Config.mongo_db)


	def create(self):
		try:
			#connect to db
			SerialDoc.connectdb()

			#save
			self.save()

			return self

		except Exception as e:
			Logger.getlogger("doc").error(e)
			return None


	@classmethod
	def get(cls,**filters):
		try:
			#connect to db
			SerialDoc.connectdb()

			#find all
			obj=cls.objects.get(**filters)

			return obj

		except Exception as e:
			return None


	@classmethod
	def list(cls,**filters):
		try:
			#connect to db
			SerialDoc.connectdb()

			#find all
			list=cls.objects(**filters)

			return list

		except Exception as e:
			return None
