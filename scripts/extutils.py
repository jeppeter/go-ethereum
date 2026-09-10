#! /usr/bin/env python


import os
import extargsparse
import sys
import traceback
import re
import logging
import subprocess
import cmdpack
import json
import signal
import time
import shutil
import rlp

sys.path.append(os.path.abspath(os.path.dirname(os.path.abspath(__file__))))

from loglib import set_logging, load_log_commandline,log_command_prefix
from fileop import read_file,write_file,make_directory_safe,mktemp_file,read_file_bytes,write_file_bytes
from envop import is_windows,is_linux
from tomlex import TomlEx
from strop import rand_buffer



class PebbleOperation(object):
    def __init__(self):
        self.opname = ''
        self.key = b''
        self.value = b''
        return

    def set_op(self,opname,key,value=None):
        self.opname = opname
        carr = re.split('\\s+',key)
        for c in carr:
            self.key += struct.pack('B',int(c))
        if value is not None:
            carr = re.split('\\s+',value)
            for c in carr:
                self.value += struct.pack('B',int(c))
        return


    def __str__(self):
        rets = '%s'%(self.opname)
        rets += ' ['
        for k in self.key:
            rets += ' %d'%(k)
        rets += ']'
        if len(self.value) > 0:
            rets += ' value ['
            for k in self.value:
                rets += ' %d'%(k)
            rets += ']'
        return rets




class ParsePebble(object):
    def __init__(self,f):
        self.file = f
        self.operations = []
        return

    def parse(self):
        ins = read_file(self.file)
        sarr = re.split('\n',ins)
        putexpr = re.compile('Put key\\s+\\[([^\\]]+)\\]\\s+value\\s+\\[([^\\]]+)\\]')
        deleteexpr = re.compile('Delete key\\s+\\[([^\\]]+)\\]')
        delrangeexpr = re.compile('DeleteRange start\\s+\\[([^\\]]+)\\]\\s+end\\s+\\[([^\\]]+)\\]')
        for l in sarr:
            l = l.rstrip('\r\n')
            logging.info('l[%s]'%(l))
            m = putexpr.findall(l)
            if m is not None and len(m) > 0:
                op = PebbleOperation()
                op.set_op('put', m[0][0],m[0][1])
                self.operations.append(op)
                continue
            m = deleteexpr.findall(l)
            if m is not None and len(m) > 0:
                op = PebbleOperation()
                op.set_op('delete',m[0])
                self.operations.append(op)
                continue
            m = delrangeexpr.findall(l)
            if m is not None and len(m) > 0:
                op = PebbleOperation()
                op.set_op('delrange',m[0][0],m[0][1])
                self.operations.append(op)
                continue
        return

    def __str__(self):
        outs = ''
        for op in self.operations:
            outs += '%s\n'%(op)
        return outs



def parsepebble_handler(args,parser):
    set_logging(args)
    for f in args.subnargs:
        p = ParsePebble(f)
        p.parse()
        sys.stdout.write('%s'%(p))        
    sys.exit(0)
    return


def rlpdec_handler(args,parser):
    set_logging(args)
    for f in args.subnargs:
        inb = read_file_bytes(f)
        rc = rlp.decode(inb)
        sys.stdout.write('%s\n'%(rc))
    sys.exit(0)
    return

def load_base_parser(parser):
    commandline_fmt='''
    {
        "input|i" : null,
        "output|o" : null,
        "catchpebble<%s.parsepebble_handler>##logfile ... to parse log for pebble handle##" : {
            "$" : "*"
        },
        "rlpdec<rlpdec_handler>##file ... to decode rlp##" : {
            "$" : "+"
        }
    }
    '''

    commandline = commandline_fmt%(__name__)
    parser.load_command_line_string(commandline)
    return parser


def main():
    parser = extargsparse.ExtArgsParse()
    load_log_commandline(parser)
    load_base_parser(parser)
    parser.parse_command_line(None,parser)
    raise Exception('can not here for no command handle')
    return


if __name__ == '__main__':
    main()	