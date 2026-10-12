"""Produce the explicit v1 excerpt edition from local sources. No network/model calls."""
from pathlib import Path
import sys,json,csv
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.server import load_library
from app.excerpts import BASE,VERSION,extract_poem,classify

def main():
    poems=load_library();counts={k:Counter() for k in ['themes','moods','appeals','visuals','uses','methods']}
    total=0;empty=[];summaries=[]
    with (BASE/'片段.jsonl').open('w') as out:
        for p in poems:
            chunks=extract_poem(p);pt=Counter();pm=Counter()
            if not chunks:empty.append(p['id'])
            for chunk in chunks:
                row={'id':f"{p['id']}:{chunk['start']}-{chunk['end']}",'poemId':p['id'],**chunk,**classify(chunk['quote'],p)}
                assert p['text'][row['start']:row['end']]==row['quote']
                out.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n');total+=1
                for k in ['themes','moods','appeals','visuals','uses']:counts[k].update(row[k])
                counts['methods'].update([row['method']]);pt.update(row['themes']);pm.update(row['moods'])
            summaries.append({'原文编号':p['id'],'作品':p['title'],'学段':p['stage'],'片段数':len(chunks),'主题初分':' / '.join(pt),'意境初分':' / '.join(pm),'状态':'已全量处理·分类提案待复核' if chunks else '无法提取·待检查'})
    with (BASE/'全篇分类.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(summaries[0]));w.writeheader();w.writerows(summaries)
    report={'version':VERSION,'poems':len(poems),'excerpts':total,'emptyPoems':empty,'review':'draft',**{k:dict(v) for k,v in counts.items()}}
    (BASE/'分类覆盖.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['themes','moods','appeals','visuals']},ensure_ascii=False))
if __name__=='__main__':main()
