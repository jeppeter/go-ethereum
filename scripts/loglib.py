#! /usr/bin/env python

import logging
import sys

from logging import handlers


def set_logging(args):
	loglvl= logging.ERROR
	if args.verbose >= 3:
		loglvl = logging.DEBUG
	elif args.verbose >= 2:
		loglvl = logging.INFO
	curlog = logging.getLogger(args.lognames)
	#sys.stderr.write('curlog [%s][%s]\n'%(args.logname,curlog))
	curlog.setLevel(loglvl)
	if len(curlog.handlers) > 0 :
		curlog.handlers = []
	formatter = logging.Formatter('%(asctime)s:%(filename)s:%(funcName)s:%(lineno)d<%(levelname)s>\t%(message)s')
	if not args.lognostderr:
		logstderr = logging.StreamHandler()
		logstderr.setLevel(loglvl)
		logstderr.setFormatter(formatter)
		curlog.addHandler(logstderr)

	for f in args.logfiles:
		flog = logging.FileHandler(f,mode='w',delay=False)
		flog.setLevel(loglvl)
		flog.setFormatter(formatter)
		curlog.addHandler(flog)
	for f in args.logappends:		
		if args.logrotate:
			flog = handlers.RotatingFileHandler(f,mode='a',maxBytes=args.logmaxbytes,backupCount=args.logbackupcnt,delay=0)
		else:
			sys.stdout.write('appends [%s] file\n'%(f))
			flog = logging.FileHandler(f,mode='a',delay=0)
		flog.setLevel(loglvl)
		flog.setFormatter(formatter)
		curlog.addHandler(flog)
	return

def load_log_commandline(parser):
	logcommand = '''
	{
		"verbose|v" : "+",
		"logname" : "root",
		"logfiles" : [],
		"logappends" : [],
		"logrotate" : true,
		"logmaxbytes" : 10000000,
		"logbackupcnt" : 2,
		"lognostderr" : false
	}
	'''
	parser.load_command_line_string(logcommand)
	return parser

def log_command_prefix():
    logging.info('==================================')
    logging.info('commande line input')
    logging.info('%s'%(sys.argv))
    logging.info('==================================')
    return
