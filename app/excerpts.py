"""Local, traceable excerpt proposals. Labels are proposals, never audience analytics."""
from collections import Counter
import json
from pathlib import Path
import re
from app.library import text_clues

BASE=Path(__file__).resolve().parents[1]/'doc/项目/01-古诗词意境/选题库/摘句分类/v1'
VERSION='excerpt-v1'
# label, textual evidence alternatives, suggested creative angle
TOPICS=[
 ('思乡怀人','故乡|思乡|乡关|乡愁|乡书|家书|归乡|还乡|故园|乡心|客中|客愁','离家与归属'),
 ('爱情相思','相思|思君|相忆|情人|情郎|相见|相逢|相知|鸳鸯|红豆|相思树|心上人|合欢','爱与想念'),
 ('送别重逢','离别|送别|别离|送君|别君|惜别|离人|离愁|征帆|分手|重逢|后会|饯别','告别与重逢'),
 ('山水行旅','山|峰|岭|江|河|溪|湖|泉|海|瀑|远游|行舟|扁舟','山河向往'),
 ('田园生活','桑麻|田|稻|耕|农|村|柴门|柴扉|鸡犬|锄|牧童|麦|蚕','日常小美好'),
 ('隐逸闲居','悠然|归隐|隐居|采菊|松间|幽篁|空山|南山|闲居|闲云|竹里|坐忘','安静与休息'),
 ('节令风物','清明|重阳|端午|七夕|中秋|元夕|元宵|除夕|屠苏|爆竹|上元|九月九','节日与仪式'),
 ('春日花事','春|桃花|杏花|海棠|牡丹|柳絮|莺啼','日常小美好'),
 ('夏日清凉','夏|暑|荷花|芙蕖|莲叶|蝉|纳凉','安静与休息'),
 ('秋色秋思','秋|枫|霜叶|菊花|梧桐|黄叶','时间与遗憾'),
 ('冬雪寒梅','雪|冰|寒梅|腊|冬|梅花','清冷审美'),
 ('月夜星河','明月|月光|月色|月明|月下|月夜|月落|月出|新月|残月|满月|斜月|皓月|星|银河|银汉','夜晚独处'),
 ('风雨烟云','雨|烟|雾|云|风','氛围沉浸'),
 ('咏物寄志','松柏|青松|翠竹|孤松|竹石|咏|梅|莲|蝉|石灰|托物','自我与成长'),
 ('人生哲思','人生|人间|世事|何必|何须|须知|不识|真面目|得失|浮生|天地|万物|祸福|道理|不以物喜','自我与成长'),
 ('惜时怀旧','光阴|流年|年华|往事|当年|旧时|白发|少年|青春|岁月|逝者|今昔','时间与遗憾'),
 ('励志求索','壮志|凌云|凌绝顶|长风破浪|济沧海|求索|自强|志士|报国|立志|千磨|不怕|坚持','自我与成长'),
 ('边塞征战','边塞|关塞|玉门|胡马|烽火|楼兰|戍|征战|将军|军|战|铁骑|金戈|沙场|弓|剑','家国与担当'),
 ('家国忧思','国破|故国|山河破碎|中原|社稷|苍生|国事|忧民|忧国|黎民|百姓','家国与担当'),
 ('怀古兴亡','故垒|遗迹|六朝|千古|兴亡|怀古|旧国|古今|王侯|宫阙|秦|汉|吴宫|陈迹','历史回望'),
 ('朋友知己','知己|知音|故人|朋友|友人|同心|兄弟|同窗','陪伴与知己'),
 ('亲情家庭','父|母|儿|女|家人|慈亲|双亲|亲恩|游子|孝','亲情与牵挂'),
 ('学习修养','学|读书|书卷|君子|仁义|修身|礼义|德|劝学|师者','自我与成长'),
 ('困顿不平','穷|贫|饥|病|坎坷|不平|谗|流落|流离|萧条|贬|失意','低谷与自处'),
 ('宴饮歌舞','酒|醉|樽|觞|宴|歌|舞|笛|琴|箫|琵琶','人间烟火'),
 ('闺情幽怨','闺|罗帏|罗帷|红妆|蛾眉|绣户|妆台|深宫|宫怨','爱与想念'),
 ('神话仙境','仙|蓬莱|瑶台|阆苑|玉京|嫦娥|鲲|鹏|天宫|龙宫','奇幻想象'),
 ('禅意观照','禅|佛|菩提|空门|寺|僧|钟声|无心','安静与休息'),
 ('典礼颂祝','皇|帝|天子|朝元|郊祀|禋|祭|銮|法驾|玉烛|圣|睿|万寿|寿|福|祥|升平|太平|尧舜','文化理解'),
 ('繁华游赏','寻芳|拾翠|绮陌|画楼|雕栏|歌楼|灯市|游赏|芳菲|群芳|锦绣|繁华|红紫','日常小美好'),
 ('容颜妆饰','妆|胭脂|蛾眉|美人|佳人|粉黛|罗袖|罗裙|鬓|翠钿|玉钗','东方人物美学'),
 ('书画雅事','翰墨|书画|文章|诗篇|笔|墨|砚|丹青|棋|诗书|经卷','文化理解'),
 ('身世仕途','朝天|仕|宦|郎署|功名|仕途|臣|官|朝廷|辞官|登科|及第','自我与成长'),
 ('归去留恋','归去|归来|留恋|恋|难舍|归期|何日|留伴|不归|归心','告别与重逢'),
 ('花木园林','花|叶|枝|蕊|芳|苔|庭|园|槛|栏|帘|红飞','日常小美好'),
]
MOODS=[
 ('空灵宁静','空山|松间|清泉|幽篁|人闲|夜静|月明|明月|清溪|水清|静|幽'),
 ('清冷孤寂','寒江|孤舟|独钓|寒山|残月|冷|霜|雪|寂寞'),
 ('孤寂怅惘','独|孤|寂|惆怅|怅|愁|悲|泪|断肠|凄|伤心'),
 ('温柔缱绻','相思|相忆|柔|温|深情|依依|相悦|情意|鸳鸯|红豆'),
 ('离愁不舍','离愁|离别|送君|惜别|别离|别恨|不忍|离人'),
 ('旷达释然','何妨|何须|何必|一蓑烟雨|也无风雨|不以物喜|莫听穿林|且放|任平生|无妨'),
 ('昂扬豪迈','壮志|凌云|凌绝顶|长风破浪|济沧海|长啸|豪|会当|天生我材|不肯低头'),
 ('苍凉悲壮','国破|烽火|沙场|战死|白骨|铁马|金戈|风萧萧|孤城|黄沙|大漠'),
 ('明丽欣悦','喜|欢|欣|笑|晴|春光|春色|花明|晴空|灿|烂漫'),
 ('闲适自在','悠然|闲|自适|逍遥|归隐|采菊|自在|卧|垂钓'),
 ('怀旧感伤','往事|当年|旧时|忆昔|白发|物是人非|人面不知|夕阳|流年|不复'),
 ('幽玄奇幻','仙|蓬莱|瑶台|阆苑|鲲|鹏|嫦娥|梦入|天姥'),
 ('庄严颂祝','圣|睿|皇|帝|郊祀|祭|禋|法驾|玉烛|万寿|福寿|祥|升平|太平'),
 ('繁华绮丽','绮|锦|华彩|繁华|群芳|红紫|金碧|琳琅|盛宴'),
 ('沉思自问','人生|世事|何日|何处|何事|几时|可乎|须知|浮生|古今|谁知|怎|何以'),
 ('眷恋期待','恋|情满|多情|留伴|盼|待归|期|相约|不改|眷'),
 ('沉郁苦闷','厄|困|艰|苦|难|无奈|憔悴|惆怅|烦|恼|悔'),
]


def hanzi(text: str) -> str:
    return ''.join(re.findall(r'[\u3400-\u9fff]',text))


def split_passages(text: str) -> list[dict]:
    """Partition content at punctuation into <=2 clauses; never synthesize source text."""
    output=[]
    for line in re.finditer(r'[^\n]+',text):
        if line.group().lstrip().startswith(('#','- ','作者：','来源：')):continue
        # Closing quotes stay with their sentence. Newlines and headings are hard boundaries.
        for sentence in re.finditer(r'[^。！？!?；;]+[。！？!?；;]*[”’」』]*',line.group()):
            value=sentence.group();base=line.start()+sentence.start()
            clauses=list(re.finditer(r'[^，,]+[，,]*',value))
            for i in range(0,len(clauses),2):
                group=clauses[i:i+2];start=base+group[0].start();end=base+group[-1].end()
                while start<end and text[start].isspace():start+=1
                while end>start and text[end-1].isspace():end-=1
                quote=text[start:end]
                if not hanzi(quote):continue
                output.append({'start':start,'end':end,'quote':quote})
    merged=[]
    for chunk in output:
        if (merged and len(hanzi(merged[-1]['quote']))<8
                and not text[merged[-1]['end']:chunk['start']].strip()
                and len(hanzi(merged[-1]['quote']+chunk['quote']))<=45):
            previous=merged[-1];previous['end']=chunk['end']
            previous['quote']=text[previous['start']:previous['end']]
        else:merged.append(chunk)
    return merged


def proposals() -> list[dict]:
    path=BASE/'助手精读提案.json'
    return json.loads(path.read_text()) if path.exists() else []


CURATED=proposals()
CURATED_BY_QUOTE={hanzi(item['quote']):item for item in CURATED}


def extract_poem(poem: dict) -> list[dict]:
    text=poem['text'];chunks=split_passages(text)
    positions=[m.start() for m in re.finditer(r'[\u3400-\u9fff]',text)]
    normalized=''.join(text[i] for i in positions)
    existing={(x['start'],x['end']) for x in chunks}
    for key in CURATED_BY_QUOTE:
        index=normalized.find(key)
        if index<0:continue
        start=positions[index];end=positions[index+len(key)-1]+1
        while end<len(text) and text[end] in '，。！？?!；;”’」』':end+=1
        if '#' in text[start:end] or (start,end) in existing:continue
        chunks.append({'start':start,'end':end,'quote':text[start:end]})
        existing.add((start,end))
    return sorted(chunks,key=lambda x:(x['start'],x['end']))


def classify(quote: str, poem: dict) -> dict:
    clues=text_clues(quote)
    cautions=[]
    if re.search(r'不见|无人|人踪灭|鸟飞绝|无鸟|无花|不闻|未见|无风|无雨',quote):
        cautions.append('有否定或空景表达，命中的景物不一定应出现在画面中')
    if re.search(r'梦|疑是|犹如|恰似|仿佛|若为|忆|当年|旧时',quote):
        cautions.append('含想象、比喻或追忆线索，先区分眼前景与心中景')
    if len(hanzi(quote))<8:cautions.append('短片段，建议连读前后文后决定是否扩句')
    if len(hanzi(quote))>45:cautions.append('长片段，制作前再精摘或拆成多个镜头')
    if quote.rstrip().endswith(('，',',','：',':')):cautions.append('句意可能未完，请检查下文')
    evidence=[];themes=[];appeals=[];moods=[]
    for label,pattern,angle in TOPICS:
        hit=re.search(pattern,quote)
        if hit:
            themes.append(label);appeals.append(angle)
            evidence.append({'dimension':'主题','label':label,'match':hit.group()})
    for label,pattern in MOODS:
        hit=re.search(pattern,quote)
        if hit:
            moods.append(label);evidence.append({'dimension':'意境','label':label,'match':hit.group()})
    visuals=[c['label'] for c in clues if c['category'] in ('场景','意象')]
    if re.search(r'鸟飞绝|无鸟|不闻鸟',quote):visuals=[x for x in visuals if x!='鸟']
    if re.search(r'无人|人踪灭',quote):cautions.append('空景不默认增加行人')
    result={'themes':themes or ['文史议论·待细分' if poem['genre']=='文言文' else '抒情咏物·待细分'],
            'moods':moods or ['意境待细分'],'appeals':list(dict.fromkeys(appeals)) or ['文化理解' if poem['genre']=='文言文' else '诗意品读'],
            'visuals':list(dict.fromkeys(visuals)),'method':'规则初分','evidence':evidence,'cautions':cautions,
            'note':'依据本片段字词提出多标签候选；共鸣切入点是创作提案，未经观众数据验证。','review':'draft'}
    normalized=hanzi(quote)
    item=CURATED_BY_QUOTE.get(normalized)
    if item:
        result.update({k:item[k] for k in ('themes','moods','appeals','note')})
        result['method']='助手精读提案'
        result['evidence']=[{'dimension':'语境解读','label':'助手提案','match':quote}]
        if 'visuals' in item:result['visuals']=item['visuals']
        result['cautions']+=item.get('cautions',[])
    if len(hanzi(quote))<8 or len(hanzi(quote))>45 or quote.rstrip().endswith(('，',',','：',':')):
        result['uses']=['需调整摘句范围']
    elif result['visuals']:
        result['uses']=['意境画面候选']
    elif any(t in result['themes'] for t in ('人生哲思','学习修养','励志求索')):
        result['uses']=['哲理旁白候选']
    else:result['uses']=['叙事抒情候选']
    return result


class ExcerptIndex:
    """Read one explicit local edition; no writes, external calls or model invocation."""
    def __init__(self, poems: dict, base: Path = BASE):
        self.poems=poems
        self.rows=[]
        with (base/'片段.jsonl').open() as f:
            for line in f:
                row=json.loads(line)
                p=poems[row['poemId']]
                if p['text'][row['start']:row['end']]!=row['quote']:
                    raise ValueError('摘句与原文不一致，需要重建新版本')
                self.rows.append(row)
        self.meta=json.loads((base/'分类覆盖.json').read_text())
        self.by_id={r['id']:r for r in self.rows}

    def query(self, params: dict[str,str]) -> dict:
        page=max(1,int(params.get('page','1')))
        selected=[];q=params.get('q','').strip().lower()
        for row in self.rows:
            p=self.poems[row['poemId']]
            if params.get('stage') and p['stage']!=params['stage']:continue
            if params.get('method') and row['method']!=params['method']:continue
            if any(params.get(k) and params[k] not in row[k] for k in ('themes','moods','appeals','visuals','uses')):continue
            if q and q not in (row['quote']+' '+p['title']+' '+p['author']).lower():continue
            selected.append(row)
        pages=max(1,(len(selected)+39)//40);page=min(page,pages)
        # Curated reading proposals appear first; rule-based matches follow in corpus order.
        selected.sort(key=lambda x:x['method']!='助手精读提案')
        rows=[]
        for row in selected[(page-1)*40:page*40]:
            p=self.poems[row['poemId']]
            rows.append({**row,'title':p['title'],'author':p['author'],'stage':p['stage']})
        return {'rows':rows,'total':len(selected),'page':page,'pages':pages}
