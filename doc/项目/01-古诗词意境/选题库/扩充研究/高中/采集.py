"""只采集公开页面古代原文区；不保存现代翻译、赏析或页面脚本。"""
from pathlib import Path
from urllib.request import urlopen
import re, html, json, concurrent.futures
P=Path(__file__).parent
items=[
('齐桓晋文之事','孟子及弟子','4a849bab9912','必修下册'),
('庖丁解牛','庄子','8def13da8f71','必修下册'),
('烛之武退秦师','《左传》','5472fd05f090','必修下册'),
('鸿门宴','司马迁','7cec0d1b3a86','必修下册'),
('窦娥冤（节选）','关汉卿','29fe1b347a74','必修下册'),
('与妻书','林觉民','7de576f0313f','必修下册'),
('促织','蒲松龄','95f1b5461664','必修下册'),
('大学之道','《礼记》','189215dc85ba','选择性必修上册'),
('人皆有不忍人之心','孟子及弟子','a2e7b92926c0','选择性必修上册'),
('《老子》四章','老子（传统署名）','353675c10e72','选择性必修上册'),
('兼爱（节选）','墨子及弟子','c01db9833cfc','选择性必修上册'),
('苏武传（节选）','班固','1a715a287bed','选择性必修中册'),
('氓','佚名《诗经·卫风》','c7a0f08d98cd','选择性必修下册'),
('孔雀东南飞（并序）','佚名','294ee4bb68a3','选择性必修下册'),
('过小孤山大孤山','陆游','fe030ab3e99a','扩展阅读'),
('项羽之死','司马迁','bc997e002dac','扩展阅读'),
('方山子传','苏轼','d096aa313844','扩展阅读'),
('大铁椎传','魏禧','1eaf8cb4d822','扩展阅读'),
('祭十二郎文','韩愈','70b78cce30db','扩展阅读'),
('狱中杂记','方苞','54ea190b7c6f','扩展阅读'),
('陶庵梦忆序','张岱','446fa45f769c','扩展阅读'),
('春夜宴从弟桃花园序','李白','7ae587439291','扩展阅读'),
('游兰溪','苏轼','672b3094c6a6','扩展阅读'),
('苦斋记','刘基','3022bd5decb8','扩展阅读'),
]
def get(it):
 title,author,key,book=it;u='https://www.guwendao.net/shiwenv_'+key+'.aspx'
 s=urlopen(u,timeout=25).read().decode()
 m=re.search(r'<div class="contson"[^>]*>(.*?)</div>',s,re.S)
 if not m:raise ValueError(title+' 原文区缺失')
 frag=m.group(1)
 frag=re.sub(r'<br\s*/?>|</p>', '\n',frag)
 t=html.unescape(re.sub(r'<[^>]+>','',frag))
 t='\n'.join(line.strip() for line in t.splitlines() if line.strip())
 return {'title':title,'author':author,'text':t,'sourceUrl':u,'stage':'高中','genre':'诗' if title in ['氓','孔雀东南飞（并序）'] else '曲' if title.startswith('窦娥') else '文言文','scope':'创作扩展·旧版选修线索' if book=='扩展阅读' else '统编教材补充','book':book,'notes':'已采集公开原文，未逐字对照教材定本；不是新增全国统一高考必背条目。' if book!='扩展阅读' else '原文已采集；旧版选修归属仅有二级目录线索，未核出版社原书，不计当前教材覆盖。','status':'已采集待校勘','accessedAt':'2026-10-08'}
rows=[]
for it in items:
 try:
  r=get(it);rows.append(r);print(r['title'],len(r['text']),r['text'][:25],r['text'][-25:])
 except Exception as e:print('FAILED',it[0],str(e))
 (P/'原文采集证据.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
