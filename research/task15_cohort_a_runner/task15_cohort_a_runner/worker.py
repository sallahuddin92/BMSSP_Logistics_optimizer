"""Dedicated synthetic child. Fixed source entry point; production dispatch does not exist."""
import sys
from pathlib import Path
if __package__ in {None,''}:
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from task15_cohort_a_runner import SYNTHETIC
from task15_cohort_a_runner.errors import RunnerError
from task15_cohort_a_runner.wire import MAX_FRAME,canonical,strict_json,validate,frame,write_all,response
from task15_cohort_a_runner.frozen import protocol,compile_plan
from task15_cohort_a_runner.lifecycle import Machine
import os
import struct
import threading


def read_exact(fd,size,allow_eof=False):
    result=bytearray()
    while len(result)<size:
        chunk=os.read(fd,size-len(result))
        if not chunk:
            if not result and allow_eof:return None
            raise RunnerError('IPC_TRUNCATED_FRAME')
        result.extend(chunk)
    return bytes(result)


def incoming():
    header=read_exact(0,4,True)
    if header is None:return None
    size=struct.unpack('!I',header)[0]
    if not 0<size<=MAX_FRAME:raise RunnerError('IPC_FRAME_TOO_LARGE')
    return validate(strict_json(read_exact(0,size)),'REQUEST')


def diagnostic(code,detail=''):
    sys.stderr.buffer.write(canonical({**SYNTHETIC,'event':'WORKER_DIAGNOSTIC','code':code,'detail':str(detail)})+b'\n');sys.stderr.buffer.flush()


def serve():
    p=protocol();machine=Machine(p.data(),compile_plan(p)['units']);fired=False
    while True:
        req=incoming()
        if req is None:
            diagnostic('IPC_DISCONNECTED');return 2
        try:data=machine.handle(req);reply=response(req,data)
        except RunnerError as exc:
            write_all(1,frame(response(req,machine.data(),status='ERROR',error=exc.code)));diagnostic(exc.code,exc.detail);return 2
        fault=machine.fault
        trigger=(not fired and req['phase']=='target' and req['execution_index']==machine.fault_at
                 and req['op']==('FINGERPRINT' if fault=='failed_fingerprint' else 'QUERY'))
        if trigger and fault not in {'none','nonzero_exit'}:
            fired=True;diagnostic('FAULT_INJECTED',fault)
            if fault=='crash':os._exit(71)
            if fault=='missing_response':os._exit(0)
            if fault=='timeout':threading.Event().wait()
            if fault=='disconnect':os.close(1);threading.Event().wait()
            if fault=='wrong_response_identity':reply['unit_id']='wrong-unit'
            if fault=='wrong_variant':reply['variant']='candidate' if req['variant']=='baseline' else 'baseline'
            if fault=='wrong_position':reply['original_position']+=1
            if fault=='wrong_session':reply['session_key']='PRIMARY/wrong'
            if fault=='out_of_order':reply['request_sequence']+=1;reply['response_sequence']+=1
            if fault=='failed_fingerprint':reply['data']['synthetic_fingerprint']='0'*64
            if fault=='malformed_frame':write_all(1,struct.pack('!I',2)+b'{!');continue
            if fault=='oversized_frame':write_all(1,struct.pack('!I',MAX_FRAME+1));continue
            if fault=='truncated_message':write_all(1,struct.pack('!I',100)+b'{');os._exit(0)
            if fault=='duplicate_response':write_all(1,frame(reply)+frame(reply));continue
            if fault=='extra_response':
                extra={**reply,'request_id':'f'*64,'request_sequence':req['request_sequence']+1,'response_sequence':req['response_sequence']+1}
                write_all(1,frame(reply)+frame(extra));continue
        write_all(1,frame(reply))
        if req['op']=='SHUTDOWN':return 72 if fault=='nonzero_exit' else 0


def main():
    if sys.argv[1:]!=['serve-synthetic']:
        diagnostic('UNSUPPORTED_OPERATION');return 2
    try:return serve()
    except RunnerError as exc:diagnostic(exc.code,exc.detail);return 2
    except BaseException as exc:diagnostic('WORKER_INTERNAL',type(exc).__name__);return 2


if __name__=='__main__':raise SystemExit(main())
