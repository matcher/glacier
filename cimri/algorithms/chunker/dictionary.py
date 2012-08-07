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


import ahocorasick

from cimri.system.logger import Logger


class DictionaryChunker():
	"""
	aho-corasick chunker algoritmasi

	java:

	http://alias-i.com/lingpipe/docs/api/com/aliasi/dict/ExactDictionaryChunker.html

	http://alias-i.com/lingpipe/demos/tutorial/ne/read-me.html


	python:

	http://pypi.python.org/pypi/ahocorasick/0.9

	http://nltk.github.com/api/nltk.chunk.html#id1
	"""


	def __init__(self,dictionary):
                """
                @type  dictionary: list
                @param dictionary: chunker icin kullanilacak terim sozlugu
                """

		self.logger=Logger(self.__class__.__name__)

		#build dictionary
		self.logger.info("generating dictionary...")
		self.tree=ahocorasick.KeywordTree()
		for item in dictionary:
			if item.strip()!="":
				self.tree.add(item)
		self.tree.make()
		self.logger.info("finished generating dictionary...")



	def find_all(self,text):
                """
                bir text icinde belirlenen sozlukte bulunan butun terimleri arar.

                @type  text: string
                @param text: icinde terimlerin aranacagi text

                @rtype: list
                @return: bulunan sozluk terimleri
                """

		return [text[match[0]:match[1]] for match in self.tree.findall(text,allow_overlaps=1)]

