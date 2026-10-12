"""Import pinned, already-downloaded classical texts. Does not download or change originals."""
import json
from pathlib import Path
import re
import subprocess
import sys
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.server import load_core_library
BASE=ROOT/'doc/项目/01-古诗词意境/选题库/扩展典籍'
RAW=BASE/'来源快照'
REVISION='b8594f81a89752241442f2ce267d6f66f96704ee'

def normalized(text):
    return re.sub(r'[^\u3400-\u9fffA-Za-z0-9]','',text)

def flatten(node):
    if isinstance(node,list):
        for value in node: yield from flatten(value)
    elif isinstance(node,dict):
        if isinstance(node.get('paragraphs'),list): yield node
        elif 'content' in node: yield from flatten(node['content'])

def simplify(data):
    raw=json.dumps(data,ensure_ascii=False)
    result=subprocess.run(['swift',str(ROOT/'scripts/simplify.swift')],input=raw,text=True,capture_output=True,check=True)
    return json.loads(result.stdout)

def main():
    core=load_core_library()
    # Keep all pre-existing stage records; deduplicate only incoming source texts.
    by_text={normalized(p['text']):p['id'] for p in core}
    imported=[]; links={}; counts=Counter();duplicates=[];excluded=[]
    sources=[('唐诗三百首','蒙学/tangshisanbaishou.json','TS','诗'),('千家诗','蒙学/qianjiashi.json','QJ','诗'),('古文观止','蒙学/guwenguanzhi.json','GW','文言文'),('诗经','诗经/shijing.json','SJ','诗'),('楚辞','楚辞/chuci.json','CC','辞赋'),('宋词三百首','宋词/宋词三百首.json','S3','词')]
    sources += [('全宋词',f'宋词/ci.song.{n}.json',f'SC{n:05d}','词') for n in range(0,21001,1000)]
    for collection,filename,prefix,genre in sources:
        original=json.loads((RAW/filename.replace('/','__')).read_text())
        raw_records=list(flatten(original)) if isinstance(original,dict) else original
        records=simplify(raw_records) if filename.startswith('蒙学/') else raw_records
        for i,record in enumerate(records,1):
            counts[collection]+=1
            rid=f'EXT-{prefix}-{i:04d}'
            paras=record.get('paragraphs',record.get('content',[]))
            if not isinstance(paras,list) or not all(isinstance(x,str) for x in paras):
                excluded.append({'id':rid,'reason':'非文本段落结构'});continue
            text='\n'.join(paras).strip()
            if len(normalized(text))<4 or any(c in text for c in ['□','�','\x00']):
                excluded.append({'id':rid,'reason':'缺字标记或过短文本','source':filename});continue
            key=normalized(text)
            if key in by_text:
                target=by_text[key]
                links.setdefault(target,[])
                if collection not in links[target]:links[target].append(collection)
                duplicates.append({'sourceId':rid,'existingId':target,'collection':collection});continue
            title=record.get('title') or record.get('chapter') or record.get('rhythmic')
            require_title=bool(title)
            if not require_title:excluded.append({'id':rid,'reason':'无题名'});continue
            author=record.get('author') or ('佚名《诗经》' if collection=='诗经' else '作者待核')
            author=re.sub(r'^（[^）]+）','',author)
            item={'id':rid,'title':title,'author':author,'text':text,'stage':'课外','genre':genre,'scope':'典籍扩展',
                  'collections':[collection],'status':'开放语料·未逐字校勘；采用前核对版本',
                  'sourceUrl':f'https://github.com/chinese-poetry/chinese-poetry/blob/{REVISION}/{filename}',
                  'sourcePath':str((RAW/filename.replace('/','__')).relative_to(ROOT)),
                  'sourceRecord':i,'notes':'仅古代原文；保留上游署名，尚未验证作者归属。'+('简体派生文本，繁体原件保存在来源快照。' if filename.startswith('蒙学/') else '')}
            imported.append(item);by_text[key]=rid;links[rid]=[collection]
        print(collection,filename,len(records),flush=True)
    for item in imported:item['collections']=links[item['id']]
    for name,data in [('扩展篇目.json',imported),('典籍关联.json',links),('导入报告.json',{'revision':REVISION,'rawByCollection':dict(counts),'acceptedNewRecords':len(imported),'duplicateCount':len(duplicates),'excludedCount':len(excluded),'duplicates':duplicates,'excluded':excluded})]:
        (BASE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print('新增',len(imported),'重复关联',len(duplicates),'排除',len(excluded))
if __name__=='__main__':main()
