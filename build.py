import json
R=json.load(open('data.json'))
keep=['id','name','year','updated','cit','cit_raw','cgt','cgt_raw','pit_top','pit_raw','vat','vat_raw','wht_div','wht_div_raw','wht_int','wht_int_raw','wht_roy','wht_roy_raw','no_cit','no_vat','flags']
D=[{k:(r.get(k)[:170] if isinstance(r.get(k),str) else r.get(k)) for k in keep} for r in R]
D.sort(key=lambda r:r['name'])
open('index.html','w').write(open('template.html').read().replace('/*DATA*/[]',json.dumps(D,ensure_ascii=False,separators=(',',':')).replace('—',',')))
print(len(D))
