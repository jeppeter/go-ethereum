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

sys.path.append(os.path.abspath(os.path.dirname(os.path.abspath(__file__))))

from loglib import set_logging, load_log_commandline,log_command_prefix
from fileop import read_file,write_file,make_directory_safe,mktemp_file
from envop import is_win,is_linux,is_cygwin
from tomlex import TomlEx


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
    if is_win() or is_cygwin():
        buildcmd += '.exe'
    if os.path.exists(buildcmd):
        return True
    # now to go for
    cmds = []
    if is_win() or is_cygwin():
        cmds.append('go.exe')
    else:
        cmds.append('go')
    cmds.append('build')
    cmds.append('-o')
    if is_win() or is_cygwin():
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
    if is_win()  or is_cygwin():
        checkbuild = os.path.join(topdir,'scripts','checkbuild.exe')
    else:
        checkbuild = os.path.join(topdir,'scripts','checkbuild')
    checkbuildgo = os.path.join(topdir,'scripts','checkbuild.go')
    if os.path.exists(checkbuild):
        return True
    if is_win() or is_cygwin():
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
    if is_win()  or is_cygwin():
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


    if is_win() or is_cygwin():
        if is_cygwin():
            cmds.append('./build/build.exe')
        else:
            cmds.append('.\\build\\build.exe')
    else:
        cmds.append('./build/build')
    cmds.append('install')
    cmds.append('-arch')
    cmds.append(defgoarch)
    cmds.append('-os')
    cmds.append(defgoos)
    if is_win() or is_cygwin():
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
    if is_win() or is_cygwin():
        gethbin = os.path.join(args.topdir,'build','bin','cmd','geth.exe')
    else:
        gethbin = os.path.join(args.topdir,'build','bin','cmd','geth')
    return gethbin


def generate_account(args,datadir,secfile):
    cmds = [get_gethbin(args)]
    cmds.append('account')
    cmds.append('new')
    cmds.append('--datadir')
    cmds.append(datadir)
    cmds.append('--password')
    cmds.append(secfile)
    retval = False
    try:
        logging.info('cmds %s'%(cmds))
        subprocess.check_call(cmds)
        retval = True
    except:
        logging.error('%s'%(traceback.format_exc()))
    return retval

def check_node_modules(args):
    nodedir = os.path.join(args.topdir,'tests','privnet')
    nodemodulesdir = os.path.join(args.topdir,'tests','privnet','node_modules')
    if os.path.exists(nodemodulesdir):
        return True
    retval = False
    cmds = []
    if is_win() or is_cygwin():
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
    if is_cygwin() or is_win():
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

def init_datadir(args,datadir):
    cmds = []
    cmds.append(get_gethbin(args))
    cmds.append('init')
    cmds.append('--datadir')
    cmds.append(datadir)
    cmds.append(os.path.join(args.topdir,'tests','privnet','common','genesis.json'))
    retval = False
    try:
        subprocess.check_call(cmds)
        retval = True
    except:
        logging.error('%s'%(traceback.format_exc()))
    return retval


def initpriv_handler(args,parser):
    set_logging(args)
    # first to init data
    signersec = os.path.join(args.topdir,'tests','privnet','secrets','password-signer.secret')
    retval = generate_account(args,args.signerdir,signersec)
    if not retval:
        sys.exit(3)
    apisec = os.path.join(args.topdir,'tests','privnet','secrets','password-api.secret')
    retval = generate_account(args,args.apidir,apisec)
    if not retval:
        sys.exit(3)
    retval = node_init_genesis(args)
    if not retval:
        sys.exit(3)
    retval = init_datadir(args,args.signerdir)
    if not retval:
        sys.exit(3)
    retval = init_datadir(args,args.apidir)
    if not retval:
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
    logfile = os.path.join(args.topdir,'%s.log'%(key))
    if os.path.exists(logfile):
        os.remove(logfile)
    cmds.append('--log.file')
    cmds.append(logfile)
    cmds.append('--log.format')
    cmds.append('logfmt')
    devnullfile = open(os.devnull,'wb')
    if is_cygwin() or is_win():
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
        curdatadir = os.path.join(args.topdir,'datadir_%s'%(k))
        if is_win() or is_cygwin():
            #curdatadir = curdatadir.replace('\\','\\\\')
            curpipe = '\\\\.\\pipe\\geth.%s'%(k)
            #curpipe = curpipe.replace('\\','\\\\')
        else:
            curpipe = '/tmp/geth.%s'%(k)
        ntex.set_value('Node.DataDir',curdatadir)
        ntex.set_value('Node.IPCPath',curpipe)

        outs = ntex.dumps()
        curtoml = os.path.join(args.topdir,'%s.toml'%(k))
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
            if (is_cygwin() or is_win()) and p.name() == 'geth.exe':
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

    if is_win() or is_cygwin():
        killproc_window(args)
    else:
        killproc_linux(args)

    sys.exit(0)
    return


def load_base_parser(parser):
    commandline_fmt='''
    {
        "input|i" : null,
        "output|o" : null,
        "topdir|T" : "%s",
        "goproxy" : "https://goproxy.cn",
        "go111module" : "auto",
        "goos" : null,
        "goarch" : null,
        "signerdir" : "%s",
        "reserved:R" : false,
        "apidir" : "%s",
        "compile<%s.compile_handler>##[target]to compile default geth can accept %s ##" : {
            "$" : "*"
        },
        "initpriv<%s.initpriv_handler>##to init private network##" : {
            "$" : "*"
        },
        "newconfig<%s.newconfig_handler>##modifile key [clause] ... from input to make output with  to make output config##" : {
            "$" : "*"
        },
        "runproc<%s.runproc_handler>##modfile to make config and give the calling##" : {
            "$" : 1
        },
        "killproc<%s.killproc_handler>##to kill process running##" : {
            "$" : 0
        }
    }
    '''
    topdir = get_topdir()
    signerdir = os.path.join(topdir,'datadir_signer')
    apidir = os.path.join(topdir,'datadir_api')
    if is_win():
        topdir = topdir.replace('\\','\\\\')
        signerdir = signerdir.replace('\\','\\\\')
        apidir = apidir.replace('\\','\\\\')

    compiledir = get_compile_targets()
    compiles = ''
    for d in compiledir:
        if len(compiles) > 0:
            compiles += ','
        compiles += '%s'%(d)
    commandline = commandline_fmt%(topdir,signerdir,apidir,__name__,compiles,__name__,__name__,__name__,__name__)
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