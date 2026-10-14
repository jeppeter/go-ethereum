#! /usr/bin/env python

import logging
import yaml
import re


class YamlEx(object):
	def __init__(self):
		self.rdict = dict()
		return

	def loads(self,s):
		self.rdict =  yaml.safe_load(s)
		return



	def dumps(self,rdict=None):
		if rdict is not None:
			self.rdict = rdict
		outs = yaml.dump(self.rdict)
		return outs

	def set_value(self,k,v):
		retval = False
		try:
			karr = re.split('\\.',k)
			curval = None
			idx = 0
			if len(karr) == 1:
				self.rdict[k] = v
			else:
				idx = 0
				curval = self.rdict
				lastkey = ''
				while idx < (len(karr) - 1):
					if karr[idx] not in curval.keys():
						curval[karr[idx]] = dict()						
					if not isinstance(curval[karr[idx]],dict):
						curval[karr[idx]] = dict()
					if idx == 0:
						self.rdict = curval
					curval = curval[karr[idx]]
					idx += 1
				# now we should give the value
				curval[karr[idx]] = v
			retval = True
		except:
			logging.error('%s'%(traceback.format_exc()))
		return retval

	def get_value(self,k):
		karr = re.split('\\.',k)
		retval = None
		curval = self.rdict
		if len(karr) == 0:
			return curval
		else:
			idx = 0
			while idx < (len(karr)-1):
				if not isinstance(curval,dict):
					return None
				if karr[idx] not in curval.keys():
					return None
				curval = curval[karr[idx]]
				idx += 1
			if not isinstance(curval,dict):
				return None
			if karr[idx] not in curval.keys():
				return None
			return curval[karr[idx]]



