""" 
cimri matcher system
--------------------   
date:                    01.31.2012
author:                  gun@alppay.com

description:
------------

revision history: 
-----------------
gun@alppay.com:          initial version

"""


import json

from cimri.system.logger import Logger

class DataObject(object):
        """
	Genel serialization operasyonlarini desteklemesi gereken classlerin icin base class.

	Bu classi extend eden classlerin Cimri API object parametrelerine denk gelen fieldlari ayni isimle tanimlanmalidir.
	Cimri API objectlerine denk gelmeyen diger fieldlar _ ile baslamalidir.
        """

	def __init__(self,data=None):
	        """
	        @type  data: dict
	        @param data: field degerlerini initialize etmek icin veriler
	        """

		if data!=None:
			for key in data:
				setattr(self,key,data[key])
		
	def to_dict(self):
	        """
		Class instance'i dictionary'e cevirir

	        @rtype: dict
	        @return: class instance fieldlarini iceren dictionary
	        """

		data={}
		for key,val in vars(self).iteritems():
			if key.startswith("_")==False:
				data[key]=val			

		return data


	@classmethod
	def from_json(cls,packet):
                """
		Bir json stringe dayanarak yeni bir class instance yaratir

                @type packet:   str
                @param packet:  class fieldlarini iceren bir json string

		@rtype:	object
                @return: eger json parse hatasi yoksa bu classin bir instancei, varsa None 
                """

		#check packet
                if packet==None:
                        return None

                #parse and instantiate objects
                try:
                        #parse
                        data=json.loads(packet)

                        #return object
                        return cls(data)

                except Exception as e:
                        Logger.getlogger(cls.__name__).error("exception ocurred while parsing json for objects ("+cls.__class__.__name__+")")

                return None



	@classmethod
        def list_from_json(cls,packet,path):
                """
		Bir json stringe dayanarak bu classin birden fazla instanceini yaratir

                @type packet:   str
                @param packet:  bu class turunde objectlerin listesini iceren bir json string

                @type path:     list
                @param path:    json objecti icinde aranan objectlerin hangi path'de bulundugunu belirleyen bir field listesi
                                ornegin bu parametre ["items"] ise, objectlerin json icindeki yeri asagidaki sekildedir:

                                data=json.loads(packet)
                                items=data["items"]

		@rtype:	list
                @return: eger json parse hatasi yoksa bu classin instancelarini iceren bir liste, varsa None 
                """

		#check packet
                if packet==None:
                        return None

                #parse and instantiate objects
                try:
                        #parse
                        data=json.loads(packet)

                        #find the field containing the list of objects to instantiate
                        for key in path:
                                data=data[key]
			
			#if this is not a list, convert into a list with single element
			if type(data).__name__!='list':
				data=[data]			
			
                        #return objects
                        return [cls(info) for info in data]

                except Exception as e:
                        Logger.getlogger(cls.__name__).error("exception ocurred while parsing json for objects ("+cls.__class__.__name__+")")

                return None


