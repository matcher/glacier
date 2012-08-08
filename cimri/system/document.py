""" 
cimri matcher
---------------------------
date:                    03.14.2012
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

from cimri.system.config import Config


class SerialDoc(object):
        """
	Genel mongodb ve serialization operasyonlarini desteklemesi gereken classlerin icin base class.

	Bu classi extend eden classlerin Cimri API object parametrelerine denk gelen fieldlari ayni isimle tanimlanmalidir.
	Cimri API objectlerine denk gelmeyen diger fieldlar _ ile baslamalidir.
        """

	def todict(self):
	        """
		Class instance'i dictionary'e cevirir

	        @rtype: dict
	        @return: class insitance fieldlarini iceren dictionary
	        """

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
	        """
		Class instance'ini bir json stringe cevirir

	        @rtype: str
	        @return: class instance fieldlarini iceren bir json string
	        """

		return json.dumps(self.todict())


	def fromjson(self,str):
                """
		Bir json stringe dayanarak yeni bir class instance yaratir

                @type str:   str
                @param str:  class fieldlarini iceren bir json string

		@rtype:	object
                @return: eger json parse hatasi yoksa bu classin bir instancei, varsa None 
                """

		pass


	
	@classmethod
	def connectdb(self):
	        """
	        MongoDB databaseine baglanir
	        """

#		connect(Config.getconfig("API").get("analytics_db"))
		connect("cimri-matcher")


	def create(self):
	        """
		Objecti mongodb'de yaratir

	        @rtype: object
	        @return: eger operasyon basarili ise self, aksi takdirde None
	        """

		try:
			#connect to db
			SerialDoc.connectdb()

			#save
			self.save()

			return self

		except Exception as e:
			print e
			return None


	@classmethod
	def get(cls,**filters):
	        """
		Bu class turunde bir objecti mongodb'den alir

	        @type  filters: dict
	        @param filters: mongodb querysini belirleyen parametreler

	        @rtype: object
	        @return: eger operasyon basarili ise bu class turunde bir object, aksi takdirde None
	        """

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
	        """
		Bu class turunde birden fazla objecti mongodb'den alir

	        @type  filters: dict
	        @param filters: mongodb querysini belirleyen parametreler

	        @rtype: list
	        @return: eger operasyon basarili ise bu class turunde objectleri iceren bir liste, aksi takdirde None
	        """

		try:
			#connect to db
			SerialDoc.connectdb()

			#find all
			list=cls.objects(**filters)

			return list

		except Exception as e:
			return None



	@classmethod
	def list_paginated(cls,skip,limit,**filters):
	        """
		Bu class turunde birden fazla objecti mongodb'den alir

	        @type  skip:    int
	        @param skip:    ilk alinacak item'in indexi

	        @type  limit:   int
	        @param limit:   alinacak itemlarin sayisi

	        @type  filters: dict
	        @param filters: mongodb querysini belirleyen parametreler

	        @rtype: list
	        @return: eger operasyon basarili ise bu class turunde objectleri iceren bir liste, aksi takdirde None
	        """

		try:
			#connect to db
			SerialDoc.connectdb()

			#find all
			list=cls.objects(**filters)[skip:skip+limit]

			return list

		except Exception as e:
			return None
