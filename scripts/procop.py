#! /usr/bin/env python

import sys
import os
import subprocess
import logging
import traceback
import struct

sys.path.append(os.path.abspath(os.path.dirname(os.path.abspath(__file__))))
from envop import is_windows

class ProcInfo(object):
	def __init__(self):
		self.pid = None
		self.cmdline = []
		self.parentpid = None
		self.firstarg = ''
		return
	def set_pid(self,pid):
		self.pid = pid
		return

	def set_cmdline(self,cmdline):
		self.cmdline = cmdline
		return

	def set_ppid(self,pid):
		self.parentpid = pid
		return

	def set_firstarg(self,firstarg):
		self.firstarg = firstarg
		return

	def __str__(self):
		rets = 'pid:%d,firstarg:%s,parentpid:%s,cmdarr:%s'%(self.pid,self.firstarg,self.parentpid,self.cmdline)
		return rets

class _winprocindex(object):
	def __init__(self):
		self._reset()
		return

	def _reset(self):
		self.pidstart = None
		self.pidend = None
		self.cmdstart = None
		self.cmdend = None
		self.execstart = None
		self.execend = None
		self.capstart = None
		self.capend = None
		return

	def parse_buf(self,buf):
		self._reset()
		idx = 0
		bstart = False
		curstart = None
		curend = None
		while idx < len(buf):
			if curstart is None:
				if buf[idx] != ord(' '):
					curstart = idx
			else:
				if curend is None:
					if buf[idx] == ord(' '):
						curend = idx
						# now to check the value
				else:
					if buf[idx] != ord(' '):						
						nbuf = buf[curstart:curend]
						cs = nbuf.decode('utf-8')
						logging.info('cs [%s]'%(cs))
						ncs = cs.lower()
						if ncs == 'caption':
							self.capstart = curstart
							self.capend = idx
						elif ncs == 'commandline':
							self.cmdstart = curstart
							self.cmdend = idx
						elif ncs == 'executablepath':
							self.execstart = curstart
							self.execend = idx
						elif ncs == 'processid':
							self.pidstart = curstart
							self.pidend = idx
						else:
							logging.error('cs not recognized [%s]'%(cs))
						# now to give the buffer
						curstart = idx
						curend = None
			idx += 1
		if curstart is not None and curstart < idx:
			nbuf = buf[curstart:]
			cs = nbuf.decode('utf-8')
			logging.info('cs [%s]'%(cs))
			cs = cs.rstrip('\r\n')
			if len(cs) > 0:
				ncs = cs.lower()
				if ncs == 'caption':
					self.capstart = curstart
					self.capend = idx
				elif ncs == 'commandline':
					self.cmdstart = curstart
					self.cmdend = idx
				elif ncs == 'executablepath':
					self.execstart = curstart
					self.execend = idx
				elif ncs == 'processid':
					self.pidstart = curstart
					self.pidend = idx
				else:
					logging.error('cs not recognized [%s]'%(cs))
		return

class _uxprocidx(object):
	def __init__(self):
		self._reset()
		return

	def _reset(self):
		self.pidstart = None
		self.pidend = None
		self.userstart = None
		self.userend = None
		self.cmdstart = None
		self.cmdend = None
		self.ppidstart = None
		self.ppidend = None
		return

	def parse_buf(self,buf):
		self._reset()
		idx = 0
		bstart = False
		curstart = None
		curend = None
		while idx < len(buf):
			if curstart is None:
				if buf[idx] != ord(' '):
					curstart = idx
			else:
				if curend is None:
					if buf[idx] == ord(' '):
						curend = idx
						# now to check the value
				else:
					if buf[idx] != ord(' '):						
						nbuf = buf[curstart:curend]
						cs = nbuf.decode('utf-8')
						cs = cs.rstrip('\r\n')
						logging.info('cs [%s]'%(cs))
						ncs = cs.lower()
						if ncs == 'user':
							self.userstart = curstart
							self.userend = idx
						elif ncs == 'cmd':
							self.cmdstart = curstart
							self.cmdend = idx
						elif ncs == 'ppid':
							self.ppidstart = curstart
							self.ppidend = idx
						elif ncs == 'pid':
							self.pidstart = curstart
							self.pidend = idx
						else:
							logging.error('cs not recognized [%s]'%(cs))
						# now to give the buffer
						curstart = idx
						curend = None
			idx += 1
		if curstart is not None and curstart < idx:
			nbuf = buf[curstart:]
			cs = nbuf.decode('utf-8')
			cs = cs.rstrip('\r\n')
			logging.info('cs [%s]'%(cs))
			ncs = cs.lower()
			if ncs == 'user':
				self.userstart = curstart
				self.userend = idx
			elif ncs == 'cmd':
				self.cmdstart = curstart
				self.cmdend = idx
			elif ncs == 'ppid':
				self.ppidstart = curstart
				self.ppidend = idx
			elif ncs == 'pid':
				self.pidstart = curstart
				self.pidend = idx
			else:
				logging.error('cs not recognized [%s]'%(cs))
		return


class ProcExpolore(object):
	def __init__(self):
		self.process = dict()
		return

	def _read_subprocess_output(self,cmds,shellmode=False):
		#logging.info('cmds %s'%(cmds))
		p = subprocess.Popen(cmds,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=shellmode)
		stdoutbuf,stderrbuf = p.communicate()
		return stdoutbuf,stderrbuf

	def _split_buf_lines(self,buf):
		retbufs = []
		idx = 0
		sidx = 0
		while idx < len(buf):			
			if buf[idx] == ord('\r') or buf[idx] == ord('\n'):
				#logging.info('[%d]=b[0x%x]'%(idx,buf[idx]))
				while (idx + 1) < len(buf) and (buf[idx] == ord('\r') or buf[idx+1] == ord('\n')):
					idx += 1
				#logging.info('add [%d:%d] [%s]'%(sidx,idx+1,buf[sidx:(idx+1)]))
				retbufs.append(buf[sidx:(idx+1)])
				sidx = idx+1
			idx += 1
		if sidx < len(buf):
			retbufs.append(buf[sidx:])
		return retbufs

	def _parse_win_pid(self,buf):
		nbuf = b''
		idx = 0
		while idx < len(buf):
			if buf[idx] >= ord('0') and buf[idx] <= ord('9'):
				nbuf += struct.pack('B',buf[idx])
			elif buf[idx] == ord(' '):
				if len(nbuf) > 0:
					break
			idx += 1
		
		try:
			c = nbuf.decode('utf-8')
			reti = int(c)
		except:
			reti = 0
			logging.error('can not parse [%s]'%(repr(buf)))
		return reti

	def _parse_ux_pid(self,buf):
		nbuf = b''
		idx = 0
		while idx < len(buf):
			if buf[idx] >= ord('0') and buf[idx] <= ord('9'):
				nbuf += struct.pack('B',buf[idx])
			idx += 1
		try:
			c = nbuf.decode('utf-8')
			reti = int(c)
		except:
			reti = 0
			logging.error('can not parse [%s]'%(repr(buf)))
		return reti

	def _decode_buf(self,buf):
		rets = None
		try:
			rets = buf.decode('utf-8')
		except:
			pass
		if rets is None:
			try:
				rets = buf.decode('gbk')
			except:
				pass
		if rets is None:
			rets = ''
		return rets

	def _parse_win_cmdline(self,buf):
		idx = 0
		quoted = False
		lastslash = False
		started = False
		nbuf = b''
		outarr = []
		cmdarr = []
		#logging.info('buf [%s]'%(repr(buf)))
		while idx < len(buf):
			if not started:
				if buf[idx] != ord(' ') and buf[idx] != ord('\t'):
					#logging.info('idx [%d] start'%(idx))
					started = True
					nbuf = b''					
					if buf[idx] == ord('"'):
						quoted = True
					elif buf[idx] == ord('\\'):
						lastslash = True
					else:
						nbuf += struct.pack('B',buf[idx])
			else:
				if buf[idx] == ord('"'):
					if lastslash:
						lastslash = False
						nbuf += struct.pack('B',ord('"'))
					elif quoted:
						quoted = False
					else:
						quoted = True
				else:
					if lastslash:
						lastslash = False
						if buf[idx] == ord('t'):
							nbuf += b'\t'
						elif buf[idx] == ord(' '):
							nbuf += b' '
						elif buf[idx] == ord('n'):
							nbuf += b'\n'
						elif buf[idx] == ord('r'):
							nbuf += b'\r'
						elif buf[idx] == ord('b'):
							nbuf += b'\b'
						else:
							nbuf += struct.pack('B',ord('\\'))
							nbuf += struct.pack('B',buf[idx])
					else:
						if buf[idx] == ord(' '):
							if not quoted:
								cmdarr.append(self._decode_buf(nbuf))
								nbuf = b''
								started = False
							else:
								nbuf += struct.pack('B', ord(' '))
						elif buf[idx] == ord('\\'):
							lastslash = True
						else:
							nbuf += struct.pack('B', buf[idx])

			idx += 1
		if len(nbuf) > 0:
			if quoted:
				logging.error('unmatched quoted [%s]'%(repr(nbuf)))
			cmdarr.append(self._decode_buf(nbuf))
			nbuf = b''
		#logging.info('cmdarr %s'%(cmdarr))
		return cmdarr

	def _parse_exec_path(self,buf):
		idx = 0
		quoted = False
		lastslash = False
		started = False
		nbuf = b''
		rets = ''
		#logging.info('buf [%s]'%(repr(buf)))
		sidx = -1
		eidx = -1
		idx = 0
		while idx < len(buf):
			if buf[idx] != ord(' ') and buf[idx] != ord('\t'):
				sidx = idx
				break
			idx += 1

		idx = len(buf) - 1
		while idx >= 0:
			if buf[idx] != ord(' ') and buf[idx] != ord('\t'):
				eidx = idx
				break
			idx -= 1
		nbuf = buf[sidx:(eidx+1)]
		logging.info('[%d:%d] [%s]'%(sidx,eidx,repr(nbuf)))
		if len(nbuf) > 0:
			rets = self._decode_buf(nbuf)
			nbuf = b''
		#logging.info('cmdarr %s'%(cmdarr))
		return rets



	def _scan_windows(self):
		outb,_ = self._read_subprocess_output(['wmic.exe','process','Get','ProcessId,Caption,CommandLine,ExecutablePath'])
		retlines = self._split_buf_lines(outb)
		# now we should give the process get caption
		wproc = _winprocindex()
		idx = 0
		while idx < len(retlines):
			curline = retlines[idx]
			if idx == 0:
				# that is to make sure the pid
				wproc.parse_buf(curline)
			else:
				if len(curline) > wproc.cmdstart and len(curline) > wproc.execstart and len(curline) > wproc.pidstart and len(curline) > wproc.capstart:

					# to split the values
					if wproc.cmdend < len(curline):
						cmdbuf = curline[wproc.cmdstart:wproc.cmdend]
					else:
						cmdbuf = curline[wproc.cmdstart:]
					if wproc.execend < len(curline):
						execbuf = curline[wproc.execstart:wproc.execend]
					else:
						execbuf = curline[wproc.execstart:]

					if wproc.pidend < len(curline):
						pidbuf = curline[wproc.pidstart:wproc.pidend]
					else:
						pidbuf = curline[wproc.pidstart:]

					if wproc.capend < len(curline):
						capbuf = curline[wproc.capstart:wproc.capend]
					else:
						capbuf = curline[wproc.capstart:]
					# now to give the values

					pinfo = ProcInfo()

					# first to parse capname
					cmdarr = self._parse_win_cmdline(cmdbuf)
					pinfo.set_cmdline(cmdarr)
					logging.info('idx [%d] [%s]'%(idx,repr(curline)))
					logging.info('execbuf [%s]'%(repr(execbuf)))
					pid = self._parse_win_pid(pidbuf)
					pinfo.set_pid(pid)
					if len(execbuf) > 0:
						pinfo.set_firstarg(self._parse_exec_path(execbuf))
					else:
						pinfo.set_firstarg('')
					self.process[pinfo.pid] = pinfo
			idx += 1
		return

	def _parse_ux_cmd(self,buf,pid):
		cmdfile = '/proc/%d/cmdline'%(pid)
		inbuf = b''
		cmdarr = []
		try:
			with open(cmdfile,'rb') as fin:
				inbuf = fin.read()
			idx = 0
			nbuf = b''
			while idx < len(inbuf):
				if inbuf[idx] == 0:
					cmdarr.append(self._decode_buf(nbuf))
					nbuf = b''
				else:
					nbuf += struct.pack('B',inbuf[idx])
				idx += 1
			if len(nbuf)>0:
				cmdarr.append(self._decode_buf(nbuf))
				nbuf = b''
			return cmdarr
		except:
			#logging.error('can not open [%s]'%(cmdfile))
			pass
		# now we should give the cmd
		cmdarr = []
		idx = 0
		nbuf = b''
		while idx < len(buf):
			if buf[idx] == ord(' ') or buf[idx] == ord('\r') or buf[idx] == ord('\n'):
				if len(nbuf) > 0:
					cmdarr.append(self._decode_buf(nbuf))
					nbuf = b''
			else:
				nbuf += struct.pack('B',buf[idx])
			idx += 1
		if len(nbuf) > 0:
			cmdarr.append(self._decode_buf(nbuf))
			nbuf = b''
		return cmdarr

	def _parse_ux_execpath(self,buf,pid,cmdarr):
		cmdfile = '/proc/%d/exe'%(pid)
		try:
			rets = os.readlink(cmdfile)
			return rets
		except:
			#logging.error('read %d\n%s'%(pid,traceback.format_exc()))
			pass
		# now to get the buf
		cs = self._decode_buf(buf)
		cs = cs.strip(' \t')
		cs = cs.rstrip('\r\n')
		cs = cs.rstrip(' \t')
		if cs.startswith('['):
			# this is kernel thread
			return cs
		if len(cs) == 0:
			return cs
		cbuf = cs.encode('utf-8')
		idx = 0
		nbuf = b''
		while idx < len(cbuf):
			if cbuf[idx] == ord(' ') or cbuf[idx] == ord('\t'):
				return self._decode_buf(nbuf)
			nbuf += struct.pack('B',cbuf[idx])
			idx += 1
		return self._decode_buf(nbuf)



	def _scan_unix(self):
		outb,_ = self._read_subprocess_output(['ps','-eo','user,pid,ppid,cmd'])
		retlines = self._split_buf_lines(outb)
		idx = 0
		logging.info('retlines [%d]'%(len(retlines)))
		uproc = _uxprocidx()
		while idx < len(retlines):
			curline = retlines[idx]
			curlen = len(curline) - 1
			while curlen >= 0:
				if curline[curlen] != ord('\r') and curline[curlen] != ord('\n'):
					break
				curlen -= 1
			curline = curline[:(curlen+1)]
			if idx == 0:
				pass
			else:
				cidx = 0
				cjdx = 0
				nbuf = b''
				cmdbuf = b''
				userbuf = b''
				pidbuf = b''
				ppidbuf = b''
				while cidx < len(curline):
					if curline[cidx] == ord(' ') or curline[cidx] == ord('\t'):
						if len(nbuf) > 0:
							if cjdx == 0:
								userbuf = nbuf
							elif cjdx == 1:
								pidbuf = nbuf
							elif cjdx == 2:
								#logging.info('cidx %d'%(cidx))
								ppidbuf = nbuf
								while (cidx < len(curline) and curline[cidx] == ord(' ')):
									cidx += 1
								#logging.info('left %s'%(repr(curline[cidx:])))
								cmdbuf = curline[cidx:]
								break
							nbuf = b''
							cjdx += 1
					else:
						nbuf += struct.pack('B',curline[cidx])
					cidx += 1
				if cjdx >= 2:
					logging.info('pidbuf [%s] ppidbuf [%s] cmdbuf [%s]'%(repr(pidbuf),repr(ppidbuf),repr(cmdbuf)))
					pinfo = ProcInfo()
					pinfo.set_pid(self._parse_ux_pid(pidbuf))
					pinfo.set_ppid(self._parse_ux_pid(ppidbuf))
					pinfo.set_cmdline(self._parse_ux_cmd(cmdbuf,pinfo.pid))
					pinfo.set_firstarg(self._parse_ux_execpath(cmdbuf,pinfo.pid,pinfo.cmdline))
					# now first to get the cmdline
					self.process[pinfo.pid] = pinfo			
			idx += 1
		return


	def snapshot(self):
		self.process = dict()
		retval = True
		try:
			if is_windows():
				self._scan_windows()
			else:
				self._scan_unix()
		except:
			retval = False
			logging.error('%s'%(traceback.format_exc()))
		return retval

	def get_result(self):
		return self.process

