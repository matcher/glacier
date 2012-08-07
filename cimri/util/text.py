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


import re
import codecs
from pattern.metrics import *


def is_empty_string(text):
	"""
	Bir stringin bos olup olmadigini kontrol eder. Bos bir string icinde sadece space karakterleri ya da satir sonu karakterleri
	olan bir stringdir.

	@type  text: str
	@param text: test edilmesi istenilen string

	@rtype: bool
    	@return: string bos ise True, aksi takdirde False
	"""

	return replace_turkish_chars(text).strip()==""


def lower_non_turkish_alphanumeric(text):
	"""
	Bir string icindeki turkce karakterleri ascii karsiliklari ile degistirip, alphanumerik olmayan karakterleri 
	L{remove_non_alphanumeric} fonksiyonuna gore cikarip, lowercase olarak verir.

	@type  text: str
	@param text: islenmesi istenen string

	@rtype: str
    	@return: islenmis string
	"""

	return remove_non_alphanumeric( replace_turkish_chars(text).lower() )


def replace_turkish_chars(text):
	"""
	Bir string icindeki turkce karakterleri ascii karsiliklari ile degistirir

	@type  text: str
	@param text: islenmesi istenen string

	@rtype: str
    	@return: islenmis string
	"""

	#apply known transformations
	for transformation in _turkish_transformations():
		text=text.replace(transformation[0],transformation[1])
	
	#remove all remaining non-ascii characters
	text="".join([c for c in text if ord(c)<=127])

	return text


def remove_non_ascii(text):
	"""
	Bir string icinde ascii olmayan karakterleri cikartir

	@type  text: str
	@param text: islenmesi istenen string

	@rtype: str
    	@return: islenmis string
	"""

	return text.encode("ascii", "ignore")


def remove_non_alphanumeric(text):
	"""
	Bir string icinde alphanumerik olmayan karakterleri cikartir. Bu islemler sirasinda asagidaki karakterler bir space karakteri ile
	degistirilir, bunlar disindaki alfanumerik olmayan karakterler ise yerlerine baska karakter konulmadan cikarilir::

		- & , ( ) [ ]

	@type  text: str
	@param text: islenmesi istenen string

	@rtype: str
    	@return: islenmis string
	"""

	for rule in [(r'[-&,()]',' '),(r'[\[\]]',' '),(r'[^a-zA-Z\s\d]', '')]:
		text=re.sub(rule[0],rule[1],text)

	return text


def ignore_non_alphanumeric(text):
	"""
	Bir string icinde alphanumerik olmayan karakterleri cikartir

	@type  text: str
	@param text: islenmesi istenen string

	@rtype: str
    	@return: islenmis string
	"""

	return re.sub(r'[^a-zA-Z\d]','',text)


def remove_numeric(text):
	"""
	Bir string icinde numerik butun karakterleri cikartir

	@type  text: str
	@param text: islenmesi istenen string

	@rtype: str
    	@return: islenmis string
	"""

	return re.sub(r'[\d]','',text)


def remove_non_numeric(text):
	"""
	Bir string icinde numerik olmayan butun karakterleri cikartir

	@type  text: str
	@param text: islenmesi istenen string

	@rtype: str
    	@return: islenmis string
	"""

	return re.sub(r'[^\d]','',text)


def remove_alpha_numeric(text):
	"""
	Bir string icinde alphanumerik olan butun karakterleri cikartir

	@type  text: str
	@param text: islenmesi istenen string

	@rtype: str
    	@return: islenmis string
	"""

	return re.sub(r'[a-zA-Z\d]','',text)


def tokenize_alphanumeric(text):
	"""
	Bir string icinde bulunan alfanumerik olmayan karakterler ile birbirinden ayrilmis alphanumerik substringleri bulur

	@type  text: str
	@param text: islenmesi istenen string

	@rtype: list
    	@return: bulunan alfanumerik stringlerin listesi
	"""

	text=re.sub(r'[^a-zA-Z\s\d]',' ',text)

	return text.split(' ')

def extract_currency(text):
	try:
		tokens=re.sub(r'[^\d,\.]','',text).replace(",",".").split(".")
		if len(tokens[-1])==2:
			return float("".join(tokens[:-1])+'.'+tokens[-1])
		else:
			return float("".join(tokens))
	except:
		return None

def similarity(stringa,stringb):
	"""
	Iki stringin L{pattern.metrics.levenshtein_similarity} algoritmasina dayanarak yakinligini bulur.

	@type  stringa: str
	@param stringa: karsilastirilmasi istenen ilk string

	@type  stringb: str
	@param stringb: karsilastirilmasi istenen ikinci string

	@rtype: float
    	@return: yakinlik katsayisi
	"""

	return levenshtein_similarity(stringa,stringb)


def file_read_utf8(file):
	"""
	Bir dosyanin icerigini utf8 encoding ile oldugunu varsayarak okur

	@type  file: str
	@param file: okunmasi istenen dosyanin path ve ismi

	@rtype: unicode
    	@return: okunan dosyanin icerigi
	"""

	f=codecs.open(file,"r","utf-8")
	content=f.read()
	f.close()
	return content


def file_write_utf8(file,text):
	"""
	Istenilen icerigi utf8 encoding ile bir dosyaya yazar

	@type  file: str
	@param file: yazilmasi istenen dosyanin path ve ismi

	@type  text: unicode
	@param text: yazilmasi istenen icerik
	"""

	f=codecs.open(file,"w","utf-8")
	f.write(text)
	f.close()

def file_append_utf8(file,text):
        """
        Istenilen icerigi utf8 encoding ile bir dosyaya ekler

        @type  file: str
        @param file: yazilmasi istenen dosyanin path ve ismi

        @type  text: unicode
        @param text: yazilmasi istenen icerik
        """

        f=codecs.open(file,"a","utf-8")
        f.write(text)
        f.close()

	
def convert_unicode_to_utf8str(text, encoding):
	"""
	python 'unicode' turunde olan bir testi python 'str' turune cevirir

	@type text:      unicode
	@param text:     cevrilmesi istenen text

	@type encoding:  str
	@param encoding: cevrilecek olan text'in orjinal encoding'i

	@rtype: str
    	@return: 'str'ye cevirlmis text
	"""

	def convert_unicode_to_str(utext):
		try:
			return "".join([chr(ord(c)) for c in utext])
		except:
			return utext

	#if the original encoding is iso-8859-9, first decode it and then encode it as utf-8
	if encoding == "iso-8859-9":
		#convert unicode to string first
		stext=convert_unicode_to_str(text)	
		
		#decode			
		utext=stext.decode("iso-8859-9")
		
		#encode as utf-8			
		text=utext.encode("utf-8")
	
	#otherwise (including utf-8), encode as a utf-8 string	
	else:
		#encode as utf-8
		text=text.encode("utf-8")

	return text


def _turkish_transformations():
	"""
	Sistemde tanimli olan cesitli utf-8, unicode, ve iso-8859-9 turkce karakterlerin ascii karsiliklarini veren bir generator fonksiyonu.
	"""

	#transformations from turkish characters to ascii (iso-8859-1)
	transformations=[
			#utf-8 ----------------------
			(u'\xc3\x87',	'C'),
			(u'\xc3\x96',	'O'),
			(u'\xc3\x9c',	'U'),
			(u'\xc3\xa7',	'c'),
			(u'\xc3\xb6',	'o'),
			(u'\xc3\xbc',	'u'),
			(u'\xc4\x9d',	'g'),
			(u'\xc4\x9f',	'g'),
			(u'\xc4\xb0',	'I'),
			(u'\xc4\xb1',	'i'),
			(u'\xc5\x9e',	'S'),
			(u'\xc5\x9f',	's'),
			#---------------------- utf-8

			#iso-8859-9 codes -----------
			(u'\xb0',	''),	#degree sign 
			(u'\xc2',	'A'), 	#A with half circle
			(u'\xc3',	'A'), 	#A with tilde
			(u'\xc4',	'A'), 	#A with 2 dots
			(u'\xc5',	'A'), 	#A with ring on top
			(u'\xc7',	'C'),
			(u'\xd6',	'O'),
			(u'\xdc',	'U'), 
			(u'\xe7',	'c'),	
			(u'\xf6',	'o'),
			(u'\xfc',	'u'),
			(u'\xfd',	'i'),	
			(u'\xfe',	's'),	
			(u'\xf0',	'g'),	
			(u'\xde',	'S'),	
			(u'\xdd',	'I'),	
			(u'\xd0',	'G'),	
			#----------- iso-8859-9 codes

			#unicode codes --------------
			(u'\u011f',	'g'),	
			(u'\u0131',	'i'),
			(u'\u015f',	's'),
			(u'\u011e',	'G'),
			(u'\u0130',	'I'),
			(u'\u015e',	'S'),
			#-------------- unicode codes

			]

	for transformation in transformations:
		yield transformation

