#! /usr/bin/env python


import os
import extargsparse
import sys
import traceback
import re
import logging
import subprocess

sys.path.append(os.path.abspath(os.path.dirname(os.path.abspath(__file__))))

from loglib import set_logging, load_log_commandline,log_command_prefix
from fileop import read_file,write_file,make_directory_safe,mktemp_file
from envop import is_win,is_linux,is_cygwin


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
        os.chdir(builddir)
        logging.info('GO111MODULE [%s] GOPROXY [%s]'%(args.go111module,args.goproxy))
        logging.info('run %s'%(cmds))
        subprocess.check_call(cmds,env=myenv)
        retval = True
    except:
        logging.error('%s'%(traceback.format_exc()))
    os.chdir(retdir)
    return retval


def compile_single_target(args,target):
    retdir = os.getcwd()
    retval = False
    cmds = []

    if is_win() or is_cygwin():
        if is_cygwin():
            cmds.append('./build/build.exe')
        else:
            cmds.append('.\\build\\build.exe')
    else:
        cmds.append('./build/build')
    cmds.append('install')
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

def generate_account(args,datadir,secfile):
    cmds = []
    if is_win() or is_cygwin():
        gethbin = os.path.join(args.topdir,'build','bin','cmd','geth.exe')
    else:
        gethbin = os.path.join(args.topdir,'build','bin','cmd','geth')
    cmds.append(gethbin)
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
    if is_win() or is_cygwin():
        gethbin = os.path.join(args.topdir,'build','bin','cmd','geth.exe')
    else:
        gethbin = os.path.join(args.topdir,'build','bin','cmd','geth')
    cmds.append(gethbin)
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


def load_base_parser(parser):
    commandline_fmt='''
    {
        "input|i" : null,
        "output|o" : null,
        "topdir|T" : "%s",
        "goproxy" : "https://goproxy.cn",
        "go111module" : "auto",
        "signerdir" : "%s",
        "apidir" : "%s",
        "compile<%s.compile_handler>##[target]to compile default geth can accept %s ##" : {
            "$" : "*"
        },
        "initpriv<%s.initpriv_handler>##to init private network##" : {
            "$" : "*"
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
    commandline = commandline_fmt%(topdir,signerdir,apidir,__name__,compiles,__name__)
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