import mongoengine
from mongoengine import *
import datetime
import json
import hashlib
import uuid

from cimri.system.document import SerialDoc

class MatchRecord(Document,SerialDoc):
        """
	Matcher analiz verilerini kayit etmek icin kullanilir
        """

	MATCH_STATUS_MATCHED="matched"
	MATCH_STATUS_MATCHED_WRONG="matched-wrong"
	MATCH_STATUS_NOT_MATCHED="not-matched"
	MATCH_STATUS_GUESSED="guessed"
	MATCH_STATUS_GUESSED_WRONG="guessed-wrong"

	taskid = StringField(max_length=40, required=True)
	item = DictField(required=True)
	refitem = DictField(required=True)
	status = StringField(max_length=20, required=True)	
	score = FloatField(required=True)	
	matches = ListField(DictField(),default=[])
	created = DateTimeField(default=datetime.datetime.now)
	   
	meta = {'indexes':['taskid']}

