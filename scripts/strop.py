#! /usr/bin/env python


import sys
import os
import re
import struct
import logging
import inspect
import base64


sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import loglib
import extargsparse

def get_buffer_value(c):
    if sys.version[0] == '3':
        return c
    return struct.unpack('B', c)[0]


def parse_k_value(s):
    kval = 0
    matchexpr = re.compile('([0-9]+)([kKmMgGtT]?)')
    m = matchexpr.findall(s)
    if m is not None and len(m) >= 1 and len(m[0]) >= 2:
        kval = int(m[0][0])
        if m[0][1] == 'k' or m[0][1] == 'K':
            kval *= 1024
        elif m[0][1] == 'm' or m[0][1] == 'M':
            kval *= 1024 * 1024
        elif m[0][1] == 'g' or m[0][1] == 'G':
            kval *= 1024 * 1024 * 1024
        elif m[0][1] == 't' or m[0][1] == 'T':
            kval *= 1024 * 1024 * 1024 * 1024
        elif m[0][1] == 'p' or m[0][1] == 'P':
            kval *= 1024 * 1024 * 1024 * 1024 * 1024
        elif m[0][1] == 'e' or m[0][1] == 'E':
            kval *= 1024 * 1024 * 1024 * 1024 * 1024 * 1024
    return kval



def dump_buffer(buf,fmt='',stkidx=1):
    i = 0
    lasti = 0
    s = ''
    _,fn,ln,_,_,_ = inspect.stack()[stkidx]
    s += '[%s:%d] '%(fn,ln)
    s += fmt

    while buf is not None and i < len(buf):
        if (i % 16) == 0 :
            if i > 0:
                s += ' ' * 4
                while lasti != i:
                    iv = get_buffer_value(buf[lasti])
                    if iv >= ord(' ') and iv <= ord('~'):
                        s += '%c'%(buf[lasti])
                    else:
                        s += '.'
                    lasti += 1
                s += '\n'
            elif len(fmt) > 0:
                s += '\n'
            s += '0x%08x:'%(i)
        iv = get_buffer_value(buf[i])
        s += ' 0x%02x'%(iv)
        i += 1

    if i != lasti:
        while (i % 16) != 0:
            s += ' ' * 5
            i += 1
        s += ' ' * 4
        while lasti != len(buf):
            iv = get_buffer_value(buf[lasti])
            if iv >= ord(' ') and iv <= ord('~'):
                s += '%c'%(buf[lasti])
            else:
                s += '.'
            lasti += 1
    return s

def dump_ints(intarr,fmt=''):
    i = 0
    lasti = 0
    s = ''
    s += fmt
    while i < len(intarr):
        if (i % 16) == 0 :
            if i > 0:
                s += ' ' * 4
                while lasti != i:
                    iv = intarr[lasti]
                    if iv >= ord(' ') and iv <= ord('~'):
                        s += '%c'%(chr(intarr[lasti]))
                    else:
                        s += '.'
                    lasti += 1
                s += '\n'
            elif len(fmt) > 0:
                s += '\n'
            s += '0x%08x:'%(i)
        iv = int(intarr[i])
        s += ' 0x%02x'%(iv)
        i += 1

    if i != lasti:
        while (i % 16) != 0:
            s += ' ' * 5
            i += 1
        s += ' ' * 4
        while lasti != len(intarr):
            iv = intarr[lasti]
            if iv >= ord(' ') and iv <= ord('~'):
                s += '%c'%(chr(intarr[lasti]))
            else:
                s += '.'
            lasti += 1
    return s



def sort_and_uniq(sarr):
    retsarr = []
    idx = 0
    sarr.sort()
    if len(sarr) > 0:
        retsarr.append(sarr[0])

    idx = 1
    while idx < len(sarr):
        if retsarr[-1] != sarr[idx]:
            retsarr.append(sarr[idx])
        idx += 1
    return retsarr


def parse_input_sarr(ins):
    sarr = re.split('\n',ins)
    retval = []
    for l in sarr:
        l = l.rstrip('\r')
        if l.startswith('#') or len(l) == 0:
            continue
        carr = re.split('\\s+', l)
        for nk in carr:
            if len(nk) > 0:
                retval.append(nk)
    return retval

def parse_int_with_comma(v):
    try:
        vs = v.replace(',','')
        return int(vs)
    except:
        return 0

def parse_float_with_comma(v):
    try:
        vs = v.replace(',','')
        return float(vs)
    except:
        return 0.0


def parse_int(v):
    c = v
    base = 10
    if c.startswith('0x') or c.startswith('0X') :
        base = 16
        c = c[2:]
    elif c.startswith('x') or c.startswith('X'):
        base = 16
        c = c[1:]
    return int(c,base)


class Maxsize:
    def __init__(self):
        self.maxsize = 0
        return

    def set_max_length(self,s):
        if len(s) > self.maxsize:
            self.maxsize = len(s)
        return


def format_output_sarr(sarr,maxnum):
    msize = Maxsize()
    for l in nlist:
        msize.set_max_length(l)

    indx = 0
    outs = ''
    for l in nlist:
        indx += 1
        if (indx % maxnum) == 1:
            outs += '%-*s'%(msize.maxsize,l)
        else:
            outs += ' %-*s'%(msize.maxsize,l)
        if (indx % maxnum) == 0:
            outs += '\n'
    return outs

def rand_bytes(numbyte):
    cb = os.urandom(numbyte)
    rets = ''
    indx = 0
    while indx < len(cb):
        cn = struct.unpack('B',cb[indx])[0]
        rets += '%02x'%(cn)
        indx += 2
    return rets

def rand_buffer(numbyte,tobase64=False):
    outb = os.urandom(numbyte)
    if tobase64:
        ob = base64.b64encode(outb)
        return ob.decode('utf-8')
    else:
        return outb


def rb_handler(args,parser):
    loglib.set_logging(args)
    val = parse_int(args.subnargs[0])
    vs = rand_bytes(val)
    sys.stdout.write('%s [%s]\n'%(args.subnargs[0],vs))
    sys.exit(0)
    return

def randbuf_handler(args,parser):
    loglib.set_logging(args)
    for v in args.subnargs:
        iv = parse_int(v)
        bf = rand_buffer(iv,True)
        sys.stdout.write('%s\n'%(bf))
    sys.exit(0)
    return

def main():
    commandline='''
    {
        "input|i" : null,
        "output|o" : null,
        "rb<rb_handler>##to give rand bytes##" : {
            "$" : 1
        },
        "randbuf<randbuf_handler>##to give rand bytes in base64##" : {
            "$" : "+"
        }
    }
    '''
    parser = extargsparse.ExtArgsParse()
    parser.load_command_line_string(commandline)
    loglib.load_log_commandline(parser)
    parser.parse_command_line(None,parser)
    raise Exception('can not reach here')
    return

if __name__ == '__main__':
    main()
