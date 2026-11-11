"""One outstanding request per owned child. Clocks are IPC deadlines only, never measurements."""
import os
import select
import struct
import subprocess
import sys
import time
from pathlib import Path
from .errors import RunnerError,require
from .wire import MAX_FRAME,frame,strict_json,validate,validate_reply,request,write_all,digest


def receive(fd,timeout,capture):
    deadline=time.monotonic()+timeout
    def exact(size,header=False):
        data=bytearray()
        while len(data)<size:
            remaining=deadline-time.monotonic()
            require(remaining>0,'IPC_TIMEOUT')
            ready,_,_=select.select([fd],[],[],remaining)
            require(bool(ready),'IPC_TIMEOUT')
            chunk=os.read(fd,size-len(data))
            if not chunk:
                raise RunnerError('IPC_EOF' if header and not data else 'IPC_TRUNCATED_FRAME')
            capture(chunk);data.extend(chunk)
        return bytes(data)
    header=exact(4,True);size=struct.unpack('!I',header)[0]
    require(0<size<=MAX_FRAME,'IPC_FRAME_TOO_LARGE')
    return validate(strict_json(exact(size)),'RESPONSE')


class Peer:
    def __init__(self,binding,directory,recorder,timeout=2.0):
        self.binding=binding;self.instance_id=digest([binding['unit_id'],binding['variant'],binding['session_key']]);self.recorder=recorder;self.timeout=timeout;self.sequence=0;self.seen=set();self.exited=False
        directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
        self.stdout_path=directory/(binding['variant']+'.stdout.bin');self.stderr_path=directory/(binding['variant']+'.stderr.jsonl')
        self.stdout=self.stdout_path.open('xb');self.stderr=self.stderr_path.open('xb')
        worker=Path(__file__).with_name('worker.py')
        env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':str(recorder.root/'private-home'),
             'TMPDIR':str(recorder.root/'private-tmp'),'LC_ALL':'C','LANG':'C','PYTHONDONTWRITEBYTECODE':'1'}
        try:
            self.process=subprocess.Popen([sys.executable,'-I','-B',str(worker),'serve-synthetic'],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.stderr,bufsize=0,
                cwd=recorder.root,env=env,start_new_session=True,close_fds=True)
        except OSError as exc:
            self.stdout.close();self.stderr.close();raise RunnerError('WORKER_START_FAILED',str(exc)) from exc
        try:recorder.worker_event('WORKER_CREATED',self,environment=env)
        except BaseException:
            self.process.terminate();self.process.wait(timeout=1)
            self.process.stdin.close();self.process.stdout.close();self.stdout.close();self.stderr.close()
            raise

    def capture(self,data):
        self.stdout.write(data)

    def classify_eof(self,exc):
        if exc.code!='IPC_EOF':raise exc
        try:code=self.process.wait(timeout=0.2)
        except subprocess.TimeoutExpired:raise RunnerError('IPC_DISCONNECTED') from exc
        raise RunnerError('WORKER_CRASH' if code!=0 else 'IPC_MISSING_RESPONSE',str(code)) from exc

    def quiet(self):
        ready,_,_=select.select([self.process.stdout.fileno()],[],[],0)
        if ready:
            try:extra=receive(self.process.stdout.fileno(),self.timeout,self.capture)
            except RunnerError as exc:self.classify_eof(exc)
            self.recorder.ipc(None,extra,self.process.pid,'UNEXPECTED_RESPONSE')
            if extra['request_id'] in self.seen or extra['response_sequence']<=self.sequence:
                raise RunnerError('IPC_DUPLICATE_RESPONSE')
            raise RunnerError('IPC_UNEXPECTED_EXTRA_RESPONSE')

    def rpc(self,op,query=None,data=None,region=''):
        self.quiet();self.sequence+=1
        req=request(self.binding,op,self.sequence,query,data,region)
        self.recorder.ipc(req,None,self.process.pid,'REQUEST')
        write_all(self.process.stdin.fileno(),frame(req))
        try:reply=receive(self.process.stdout.fileno(),max(self.timeout,10) if op=='HELLO' else self.timeout,self.capture)
        except RunnerError as exc:self.classify_eof(exc)
        self.recorder.ipc(None,reply,self.process.pid,'RESPONSE')
        require(reply['request_id'] not in self.seen,'IPC_DUPLICATE_RESPONSE');self.seen.add(reply['request_id'])
        validate_reply(req,reply)
        require(reply['data']['pid']==self.process.pid,'IPC_WORKER_PID')
        self.quiet_unless_shutdown(op)
        return reply

    def quiet_unless_shutdown(self,op):
        # Shutdown EOF is expected, but final trailing bytes are checked after wait().
        if op!='SHUTDOWN':self.quiet()

    def shutdown(self):
        reply=self.rpc('SHUTDOWN')
        require(reply['data']['worker_complete'] is True,'WORKER_INCOMPLETE')
        try:code=self.process.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired as exc:raise RunnerError('WORKER_EXIT_TIMEOUT') from exc
        require(code==0,'WORKER_NONZERO_EXIT',str(code))
        extra=self.process.stdout.read()
        if extra:
            self.capture(extra);raise RunnerError('IPC_UNEXPECTED_EXTRA_RESPONSE')
        self.exited=True
        self.recorder.worker_event('WORKER_EXIT_VERIFIED',self,exit_code=code)
        return code

    def cleanup(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=1)
        # Preserve remaining partial/corrupt wire bytes after termination.
        rest=self.process.stdout.read()
        if rest:self.capture(rest)
        self.process.stdin.close();self.process.stdout.close()
        self.stdout.flush();os.fsync(self.stdout.fileno());self.stdout.close()
        self.stderr.flush();os.fsync(self.stderr.fileno());self.stderr.close()
        self.recorder.worker_event('WORKER_CLEANED',self,exit_code=self.process.returncode,verified_exit=self.exited)
        return {'pid':self.process.pid,'instance_id':self.instance_id,'variant':self.binding['variant'],'exit_code':self.process.returncode,'verified_exit':self.exited}
