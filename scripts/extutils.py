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
from Crypto.Hash import keccak


sys.path.append(os.path.abspath(os.path.dirname(os.path.abspath(__file__))))

from loglib import set_logging, load_log_commandline,log_command_prefix
from fileop import read_file,write_file,make_directory_safe,mktemp_file,read_file_bytes,write_file_bytes
from envop import is_windows,is_linux
from tomlex import TomlEx
from strop import rand_buffer


SnapshotRoot=b'SnapshotRoot'
SnapshotGenerator=b'SnapshotGenerator'
GenesisPrefix=b'ethereum-genesis-'
configPrefix=b'ethereum-config-'
BlockBodyPrefix=b'b'
CodePrefix=b'c'
stateIDPrefix=b'L'
headerNumberPrefix=b'H'
headerPrefix=b'h'
headerHashSuffix=b'n'
blockReceiptsPrefix=b'r'
TrieNodeAccountPrefix=b'A'
NUMBER8_SIZE = 8

def calc_rlp_hash(inb):
    nhash = keccak.new(digest_bits=256)
    nhash.update(inb)
    return nhash.hexdigest()


class PebbleOperation(object):
    def __init__(self):
        self.opname = ''
        self.key = b''
        self.value = b''
        self.lineno = -1
        return

    def set_op(self,opname,key,value=None,lineno=None):
        self.opname = opname
        carr = re.split('\\s+',key)
        for c in carr:
            self.key += struct.pack('B',int(c))
        if value is not None and len(value) > 0:
            carr = re.split('\\s+',value)
            for c in carr:
                self.value += struct.pack('B',int(c))
        if lineno is not None:
            self.lineno = lineno
        return

    def _default_value(self):
        rets = ' ('
        rets += ' key ['
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
                if len(rc) > 0:                    
                    rets += ' .transactions ['
                    tidx = 0
                    ts = rc[0]
                    while tidx < len(ts):
                        if tidx > 0:
                            rets += ','                                
                        tidx += 1
                    rets += ']'
                if len(rc) > 1:
                    rets += ' ,.uncles ['
                    uidx = 0
                    us = rc[1]
                    while uidx < len(us):
                        if uidx > 0:
                            rets += ','
                        uidx += 1
                    rets += ']'
                if len(rc) > 2:
                    rets += ' ,.withdraws ['
                    widx = 0
                    ws = k[2]
                    while widx < len(ws):
                        if widx > 0:
                            rets += ','
                        widx += 1
                    rets += ']'
                rets += ']'

        except:
            logging.error('%s'%(traceback.format_exc()))
            rets += ' .value not parse'
        return rets


    def _fmt_header_number(self):
        rets = ' Header Number'
        rets += ' .hash 0x'
        idx = 1
        while idx < len(self.key):
            rets += '%02x'%(self.key[idx])
            idx += 1

        rets += ' .number 0x'
        idx = 0
        while idx < len(self.value):
            rets += '%02x'%(self.value[idx])
            idx += 1
        return rets

    def _fmt_header_part(self,rc,idx,note):
        rets = ''
        if len(rc) > idx:
            if idx > 0:
                rets += ' ,.%s 0x'%(note)
            else:
                rets += ' .%s 0x'%(note)
            cidx = 0
            curb = rc[idx]
            while cidx < len(curb):
                rets += '%02x'%(curb[cidx])
                cidx += 1
            if len(curb) == 0:
                rets += '00'
        else:
            if idx > 0:
                rets += ' .%s None'%(note)
            else:
                rets += ' ,.%s None'%(note)
        return rets


    def _fmt_header(self):
        rets = ' Header'
        rets += ' .nubmer 0x' 
        idx = 1
        while idx < (1 + NUMBER8_SIZE) and idx < len(self.key):
            rets += '%02x'%(self.key[idx])
            idx += 1
        rets += ' .hash 0x'
        idx = 1 + NUMBER8_SIZE
        while idx < len(self.key):
            rets += '%02x'%(self.key[idx])
            idx += 1
        rc = rlp.decode(self.value)

        rets += ' .header {'
        rets += self._fmt_header_part(rc,0,'parentHash')
        rets += self._fmt_header_part(rc,1,'sha3Uncles')
        rets += self._fmt_header_part(rc,2,'miner')
        rets += self._fmt_header_part(rc,3,'stateRoot')
        rets += self._fmt_header_part(rc,4,'transactionsRoot')
        rets += self._fmt_header_part(rc,5,'receiptsRoot')
        rets += self._fmt_header_part(rc,6,'logsBloom')
        rets += self._fmt_header_part(rc,7,'difficulty')
        rets += self._fmt_header_part(rc,8,'number')
        rets += self._fmt_header_part(rc,9,'gasLimit')
        rets += self._fmt_header_part(rc,10,'gasUsed')
        rets += self._fmt_header_part(rc,11,'timestamp')
        rets += self._fmt_header_part(rc,12,'extraData')
        rets += self._fmt_header_part(rc,13,'mixHash')
        rets += self._fmt_header_part(rc,14,'nonce')
        rets += self._fmt_header_part(rc,15,'baseFeePerGas')
        rets += self._fmt_header_part(rc,16,'withdrawalsRoot')
        rets += self._fmt_header_part(rc,17,'blobGasUsed')
        rets += self._fmt_header_part(rc,18,'excessBlobGas')
        rets +=  self._fmt_header_part(rc,19,'parentBeaconBlockRoot')
        rets += ' ,.requestsHash 0x%s'%(calc_rlp_hash(self.value))
        rets += '}'
        return rets

    def _fmt_header_hash(self):
        rets = ' Header Hash'
        rets += ' .number 0x'
        idx = 1
        while idx < (1+NUMBER8_SIZE):
            rets += '%02x'%(self.key[idx])
            idx += 1

        rets += ' .hash 0x'
        idx = 0
        while idx < len(self.value):
            rets += '%02x'%(self.value[idx])
            idx += 1
        return rets

    def _fmt_block_receipts(self):
        rets = ' Block Receipts'
        rets += ' .number 0x'
        idx = 1
        while idx < (1+ NUMBER8_SIZE):
            rets += '%02x'%(self.key[idx])
            idx += 1
        idx = 1 + NUMBER8_SIZE
        rets += ' .hash 0x'
        while idx < len(self.key):
            rets += '%02x'%(self.key[idx])
            idx += 1

        rc = rlp.decode(self.value)
        rets += ' .receipts ['
        idx = 0
        while idx < len(rc):
            idx += 1
        rets += ']'
        return rets

    def _fmt_config(self):
        rets = ' Config'
        rets += ' .hash 0x'
        idx = len(configPrefix)
        while idx < len(self.key):
            rets += '%02x'%(self.key[idx])
            idx += 1
        try:
            rs = self.value.decode('utf-8')
            rets += ' .value %s'%(rs)
        except:
            logging.error('decode config error\n%s'%(traceback.format_exc()))
            rets += ' .config None'
        return rets

    def _fmt_account(self):
        rets = ' Account'
        return rets


    def __str__(self):
        rets = '%s '%(self.opname)
        if len(self.key) == len(SnapshotRoot) and self.key == SnapshotRoot:
            rets += self._fmt_snapshot_root()
        elif len(self.key) == len(SnapshotGenerator) and self.key == SnapshotGenerator:
            rets += self._fmt_snapshot_generator()
        elif len(self.key) > len(CodePrefix) and self.key[:len(CodePrefix)] == CodePrefix:
            rets += self._fmt_code()
        elif len(self.key) > len(stateIDPrefix) and self.key[:len(stateIDPrefix)] == stateIDPrefix:
            rets += self._fmt_state_idkey()
        elif len(self.key) > len(GenesisPrefix) and self.key[:len(GenesisPrefix)] == GenesisPrefix:
            rets += self._fmt_genesis_state_key()
        elif len(self.key) >= len(BlockBodyPrefix) and self.key[:len(BlockBodyPrefix)] == BlockBodyPrefix:
            rets += self._fmt_block_body()
        elif len(self.key) > len(headerNumberPrefix) and self.key[:len(headerNumberPrefix)] == headerNumberPrefix:
            rets += self._fmt_header_number()
        elif len(self.key) > len(headerPrefix) and self.key[:len(headerPrefix)] == headerPrefix and len(self.key) == (len(headerPrefix) + NUMBER8_SIZE + len(headerHashSuffix)) and self.key[-(len(headerHashSuffix)):] == headerHashSuffix:
            rets += self._fmt_header_hash()
        elif len(self.key) > len(headerPrefix) and self.key[:len(headerPrefix)] == headerPrefix:
            rets += self._fmt_header()
        elif len(self.key) > len(blockReceiptsPrefix) and self.key[:len(blockReceiptsPrefix)] == blockReceiptsPrefix:
            rets += self._fmt_block_receipts()
        elif len(self.key) > len(configPrefix) and self.key[:len(configPrefix)] == configPrefix:
            rets += self._fmt_config()
        elif len(self.key) > len(TrieNodeAccountPrefix) and self.key[:len(TrieNodeAccountPrefix)] == TrieNodeAccountPrefix:
            rets += self._fmt_account()
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
        lindex = 0
        for l in sarr:
            lindex += 1
            l = l.rstrip('\r\n')
            #logging.info('l[%s]'%(l))
            m = putexpr.findall(l)
            if m is not None and len(m) > 0:
                op = PebbleOperation()
                op.set_op('put', m[0][0],m[0][1],lindex)
                self.operations.append(op)
                continue
            m = deleteexpr.findall(l)
            if m is not None and len(m) > 0:
                op = PebbleOperation()
                op.set_op('delete',m[0],[],lindex)
                self.operations.append(op)
                continue
            m = delrangeexpr.findall(l)
            if m is not None and len(m) > 0:
                op = PebbleOperation()
                op.set_op('delrange',m[0][0],m[0][1],lindex)
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
        for cp in p.operations:
            sys.stdout.write('%s\n'%(cp))
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

def rlphash_handler(args,parser):
    set_logging(args)
    for f in args.subnargs:
        inb = read_file_bytes(f)
        sys.stdout.write('[%s] %s\n'%(f,calc_rlp_hash(inb)))
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
        },
        "rlphash<rlphash_handler>##file ... to make sha256 values##" : {
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