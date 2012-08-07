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


from time import *
 
def format_time_for_log(ts):
        """
	Belli bir timestampi log file'da kullanildigi sekilde formatlar

        @type  ts: long
        @param ts: timestamp

        @rtype: str
        @return: formatlanmis tarih ve zaman bilgileri
        """

        return strftime('%m.%d.%y %H:%M:%S',gmtime(ts))


