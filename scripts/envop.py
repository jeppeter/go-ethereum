#! /usr/bin/env python

import os
import sys
import logging


def is_windows():
	if sys.platform == 'win32' or sys.platform == 'cygwin':
		return True
	return False

def is_unix():
	if sys.platform == 'linux':
		return True
	return False

def is_linux():
	if sys.platform == 'linux':
		return True
	return False