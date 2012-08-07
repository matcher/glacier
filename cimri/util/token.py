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


import uuid
import hashlib


def generate_uuid():
        """
	Bir unique ID yaratir

        @rtype: str
        @return: yaratilan unique id
        """

	return str(uuid.uuid4())


def hash_url(url):
        """
	Belli bir URL stringinin hash'ini yaratir

        @type  url: str
        @param url: hash edilmesi istenilen URL 

        @rtype: str
        @return: hash edilmis URL
        """

	return hashlib.sha1(url).hexdigest()
