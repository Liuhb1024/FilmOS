"""Classical corpus loading and transparent text-based discovery clues.

Clues are literal word matches, never an assertion of scene, emotion or cinematic style.
"""
from collections import Counter
import json
from pathlib import Path
import re

# Category, visible label, literal alternatives. Keep meaning inspectable; no model calls.
RULES = {
    '场景': {
        '山野': '山|峰|岭|崖|嶂', '江河': '江|河|川', '湖泊': '湖|洞庭',
        '海岸': '海|沧溟', '溪泉': '溪|泉|涧', '池塘': '池|塘', '田园': '田|稻|麦|桑麻',
        '林间': '林|森林|松间|竹里|幽篁', '庭院': '庭|院|阶|柴扉', '楼台': '楼|台|阁|阙',
        '古城': '城|故都|长安|洛阳|金陵', '边塞': '关塞|边塞|玉门|阴山|胡马|烽火|楼兰',
        '寺观': '寺|禅|僧|钟声', '舟渡': '舟|船|帆|渡|橹', '道路': '路|古道|官道|山道|驿|长亭',
        '桥畔': '桥', '宫阙': '宫|阙|禁苑', '沙漠': '沙漠|大漠|瀚海',
    },
    '意象': {
        '月': '月', '日光': '日照|斜阳|夕阳|朝阳|落日|日出', '星河': '星|银河|银汉',
        '云': '云', '烟雾': '烟|雾|霭', '雨': '雨', '雪': '雪', '霜露': '霜|露',
        '风': '风', '松柏': '松|柏', '竹': '竹|篁', '梅': '梅', '荷莲': '荷|莲|芙蕖|芙蓉',
        '柳': '柳', '桃杏': '桃|杏', '菊': '菊', '落花': '落花|花落|残红|落红',
        '鸟': '鸟|莺|燕|鹤|鸦|鹊|鸥', '雁': '雁|鸿', '鱼': '鱼', '马': '马',
        '灯火': '灯|烛|火', '琴笛': '琴|笛|箫|琵琶|筝', '酒': '酒|樽|觞|醉',
    },
    '时令': {
        '春': '春', '夏': '夏|暑', '秋': '秋', '冬': '冬|腊',
        '清晨': '晓|晨|朝阳|日出', '黄昏': '暮|黄昏|夕阳|落日|晚照',
        '夜': '夜|宵|更漏', '清明': '清明', '七夕': '七夕|鹊桥',
        '中秋': '中秋|八月十五', '重阳': '重阳|九月九', '元夕': '元夕|上元|元宵',
    },
    '情绪字词': {
        '思念': '思乡|相思|思君|忆|故乡|怀人', '离别': '离别|别离|送别|别君|别恨|离人|离愁|送君|惜别|话别',
        '孤独': '孤|独|寂寞', '愁绪': '愁|忧|断肠', '悲伤': '悲|泪|伤心|哀',
        '闲适': '闲|悠然|逍遥', '喜悦': '喜|欢|欣', '怨恨': '怨|恨',
        '豪情': '壮志|豪|长啸', '追怀': '当年|往事|旧时|忆昔',
        '归意': '归|还乡', '惜时': '流年|年华|白发|光阴',
    },
}

def text_clues(text: str) -> list[dict]:
    result=[]
    for category,rules in RULES.items():
        for label,terms in rules.items():
            matches=[(text.find(t),t) for t in terms.split('|') if t in text]
            if not matches:continue
            index,word=min(matches)
            start=max(text.rfind('\n',0,index)+1,index-35)
            end=text.find('\n',index)
            end=min(len(text) if end<0 else end,index+len(word)+55)
            result.append({'category':category,'label':label,'kind':'字词线索','match':word,'evidence':text[start:end]})
    return result


def expand_library(core: list[dict], root: Path) -> list[dict]:
    base=root/'doc/项目/01-古诗词意境/选题库'
    extension=base/'扩展典籍/扩展篇目.json'
    links_path=base/'扩展典籍/典籍关联.json'
    links=json.loads(links_path.read_text()) if links_path.exists() else {}
    records=core + (json.loads(extension.read_text()) if extension.exists() else [])
    # Research files are only integrated after review into a single explicit catalogue.
    additions=base/'教材新增篇目.json'
    if additions.exists(): records += json.loads(additions.read_text())
    for p in records:
        p.setdefault('draft',{})
        p.setdefault('sourceText',p['text'])
        p.setdefault('status','原文已采集·教材版次与用字待核')
        p.setdefault('collections',links.get(p['id'],[]))
        p.setdefault('notes','')
        p.setdefault('sourcePath','')
        p['clues']=text_clues(p['text'])
        p['tier']='扩展典籍' if p['stage']=='课外' else '课标与教材'
        p['schoolCore']=p['scope']=='课标推荐'
    return records


def library_stats(poems: list[dict]) -> dict:
    counts=Counter();facets=Counter()
    for p in poems:
        counts.update(p['collections'])
        facets.update((c['category'],c['label']) for c in p['clues'])
    return {'total':len(poems),'schoolCore':sum(p['schoolCore'] for p in poems),
            'stages':dict(Counter(p['stage'] for p in poems)),
            'collections':dict(counts),
            'facets':[{'category':cat,'label':label,'count':facets[(cat,label)]} for cat,rules in RULES.items() for label in rules]}
