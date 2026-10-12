from pathlib import Path
import re,csv
p=Path(__file__).parent
src='https://www.hnwu.edu.cn/ewebeditor/uploadfile/20231006195220323.pdf'
standard='https://www.ictr.edu.cn/Uploads/File/2022/04/28/3.%E4%B9%89%E5%8A%A1%E6%95%99%E8%82%B2%E8%AF%AD%E6%96%87%E8%AF%BE%E7%A8%8B%E6%A0%87%E5%87%86%EF%BC%882022%E5%B9%B4%E7%89%88%EF%BC%89.20220428161048.pdf'
s=(p/'来源/来源提取-初中60篇.txt').read_text();s=re.sub(r'^\d+\n','',s,flags=re.M)
c=re.split(r'(?m)^(\d+)\.\s*([^\n]+)\n',s)
rows=[]; docs=['# 初中课标推荐古诗文原文（60个推荐条目）\n\n按2022课标原序号，先分体裁，不加场景、情绪或镜头标签。古代公版文本已收录，**仍待采用时对照指定教材版次逐字复核**。推荐篇目已直接对照课程教材研究所所载课标扫描页61–63；原文不能仅靠课标校验，因为课标只列目录。\n\n本文件是从原始汇编派生的工作文本，不改原件；已识别的错误与替换见[来源与覆盖](来源与覆盖.md)。\n']
authors='《诗经》|《诗经》|汉乐府|曹操|陶潜|北朝民歌|王勃|陈子昂|王湾|王维|李白|李白|崔颢|杜甫|杜甫|杜甫|岑参|刘禹锡|白居易|白居易|李贺|杜牧|杜牧|李商隐|李商隐|李煜|范仲淹|晏殊|王安石|苏轼|苏轼|李清照|陆游|辛弃疾|辛弃疾|文天祥|马致远|张养浩|龚自珍|秋瑾|《论语》|《左传》|《孟子》|《庄子》|《礼记》|《吕氏春秋》|《战国策》|诸葛亮|陶潜|陶弘景|郦道元|韩愈|刘禹锡|柳宗元|范仲淹|欧阳修|周敦颐|苏轼|宋濂|张岱'.split('|')
add_sources={10:'https://www.gushiwen.cn/shiwenv_eae647c5c110.aspx',17:'https://www.gushiwen.cn/shiwenv_444df93c9bdf.aspx',43:'https://www.gushiwen.cn/shiwenv_294c939b3665.aspx',45:'https://m.gushiwen.cn/shiwenv_b85acee19435.aspx',46:'https://www.guwendao.net/shiwenv_a00028c4f0be.aspx',51:'https://www.gushiwen.cn/gushiwen_76c98b6c01.aspx'}
for i in range(1,len(c),3):
 n=int(c[i]);t=c[i+1];b=c[i+2].strip()
 if n<=40 or n in [42,47,48,49,50,51,52,53,54,55,56,57,58,59,60]: b=b.split('\n',1)[1]
 b=re.sub(r'\([^)]*一作[^)]*\)','',b)
 b=b.replace('将军角弓不得空','将军角弓不得控').replace('萧关逢侯骑','萧关逢候骑').replace('绝 多生怪柏','绝巘多生怪柏')
 # PDF行末换行只是排版，古诗保留完整句行，文言文合并为连续段落。
 b=b.replace('是（斯）人也','是人也')
 if n==43:
  old=re.search(r'（2）富贵不能淫\n(.*?)（3）',b,re.S).group(1)
  (p/'补充-富贵不能淫.md').write_text('# 富贵不能淫\n\n体裁：文言文；出处：《孟子》。这是教材补充，**不属于2022课标《孟子》三则的那三则**。\n\n教学依据：[人民教育出版社八年级上册2017年7月版目录](https://www.pep.com.cn/products/jc/czjks/201802/t20180209_1922717.shtml)。仅确认此旧版归属，现行修订版归属待核。\n\n原文来源：[湖南女子学院公开汇编]('+src+')，原汇编误列入课标三则，此处独立存放；采用前仍需校对。\n\n'+re.sub(r'\s+','',old)+'\n')
  new='（2）得道多助，失道寡助\n天时不如地利，地利不如人和。三里之城，七里之郭，环而攻之而不胜。夫环而攻之，必有得天时者矣，然而不胜者，是天时不如地利也。城非不高也，池非不深也，兵革非不坚利也，米粟非不多也，委而去之，是地利不如人和也。故曰：域民不以封疆之界，固国不以山溪之险，威天下不以兵革之利。得道者多助，失道者寡助。寡助之至，亲戚畔之；多助之至，天下顺之。以天下之所顺，攻亲戚之所畔，故君子有不战，战必胜矣。\n（3）'
  b=re.sub(r'（2）富贵不能淫\n.*?（3）',lambda _:new,b,flags=re.S)
 if n==45: b+='《兑命》曰“学学半”，其此之谓乎！'
 if n==46:
  t='《吕氏春秋》一则（伯牙鼓琴）'
  b='伯牙鼓琴，锺子期听之。方鼓琴而志在太山，锺子期曰：“善哉乎鼓琴，巍巍乎若太山。”少选之间而志在流水，锺子期又曰：“善哉乎鼓琴，汤汤乎若流水。”锺子期死，伯牙破琴绝弦，终身不复鼓琴，以为世无足复为鼓琴者。'
 if n==60:b+='”'
 names={5:'饮酒（结庐在人境）',12:'行路难（金樽清酒斗十千）',25:'无题（相见时难别亦难）',26:'相见欢（无言独上西楼）',27:'渔家傲（塞下秋来风景异）',28:'浣溪沙（一曲新词酒一杯）',30:'江城子（老夫聊发少年狂）',31:'水调歌头（明月几时有）',32:'渔家傲（天接云涛连晓雾）',34:'南乡子（何处望神州）',35:'破阵子（醉里挑灯看剑）',39:'己亥杂诗（浩荡离愁白日斜）',40:'满江红（小住京华）',41:'《论语》十二章',43:'《孟子》三则',44:'《庄子》一则（北冥有鱼）',45:'《礼记》一则（虽有嘉肴）',52:'杂说（四）（马说）',59:'送东阳马生序（节选）'}
 t=names.get(n,t); genre='文言文' if n>=41 else ('曲' if n in [37,38] else ('词' if n in [26,27,28,30,31,32,34,35,40] else '诗'))
 scope='课标2022：7—9年级推荐第'+str(n)+'条；非教材册次'
 extent='全文（该首或该词）' if n<=40 else ('选文全文（非所属典籍全书）')
 if n==41:extent='12章选段；逐章保留，课标计1条'
 if n==43:extent='3则选段：鱼我所欲也、得道多助失道寡助、生于忧患死于安乐；课标计1条'
 if n==44:extent='北冥有鱼至亦若是则已矣'
 if n==46:extent='伯牙鼓琴至世无足复为鼓琴者'
 if n==59:extent='余幼时即嗜学至况才之过于余者乎；不是文章全文'
 uid=f'CZ-{n:03d}'; sources=src+(' ; '+add_sources[n] if n in add_sources else '')
 rows.append(dict(id=uid,title=t,author=authors[n-1],genre=genre,scope=scope,source_url=standard,text_source_url=sources,text_status='已收录；已处理已发现错误；待指定教材版逐字复核',extent=extent))
 if n>=41: b=re.sub(r'\s+','',b);b=re.sub(r'([（(]\d+[）)])',r'\n\n\1',b)
 else:
  lines=b.splitlines();merged=[]
  for line in lines:
   if merged and not re.search(r'[。！？；”]$',merged[-1]): merged[-1]+=line.strip()
   else:merged.append(line.strip())
  b='\n\n'.join(merged)
 docs.append(f'## {uid} {t}\n\n作者／出处：{authors[n-1]}；体裁：{genre}。\n\n范围：{extent}。\n\n原文来源：[公开汇编]({src})'+(f'；[修订文本依据]({add_sources[n]})' if n in add_sources else '')+'。\n\n'+b+'\n')
assert len(rows)==60
with (p/'清单.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(p/'原文.md').write_text('\n'.join(docs))
print('rows',len(rows),'genres',{g:sum(r['genre']==g for r in rows) for g in ['诗','词','曲','文言文']})
