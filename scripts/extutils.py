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
import struct

sys.path.append(os.path.abspath(os.path.dirname(os.path.abspath(__file__))))

from loglib import set_logging, load_log_commandline,log_command_prefix
from fileop import read_file,write_file,make_directory_safe,mktemp_file,read_file_bytes,write_file_bytes
from envop import is_windows,is_linux
from tomlex import TomlEx
from strop import rand_buffer


SnapshotRoot=b'SnapshotRoot'
SnapshotGenerator=b'SnapshotGenerator'
GenesisPrefix=b'ethereum-genesis-'
BlockBodyPrefix=b'b'

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
        if value is not None and len(value) > 0:
            carr = re.split('\\s+',value)
            for c in carr:
                self.value += struct.pack('B',int(c))
        return

    def _default_value(self):
        rets = ' ('
        rets += '['
        idx = 0
        while idx < len(self.key):
            if idx > 0:
                rets += ' '
            rets += '%d'%(self.key[idx])
            idx += 1
        rets += ']'
        if len(self.value) > 0:
            rets += ' value ['
            idx = 0
            while idx < len(self.value):
                if idx > 0:
                    rets += ' '
                rets += '%d'%(self.value[idx])
                idx += 1
            rets += ']'
        rets += ')'
        return rets

    def _fmt_hex(self,hexb,note):
        rets = ' .%s 0x'%(note)
        idx = 0
        while idx < len(hexb):
            rets += '%02x'%(hexb[idx])
            idx += 1
        if len(hexb) == 0:
            rets += '0'
        return rets

    def _fmt_snapshot_root(self):
        rets = 'SnapshotRoot %s'%(self._fmt_hex(self.value,'hash'))
        return rets

    def _fmt_bool(self,inb):
        if len(inb) == 0:
            return  'False'
        return 'True'

    def _fmt_byte(self,inb):
        rets = 'byte("'
        idx = 0
        while idx < len(inb):
            if idx == 0:
                rets += '0x'
            rets += '%02x'%(inb[idx])
            idx += 1
        rets += '")'
        return rets

    def _fmt_uint64(self,inb):
        retval = 0
        idx = 0
        while idx < len(inb):
            retval <<= 8
            retval += inb[idx]
            idx += 1
        rets = '0x%x'%(retval)
        return rets

    def _fmt_snapshot_generator(self):
        rets = 'SnapshotGenerator '
        rc = rlp.decode(self.value)
        if len(rc) >= 6:
            rets += ' .Wiping %s'%(self._fmt_bool(rc[0]))
            rets += ' .Done %s'%(self._fmt_bool(rc[1]))
            rets += ' .Maker %s'%(self._fmt_byte(rc[2]))
            rets += ' .Accounts %s'%(self._fmt_uint64(rc[3]))
            rets += ' .Slots %s'%(self._fmt_uint64(rc[4]))
            rets += ' .Storage %s'%(self._fmt_uint64(rc[5]))
        else:
            rets += ' %s'%(rc)
        return rets

    def _fmt_code(self):
        rets = 'Code '
        rets += self._fmt_hex(self.key[1:],'key')
        rets += ' %s'%(self._fmt_hex(self.value,'value'))
        return rets

    def _fmt_state_idkey(self):
        rets = 'State Key'
        rets += ' %s'%(self._fmt_hex(self.key[1:],'root'))
        rets += ' %s'%(self._fmt_hex(self.value,'id'))
        return rets

    def _fmt_genesis_state_key(self):
        rets = ' Genesis State Key'
        rets += ' %s'%(self._fmt_hex(self.key[len(GenesisPrefix):],'blockhash'))
        try:
            jsons = self.value.decode('utf-8')
            rdict = json.loads(jsons)
            idx = 0
            rets += ' .value ['
            for k,v in rdict.items():
                idx += 1
                if idx > 1:
                    rets += ','
                    
                rets += '%s :{ '%(k)
                cidx = 0
                for ck,cv in v.items():
                    cidx += 1
                    if cidx > 1:
                        rets += ','
                    rets += ' .%s : %s '%(ck,cv)
                rets += '}'
            rets += ']'
        except:
            logging.error('%s'%(traceback.format_exc()))
            rets += '%s'%(self._fmt_hex(self.value,'value'))
        return rets

    def _fmt_block_body(self):
        rets = ' Block body '
        if len(self.key) < 9:
            raise Exception('key for Block body %d < 9'%(len(self.key)))
        blknumber = 0
        idx = 1
        while idx < 9:
            blknumber <<= 8
            blknumber += self.key[idx]
            idx += 1

        rets += ' .number 0x%x'%(blknumber)
        rets += ' .hash 0x'
        idx = 9
        while idx < len(self.key):
            rets += '%02x'%(self.key[idx])
            idx += 1
        try:
            rc = rlp.decode(self.value)
            if len(rc) == 0:
                rets += ' .value None'
            else:
                rets += ' .value ['
                cidx = 0
                while cidx < len(rc):
                    k = rc[cidx]
                    if cidx > 0:
                        rets += ','
                    if len(k) > 0:
                        rets += ' .transactions ['
                        tidx = 0
                        ts = k[0]
                        while tidx < len(ts):
                            if tidx > 0:
                                rets += ','                                
                            tidx += 1
                        rets += ']'
                    if len(k) > 1:
                        rets += ' .uncles ['
                        uidx = 0
                        us = k[1]
                        while uidx < len(us):
                            if uidx > 0:
                                rets += ','
                            uidx += 1
                        rets += ']'
                    if len(k) > 2:
                        rets += ' .withdraws ['
                        widx = 0
                        ws = k[2]
                        while widx < len(ws):
                            if widx > 0:
                                rets += ','
                            widx += 1
                        rets += ']'
                    cidx += 1
                rets += ']'

        except:
            logging.error('%s'%(traceback.format_exc()))
            rets += ' .value not parse'
        return rets




    def __str__(self):
        rets = '%s '%(self.opname)
        if len(self.key) == len(SnapshotRoot) and self.key == SnapshotRoot:
            rets += self._fmt_snapshot_root()
        elif len(self.key) == len(SnapshotGenerator) and self.key == SnapshotGenerator:
            rets += self._fmt_snapshot_generator()
        elif len(self.key) > 1 and self.key[0] == ord('c'):
            rets += self._fmt_code()
        elif len(self.key) > 1 and self.key[0] == ord('L'):
            rets += self._fmt_state_idkey()
        elif len(self.key) > len(GenesisPrefix) and self.key[:len(GenesisPrefix)] == GenesisPrefix:
            rets += self._fmt_genesis_state_key()
        elif len(self.key) >= len(BlockBodyPrefix) and self.key[:len(BlockBodyPrefix)] == BlockBodyPrefix:
            rets += self._fmt_block_body()
        rets += self._default_value()
        return rets




class ParsePebble(object):
    def __init__(self,f):
        self.file = f
        self.operations = []
        return

    def parse(self):
        ins = read_file(self.file)
        sarr = re.split('\n',ins)
        putexpr = re.compile('Put key\\s+\\[([^\\]]+)\\]\\s+value\\s+\\[([^\\]]*)\\]')
        deleteexpr = re.compile('Delete key\\s+\\[([^\\]]*)\\]')
        delrangeexpr = re.compile('DeleteRange start\\s+\\[([^\\]]+)\\]\\s+end\\s+\\[([^\\]]*)\\]')
        for l in sarr:
            l = l.rstrip('\r\n')
            #logging.info('l[%s]'%(l))
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