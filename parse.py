import re,glob,os,json
S="/private/tmp/claude-501/-Users-gennaropancia-Desktop-0-Claude-Claude-Code/50949316-693a-45f0-ada1-788c9e9087e8/scratchpad/tax"
PCT=r'(\d+(?:\.\d+)?)\s*%'
def clean(s): return re.sub(r'\s+',' ',s).strip()
def block(lines,start_re,stop_re):
    out=[];on=False
    for l in lines:
        if not on and re.match(start_re,l): on=True; out.append(l); continue
        if on:
            if re.match(stop_re,l): break
            out.append(l)
    return out
def row(sec,label):
    """cella di una riga in tabella, con le righe di continuazione rientrate"""
    for i,l in enumerate(sec):
        m=re.match(r'\s*'+label+r'\s{2,}(.*)$',l)
        if m:
            col=l.index(m.group(1)); val=m.group(1)
            for n in sec[i+1:i+5]:
                if not n.strip(): break
                if len(n)-len(n.lstrip())>=col-2: val+=' '+n.strip()
                else: break
            return clean(val)
    return None
def nums(s): return [float(x) for x in re.findall(PCT,s or '')]
def head(s):
    if s is None: return None
    if re.match(r'(?i)^(0|nil|none|n/a|no\b|there (is|are) no|not applicable)',s) and not nums(s): return 0.0
    n=nums(s); return n[0] if n else None
rows=[]
for f in sorted(glob.glob(S+'/*.txt')):
    t=open(f,errors='ignore').read(); L=t.split('\n')
    slug=re.search(r'dttl-tax-(.+)highlights-(\d{4})',f); 
    title=next((l.strip() for l in L if re.search(r'Highlights\s+\d{4}',l)),'')
    name=re.sub(r'\s*Highlights\s+\d{4}.*','',title).strip()
    upd=next((clean(l).replace('Updated ','') for l in L[:15] if 'Updated' in l),None)
    corp=block(L,r'^Corporate taxation',r'^(Residence|Withholding tax|Individual taxation)')
    ind=block(L,r'^Individual taxation',r'^(Residence|Basis|Taxable income|Withholding tax|Compliance|Value added|Other taxes|Anti-avoidance|Page )')
    vat=block(L,r'^(Value added tax|Goods and services|Consumption|Sales tax|VAT|GST)',r'^(Taxable transactions|Other taxes)')
    wh=block(L,r'^Withholding tax',r'^(Anti-avoidance|Dividends:|Interest:|Royalties:|Tax treaties|Disposition)')
    name=name or {'afghanistan':'Afghanistan','algeria':'Algeria','stvincentandthegrenadines':'St. Vincent and the Grenadines'}.get(slug.group(1),slug.group(1).title())
    r=dict(id=slug.group(1),name=name,year=int(slug.group(2)),updated=upd)
    r['cit_raw']=row(corp,r'Corporate income tax rate(?: \(federal\))?'); r['branch_raw']=row(corp,r'Branch tax rate(?: \(federal\))?'); r['cgt_raw']=row(corp,r'Capital gains tax rate(?: \(federal\))?')
    irow=[l for l in ind]
    # aliquote persone: tutte le % nel blocco fino alla riga capital gains
    cut=next((i for i,l in enumerate(irow) if re.match(r'\s*Capital gains tax rate',l)),len(irow))
    txt=' '.join(irow[:cut]); has=any(re.search('Rate|rate',l) for l in irow[:4])
    ip=[x for x in nums(txt) if x<=70] if has else []
    full=clean(' '.join(block(L,r'^Individual taxation',r'^(Withholding tax|Anti-avoidance|Value added)')))[:400]
    r['pit_top']=max(ip) if ip else (0.0 if re.search(r'(?i)(no individual income tax|no income tax|does not impose income tax|not subject to income|neither resident|zero-rated income tax|zero-tax)',full) else None)
    r['pit_raw']=clean(txt)[:300]
    r['vat_raw']=row(vat,'Standard rate')
    for k,lab in [('wht_div','Dividends'),('wht_int','Interest'),('wht_roy','Royalties')]:
        c=[x for x in wh if re.match(r'\s*'+lab+r'\s{2,}',x)]
        r[k+'_raw']=clean(re.sub(r'^\s*'+lab,'',c[0])) if c else None
    def top(c):
        n=[x for x in nums(c) if x<=60]
        if c and re.search(r'\bplus\b',c) and n: return n[0]
        return max(n) if n else head(c)
    r['cit']=top(r['cit_raw']); r['cgt']=top(r['cgt_raw']); r['vat']=head(r['vat_raw'])
    corp_txt=clean(' '.join(block(L,r'^Corporate taxation',r'^(Individual taxation|Withholding tax)')))[:600]
    r['no_cit']=False
    if r['cit'] is None and re.search(r'(?i)(does not (currently )?have a general corporate|no (general )?corporate (income )?tax|zero-tax|zero-rated|not subject to (corporate )?(income )?tax|no income tax|does not (impose|levy)[^.]{0,40}(income|corporate))',corp_txt):
        r['cit']=0.0; r['no_cit']=True; r['cit_raw']=corp_txt[:160]+'...'
    r['no_vat']=False
    if r['vat'] is None:
        for l in L:
            m=re.match(r'\s*(Standard rate|General rate|Rate|Rates?)\s{2,}(.*\d.*%.*)$',l)
            if m and re.search(r'(?i)(vat|gst|goods|sales|consumption|general)',' '.join(L[max(0,L.index(l)-4):L.index(l)])):
                r['vat_raw']=clean(m.group(2)); r['vat']=head(r['vat_raw']); break
    if r['vat'] is None and re.search(r'(?i)(no|not have an?|does not (impose|levy)( a| any)?) (vat|value added tax|gst|goods and services tax|sales tax)',t):
        r['vat']=0.0; r['no_vat']=True
    for k in ('wht_div','wht_int','wht_roy'):
        n=nums(r[k+'_raw']); r[k]=max(n) if n else (0.0 if r[k+'_raw'] and re.search(r'(?i)\b0\b|nil|none',r[k+'_raw']) else None)
    OV={'bahrain':dict(cit=0.0,no_cit=True,cit_raw='Imposta solo su societa di petrolio e gas; fonte: Corporate taxation'),
        'bvi':dict(cit=0.0,no_cit=True,cit_raw='Societa BVI generalmente esenti da imposta sul reddito; fonte: Corporate taxation'),
        'spain':dict(pit_top=24.5),
        'macausars':dict(cit=12.0,cit_raw='Complementary tax: 0% fino a MOP 600.000, 12% oltre'),
        'india':dict(vat=18.0,vat_raw='General rates 0%/5%/12%/18%/28% (18% come riferimento)'),
        'tanzania':dict(vat=18.0,vat_raw='18% (Tanzania), 15%/18% (Zanzibar)')}
    manual=r['id'] in OV
    r.update(OV.get(r['id'],{}))
    # Controlli qualità
    q=[]
    if r['year']<2026: q.append(f"Edizione {r['year']}: dato da aggiornare")
    if r['cit'] is None: q.append('Aliquota societaria non estratta')
    if r['pit_top'] is None: q.append('Aliquota persone fisiche non estratta')
    if r['vat'] is None: q.append('IVA/GST non estratta (o assente a livello nazionale)')
    if r['cit_raw'] and not r['no_cit'] and len(set(nums(r['cit_raw'])))>1: q.append('Aliquota societaria con più valori: mostrata la più alta')
    if r['no_cit']: q.append('Nessuna imposta societaria generale: leggere le eccezioni nella fonte')
    if r['cit'] is not None and r['cit']>45: q.append('Aliquota societaria insolitamente alta: verificare')
    if r['pit_top'] is not None and r['pit_top']>=56: q.append('Aliquota persone fisiche molto alta: possibile somma di più imposte, verificare')
    if r['vat'] is not None and r['vat']>28: q.append('IVA insolitamente alta: verificare')
    m=re.search(r'standard corporate[^.]{0,60}?rate[^.]{0,40}?'+PCT,t)
    if m and r['cit'] is not None and abs(float(m.group(1))-r['cit'])>0.01: q.append(f"Tabella ({r['cit']}%) e testo ({m.group(1)}%) non coincidono")
    if re.search(r'(?i)national rate|federal|excluding|not including|municipal|communal|regional|cantonal|state',r['pit_raw'] or ''): q.append('Persone fisiche: mostrata la sola quota nazionale o parziale')
    if manual: q.append('Valore inserito a mano dopo lettura della fonte')
    if r['cit_raw'] and re.search(r'\bplus\b|provincial|cantonal|state|local',r['cit_raw']) or r['id'] in ('switzerland','unitedstates'): q.append('Esistono imposte locali o regionali non incluse nel valore mostrato')
    r['flags']=q; rows.append(r)
json.dump(rows,open('data.json','w'),ensure_ascii=False,indent=0)
n=len(rows); print(n)
for k in ('cit','pit_top','vat','cgt','wht_div','wht_int','wht_roy'): print(k,sum(r[k] is not None for r in rows))
print('flagged',sum(bool(r['flags']) for r in rows))
print('NO CIT',[r['id'] for r in rows if r['cit'] is None]); print('NO VAT',[r['id'] for r in rows if r['vat'] is None]); print('NO PIT',[r['id'] for r in rows if r['pit_top'] is None])
print([ (r['id'],r['cit'],r['pit_top'],r['vat'],r['wht_div']) for r in rows if r['id'] in ('uae','bahamas','caymanislands','albania','lithuania','india','australia','canada','singapore','brazil','qatar','switzerland','hongkongsar','unitedstates','ireland','spain','netherlands','portugal')])
