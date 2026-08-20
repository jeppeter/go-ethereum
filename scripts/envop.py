#! /usr/bin/env python

import os
import sys
import logging


def is_win():
	if sys.platform == 'win32':
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

def is_cygwin():
	if sys.platform == 'cygwin':
		return True
	return False
