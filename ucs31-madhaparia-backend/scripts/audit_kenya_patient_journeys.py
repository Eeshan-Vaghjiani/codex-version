"""Capture actual patient-API journeys for baseline/final comparison.

Synthetic software inputs carry expected behavior categories, never invented
clinical disease labels. Loopback hosts only; writes synthetic audit users.
"""
import argparse,json,uuid
from pathlib import Path
from urllib.parse import urlparse
import httpx

CASES = [
 ('tiredness','nonspecific','I am tired all the time.'),
 ('headache','nonspecific','I have a headache.'),
 ('mild_fever','nonspecific','I have a mild fever.'),
 ('muscle_aches','nonspecific','My muscles ache all over my body.'),
 ('headache_tiredness','nonspecific','I have a headache and feel tired.'),
 ('fever_headache','nonspecific','I have a mild fever and headache.'),
 ('cough','respiratory','I have a cough.'),
 ('sore_throat','respiratory','My throat is sore.'),
 ('cough_throat','respiratory','I have cough and a sore throat.'),
 ('flu_like','respiratory','I have fever, cough, sore throat and body aches for two days.'),
 ('informative','respiratory','I have fever and cough with a runny nose and sore throat for two days, but no difficulty breathing.'),
 ('sw_negation','language','Nina kikohozi lakini sina homa.'),
 ('misspelling','language','I have a couhg and feaver.'),
 ('unsupported','unsupported','I have abdominal pain and nausea.'),
 ('mixed_unsupported','unsupported','I have a headache and a skin rash.'),
 ('contradictory','contradictory','I have cough but I do not have cough.'),
 ('vague','vague','I feel unwell.'),
 ('urgent_breathing','urgent','I am struggling to breathe.'),
 ('urgent_sw','urgent','Siwezi kupumua.'),
 ('urgent_blue_lips','urgent','My lips are turning blue.'),
 ('negated_warning','nonurgent','I have cough but no difficulty breathing.'),
 ('prolonged_cough','review','I have cough for two weeks and have lost weight without trying.'),
]


def run(base_url):
 if urlparse(base_url).hostname not in {'localhost','127.0.0.1','::1'}:
  raise ValueError('Loopback audit API only')
 outputs=[]
 with httpx.Client(base_url=base_url,timeout=60) as client:
  credentials={'email':f'kenya-audit-{uuid.uuid4().hex}@example.com','password':'LocalKenyaAudit2026!'}
  client.post('/auth/register',json=credentials).raise_for_status()
  token=client.post('/auth/login',json=credentials);token.raise_for_status()
  client.headers['Authorization']='Bearer '+token.json()['access_token']
  status=client.get('/model/status');status.raise_for_status()
  for case_id,category,text in CASES:
   mapped=client.post('/nlp/map',json={'text':text});mapped.raise_for_status();mapping=mapped.json()
   selected=[s['code'] for s in mapping['recognised_symptoms'] if s.get('status','present')=='present' and s.get('reported_subject')!='other_person']
   payload={'age':21,'sex':'M','text':text,'confirmed_codes':selected,'follow_up_answers':[]}
   turns=[]
   for _ in range(6):
    response=client.post('/predict',json=payload);response.raise_for_status();result=response.json()
    if result['status']!='needs_follow_up': break
    question=result['follow_up_question']; choices={x['value'] for x in question['options']}
    answer='no' if question['id']=='breathing_difficulty' else 'unknown'
    assert answer in choices
    turns.append({'id':question['id'],'question':question['text'],'answer':answer})
    payload['follow_up_answers'].append({'question_id':question['id'],'answer':answer})
   else: raise AssertionError('Follow-up limit exceeded')
   outputs.append({'id':case_id,'category':category,'input':text,'mapping':mapping,'turns':turns,'result':result})
 return {'purpose':'Actual API observations for synthetic software cases, not clinical disease ground truth',
         'model_status':status.json(),'answer_policy':'No breathing difficulty; all other unreported questions explicitly not sure',
         'cases':outputs}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://127.0.0.1:8000');parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 data=run(args.base_url);args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
 print(json.dumps([{'id':x['id'],'category':x['category'],'status':x['result']['status'],'displayed_conditions':[p['condition'] for p in x['result'].get('predictions',[])]} for x in data['cases']]))
