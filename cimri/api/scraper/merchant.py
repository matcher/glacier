import mongoengine
from mongoengine import *
import datetime
import json
import hashlib
import uuid

from cimri.system.document import SerialDoc

class MerchantScraperRecord(Document,SerialDoc):
        """
	Merchant scraper status ve training verilerini kayit etmek icin kullanilir
        """
	merchantid = IntField(required=True)	
	is_trained = BooleanField(default=False) 		#trained or not
	is_approved = BooleanField(default=False)		#approved to use in workflow?
    	accuracy = FloatField(default=0.0) 			#current scraper accuracy
	scraped_fields = ListField(StringField(),default=[])	#actively scraped fields
	ref = DictField(default={})				#reference data for detecting when merchant html changes
	price_accuracy = DictField(default={})
	errors = DictField(default={})				#stats on errors encountered the last time this merchant was processed

	created = DateTimeField(default=datetime.datetime.now)
	   
	meta = {'indexes':['merchantid']}

