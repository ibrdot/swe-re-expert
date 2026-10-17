#!/usr/bin/env python3
"""Build a deterministic, read-only versioned JSON API from the catalogue."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def build():
    data=json.loads((ROOT/'docs/data/skills.json').read_text())
    target=ROOT/'docs/api/v1'
    if target.exists(): shutil.rmtree(target)
    target.mkdir(parents=True)
    def write(name,obj):
        p=target/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(obj,ensure_ascii=True,indent=2)+'\n')
    skills=[]
    for row in data['skills']:
        skill=dict(row)
        skill['key']=hashlib.sha256(row['skill_file'].encode()).hexdigest()[:20]
        skill['content_sha256']=hashlib.sha256((ROOT/row['skill_file']).read_bytes()).hexdigest()
        skills.append(skill)
        write('skills/'+skill['key']+'.json',skill)
    digest=hashlib.sha256(json.dumps(skills,sort_keys=True).encode()).hexdigest()
    write('skills.json',{'api_version':'1','revision':digest,**data,'skills':skills})
    write('stats.json',{'api_version':'1','revision':digest,'counts':data['counts'],'categories':data['categories']})
    write('categories.json',{'api_version':'1','categories':[{'name':name,'count':count} for name,count in data['categories'].items()]})
    collections=[{'id':key,'name':label,'count':data['counts'][key]} for key,label in [('builtin','Suite skills'),('awesome','Community collection'),('mattpocock','Engineering collection')]]
    write('collections.json',{'api_version':'1','collections':collections})
    write('index.json',{'api_version':'1','revision':digest,'read_only':True,'endpoints':{'skills':'skills.json','stats':'stats.json','categories':'categories.json','collections':'collections.json','skill':'skills/{key}.json'},'filtering':'Download skills.json and filter client-side. Query parameters do not filter static JSON.','authentication':'None. Public static files; no writes, secrets, or account API.'})
    fields=['key','name','skill_file','description','content_sha256']
    item={'type':'object','required':fields,'properties':{k:{'type':'string'} for k in fields}}
    schema={'$schema':'https://json-schema.org/draft/2020-12/schema','title':'Skill collection API v1','type':'object','required':['api_version','revision','skills','counts'],'properties':{'api_version':{'const':'1'},'revision':{'type':'string'},'counts':{'type':'object'},'skills':{'type':'array','items':item}}}
    write('schema.json',schema)
    print(f'Generated API v1: {len(skills)} detail endpoints; revision {digest[:12]}')
if __name__=='__main__':build()
