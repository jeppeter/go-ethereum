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
import urllib
import hashlib

sys.path.append(os.path.abspath(os.path.dirname(os.path.abspath(__file__))))

from loglib import set_logging, load_log_commandline,log_command_prefix
from fileop import read_file,write_file,make_directory_safe,mktemp_file,get_disk_free_space
from envop import is_windows,is_linux
from tomlex import TomlEx
from strop import rand_buffer
from procop import ProcExpolore
from key_word import *



def get_topdir():
    dname = os.path.dirname(os.path.abspath(__file__))
    topdir = os.path.abspath(os.path.join(dname,'..'))
    return topdir

def get_sha256_sum(inb):
    s256 = hashlib.sha256()
    s256.update(inb)
    return s256.hexdigest()

def get_compile_targets(topdir = None):
    if topdir is None:
        topdir = get_topdir()
    bindir = os.path.join(topdir,'cmd')
    compiledir = os.listdir(bindir)
    return compiledir

def compile_build_target(args):
    retval = False
    builddir = os.path.join(args.topdir,'build')
    buildcmd = os.path.join(builddir,'build')
    if is_windows():
        buildcmd += '.exe'
    if os.path.exists(buildcmd):
        return True
    # now to go for
    cmds = []
    if is_windows():
        cmds.append('go.exe')
    else:
        cmds.append('go')
    cmds.append('build')
    cmds.append('-o')
    if is_windows():
        cmds.append('build.exe')
    else:
        cmds.append('build')
    cmds.append('ci.go')
    retdir = os.getcwd()
    try:
        myenv = os.environ.copy()
        myenv['GO111MODULE'] = args.go111module
        myenv['GOPROXY'] = args.goproxy
        # make default platform 
        if 'GOOS' in myenv.keys():
            del myenv['GOOS']
        if 'GOARCH' in myenv.keys():
            del myenv['GOARCH']
        os.chdir(builddir)
        logging.info('GO111MODULE [%s] GOPROXY [%s]'%(args.go111module,args.goproxy))
        logging.info('run %s'%(cmds))
        subprocess.check_call(cmds,env=myenv)
        retval = True
    except:
        logging.error('%s'%(traceback.format_exc()))
    os.chdir(retdir)
    return retval

def build_checkbuild(topdir):
    cmds = []
    if is_windows():
        checkbuild = os.path.join(topdir,'scripts','checkbuild.exe')
    else:
        checkbuild = os.path.join(topdir,'scripts','checkbuild')
    checkbuildgo = os.path.join(topdir,'scripts','checkbuild.go')
    if os.path.exists(checkbuild):
        return True
    if is_windows():
        cmds.append('go.exe')
    else:
        cmds.append('go')
    cmds.append('build')
    cmds.append('-o')
    cmds.append(checkbuild)
    cmds.append(checkbuildgo)
    retval = False
    try:
        logging.info('call %s'%(cmds))
        subprocess.check_call(cmds)
        retval = True
    except:
        logging.error('%s'%(traceback.format_exc()))
    return retval

def get_goos_goarch(topdir):
    retval = build_checkbuild(topdir)
    if not retval:
        raise Exception('can not checkbuild ok')
    goos = ''
    goarch = ''
    if is_windows():
        checkbuild = os.path.join(topdir,'scripts','checkbuild.exe')
    else:
        checkbuild = os.path.join(topdir,'scripts','checkbuild')
    copyenv = os.environ.copy()
    if 'GOOS' in copyenv.keys():
        del copyenv['GOOS']
    if 'GOARCH' in copyenv.keys():
        del copyenv['GOARCH']
    for l in cmdpack.run_cmd_output([checkbuild],copyenv=copyenv):
        l = l.rstrip('\r\n')
        if l.startswith('GOOS='):
            goos = l.replace('GOOS=','')
        elif l.startswith('GOARCH='):
            goarch = l.replace('GOARCH=','')
    return goos,goarch



def compile_single_target(args,target):
    retdir = os.getcwd()
    retval = False
    cmds = []
    defgoos = args.goos
    defgoarch = args.goarch
    if defgoos is None and defgoarch is None:
        defgoos,defgoarch = get_goos_goarch(args.topdir)
    elif defgoos is None:
        defgoos, _ = get_goos_goarch(args.topdir)
    elif defgoarch is None:
        _ , defgoarch = get_goos_goarch(args.topdir)


    if is_windows():
        cmds.append('.\\build\\build.exe')
    else:
        cmds.append('./build/build')
    cmds.append('install')
    cmds.append('-arch')
    cmds.append(defgoarch)
    cmds.append('-os')
    cmds.append(defgoos)
    if is_windows():
        cmds.append('.\\cmd\\%s'%(target))
    else:
        cmds.append('./cmd/%s'%(target))
    try:
        myenv = os.environ.copy()
        myenv['GO111MODULE'] = args.go111module
        myenv['GOPROXY'] = args.goproxy
        os.chdir(args.topdir)
        logging.info('GO111MODULE [%s] GOPROXY [%s]'%(args.go111module,args.goproxy))
        logging.info('run %s'%(cmds))
        subprocess.check_call(cmds,env=myenv)
        retval = True
    except:
        logging.error('%s'%(traceback.format_exc()))
    os.chdir(retdir)
    return retval

	
def compile_handler(args,parser):
    set_logging(args)
    totalret = True
    targets = ['geth']
    if len(args.subnargs) > 0:
        targets = args.subnargs
    accept_targets = get_compile_targets(args.topdir)
    for d in targets:
        if d not in accept_targets:
            raise Exception('[%s] not accept'%(d))
    retval = compile_build_target(args)
    if not retval:
        sys.exit(3)
    for d in targets:
        retval = compile_single_target(args,d)
        if not retval:
            totalret = False
    if not totalret:
        sys.exit(3)
    sys.exit(0)

def get_gethbin(args):
    if is_windows():
        gethbin = os.path.join(args.topdir,'build','bin','cmd','geth.exe')
    else:
        gethbin = os.path.join(args.topdir,'build','bin','cmd','geth')
    retcmds = [gethbin]
    if args.verbose == 0 and args.subcommand != 'runproc':
        retcmds.append('--verbosity')
        retcmds.append('5')
    return retcmds

def new_verbose_mode(args):
    return ['--verbosity','0']


def generate_account(args,datadir,secfile):
    cmds = get_gethbin(args)
    cmds.extend(new_verbose_mode(args))
    cmds.append('account')
    cmds.append('new')
    cmds.append('--datadir')
    cmds.append(datadir)
    cmds.append('--password')
    cmds.append(secfile)
    retval = False
    outf = None
    try:
        logging.info('cmds %s'%(cmds))
        if args.verbose >= 3:
            outf = None
        else:
            outf = open(os.devnull,'w+')
        subprocess.check_call(cmds,stdout=outf)
        retval = True
    except:
        logging.error('%s'%(traceback.format_exc()))
    if outf is not None:
        outf.close()
    return retval

def check_node_modules(args):
    nodedir = os.path.join(args.topdir,'tests','privnet')
    nodemodulesdir = os.path.join(args.topdir,'tests','privnet','node_modules')
    if os.path.exists(nodemodulesdir):
        return True
    retval = False
    cmds = []
    if is_windows():
        cmds.append('npm.cmd')
    else:
        cmds.append('npm')
    cmds.append('install')
    pwddir = os.getcwd()
    try:
        os.chdir(nodedir)
        logging.info('cmds %s'%(cmds))
        subprocess.check_call(cmds)
        retval = True
    except:
        logging.error('%s'%(traceback.format_exc()))
    os.chdir(pwddir)
    return retval

def node_init_genesis(args):
    retval = check_node_modules(args)
    if not retval:
        return retval
    cmds = []
    if is_windows():
        cmds.append('node.exe')
    else:
        cmds.append('node')
    cmds.append(os.path.join(args.topdir,'tests','privnet','scripts','generate-keypair.js'))
    retval = False
    try:
        logging.info('run %s'%(cmds))
        subprocess.check_call(cmds)
        retval = True
    except:
        logging.error('%s'%(traceback.format_exc()))
    return retval

def init_datadir_genesis(args,datadir,gensisfile):
    cmds = []
    cmds.extend(get_gethbin(args))
    #cmds.extend(new_verbose_mode(args))
    cmds.append('init')
    cmds.append('--datadir')
    cmds.append(datadir)
    cmds.append(gensisfile)
    retval = False
    try:
        subprocess.check_call(cmds)
        retval = True
    except:
        logging.error('%s'%(traceback.format_exc()))
    return retval

def remove_file_or_stdout(args,fname,note):
    if not args.reserved:
        sys.stdout.write('remove %s [%s]\n'%(note,fname))
        os.remove(fname)
    else:
        sys.stdout.write('reserved %s [%s]\n'%(note,fname))
    return

def get_user_datadir(args,username):
    return os.path.join(args.datadir,'datadir_%s'%(username))

def init_user_toml(args,username,rdict,tex):
    ns = tex.dumps()
    ntex = TomlEx()
    ntex.loads(ns)
    logging.info('username [%s]rdict\n%s'%(username,json.dumps(rdict,indent=4)))
    ntex = toml_set_value(ntex,rdict,username)
    # now to make dir
    curdatadir = get_user_datadir(args,username)
    if is_windows():
        #curdatadir = curdatadir.replace('\\','\\\\')
        curpipe = '\\\\.\\pipe\\geth.%s'%(username)
        #curpipe = curpipe.replace('\\','\\\\')
    else:
        curpipe = '/tmp/geth.%s'%(username)
    ntex.set_value(NODE_DATADIR_KEYWORD,curdatadir)
    ntex.set_value(NODE_IPCPATH_KEYWORD,curpipe)

    outs = ntex.dumps()
    curtoml = os.path.join(curdatadir,'%s.toml'%(username))
    write_file(outs,curtoml)
    return True

def username_datadir_account_init(args,username,rdict,tex):
    datadir = get_user_datadir(args,username)
    secfile = mktemp_file('secfile.XXXXXXX.password',datadir)
    password = ''
    if PASSWORD_KEYWORD in rdict.keys():
        password = rdict[PASSWORD_KEYWORD]
    else:
        password = rand_buffer(16,True)
    logging.info('[%s] password [%s]'%(username,password))
    write_file(password,secfile)
    retval = generate_account(args,datadir,secfile)
    #remove_file_or_stdout(args,secfile,'secfile')
    if not retval:
        return retval
    retval = init_user_toml(args,username,rdict,tex)
    return retval

def get_user_account_info(userdir):
    keystoredir = os.path.join(userdir,'keystore')
    files = os.listdir(keystoredir)
    retinfos = []
    for f in files:
        curf = os.path.join(keystoredir,f)
        if os.path.isfile(curf):
            try:
                ins = read_file(curf)
                cdict = json.loads(ins)
                if ADDRESS_KEYWORD in cdict.keys():
                    retinfos.append(cdict)
            except:
                logging.error('%s'%(traceback.format_exc()))
    return retinfos



def username_generate_gensis(args,rdict,gensisfile):
    datadir = args.datadir
    newgenesis = mktemp_file('genesis.XXXXXX.json',datadir)
    ins = read_file(gensisfile)
    cdict = json.loads(ins)
    if GENESIS_CONFIG not in cdict.keys():
        cdict[GENESIS_CONFIG] = dict()
    cdict[GENESIS_CONFIG][GENESIS_CHAINID] = args.networkid
    cdict[GENESIS_ALLOC] = dict()
    # now we should get the account and make allocate the account values
    for k in rdict.keys():
        curdatadir = get_user_datadir(args,k)
        # now we should give 
        infos = get_user_account_info(curdatadir)
        if len(infos) > 0:
            for uinfo in infos:
                curaddress = uinfo[ADDRESS_KEYWORD]
                curbalance = ETH_WEI * 100
                if GENESIS_BLANCE in rdict[k].keys():
                    if isinstance(rdict[k][GENESIS_BLANCE], int):
                        curbalance = rdict[k][GENESIS_BLANCE]
                    else:
                        try:
                            balances = rdict[k][GENESIS_BLANCE]
                            curbalance = parse_int(balances)
                        except:
                            logging.error('%s'%(traceback.format_exc()))
                adict = dict()
                adict[GENESIS_BLANCE] = '0x%x'%(curbalance)
                cdict[GENESIS_ALLOC][curaddress] = adict
    outs = json.dumps(cdict,indent=4)
    write_file(outs,newgenesis)
    logging.info('newgenesis [%s]\n%s'%(newgenesis,outs))
    for k in rdict.keys():
        curdatadir = get_user_datadir(args,k)
        retval =  init_datadir_genesis(args,curdatadir,newgenesis)
        if not retval :
            remove_file_or_stdout(args,newgenesis,'newgenesis')
            return retval
    #remove_file_or_stdout(args,newgenesis,'newgenesis')
    return True



def initpriv_handler(args,parser):
    set_logging(args)
    # first to init data
    if len(args.subnargs) < 2:
        raise Exception('need config.json and gensisfile')
    s = read_file(args.subnargs[0])
    gensisfile = args.subnargs[1]
    rdict = json.loads(s)
    totalret = True
    tex = get_toml_value(args)
    for k in rdict.keys():
        retval = username_datadir_account_init(args,k,rdict[k],tex)
        if not retval:
            sys.stderr.write('init %s error\n'%(k))
            totalret = False
        else:
            if args.verbose == 0:
                sys.stdout.write('init [%s] succ\n'%(k))
    if totalret:
        retval = username_generate_gensis(args,rdict,gensisfile)
        if not retval:
            totalret = False
    if not totalret:
        sys.exit(3)
    sys.exit(0)
    return

def run_geth_dumpconfig(args):
    retfile = mktemp_file('eth-config.XXXXXXXX.toml')
    cmds = get_gethbin(args)
    cmds.append('dumpconfig')
    cmds.append(retfile)
    try:
        subprocess.check_call(cmds)
    except:
        logging.error('%s'%(traceback.format_exc()))
        os.remove(retfile)
        return None
    return retfile

def toml_set_value(tex,rdict,key):
    for k,v in rdict.items():
        if k != PASSWORD_KEYWORD and k != GENESIS_BLANCE:
            tex.set_value(k,v)
    return tex

def get_toml_value(args):
    if args.input is not None:
        ins = read_file(args.input)
    else:
        ins = ''
        retfile = run_geth_dumpconfig(args)
        if retfile is None:
            raise Exception('can not dumpconfig')
        logging.info('dump conifg [%s]'%(retfile))
        ins = read_file(retfile)
        remove_file_or_stdout(args,retfile,'dumpconfig file')
    tex = TomlEx()
    tex.loads(ins)
    return tex



def newconfig_handler(args,parser):
    set_logging(args)
    tex = get_toml_value(args)
    if len(args.subnargs) > 0:
        ins = read_file(args.subnargs[0])
        rdict = json.loads(ins)
        if len(args.subnargs) > 1:
            key = args.subnargs[1]
            if key in rdict.keys():
                for k,v in rdict[key].items():
                    tex.set_value(k,v)

    if len(args.subnargs) > 2:
        for l in args.subnargs[2:]:
            l = l.rstip('\n\r')
            carr = re.split('=',l,2)
            if len(carr) >= 2:
                k = carr[0]
                v = json.loads(carr[1])
                tex.set_value(k,v)
    outs = tex.dumps()
    write_file(outs,args.output)
    sys.exit(0)
    return

def run_geth_with_config(args,tomlfile,key):
    cmds = get_gethbin(args)
    cmds.append('--config')
    cmds.append(tomlfile)
    cmds.append('--verbosity')
    cmds.append('5')
    curdatadir = get_user_datadir(args,key)
    logfile = os.path.join(curdatadir,'%s.log'%(key))
    # do not remove log file
    #if os.path.exists(logfile):
    #    os.remove(logfile)
    cmds.append('--log.file')
    cmds.append(logfile)
    cmds.append('--log.format')
    cmds.append('logfmt')
    devnullfile = open(os.devnull,'wb')
    if is_windows():
        flags = 0
        flags |= 0x00000008  # DETACHED_PROCESS
        flags |= 0x00000200  # CREATE_NEW_PROCESS_GROUP
        flags |= 0x08000000  # CREATE_NO_WINDOW

        pkwargs = {
            'close_fds': True,  # close stdin/stdout/stderr on child
            'creationflags': flags,
        }
        p = subprocess.Popen(cmds,stdout=devnullfile,stderr=devnullfile)
    else:
        logging.info('cmds %s'%(cmds))
        p = subprocess.Popen(cmds,stdout=devnullfile,stderr=devnullfile)
    return p
    

def get_user_toml(args,username):
    curdatadir = get_user_datadir(args,username)
    curtoml = os.path.join(curdatadir,'%s.toml'%(username))
    return curtoml

def runproc_handler(args,parser):
    # now to make running
    set_logging(args)
    tex = get_toml_value(args)

    frspc = get_disk_free_space(args.datadir)
    if frspc < MIN_FREE_SPACE:
        raise Exception('frspc 0x%x < MIN_FREE_SPACE 0x%x'%(frspc,MIN_FREE_SPACE))

    ins = read_file(args.subnargs[0])
    rdict = json.loads(ins)
    for k in rdict.keys():
        curtoml = get_user_toml(args,k)
        p = run_geth_with_config(args,curtoml,k)
        sys.stdout.write('[%s] pid [%d]\n'%(k,p.pid))

    sys.exit(0)
    return

def killproc_linux(args):
    cont = True
    maxcnt = 0 
    procs = ProcExpolore()
    while cont:
        cont = False
        maxcnt += 1
        procs.snapshot()
        ps = procs.get_result()
        tokill = []
        for k,v in ps.items():
            if v.firstarg == 'geth' or v.firstarg.endswith('/geth'):
                sys.stdout.write('gethbin %s\n'%(k))
                tokill.append(k)
                cont = True
        idx = 0
        while idx < len(tokill):
            try:
                logging.info('kill [%d]'%(tokill[idx]))
                os.kill(tokill[idx],signal.SIGINT)
            except:
                cont = True
                #if maxcnt >= 3:
                #    logging.error('%s'%(traceback.format_exc()))
            idx += 1
        if cont:
            logging.info('to cont')
            time.sleep(1.0)
    return


def killproc_window(args):
    cont = True
    maxcnt = 0
    procs = ProcExpolore()
    while cont:
        cont = False
        maxcnt += 1
        procs.snapshot()
        ps = procs.get_result()
        tokill = []
        for k,v in ps.items():
            if v.firstarg == 'geth.exe' or (v.firstarg.endswith('\\geth.exe')):
                #logging.info('pid %d'%(k))
                sys.stdout.write('kill [%d]\n'%(k))
                tokill.append(k)
                cont = True
        idx = 0
        while idx < len(tokill):
            try:
                os.kill(tokill[idx],signal.CTRL_C_EVENT)
            except:
                if maxcnt >= 3:
                    logging.error('%s'%(traceback.format_exc()))
            idx += 1
    return

def killproc_handler(args,parser):
    set_logging(args)

    if is_windows():
        killproc_window(args)
    else:
        killproc_linux(args)

    sys.exit(0)
    return

def exec_js(args,rpcpipe,jsstr):
    if rpcpipe is None or len(rpcpipe) == 0:
        raise Exception('please set rpcpipe for connect')
    cmds = get_gethbin(args)
    cmds.append('--exec')
    cmds.append(jsstr)
    cmds.append('attach')
    cmds.append(rpcpipe)
    outs = ''
    for l in cmdpack.run_cmd_output(cmds):
        outs += l
    logging.info('[%s] output\n%s'%(jsstr,outs))
    return outs


def execjs_handler(args,parser):
    set_logging(args)

    for s in args.subnargs:
        outs = exec_js(args,args.rpcpipe,s)
        sys.stdout.write('%s\n'%(outs))
    sys.exit(0)
    return

def remove_genesis(args):
    allfiles = os.listdir(args.datadir)
    genexpr = re.compile('genesis\\.([^\\.]+)\\.json')
    retval = True
    for f in allfiles:
        curf = os.path.join(args.datadir,f)
        if os.path.isfile(curf):
            if genexpr.match(f):
                try:
                    os.remove(curf)
                except:
                    retval = False
                    logging.error('%s'%(traceback.format_exc()))
    return retval




def cleandata_handler(args,parser):
    set_logging(args)
    s = read_file(args.subnargs[0])
    rdict = json.loads(s)
    totalret = True
    for k in rdict.keys():
        curdatadir = get_user_datadir(args,k)
        retval = True
        try:
            if os.path.exists(curdatadir):
                shutil.rmtree(curdatadir)
        except:
            retval = False
            logging.error('%s'%(traceback.format_exc()))
        if not retval:
            totalret = False
    retval = remove_genesis(args)
    if not retval:
        totalret = False
    if not totalret:
        sys.exit(3)
    sys.exit(0)
    return



def makecfg_handler(args,parser):
    set_logging(args)
    rdict = dict()
    num = 3
    defport = 10000
    if len(args.subnargs) > 0:
        num = int(args.subnargs[0])
    if len(args.subnargs) > 1:
        defport = int(args.subnargs[1])
    idx = 0
    curstartport = defport
    while idx < num:
        curk = 'signer%d'%(idx)
        jwtsecfile = make_user_datadir_file(args,curk,'jwt_%s.secret'%(curk))
        jwtpalinfile = make_user_datadir_file(args,curk,'jwt_%s.plain'%(curk))
        curdict = dict()
        curport = curstartport
        for k in CFG_PORT_VALUES:
            curdict[k] = curport 
            curport += 1
        curdict[CFG_LISTEN_PORT] = ':%d'%(curport)
        curport += 1
        curdict[PASSWORD_KEYWORD] = '%s_%d'%(curk,curport)
        curport += 1
        curdict[CFG_NETWORKID] = args.networkid
        curdict[CFG_INFLUX_DB_PORT] = 'http://127.0.0.1:%d'%(curport)
        curport += 1
        curdict[NODE_AUTHPORT_KEYWORD] = curport
        curport += 1
        curdict[NODE_AUTHADDR_KEYWORD] = '127.0.0.1'
        # max peers
        curdict[P2P_MAXPENDINGPEERS_KEYWORD] = num
        curdict[P2P_MAXPEERS_KEYWORD] = num * 10
        curdict[NODE_JWTSECRET_KEYWORD] = jwtsecfile

        jwtsec = 'jwt_%s_%d'%(curk,curport)
        if sys.version[0] == '3':
            inb = jwtsec.encode('utf-8')
        else:
            inb = byte(jwtsec)
        outccs = get_sha256_sum(inb)
        logging.info('jwtsec [%s] outccs [%s]'%(jwtsec,outccs))
        write_file(outccs,jwtsecfile)
        write_file(jwtsec,jwtpalinfile)

        for k,v in CFG_DEF_VALUES.items():
            curdict[k]=v
        rdict[curk] = curdict
        idx += 1
        curstartport += 20

    outs = json.dumps(rdict,indent=4)
    write_file(outs,args.output)
    sys.exit(0)

def make_user_datadir_file(args,username,partfile):
    retfile =  os.path.join(args.datadir,'datadir_%s'%(username),partfile)
    make_directory_safe(os.path.dirname(retfile))
    return retfile


def get_node_ipcpath(args,username):
    tomlfile = make_user_datadir_file(args,username,'%s.toml'%(username))
    tomls = read_file(tomlfile)
    tex = TomlEx()
    tex.loads(tomls)
    # now to get the value
    ipcpath = tex.get_value(NODE_IPCPATH_KEYWORD)
    if ipcpath is None:
        raise Exception('can not get %s in %s'%(NODE_IPCPATH_KEYWORD,username))
    return ipcpath


def get_node_peers(args,username,ipcpath):
    # now we should get the ipcpath
    rets = exec_js(args,ipcpath,'admin.peers')
    retval = []
    sarr = re.split('\n',rets)
    enodeexpr =re.compile('\\s+enode\\s*:\\s*"(.*)",\\s*$')
    index = 0
    for l in sarr:
        index += 1        
        l = l.rstrip('\r\n')
        m = enodeexpr.findall(l)
        if m is not None and len(m) > 0:
            logging.info('[%s] append [%s]'%(username,m[0]))
            retval.append(m[0])            
    return retval

def get_enode_value(args,username,ipcpath):
    rets = exec_js(args,ipcpath,'admin.nodeInfo.enode')
    return json.loads(rets)


def url_enode_parse(enode):
    retval = urllib.parse.urlsplit(enode)
    return retval

def check_peer_in(peers,enode):
    ks = []
    for k in peers:
        retval = url_enode_parse(k)
        if retval.username is not None:
            ks.append(retval.username)
    logging.info('ks %s'%(ks))
    retval = url_enode_parse(enode)
    retv = False
    logging.info( 'enode %s retval.username %s'%(enode,retval.username))
    if retval.username is not None:
        if retval.username in ks:
            retv = True
    return retv

def add_peer(args,node1,peernode,ipcpath):
    ins = 'admin.addPeer("%s")'%(peernode)
    logging.info('ins [%s]'%(ins))
    rets = exec_js(args,ipcpath,ins)
    logging.info('rets %s'%(rets))
    return json.loads(rets)



def addpeers_handler(args,parser):
    set_logging(args)
    ins = read_file(args.subnargs[0])
    rdict = json.loads(ins)
    keys = []
    for k in rdict.keys():
        keys.append(k)
    # now to read the peers
    ipcdict = dict()
    for k in keys:
        ipcdict[k] = get_node_ipcpath(args,k)
    peerdict = dict()
    for k in keys:
        peerdict[k] = get_node_peers(args,k,ipcdict[k])
        logging.info('[%s]=%s'%(k,peerdict[k]))

    enodedict = dict()
    for k in keys:
        enodedict[k] = get_enode_value(args,k,ipcdict[k])
        logging.info('[%s]enode[%s]'%(k,enodedict[k]))

    idx = 0
    while idx < len(keys):
        jdx = idx + 1
        while jdx < len(keys):
            curik = keys[idx]
            curjk = keys[jdx]
            if not check_peer_in(peerdict[curik],enodedict[curjk]):
                retval = add_peer(args,curik,enodedict[curjk],ipcdict[curik])
                if not retval:
                    raise Exception('can not add [%s] in %s'%(curjk,curik))
            jdx += 1
        idx += 1

    sys.exit(0)
    return


def load_base_parser(parser):
    commandline_fmt='''
    {
        "input|i" : null,
        "output|o" : null,
        "topdir|T" : "%s",
        "datadir|D" : "%s",
        "goproxy" : "https://goproxy.cn",
        "go111module" : "auto",
        "goos" : null,
        "goarch" : null,
        "rpcpipe" : null,
        "reserved|R" : false,
        "networkid" : 2363,
        "compile<%s.compile_handler>##[target]to compile default geth can accept %s ##" : {
            "$" : "*"
        },
        "initpriv<%s.initpriv_handler>##modfile genesisfile to init private network##" : {
            "$" : 2
        },
        "newconfig<%s.newconfig_handler>##modifile key [clause] ... from input to make output with  to make output config##" : {
            "$" : "*"
        },
        "runproc<%s.runproc_handler>##modfile to make config and give the calling##" : {
            "$" : 1
        },
        "killproc<%s.killproc_handler>##to kill process running##" : {
            "$" : 0
        },
        "execjs<%s.execjs_handler>##jscmds ... to get the process##" : {
            "$" : "+"
        },
        "cleandata<%s.cleandata_handler>##newconfig to clean datadir##" : {
            "$" : 1
        },
        "makecfg<%s.makecfg_handler>##[num] [startport] to set default value for config default 5 startport 10000##" : {
            "$" : "*"
        },
        "addpeers<%s.addpeers_handler>##jsonfile to add peers by the default values##" : {
            "$" : 1
        }
    }
    '''
    topdir = get_topdir()
    if is_windows():
        datadir = os.path.join(topdir,'datastore_windows')
    else:
        datadir = os.path.join(topdir,'datastore_linux')
    if is_windows():
        topdir = topdir.replace('\\','\\\\')
        datadir = datadir.replace('\\','\\\\')

    compiledir = get_compile_targets()
    compiles = ''
    for d in compiledir:
        if len(compiles) > 0:
            compiles += ','
        compiles += '%s'%(d)
    commandline = commandline_fmt%(topdir,datadir,__name__,compiles,__name__,__name__,__name__,__name__,__name__,__name__,__name__,__name__)
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