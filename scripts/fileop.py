#! /usr/bin/env

import sys
import os
import logging
import hashlib
import platform
import struct
import random
import time
import math
import re
import tarfile
import gzip
import traceback
import tempfile

sys.path.insert(0,os.path.join(os.path.dirname(__file__),'pythonlib'))
sys.path.append(os.path.abspath(os.path.dirname(os.path.abspath(__file__))))
import extargsparse
from loglib import set_logging,load_log_commandline
from strop import parse_int

class ReadTar(object):
    def __init__(self,fname):
        self.fname = fname
        self.tarobj = None
        return

    def open(self,types='r:gz'):
        if self.tarobj is not None:
            self.tarobj.close()
            self.tarobj = None
        self.tarobj = tarfile.open(self.fname,types)
        return

    def get_list(self):
        if self.tarobj is None:
            raise Exception('not opened %s'%(self.fname))
        retobj = []
        for info in self.tarobj:
            retobj.append(info)
        return retobj

    def extract_file_content(self,fname):
        if self.tarobj is None:
            raise Exception('not opened %s'%(self.fname))
        f = self.tarobj.extractfile(fname)
        inb = f.read()
        return inb


class ReadGzip(object):
    def __init__(self,filename=None,types="rb"):
        self.fname = filename
        if filename is None:
            self.fname = sys.stdin.buffer
        self.fobj = gzip.open(self.fname,types)
        self.fbuf = b''
        return

    def _find_partbuf(self):
        idx = 0
        fidx = -1
        while idx < len(self.fbuf):
            if self.fbuf[idx]  == b'\n':
                fidx = idx
                break
            idx += 1
        if fidx >= 0:
            retbuf = self.fbuf[:fidx]
            self.fbuf = self.fbuf[fidx:]
            return retbuf
        return None


    def __iter__(self):
        if self.fobj is not None:
            while True:
                cbuf = self.fobj.read(1024*128)
                if cbuf is None or len(cbuf) == 0:
                    break
                self.fbuf += cbuf
                while True:
                    retbuf = self._find_partbuf()
                    if retbuf is None:
                        break
                    yield retbuf.decode('utf-8')
            while True:
                retbuf = self._find_partbuf()
                if retbuf is None:
                    break
                yield retbuf.decode('utf-8')
            if len(self.fbuf) != 0:
                yield self.fbuf.decode('utf-8')
                self.fbuf = b''
            self.fobj.close()
            self.fobj = None



class ReadFileLarge(object):
    def __init__(self,fname=None):
        self.fname = fname
        if fname is not None:
            self.fh = open(fname,'r')
        else:
            self.fh = sys.stdin
        self.readb = b''
        self.sidx = 0
        self.linenum = 0
        return

    def __del__(self):
        if self.fh != sys.stdin and self.fh is not None:
            self.fh.close()
        self.fh = None
        return

    def _append_rbuf(self,blocksize):
        if 'b' in self.fh.mode:
            curb = self.fh.read(blocksize)
        else:
            curb = self.fh.buffer.read()
        if curb is None or len(curb) == 0:
            return b''
        logging.info('curb %d'%(len(curb)))
        return curb

    def _search_linefeed(self):
        news = None
        curidx = self.sidx
        while curidx < len(self.readb):
            if self.readb[curidx] == 0xa:
                try:
                    if sys.version[0] == '3':
                        news = self.readb[self.sidx:(curidx+1)].decode('utf-8')
                    else:
                        news = str(self.readb[self.sidx:(curidx+1)])
                    self.sidx = curidx + 1
                    return news
                except:
                    self.readb = self.readb[(curidx+1):]
                    self.sidx = 0
                    return None
            curidx += 1
        if self.sidx != 0:
            self.readb = self.readb[self.sidx:]
            self.sidx = 0
        return None

    def _next_step(self):
        while True:
            nline = self._search_linefeed()
            if nline is not None:
                self.linenum += 1
                return nline
            #logging.info('readb %d'%(len(self.readb)))
            # it is none so read again
            nb = self._append_rbuf((1 << 20))
            if nb is None or len(nb) == 0:
                if len(self.readb) > 0:
                    try:
                        if sys.version[0] == '3':
                            news = self.readb.decode('utf-8')
                        else:
                            news = str(self.readb)
                        self.readb = b''
                        self.sidx = 0
                        self.linenum += 1
                        return news
                    except:
                        raise StopIteration
                else:
                    raise StopIteration
            else:
                self.readb += nb

    def __iter__(self):        
        while True:
            try:
                val = self._next_step()
                yield val
            except StopIteration:
                break

    def __next__(self):
        return self._next_step()


class Utf8Encode(object):
    def __dict_utf8(self,val):
        newdict =dict()
        for k in val.keys():
            newk = self.__encode_utf8(k)
            newv = self.__encode_utf8(val[k])
            newdict[newk] = newv
        return newdict

    def __list_utf8(self,val):
        newlist = []
        for k in val:
            newk = self.__encode_utf8(k)
            newlist.append(newk)
        return newlist

    def __encode_utf8(self,val):
        retval = val

        if sys.version[0]=='2' and isinstance(val,unicode):
            retval = val.encode('utf8')
        elif isinstance(val,dict):
            retval = self.__dict_utf8(val)
        elif isinstance(val,list):
            retval = self.__list_utf8(val)
        return retval

    def __init__(self,val):
        self.__val = self.__encode_utf8(val)
        return

    def __str__(self):
        return self.__val

    def __repr__(self):
        return self.__val
    def get_val(self):
        return self.__val


def init_random():
    random.seed(int(time.time()))

def get_random_int(maxnum):
    return random.randint(0,maxnum)


def make_directory_safe(dname,mode=0o755):
    retval = True
    try:
        if dname is not None:
            os.makedirs(dname,mode=mode,exist_ok=True)
    except:
        logging.error('%s'%(traceback.format_exc()))
        retval = False
    return retval


def mktemp_dir(ind=None):
    tempd = None
    try:
        if ind is None:
            ind = os.getcwd()
        retval = make_directory_safe(ind)
        if not retval:
            return None
        tempd = tempfile.mkdtemp(dir=ind)
    except:
        logging.error('%s'%(traceback.format_exc()))
    return tempd

def mktemp_file(templ='tempfile.XXXXXX',ind=None):
    tempf = None
    try:
        if ind is None:
            ind = os.getcwd()
        retval = make_directory_safe(ind)
        if not retval:
            return None
        sarr = re.split('X{6,}',templ)
        if len(sarr) == 1:
            logging.warning('%s not match XXXXXX more 6'%(templ))
        prefix = None
        suffix = None
        if len(sarr[0]) > 0:
            prefix = sarr[0]
        if len(sarr) > 1 and len(sarr[1]) > 0:
            suffix = sarr[1]
        fd , tempf = tempfile.mkstemp(suffix=suffix,prefix=prefix,dir=ind)
        os.close(fd)
        fd = -1
    except:
        logging.error('%s'%(traceback.format_exc()))
    return tempf



def format_bytes(inb,note=''):
    rets = '%s'%(note)
    idx = 0
    lastidx = 0
    for b in inb:
        if (idx % 16) == 0:
            if idx > 0:
                rets += '    '
                while lastidx != idx:
                    curv = inb[lastidx]
                    if curv >= ord(' ') and curv <= ord('~'):
                        rets += '%c'%(curv)
                    else:
                        rets += '.'
                    lastidx += 1
            rets += '\n0x%08x'%(idx)
        rets += ' 0x%02x'%(b)
        idx += 1

    if idx != lastidx:
        while (idx % 16) != 0:
            rets += '     '
            idx += 1
        rets += '    '
        while lastidx < len(inb):
            curv = inb[lastidx]
            if curv >= ord(' ') and curv <= ord('~'):
                rets += '%c'%(curv)
            else:
                rets += '.'
            lastidx += 1
        rets += '\n'
    return rets

def format_int_val(intv, note=''):
    sarr = []
    lastv = intv
    while lastv > 0:
        curv = lastv & 0xff
        sarr.insert(0,curv)
        lastv = lastv >> 8

    rets = '%s'%(note)
    idx = 0
    lastidx = 0
    while idx < len(sarr):
        if (idx % 16) == 0:
            if idx > 0:
                rets += '    '
                while lastidx != idx:
                    curv = sarr[lastidx]
                    if curv >= ord(' ') and curv <= ord('~'):
                        rets += '%c'%(curv)
                    else:
                        rets += '.'
                    lastidx += 1
            rets += '\n0x%08x'%(idx)
        rets += ' 0x%02x'%(sarr[idx])
        idx += 1

    if idx != lastidx:
        while (idx % 16) != 0:
            rets += '     '
            idx += 1
        rets += '    '
        while lastidx < len(sarr):
            curv = sarr[lastidx]
            if curv >= ord(' ') and curv <= ord('~'):
                rets += '%c'%(curv)
            else:
                rets += '.'
            lastidx += 1
        rets += '\n'
    return rets



def is_in_windows():
    s = platform.system().lower()
    if s == 'windows':
        return True
    return False


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
            flog = logging.handlers.RotatingFileHandler(f,mode='a',maxBytes=args.logmaxbytes,backupCount=args.logbackupcnt,delay=0)
        else:
            sys.stdout.write('appends [%s] file\n'%(f))
            flog = logging.FileHandler(f,mode='a',delay=0)
        flog.setLevel(loglvl)
        flog.setFormatter(formatter)
        curlog.addHandler(flog)
    return

def read_file(infile=None):
    fin = sys.stdin
    if infile is not None:
        fin = open(infile,'rb')
    rets = ''
    if 'b' in fin.mode:
        rdata = b''
        while True:
            try:
                l = fin.read(64 * 1024)
                if l is None or len(l) == 0:
                    break
                rdata += l
            except:
                break
        if sys.version[0] == '3':
            rets = rdata.decode('utf-8')
        else:
            rets = rdata
    else:        
        for l in fin:
            s = l
            rets += s

    if fin != sys.stdin:
        fin.close()
    fin = None
    return rets

def read_file_bytes(infile=None):
    fin = sys.stdin
    if infile is not None:
        fin = open(infile,'rb')
    retb = b''
    while True:
        if fin != sys.stdin:
            curb = fin.read(1024 * 1024)
        else:
            curb = fin.buffer.read()
        if curb is None or len(curb) == 0:
            break
        retb += curb
    if fin != sys.stdin:
        fin.close()
    fin = None
    return retb


def write_file(s,outfile=None):
    fout = sys.stdout
    if outfile is not None:
        fout = open(outfile, 'w+b')
    outs = s
    if 'b' in fout.mode:
        outs = s.encode('utf-8')
    fout.write(outs)
    if fout != sys.stdout:
        fout.close()
    fout = None
    return 

def write_file_bytes(sarr,outfile=None):
    fout = sys.stdout
    if outfile is not None:
        fout = open(outfile, 'wb')
    if 'b' not in fout.mode:
        fout.buffer.write(sarr)
    else:        
        fout.write(sarr)
    if fout != sys.stdout:
        fout.close()
    fout = None
    return 

def get_file_md5(infile=None):
    retval = ''
    if infile is not None:
        md5chk = hashlib.md5()
        with open(infile,'rb') as fin:
            while True:
                bs = fin.read(1024 * 64)
                if bs is None or len(bs) == 0:
                    break
                md5chk.update(bs)
        retval = md5chk.hexdigest().lower()
    else:
        bs = read_file_bytes(infile)
        md5chk = hashlib.md5()
        md5chk.update(bs)
        retval = md5chk.hexdigest().lower()
    return retval

def make_dir_safe(basedir,throwexp=True):
    retval = False
    err = ''
    try:
        if not os.path.exists(basedir):
            os.makedirs(basedir)
        retval = True
    except:
        retval = False
        err = '%s'%(traceback.format_exc())
        logging.error('%s'%(err))
    if not retval and throwexp:
        raise Exception('%s'%(err))
    return retval

def display_file(f,c):
    sys.stdout.write('[%s] ----------\n'%(f))
    sys.stdout.write('%s'%(c))
    sys.stdout.write('\n[%s]++++++++++++++++\n'%(f))
    return

def read_handler(args,parser):
    set_logging(args)
    if len(args.subnargs) > 0:
        for f in args.subnargs:
            s = read_file(f)
            display_file(f,s)
    else:
        s = read_file()
        display_file('sys.stdin',s)
    sys.exit(0)
    return

def display_byte_file(f,bb):
    sys.stdout.write('[%s] -------------\n'%(f))
    idx = 0
    lastidx = 0
    while idx < len(bb):
        if (idx % 16) == 0:
            if idx > 0:
                sys.stdout.write('    ')
                while lastidx < idx:
                    cb = bb[lastidx]
                    if cb >= ord(' ') and cb <= ord('~'):
                        sys.stdout.write('%c'%(cb))
                    else:
                        sys.stdout.write('.')
                    lastidx += 1
                sys.stdout.write('\n')
            sys.stdout.write('0x%08x:'%(idx))
        sys.stdout.write(' 0x%02x'%(bb[idx]))
        idx += 1

    if (idx % 16) != 0:
        while (idx % 16) != 0:
            sys.stdout.write('     ')
            idx += 1
        sys.stdout.write('    ')
        while lastidx < len(bb):
            cb = bb[lastidx]
            if cb >= ord(' ') and cb <= ord('~'):
                sys.stdout.write('%c'%(cb))
            else:
                sys.stdout.write('.')
            lastidx += 1
        sys.stdout.write('\n')
    sys.stdout.write('[%s]+++++++++++++++++\n'%(f))
    return

def readbyte_handler(args,parser):
    set_logging(args)
    if len(args.subnargs) > 0:
        for f in args.subnargs:
            bb = read_file_bytes(f)
            display_byte_file(f,bb)
    else:
        bb = read_file_bytes()
        display_byte_file('sys.stdin',bb)
    sys.exit(0)
    return

def write_handler(args,parser):
    set_logging(args)
    s = read_file(args.input)
    if len(args.subnargs):
        for f in args.subnargs:
            write_file(s,f)
    else:
        write_file(s)
    sys.exit(0)
    return

def convert_bytes_to_ints(inb):
    retint = []
    idx = 0
    while idx < len(inb):
        retint.append(inb[idx])
        idx += 1
    return retint

def convert_ints_to_bytes(inints):
    retb = b''
    idx = 0
    while idx < len(inints):
        retb += struct.pack('B',inints[idx])
        idx += 1
    return retb


def diff_dir(srcd,dstd):
    srcfs = []
    dstfs = []
    cmpfs = []
    srcd = os.path.abspath(srcd)
    dstd = os.path.abspath(dstd)
    sf = []
    df = []
    if os.path.exists(srcd):
        sf = os.listdir(srcd)
        nf1 = []
        for f in sf:
            if f != '.' and f != '..':
                nf1.append(os.path.join(srcd,f))
        sf = nf1
    if os.path.exists(dstd):
        df = os.listdir(dstd)
        nf2 = []
        for f in df:
            if f != '.' and f != '..':
                nf2.append(os.path.join(dstd,f))
        df = nf2
    sidx = 0
    didx = 0
    sf = sorted(sf)
    df = sorted(df)

    while True:
        if sidx >= len(sf) and didx >= len(df):
            break
        sc = None
        dc = None
        sb = None
        db = None
        if sidx < len(sf):
            sc = sf[sidx]
            sb = os.path.basename(sc)
        if didx < len(df):
            dc = df[didx]
            db = os.path.basename(dc)
        logging.info('[%s][%d]sc [%s] [%s][%d]dc [%s]'%(srcd,sidx,sc,dstd,didx,dc))

        if sc is None and dc is not None:
            dstfs.append(dc)
            didx += 1            
        elif dc is None and sc is not None:
            srcfs.append(sc)
            sidx += 1
        elif sb < db:
            srcfs.append(sc)
            sidx += 1
        elif db < sb:
            dstfs.append(dc)
            didx += 1
        elif sb == db:
            if os.path.isfile(sc) and os.path.isfile(dc):
                smd5 = hashlib.md5(read_file_bytes(sc)).hexdigest()
                dmd5 = hashlib.md5(read_file_bytes(dc)).hexdigest()
                if smd5 != dmd5:
                    cmpfs.append(sc)
            elif os.path.isdir(sc) and os.path.isdir(dc):
                ns,nd,nc = diff_dir(sc,dc)
                srcfs.extend(ns)
                dstfs.extend(nd)
                cmpfs.extend(nc)
            else:
                cmpfs.append(sc)
            sidx += 1
            didx += 1
    
    return srcfs,dstfs,cmpfs

def get_path_split():
    if is_in_windows():
        return '\\'
    return '/'

def filter_path_array(partpath,sarr):
    retsarr = []
    sarr = sorted(sarr)
    idx = 0
    curf = None
    partpath = os.path.abspath(partpath)
    if is_in_windows():
        partpath += '\\'
    else:
        partpath += '/'
    while idx < len(sarr):
        if curf is None:
            curf = sarr[idx]
            idx += 1
            continue
        if sarr[idx].startswith(curf) and sarr[idx].startswith(curf + get_path_split()):
            idx += 1
            continue
        curf = curf.replace(partpath,'',1)
        retsarr.append(curf)
        curf = sarr[idx]
        idx += 1
        continue
    if curf is not None:
        curf = curf.replace(partpath,'',1)
        retsarr.append(curf)
    return retsarr

class MaxSize(object):
    def __init__(self):
        self.__obj = dict()
        return

    def __setattr__(self,name,val):
        if name.startswith('_'):
            self.__dict__[name] = val
            return
        defval = 1
        if name in self.__obj.keys():
            defval = self.__obj[name]
        if defval <= val:
            self.__obj[name] = (val + 1)
        return

    def __getattr__(self,name,val=None):
        if name.startswith('_'):
            return self.__dict__[name]
        if name not in self.__obj.keys():
            return 1
        return self.__obj[name]

    def __str__(self):
        s = '{'
        for k in self.__obj.keys():
            s += '%s=%s;'%(k,self.__obj[k])
        s += '}'
        return s

def format_slen_middle(s,slen):
    rets = ''
    if len(s) < slen:
        prel = int((slen - len(s)) / 2)
        sufl = slen - prel - len(s)
        rets = ' ' * prel
        rets += s
        rets += ' ' * sufl
    else:
        rets = '%s'%(s)
    return rets

def display_diff(srcd,dstd,srcfs,dstfs,cmpfs):
    srcfs = filter_path_array(srcd,srcfs)
    dstfs = filter_path_array(dstd,dstfs)
    cmpfs = sorted(cmpfs)
    s = ''
    ms = MaxSize()
    ms.slen = len(srcd)
    ms.dlen = len(dstd)
    ms.clen = 2
    for f in srcfs:
        ms.slen = len(f)
    for f in dstfs:
        ms.dlen = len(f)
    for f in cmpfs:
        ms.clen = len(f) + 2

    sidx = 0
    didx = 0
    cidx = 0    
    s = '%-*s|%-*s|%*s\n'%(ms.slen,srcd, ms.clen,' ',ms.dlen,dstd)
    while True:
        if sidx >= len(srcfs) and didx >= len(dstfs) and cidx >= len(cmpfs):
            break
        sf = None
        df = None
        cf = None
        selidx = 0
        selval = None
        if sidx < len(srcfs):
            sf = srcfs[sidx]
        if didx < len(dstfs):
            df = dstfs[didx]
        if cidx < len(cmpfs):
            cf = cmpfs[cidx]

        if sf is not None and df is not None and cf is not None:
            if sf < df and sf < cf:
                pass
            elif df < sf and df < cf:
                selidx = 2
            elif cf < sf and cf < df:
                selidx = 1
        elif sf is None:
            if df is None:
                selidx = 1
            elif cf is None:
                selidx = 2
            else:
                if cf < df:
                    selidx = 1
                else:
                    selidx = 2
        elif cf is None:
            if sf is None:
                selidx = 2
            elif df is None:
                pass
            else:
                if df < sf:
                    selidx = 2
        elif df is None:
            if sf is None:
                selidx = 1
            elif cf is None:
                pass
            else:
                if cf < sf:
                    selidx = 1
        logging.info('selidx [%d] sidx [%d] cidx[%d] didx [%d]'%(selidx,sidx,cidx,didx))
        if selidx == 0:
            s += '%-*s|%-*s|%*s'%(ms.slen,sf,ms.clen,' ',ms.dlen,' ')
            sidx += 1
        elif selidx == 1:
            s += '%-*s|%s|%*s'%(ms.slen,' ',format_slen_middle(cf,ms.clen),ms.dlen,' ')
            cidx += 1
        elif selidx == 2:
            s += '%-*s|%-*s|%*s'%(ms.slen,' ',ms.clen,' ',ms.dlen,df)
            didx += 1
        s += '\n'
    return s

def diff_handler(args,parser):
    set_logging(args)
    srcd = args.subnargs[0]
    dstd = args.subnargs[1]
    sd , dd , cd = diff_dir(srcd,dstd)
    s = display_diff(srcd,dstd,sd,dd,cd)
    write_file(s,args.output)
    sys.exit(0)
    return

def writebyte_handler(args,parser):
    set_logging(args)
    srcf = None
    dstf = None
    if len(args.subnargs) > 0:        
        srcf = args.subnargs[0]
        if srcf == '-':
            srcf = None
    if len(args.subnargs) > 1:
        dstf = args.subnargs[1]
        if dstf == '-':
            dstf = None
    sarr = read_file_bytes(srcf)
    write_file_bytes(sarr,dstf)
    sys.exit(0)
    return


def padzero_handler(args,parser):
    set_logging(args)
    align = 16
    if len(args.subnargs) > 0:
        align = int(args.subnargs[0])
    inbuf = read_file_bytes(args.input)
    outbuf = convert_bytes_to_ints(inbuf)
    while (len(outbuf) % align) != 0:
        outbuf.append(0)
    outbuf = convert_ints_to_bytes(outbuf)
    write_file_bytes(outbuf,args.output)
    sys.exit(0)
    return

def padpkcs_handler(args,parser):
    set_logging(args)
    align = 16
    if len(args.subnargs) > 0:
        align = int(args.subnargs[0])
    inbuf = read_file_bytes(args.input)
    outbuf = convert_bytes_to_ints(inbuf)
    padnum = align
    padlen = align
    if (len(inbuf) % align)  != 0:
        padnum = align - (len(inbuf) % align)
        padlen = padnum
    idx = 0
    while idx < padlen:
        outbuf.append(padnum)
        idx += 1
    outbuf = convert_ints_to_bytes(outbuf)
    write_file_bytes(outbuf,args.output)
    sys.exit(0)
    return


def md5_handler(args,parser):
    set_logging(args)
    for f in args.subnargs:
        m = get_file_md5(f)
        sys.stdout.write('%s %s\n'%(f,m))
    sys.exit(0)
    return

def rmlist_handler(args,parser):
    set_logging(args)
    s = read_file(args.input)
    sarr = re.split('\n',s)
    dname = args.subnargs[0]
    dname = os.path.abspath(dname)
    ofiles = []
    for f in sarr:
        if len(f) > 0:
            ofiles.append(f)
    files = []
    ofiles.sort()
    for dp,dns,fns in os.walk(dname):
        #logging.info('dp %s fns %s'%(dp,fns))
        for f in fns:
            if dp == dname:
                files.append(f)
                logging.info('append %s'%(f))
            else:
                nfile = os.path.join(dp,f)
                nfile = nfile.replace(dname,'')
                files.append(nfile)
                logging.info('append %s'%(nfile))
    files.sort()
    sidx = 0
    didx = 0
    while sidx < len(ofiles) and didx < len(files):
        if ofiles[sidx] < files[didx]:
            logging.info('skip [%s]'%(ofiles[sidx]))
            sidx += 1
        elif ofiles[sidx] > files[didx]:
            logging.info('will remove [%s]'%(files[didx]))
            didx += 1
        else:
            logging.info('pair [%d] [%d] [%s]'%(sidx,didx,ofiles[sidx]))
            sidx += 1
            didx += 1
    while sidx < len(ofiles):
        logging.info('no %s'%(ofiles[sidx]))
        sidx += 1
    while didx < len(files):
        logging.info('remove %s'%(files[didx]))
        didx += 1


    sys.exit(0)
    return

def largefile_handler(args,parser):
    set_logging(args)
    for f in args.subnargs:
        nf= ReadFileLarge(f)
        for l in nf.fh:
            sys.stdout.write('%s'%(l))
    sys.exit(0)
    return

def listdir_handler(args,parser):
    set_logging(args)
    for d in args.subnargs:
        for (root,dirs,files) in os.walk(d):
            logging.info('in root [%s]'%(root))
            logging.info('\tdirs %d'%(len(dirs)))
            for dn in dirs:
                logging.info('\t\t%s'%(dn))
            logging.info('\tfiles %d'%(len(files)))
            for fn in files:
                logging.info('\t\t%s'%(fn))
    sys.exit(0)
    return

def readtar_handler(args,parser):
    set_logging(args)
    tarfile = args.subnargs[0]
    fobj = ReadTar(args.subnargs[0])
    fobj.open('r:gz')
    if len(args.subnargs) == 1:
        dinfo = fobj.get_list()
        sys.stdout.write('[%s] contect\n'%(args.subnargs[0]))
        for i in dinfo:
            if i.isfile():
                sys.stdout.write('[%s]file\n'%(i.name))
            elif i.isdir():
                sys.stdout.write('[%s]dir\n'%(i.name))
            else:
                sys.stdout.write('[%s]unknown\n'%(i.name))
    else:
        for f in args.subnargs[1:]:
            content = fobj.extract_file_content(f)
            try:
                if sys.version[0] == '3':
                    outs = content.decode('utf-8')
                else:
                    outs = string(content)
                write_file(outs,args.output)
            except:
                write_file_bytes(content,args.output)



    sys.exit(0)
    return

def gzread_handler(args,parser):
    set_logging(args)
    if len(args.subnargs) > 0:
        for f in args.subnargs:
            gzobj = ReadGzip(f)
            for l in gzobj:
                sys.stdout.write('%s'%(l))
    else:
        gzobj = ReadGzip(None)
        for l in gzobj:
            sys.stdout.write('%s'%(l))
    sys.exit(0)
    return

def mktemp_handler(args,parser):
    set_logging(args)
    for f in args.subnargs:
        retf = mktemp_file(f,args.directory)
        sys.stdout.write('[%s] retf [%s]\n'%(f,retf))
    sys.exit(0)
    return


def main():
    commandline='''
    {
        "input|i" : null,
        "output|o" : null,
        "directory|D" : null,
        "read<read_handler>" : {
            "$" : "*"
        },
        "readbytes<readbyte_handler>" : {
            "$" : "*"
        },
        "write<write_handler>" : {
            "$" : "*"
        },
        "diff<diff_handler>## adir bdir  ##" : {
            "$" : 2
        },
        "writebytes<writebyte_handler>## src dst ##" : {
            "$" : "*"
        },
        "padzero<padzero_handler>##[align] to padd for align##" : {
            "$" : "?"
        },
        "padpkcs<padpkcs_handler>##[align] to padd for align##" : {
            "$" : "?"
        },
        "md5<md5_handler>##file ... to get file md5##" : {
            "$" : "+"
        },
        "rmlist<rmlist_handler>##dir  to compare with dirlist##" : {
            "$": 1
        },
        "largefile<largefile_handler>##file ... to read large file##" : {
            "$" : "+"
        },
        "listdir<listdir_handler>##d ... to list##" : {
            "$" : "+"
        },
        "readtar<readtar_handler>##tarfile extractfiles... to list tar file##" : {
            "$" : "+"
        },
        "gzread<gzread_handler>##[file] to read##" : {
            "$" : "*"
        },
        "mktemp<mktemp_handler>##template ... to create temp file##" : {
            "$" : "+"
        }
    }
    '''
    parser = extargsparse.ExtArgsParse()
    load_log_commandline(parser)
    parser.load_command_line_string(commandline)
    parser.parse_command_line(None,parser)
    raise Exception('can not here for no command handle')
    return


if __name__ == '__main__':
    main()