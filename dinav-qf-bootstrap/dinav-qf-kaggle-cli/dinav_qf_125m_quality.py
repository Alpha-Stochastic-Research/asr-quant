import json, math, os, random, re, shutil, subprocess, sys, time, hashlib
from pathlib import Path

WORK=Path('/kaggle/working')
INPUT=Path('/kaggle/input/dinav-qf-125m-pilot-cli')
ROOT=WORK/'dinav_qf_zero_cost_v3'
QUALITY=WORK/'dinav_qf_125m_quality'
STATUS=WORK/'dinav_qf_125m_quality_status.json'
HELD_OUT=[
'A fair coin is tossed twice. Give P(exactly one head) as a decimal.',
'For standard normal Z, give E[Z^2].',
'A zero coupon bond pays 100 in one year. Continuously compounded rate is 5%. Give price rounded to 4 decimals.',
'A 1Y zero rate is 4% continuously compounded. Give the discount factor.',
'For a forward on a non-dividend asset with S0=100, continuously compounded r=5%, T=1, give fair delivery price.',
'State the two quantities needed for a historical 99% one-day VaR calculation.',
]

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def write_status(**kw):
    data={'project':'DINAV-QF','stage':'125M quality post-training','external_llm_calls':0,**kw}
    STATUS.write_text(json.dumps(data,indent=2)); print('STATUS_JSON',json.dumps(data,sort_keys=True),flush=True)

def find_one(pattern):
    xs=list(INPUT.rglob(pattern))
    if not xs: raise FileNotFoundError(pattern)
    xs.sort(key=lambda p:p.stat().st_mtime)
    return xs[-1]

def run(*args,cwd=None):
    print('+',' '.join(map(str,args)),flush=True); subprocess.run(list(map(str,args)),cwd=cwd,check=True)

def canonical(s): return re.sub(r'\s+',' ',s).strip().lower()

def rec(text, i):
    return {
      'text':text,
      'source_uri':f'asr://dinav-qf/deterministic-curriculum/{i}',
      'source_type':'deterministic_quantitative_curriculum',
      'publication_time':'2026-09-12T00:00:00+00:00',
      'retrieved_time':'2026-09-12T00:00:00+00:00',
      'license_id':'owned','rights_owner':'Alpha Stochastic Research',
      'permission_evidence':'Deterministically generated from mathematical identities and numerical computation; no external LLM text generation used.'
    }

def build_curriculum(path):
    rng=random.Random(20260912); rows=[]; i=0
    for _ in range(5000):
        n=rng.randint(3,12); k=rng.randint(0,n); p=rng.choice([.2,.25,.3,.4,.5,.6,.7,.75,.8])
        ans=math.comb(n,k)*(p**k)*((1-p)**(n-k))
        t=f'Question: A Bernoulli trial has success probability p={p:.2f} and is repeated n={n} times independently. What is P(X={k}) for X~Binomial(n,p)? Give a decimal.\nAnswer: {ans:.10f}'
        rows.append(rec(t,i)); i+=1
    for _ in range(5000):
        mu=rng.choice([-2,-1.5,-1,-.5,0,.5,1,1.5,2]); var=rng.choice([.25,.5,1,1.5,2,3,4])
        kind=rng.randrange(4)
        if kind==0: q,a='mean',mu
        elif kind==1: q,a='variance',var
        elif kind==2: q,a='second moment E[X^2]',var+mu*mu
        else: q,a='standard deviation',math.sqrt(var)
        t=f'Question: Let X be normally distributed with mean {mu:.4f} and variance {var:.4f}. Give the {q} as a decimal.\nAnswer: {a:.10f}'
        rows.append(rec(t,i)); i+=1
    for _ in range(8000):
        r=rng.randint(5,120)/1000; T=rng.choice([.25,.5,.75,1.25,1.5,2,3,5,7,10])
        if rng.random()<.5:
            a=math.exp(-r*T); t=f'Question: With continuously compounded zero rate r={r:.4f} and maturity T={T:.2f} years, what is the discount factor exp(-rT)?\nAnswer: {a:.10f}'
        else:
            face=rng.choice([50,80,90,100,120,150,200,1000]); a=face*math.exp(-r*T); t=f'Question: A zero-coupon bond pays {face} at T={T:.2f} years. The continuously compounded zero rate is r={r:.4f}. What is its present value?\nAnswer: {a:.10f}'
        rows.append(rec(t,i)); i+=1
    for _ in range(7000):
        s=rng.choice([40,50,75,80,90,110,120,150,200,250]); r=rng.randint(5,120)/1000; q=rng.choice([0,.005,.01,.015,.02,.025,.03]); T=rng.choice([.25,.5,.75,1.25,1.5,2,3])
        a=s*math.exp((r-q)*T)
        t=f'Question: For an asset with spot S0={s:.2f}, continuously compounded risk-free rate r={r:.4f}, dividend yield q={q:.4f}, and maturity T={T:.2f}, compute the fair forward delivery price S0*exp((r-q)T).\nAnswer: {a:.10f}'
        rows.append(rec(t,i)); i+=1
    concepts=[
      ('Question: In historical Value-at-Risk, which empirical object is taken at the confidence level?', 'Answer: the empirical loss quantile at the selected confidence level.'),
      ('Question: What data and threshold define a one-day historical VaR estimate?', 'Answer: a sample of one-day portfolio losses and the empirical quantile corresponding to the chosen confidence level.'),
      ('Question: Historical VaR is computed from which distribution and which statistic?', 'Answer: the empirical distribution of historical losses and its confidence-level quantile.'),
    ]
    for _ in range(3000):
        q,a=rng.choice(concepts); rows.append(rec(q+'\n'+a,i)); i+=1
    rng.shuffle(rows)
    held=[canonical(x) for x in HELD_OUT]
    for row in rows:
        c=canonical(row['text'])
        if any(h in c for h in held): raise RuntimeError('held-out prompt contamination')
    with path.open('w',encoding='utf-8') as f:
        for row in rows: f.write(json.dumps(row,ensure_ascii=False)+'\n')
    print('CURRICULUM_RECORDS',len(rows),'SHA256',sha(path),flush=True)
    return len(rows)

print('DINAV-QF QUALITY POST-TRAINING',flush=True)
import torch
print('TORCH',torch.__version__,'CUDA',torch.cuda.is_available(),'GPUS',torch.cuda.device_count(),flush=True)
for j in range(torch.cuda.device_count()): print('GPU',j,torch.cuda.get_device_name(j),flush=True)
base_ck=find_one('DINAV-QF-125M-1000.pt'); tokenizer=find_one('dinav_qf_tokenizer.json'); runtime_cfg=find_one('pilot-runtime-config.json')
root_candidates=list(INPUT.rglob('training/model.py'))
if not root_candidates: raise FileNotFoundError('training/model.py in pilot output')
source_root=root_candidates[-1].parents[1]
if ROOT.exists(): shutil.rmtree(ROOT)
shutil.copytree(source_root,ROOT)
QUALITY.mkdir(parents=True,exist_ok=True)
print('BASE_CHECKPOINT',base_ck,'SHA256',sha(base_ck),flush=True)
print('TOKENIZER',tokenizer,'SHA256',sha(tokenizer),flush=True)
train_path=ROOT/'training/train.py'; text=train_path.read_text()
text=text.replace("p.add_argument('--resume', help='checkpoint path to resume model/optimizer/scaler and deterministic batch cursor from')", "p.add_argument('--resume', help='checkpoint path to resume model/optimizer/scaler and deterministic batch cursor from')\n    p.add_argument('--init-model', help='checkpoint whose model weights initialize a fresh optimizer/schedule')")
text=text.replace("model = DinavQF(cfg).to(device)\n    model.set_gradient_checkpointing(args.gradient_checkpointing)", "model = DinavQF(cfg).to(device)\n    if args.init_model:\n        init_state=torch.load(Path(args.init_model).expanduser().resolve(),map_location=device,weights_only=False)\n        model.load_state_dict(init_state['model'])\n        print(json.dumps({'initialized_model_from':str(Path(args.init_model).expanduser().resolve()),'initialized_step':init_state.get('step')}),flush=True)\n    model.set_gradient_checkpointing(args.gradient_checkpointing)")
train_path.write_text(text)
curr=QUALITY/'deterministic_curriculum.jsonl'; n=build_curriculum(curr)
corpus=QUALITY/'corpus'; run(sys.executable,'corpus/bootstrap_125m.py','--raw',str(curr),'--out-dir',str(corpus),cwd=ROOT)
run(sys.executable,'eval/contamination.py','--corpus',str(corpus/'accepted.jsonl'),'--out',str(QUALITY/'contamination.json'),cwd=ROOT)
run(sys.executable,'training/prepare_tokens.py','--tokenizer',str(tokenizer),'--input',str(corpus/'train.jsonl'),'--output',str(QUALITY/'train.bin'),'--meta',str(QUALITY/'train.meta.json'),cwd=ROOT)
out=QUALITY/'checkpoints'
write_status(status='RUNNING',base_checkpoint=str(base_ck),base_checkpoint_sha256=sha(base_ck),curriculum_records=n)
run(sys.executable,'training/train.py','--config',str(runtime_cfg),'--tokens',str(QUALITY/'train.bin'),'--out',str(out),'--steps','500','--micro-batch-size','1','--grad-accum','8','--lr','5e-5','--warmup-steps','50','--checkpoint-every','250','--gradient-checkpointing','--init-model',str(base_ck),cwd=ROOT)
final=out/'DINAV-QF-125M-500.pt'
if not final.exists(): raise FileNotFoundError(final)
run(sys.executable,'eval/model_eval.py','--checkpoint',str(final),'--config',str(runtime_cfg),'--tokenizer',str(tokenizer),'--out',str(QUALITY/'quality-eval.json'),'--max-new-tokens','32',cwd=ROOT)
meta=json.loads((QUALITY/'train.meta.json').read_text())
result=json.loads((QUALITY/'quality-eval.json').read_text())
write_status(status='COMPLETED',base_checkpoint_sha256=sha(base_ck),final_checkpoint=str(final),final_checkpoint_sha256=sha(final),curriculum_records=n,train_tokens=meta.get('tokens'),eval_overall=result.get('overall'),eval_cases=result.get('cases'),completed_at=time.time())
print('QUALITY_FINAL',json.dumps(result,indent=2),flush=True)
