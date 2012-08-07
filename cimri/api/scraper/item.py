import mongoengine
from mongoengine import *
import datetime
import json
import hashlib
import uuid

from cimri.system.document import SerialDoc

class MerchantItemScraperRecord(Document,SerialDoc):
        """
	Merchant item scraper verilerini kayit etmek icin kullanilir
        """
	merchantid = IntField(required=True)	
	url = StringField()
	info = DictField(default={})
	updated = DateTimeField(default=datetime.datetime.now)
	   
	meta = {'indexes':['merchantid','url']}

