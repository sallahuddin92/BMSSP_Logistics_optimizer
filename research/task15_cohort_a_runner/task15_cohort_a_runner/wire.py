"""Closed canonical JSON messages in bounded network-order length frames."""
import hashlib
import json
import math
import os
import struct
from . import SYNTHETIC
from .errors import RunnerError, require

MAX_FRAME = 65536
OPS = {'HELLO','PREPARE','QUERY','FINGERPRINT','RELEASE','SHUTDOWN'}
FAULTS = {'none','crash','nonzero_exit','timeout','wrong_response_identity','missing_response',
    'duplicate_response','wrong_variant','wrong_position','failed_fingerprint','wrong_session',
    'out_of_order','malformed_frame','oversized_frame','truncated_message','extra_response','disconnect'}
IDENTITY = {'protocol_sha256','session_key','unit_id','variant','query_id','phase','region',
            'execution_index','original_position','source_id','source_occurrence'}
FIELDS = {'schema_version','kind','op','request_id','request_sequence','response_sequence',
          'status','error_code','data','synthetic','measurement_eligible'} | IDENTITY


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def strict_json(data):
    def pairs(items):
        out={}
        for key,value in items:
            require(key not in out,'IPC_DUPLICATE_KEY',key);out[key]=value
        return out
    def reject(value):
        raise RunnerError('IPC_NONFINITE',value)
    try:
        obj=json.loads(data.decode('utf-8'),object_pairs_hook=pairs,parse_constant=reject,
                       parse_float=lambda v: float(v) if math.isfinite(float(v)) else reject(v))
    except (ValueError,UnicodeError) as exc:
        raise RunnerError('IPC_MALFORMED_JSON',str(exc)) from exc
    require(canonical(obj)==data,'IPC_NONCANONICAL_JSON','exact canonical encoding required')
    return obj


def validate(message, kind):
    require(type(message) is dict and set(message)==FIELDS,'IPC_SCHEMA_FIELDS')
    for key in ['schema_version','kind','op','status','error_code']:
        require(type(message[key]) is str,'IPC_SCHEMA_TYPE',key)
    require(message['synthetic'] is True and message['measurement_eligible'] is False,'IPC_SYNTHETIC_BOUNDARY')
    require(message['schema_version']=='1' and message['kind']==kind,'IPC_SCHEMA_VERSION')
    require(message['op'] in OPS,'IPC_UNSUPPORTED_OPERATION')
    require(type(message['request_sequence']) is int and type(message['response_sequence']) is int
            and message['request_sequence']>0 and message['response_sequence']==message['request_sequence'],'IPC_SEQUENCE')
    require(type(message['data']) is dict,'IPC_DATA_SCHEMA')
    for key in IDENTITY-{'execution_index','original_position','source_occurrence'}:
        require(type(message[key]) is str,'IPC_SCHEMA_TYPE',key)
    for key in ['execution_index','original_position','source_occurrence']:
        require(type(message[key]) is int,'IPC_SCHEMA_TYPE',key)
    require(message['variant'] in {'baseline','candidate'} and message['phase'] in {'control','warmup','target'},'IPC_SCHEMA_ENUM')
    require(type(message['request_id']) is str and len(message['request_id'])==64 and all(c in '0123456789abcdef' for c in message['request_id']),'IPC_REQUEST_ID')
    require(message['status'] in ({'REQUEST'} if kind=='REQUEST' else {'OK','ERROR'}) and type(message['error_code']) is str,'IPC_STATUS')
    if kind=='REQUEST':
        keys={'fault','fault_at'} if message['op']=='HELLO' else {'graph_kind'} if message['op']=='PREPARE' else set()
        require(set(message['data'])==keys,'IPC_DATA_FIELDS')
        if message['op']=='HELLO':
            require(type(message['data']['fault']) is str and message['data']['fault'] in FAULTS and type(message['data']['fault_at']) is int and message['data']['fault_at']>=0,'IPC_FAULT_CONFIG')
        if message['op']=='PREPARE':require(message['data']['graph_kind']=='SYNTHETIC_STRUCTURAL_ONLY','IPC_GRAPH_KIND')
    else:
        d=message['data'];keys={'pid','backend','states','retained','prior_result_cleared','synthetic_fingerprint',
            'completed_queries','prepared_regions','worker_complete','conceptual_timing_active'}
        require(set(d)==keys,'IPC_DATA_FIELDS')
        require(type(d['pid']) is int and d['pid']>0 and d['backend']=='SYNTHETIC_ONLY','IPC_BACKEND')
        for key in ['retained','prior_result_cleared','worker_complete','conceptual_timing_active']:
            require(type(d[key]) is bool,'IPC_DATA_TYPE',key)
        require(type(d['states']) is list and all(type(x) is str for x in d['states']),'IPC_DATA_TYPE','states')
        require(type(d['prepared_regions']) is list and all(type(x) is str for x in d['prepared_regions']),'IPC_DATA_TYPE','prepared_regions')
        require(type(d['completed_queries']) is int and d['completed_queries']>=0 and type(d['synthetic_fingerprint']) is str,'IPC_DATA_TYPE')
        require(d['conceptual_timing_active'] is False,'IPC_CONCEPTUAL_BOUNDARY')
    return message


def frame(message):
    data=canonical(message);require(0<len(data)<=MAX_FRAME,'IPC_FRAME_TOO_LARGE')
    return struct.pack('!I',len(data))+data


def write_all(fd,data):
    view=memoryview(data)
    try:
        while view:
            count=os.write(fd,view);require(count>0,'IPC_DISCONNECTED');view=view[count:]
    except (BrokenPipeError,OSError) as exc:
        raise RunnerError('IPC_DISCONNECTED',str(exc)) from exc


def request(binding, op, sequence, query=None, data=None, region=''):
    q=query or {}
    msg={**SYNTHETIC,'schema_version':'1','kind':'REQUEST','op':op,
        'protocol_sha256':binding['protocol_sha256'],'session_key':binding['session_key'],
        'unit_id':binding['unit_id'],'variant':binding['variant'],
        'query_id':q.get('query_id',''),'phase':q.get('phase','control'),
        'region':q.get('region',region),'execution_index':q.get('execution_index',-1),
        'original_position':q.get('original_position',-1),'source_id':q.get('source_id',''),
        'source_occurrence':q.get('source_occurrence',0),'request_sequence':sequence,
        'response_sequence':sequence,'status':'REQUEST','error_code':'','data':data or {}}
    msg['request_id']=digest([msg[k] for k in ['protocol_sha256','unit_id','variant','op','query_id','region','request_sequence']])
    return validate(msg,'REQUEST')


def response(req,data,status='OK',error=''):
    msg={**req,'kind':'RESPONSE','status':status,'error_code':error,'data':data}
    return validate(msg,'RESPONSE')


def validate_reply(req, reply):
    validate(reply,'RESPONSE')
    checks=[('variant','IPC_WRONG_VARIANT'),('session_key','IPC_WRONG_SESSION'),
        ('unit_id','IPC_WRONG_UNIT'),('original_position','IPC_WRONG_POSITION'),
        ('protocol_sha256','IPC_PROTOCOL_IDENTITY'),('query_id','IPC_QUERY_IDENTITY'),
        ('region','IPC_REGION_IDENTITY'),('execution_index','IPC_EXECUTION_INDEX'),
        ('source_id','IPC_SOURCE_IDENTITY'),('source_occurrence','IPC_SOURCE_OCCURRENCE'),
        ('phase','IPC_PHASE'),('op','IPC_OPERATION'),('request_id','IPC_CORRELATION'),
        ('request_sequence','IPC_OUT_OF_ORDER'),('response_sequence','IPC_OUT_OF_ORDER')]
    for field,code in checks:
        require(reply[field]==req[field],code,field)
    require(reply['status']=='OK',reply['error_code'] or 'WORKER_ERROR')
    return reply
