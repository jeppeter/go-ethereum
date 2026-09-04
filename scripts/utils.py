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
import psutil
import signal
import time
import shutil

sys.path.append(os.path.abspath(os.path.dirname(os.path.abspath(__file__))))

from loglib import set_logging, load_log_commandline,log_command_prefix
from fileop import read_file,write_file,make_directory_safe,mktemp_file
from envop import is_windows,is_linux
from tomlex import TomlEx
from strop import rand_buffer


def get_topdir():
    dname = os.path.dirname(os.path.abspath(__file__))
    topdir = os.path.abspath(os.path.join(dname,'..'))
    return topdir

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
        if is_cygwin():
            cmds.append('./cmd/%s'%(target))
        else:
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
    return gethbin

def new_verbose_mode(args):
    return ['--verbosity','0']


def generate_account(args,datadir,secfile):
    cmds = [get_gethbin(args)]
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
    cmds.append(get_gethbin(args))
    cmds.extend(new_verbose_mode(args))
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

PASSWORD_KEYWORD = 'PASSWORD.KEY'

def get_user_datadir(args,username):
    return os.path.join(args.datadir,'datadir_%s'%(username))

def username_datadir_init(args,username,rdict,gensisfile):
    datadir = get_user_datadir(args,username)
    secfile = mktemp_file('secfile.XXXXXXX.password')
    password = ''
    if PASSWORD_KEYWORD in rdict.keys():
        password = rdict[PASSWORD_KEYWORD]
    else:
        password = rand_buffer(16,True)
    logging.info('[%s] password [%s]'%(username,password))
    write_file(password,secfile)
    retval = generate_account(args,datadir,secfile)
    if not args.reserved:
        os.remove(secfile)
    if not retval:
        return retval
    return init_datadir_genesis(args,datadir,gensisfile)
    return retval





def initpriv_handler(args,parser):
    set_logging(args)
    # first to init data
    if len(args.subnargs) < 2:
        raise Exception('need config.json and gensisfile')
    s = read_file(args.subnargs[0])
    gensisfile = args.subnargs[1]
    rdict = json.loads(s)
    totalret = True
    for k in rdict.keys():
        retval = username_datadir_init(args,k,rdict[k],gensisfile)
        if not retval:
            sys.stderr.write('init %s error\n'%(k))
            totalret = False
        else:
            if args.verbose == 0:
                sys.stdout.write('init [%s] succ\n'%(k))

    if not totalret:
        sys.exit(3)
    sys.exit(0)
    return

def run_geth_dumpconfig(args):
    retfile = mktemp_file('eth-config.XXXXXXXX.toml')
    cmds = [get_gethbin(args)]
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
    if key in rdict.keys():
        for k,v in rdict[key].items():
            if k != PASSWORD_KEYWORD:
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
        if not args.reserved:
            os.remove(retfile)
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
    cmds = [get_gethbin(args)]
    cmds.append('--config')
    cmds.append(tomlfile)
    cmds.append('--verbosity')
    cmds.append('5')
    curdatadir = get_user_datadir(args,key)
    logfile = os.path.join(curdatadir,'%s.log'%(key))
    if os.path.exists(logfile):
        os.remove(logfile)
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
    


def runproc_handler(args,parser):
    # now to make running
    set_logging(args)
    tex = get_toml_value(args)

    ins = read_file(args.subnargs[0])
    rdict = json.loads(ins)
    for k in rdict.keys():
        ntex = toml_set_value(tex,rdict,k)
        # now to make dir
        curdatadir = get_user_datadir(args,k)
        if is_windows():
            #curdatadir = curdatadir.replace('\\','\\\\')
            curpipe = '\\\\.\\pipe\\geth.%s'%(k)
            #curpipe = curpipe.replace('\\','\\\\')
        else:
            curpipe = '/tmp/geth.%s'%(k)
        ntex.set_value('Node.DataDir',curdatadir)
        ntex.set_value('Node.IPCPath',curpipe)

        outs = ntex.dumps()
        curtoml = os.path.join(curdatadir,'%s.toml'%(k))
        write_file(outs,curtoml)
        p = run_geth_with_config(args,curtoml,k)
        sys.stdout.write('[%s] pid [%d]\n'%(k,p.pid))

    sys.exit(0)
    return

def killproc_linux(args):
    cont = True
    maxcnt = 0 
    while cont:
        cont = False
        maxcnt += 1
        ps = psutil.process_iter(['name','pid'])
        tokill = []
        for p in ps:
            if p.name() == 'geth':
                sys.stdout.write('gethbin %s\n'%(p.pid))
                tokill.append(p)
        idx = 0
        while idx < len(tokill):
            try:
                logging.info('kill [%d]'%(tokill[idx].pid))
                os.kill(tokill[idx].pid,signal.SIGINT)
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
    while cont:
        cont = False
        maxcnt += 1
        ps = psutil.process_iter(['name','exe','pid'])
        tokill = []
        for p in ps:
            if is_windows() and p.name() == 'geth.exe':
                if maxcnt == 1:
                    sys.stdout.write('gethbin %s\n'%(p.pid))
                tokill.append(p)                    
        idx = 0
        while idx < len(tokill):
            try:
                tokill[idx].send_signal(signal.CTRL_C_EVENT)
            except:
                pass
                #if maxcnt >= 3:
                #    logging.error('%s'%(traceback.format_exc()))
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

def exec_js(args,jsstr):
    rpcpipe = args.rpcpipe
    if rpcpipe is None or len(rpcpipe) == 0:
        raise Exception('please set rpcpipe for connect')
    cmds = [get_gethbin(args)]
    cmds.append('--exec')
    cmds.append(jsstr)
    cmds.append('attach')
    cmds.append(rpcpipe)
    outs = ''
    for l in cmdpack.run_cmd_output(cmds):
        outs += l
    return outs


def execjs_handler(args,parser):
    set_logging(args)

    for s in args.subnargs:
        outs = exec_js(args,s)
        sys.stdout.write('%s\n'%(outs))
    sys.exit(0)
    return


def clean_handler(args,parser):
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
    if not totalret:
        sys.exit(3)
    sys.exit(0)
    return

CFG_PORT_VALUES = ['Node.HTTPPort','Node.AuthPort','Node.WSPort']
CFG_LISTEN_PORT = 'Node.P2P.ListenAddr'
CFG_NETWORKID = 'Eth.NetworkId'

CFG_DEF_VALUES = {
    'Node.P2P.BootstrapNodes' : [],
    'Node.P2P.BootstrapNodesV5' : []
}


def makecfg_handler(args,parser):
    set_logging(args)
    rdict = dict()
    num = 5
    defport = 10000
    if len(args.subnargs) > 0:
        num = int(args.subnargs[0])
    if len(args.subnargs) > 1:
        defport = int(args.subnargs[1])
    idx = 0
    curstartport = defport
    while idx < num:
        curk = 'signer%d'%(idx)
        curdict = dict()
        curport = curstartport
        for k in CFG_PORT_VALUES:
            curdict[k] = curport 
            curport += 1
        curdict[CFG_LISTEN_PORT] = ':%d'%(curport)
        curport += 1
        curdict[PASSWORD_KEYWORD] = '%s_%d'%(curk,curport)
        curdict[CFG_NETWORKID] = args.networkid

        for k,v in CFG_DEF_VALUES.items():
            curdict[k]=v
        rdict[curk] = curdict
        idx += 1
        curstartport += 10

    outs = json.dumps(rdict,indent=4)
    write_file(outs,args.output)
    sys.exit(0)


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
        "reserved:R" : false,
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
        "clean<%s.clean_handler>##newconfig to clean datadir##" : {
            "$" : 1
        },
        "makecfg<%s.makecfg_handler>##[num] [startport] to set default value for config default 5 startport 10000##" : {
            "$" : "*"
        }
    }
    '''
    topdir = get_topdir()
    datadir = os.path.join(topdir,'datastore')
    if is_windows():
        topdir = topdir.replace('\\','\\\\')
        datadir = datadir.replace('\\','\\\\')

    compiledir = get_compile_targets()
    compiles = ''
    for d in compiledir:
        if len(compiles) > 0:
            compiles += ','
        compiles += '%s'%(d)
    commandline = commandline_fmt%(topdir,datadir,__name__,compiles,__name__,__name__,__name__,__name__,__name__,__name__,__name__)
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