"""Pre-primary clock and byte-identity checks. No native work is launched here."""
import hashlib,math
from campaign import ROOT,read,rows,put

def q(values):
 x=sorted(values);return {f'p{p}':x[math.ceil(len(x)*p/100)-1] for p in [50,95,99]}
def members(path):
 data=path.read_bytes();assert data.startswith(b'!<arch>\n');at=8;out={}
 while at<len(data):
  header=data[at:at+60];assert len(header)==60 and header[58:60]==b'\x60\n';size=int(header[48:58]);payload=data[at+60:at+60+size];name=header[:16].decode().strip()
  if name.startswith('#1/'):
   n=int(name[3:]);name=payload[:n].decode().rstrip('\0');payload=payload[n:]
  if not name.startswith('__.SYMDEF'):out[name]=hashlib.sha256(payload).hexdigest()
  at+=60+size+(size%2)
 return out
def main():
 previous=read(ROOT/'build-identities.json');current=read(ROOT/'build-identities-raw.json');identities={}
 for v in ['A','B']:
  assert previous['variants'][v]['correctness_executable_sha256']==current['variants'][v]['correctness_executable_sha256']
  a=members(ROOT/('build-'+v)/'libbmssp_foundation.a');b=members(ROOT/('build-raw-'+v)/'libbmssp_foundation.a');assert a==b
  identities[v]={'same_correctness_executable_bytes':True,'identical_native_object_members':a,'prior_correctness_reports_remain_applicable':True}
 data=rows(ROOT/'clock-characterization-raw.log');empty=[x for x in data if x['kind']=='empty_pair'];assert len(empty)==10000
 assert all(not any(x['clock_rc']) and x['wall_ns']>=0 and x['cpu_ns']>=0 and x['start_aperture_ns']>=0 and x['end_aperture_ns']>=0 for x in empty)
 assert not any(x['off_upper_aperture_ns']<0 for x in empty),'Unvalidated aperture envelope: stop off-CPU collection'
 summary={'empty_pairs':10000,'clock_errors':sum(sum(rc!=0 for rc in x['clock_rc']) for x in empty),'negative_empty_off_estimates':sum(x['off_estimate_ns']<0 for x in empty),'empty_cpu_outside_envelope':sum(x['off_upper_aperture_ns']<0 for x in empty),'empty_distributions_ns':{k:q([x[k] for x in empty]) for k in ['wall_ns','cpu_ns','wall_envelope_ns','start_aperture_ns','end_aperture_ns','off_estimate_ns']},'resolutions':[x for x in data if x['kind']=='clock_resolution'],'observed_increments':{},'native_identity_continuity':identities,'interpretation':'Representation, reported resolution and observed increments do not establish accuracy. Signed wall-minus-CPU is not clamped; CPU spans a wider endpoint interval.'}
 for clock in {x['clock_id'] for x in data if x['kind']=='clock_increment'}:
  group=[x for x in data if x['kind']=='clock_increment' and x['clock_id']==clock];assert len(group)==10000 and all(x['rc']==0 and x['delta_ns']>=0 for x in group)
  summary['observed_increments'][str(clock)]={'min_positive_ns':min(x['delta_ns'] for x in group if x['delta_ns']>0),'zero_count':sum(x['delta_ns']==0 for x in group),'quantiles_ns':q([x['delta_ns'] for x in group])}
 put('clock-quality-raw.json',summary)
if __name__=='__main__':main()
