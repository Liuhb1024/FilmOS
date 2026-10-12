"""FilmOS single-user loopback dashboard. Run: python3 -m app.server"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import mimetypes
from pathlib import Path
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from typing import Any
from urllib.parse import urlparse, parse_qs
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'doc/项目/01-古诗词意境'
WEB = Path(__file__).parent / 'web'
MEDIA = {'.png', '.jpg', '.jpeg', '.webp', '.mp4', '.mov', '.webm'}
IMAGES = {'.png', '.jpg', '.jpeg', '.webp'}

class Invalid(ValueError):
    """User input cannot be saved; no mutation performed."""

class Conflict(Invalid):
    """Disk changed since the client read it."""


def load_core_library(root: Path = ROOT) -> list[dict[str, Any]]:
    base = root / 'doc/项目/01-古诗词意境/选题库'
    drafts = {}
    for line in (base / '创作分类草案-v0.1.md').read_text().splitlines():
        cells = [v.strip() for v in line.strip('|').split('|')]
        if len(cells) == 5 and re.match(r'^(P\d|PS\d|CZ-\d|GZ-\d)', cells[0]):
            drafts[cells[0].split()[0]] = dict(zip(['theme','scene','imagery','mood'],cells[1:]))
    result = []
    with (base / '篇目总索引.csv').open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            source = (base / row['原文文档']).read_text()
            match = re.search(r'^## ' + re.escape(row['编号']) + r'\b[^\n]*\n(.*?)(?=^## |\Z)', source, re.M | re.S)
            section = match.group(1).strip() if match else source.strip()
            # Preserve the complete source section separately; remove leading catalogue bullets for reading.
            lines = section.splitlines()
            while lines and (not lines[0].strip() or lines[0].startswith(('- ', '# ', '作者／出处：', '范围：', '原文来源：', '整理说明：', '收录编号：', '体裁：', '教学依据：', '[原文来源]'))):
                lines.pop(0)
            body = '\n'.join(lines).strip() or section
            result.append({'id':row['编号'], 'title':row['作品'], 'author':row['作者或出处'],
                           'stage':row['学段'], 'genre':row['体裁'], 'scope':row['归类'],
                           'status':row['状态'], 'text':body, 'sourceText':section,
                           'sourcePath':str((base / row['原文文档']).relative_to(root)),
                           'sourceUrl':row['文本来源'], 'draft':drafts.get(row['编号'],{})})
    return result


def load_library(root: Path = ROOT) -> list[dict[str, Any]]:
    from app.library import expand_library
    return expand_library(load_core_library(root), root)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Invalid(message)


def compact(text: str) -> str:
    return re.sub(r'\s+', '', text)


class Store:
    def __init__(self, project: Path = PROJECT):
        self.project = project.resolve()
        self.path = self.project / '分期/看板数据.json'
        self.lock = threading.RLock()
        self.poems = {p['id']:p for p in load_library()}

    def read(self) -> dict[str, Any]:
        with self.lock:
            if not self.path.exists():
                return {'version':'0', 'data':{'classifications':{}, 'episodes':[]}}
            stat = self.path.stat()
            return {'version':f'{stat.st_mtime_ns}-{stat.st_size}', 'data':json.loads(self.path.read_text())}

    def asset_path(self, relative: str) -> Path:
        require(isinstance(relative,str), '素材路径应为文本')
        path = (self.project / relative).resolve()
        require(path.is_relative_to((self.project / '资产库').resolve()) and path.suffix.lower() in MEDIA, '素材必须位于本项目资产库，且为支持的图片或视频')
        return path

    def import_asset(self, name: str, content: bytes) -> str:
        suffix = Path(name).suffix.lower()
        require(suffix in MEDIA and bool(content), '请选择PNG/JPG/WebP图片或MP4/MOV/WebM视频')
        relative = '资产库/看板导入/' + uuid.uuid4().hex[:16] + suffix
        path = self.asset_path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as f:
            f.write(content)
        return relative

    def ready_videos(self, episode: dict) -> list[tuple[dict, Path]]:
        require(any(s.get('included', True) for s in episode['shots']), '请先选入至少一条诗句')
        result = []
        for shot in episode['shots']:
            if not shot.get('included', True):
                continue
            version = next((v for v in shot['versions'] if v['id']==shot['videoId'] and v['kind']=='video'),None)
            require(bool(version and version.get('path')), '每条诗句都需要选择采用的视频，才能交付或归档')
            path = self.asset_path(version['path'])
            require(path.is_file(), '采用的视频不存在，请检查素材文件')
            result.append((shot,path))
        return result

    def validate(self, data: dict, previous: dict) -> None:
        require(isinstance(data,dict) and set(data)=={'classifications','episodes'}, '看板数据结构不正确')
        require(isinstance(data['classifications'],dict) and isinstance(data['episodes'],list), '分类和作品数据不正确')
        for pid, tags in data['classifications'].items():
            require(pid in self.poems and isinstance(tags,dict), '分类未对应已收录作品')
            require(set(tags)=={'theme','scene','imagery','mood','notes','review'}, '分类字段不完整')
            require(all(isinstance(v,str) and len(v)<10000 for v in tags.values()), '分类内容过长或格式错误')
            require(tags['review'] in ('draft','confirmed'), '分类状态错误')
        prior = {e['id']:e for e in previous['episodes']}
        ids = set()
        for episode in data['episodes']:
            require(isinstance(episode,dict) and set(episode)=={'id','title','mood','notes','status','shots'}, '作品字段不完整')
            require(all(isinstance(episode[k],str) for k in ['id','title','mood','notes','status']), '作品字段必须为文本')
            require(re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',episode['id']) is not None and episode['id'] not in ids, '作品编号重复或不正确')
            ids.add(episode['id'])
            require(bool(episode['title'].strip()) and episode['status'] in ('active','archived'), '填写作品名称并检查状态')
            require(isinstance(episode['shots'],list), '诗句列表格式错误')
            old = prior.get(episode['id'])
            if old and old['status']=='archived':
                require(old==episode, '已归档作品不可覆盖；请创建新的一期')
                continue
            oldshots = {s['id']:s for s in old['shots']} if old else {}
            shotids = set()
            for shot in episode['shots']:
                require(isinstance(shot,dict) and set(shot)-{'included'}=={'id','poemId','quote','idea','versions','imageId','videoId'}, '诗句字段不完整')
                require(all(isinstance(shot[k],str) for k in ['id','poemId','quote','idea','imageId','videoId']), '诗句字段必须为文本')
                require(shot['id'] not in shotids and bool(shot['id']), '诗句编号重复')
                shotids.add(shot['id'])
                require(isinstance(shot.get('included', True), bool), '候选状态错误')
                require(shot['poemId'] in self.poems and bool(compact(shot['quote'])), '请选择作品并摘录原句')
                require(compact(shot['quote']) in compact(self.poems[shot['poemId']]['text']), '摘句未在对应原文中找到，请保留原文文字和标点')
                require(isinstance(shot['versions'],list), '版本记录格式错误')
                oldshot = oldshots.get(shot['id'])
                if oldshot:
                    require(shot['poemId']==oldshot['poemId'] and shot['quote']==oldshot['quote'], '已保存的摘句不可替换，可另加一条')
                    require(shot['versions'][:len(oldshot['versions'])]==oldshot['versions'], '历史生成版本不可覆盖，请追加新版本')
                vids = set()
                for v in shot['versions']:
                    require(isinstance(v,dict) and set(v)=={'id','kind','prompt','model','params','reference','path','cost','reason'}, '生成版本字段不完整')
                    require(all(isinstance(x,str) for x in v.values()), '生成版本字段必须为文本')
                    require(v['id'] not in vids and bool(v['id']) and v['kind'] in ('image','video') and bool(v['prompt'].strip()), '版本编号、类型或提示词不正确')
                    vids.add(v['id'])
                    if v['path']:
                        path=self.asset_path(v['path'])
                        require((path.suffix.lower() in IMAGES)==(v['kind']=='image'), '素材类型与生成类型不一致')
                for field,kind in [('imageId','image'),('videoId','video')]:
                    if shot[field]:
                        chosen=next((v for v in shot['versions'] if v['id']==shot[field] and v['kind']==kind),None)
                        require(bool(chosen and chosen['path']), '采用版本必须具有对应素材')
                        require(self.asset_path(chosen['path']).is_file(), '采用素材文件不存在')
            require(set(oldshots).issubset(shotids), '已保存的诗句记录不可删除')
            if episode['status']=='archived':
                self.ready_videos(episode)
        require(set(prior).issubset(ids), '已保存的作品不可删除')

    def save(self, data: dict, expected: str) -> dict:
        with self.lock:
            old = self.read()
            if expected != old['version']:
                raise Conflict('本地资料已改变，请先复制未保存内容，再重新载入；没有覆盖磁盘资料。')
            self.validate(data,old['data'])
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix('.tmp')
            temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
            temporary.replace(self.path)
            return self.read()

    def export(self, episode_id: str) -> bytes:
        episode=next((e for e in self.read()['data']['episodes'] if e['id']==episode_id),None)
        require(episode is not None, '找不到这一期')
        videos=self.ready_videos(episode)
        output=io.BytesIO()
        notes=[f"# {episode['title']}",f"意境：{episode['mood']}",episode['notes'],'素材交付包；非最终剪辑成片。配音、BGM与剪辑由后续人员安排。']
        with zipfile.ZipFile(output,'w',zipfile.ZIP_STORED) as archive:
            for i,(shot,path) in enumerate(videos,1):
                filename=f"{i:02d}-{shot['poemId']}{path.suffix}"
                archive.write(path,filename)
                poem=self.poems[shot['poemId']]
                notes.extend([f'\n## {i:02d} {poem["title"]} · {poem["author"]}',shot['quote'],f'文件：{filename}',f'画面说明：{shot["idea"]}'])
            archive.writestr('交付说明.md','\n\n'.join(notes))
        return output.getvalue()


def make_handler(store: Store):
    excerpts = None
    def excerpt_index():
        nonlocal excerpts
        with store.lock:
            if excerpts is None:
                from app.excerpts import ExcerptIndex
                excerpts = ExcerptIndex(store.poems)
        return excerpts

    class Handler(BaseHTTPRequestHandler):
        def reply(self, code: int, content: bytes, mime: str) -> None:
            self.send_response(code)
            if len(content)>131072 and 'gzip' in self.headers.get('Accept-Encoding','') and mime.startswith('application/json'):
                content=gzip.compress(content,compresslevel=3)
                self.send_header('Content-Encoding','gzip')
            self.send_header('Content-Type',mime)
            self.send_header('Content-Length',str(len(content)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' blob:; media-src 'self' blob:; style-src 'self'; script-src 'self'; frame-ancestors 'self'")
            if mime=='application/zip': self.send_header('Content-Disposition','attachment; filename="FilmOS-delivery.zip"')
            self.end_headers()
            self.wfile.write(content)

        def send_json(self, code: int, data: Any) -> None:
            self.reply(code,json.dumps(data,ensure_ascii=False).encode(),'application/json; charset=utf-8')

        def boundary(self, mutate: bool=False) -> None:
            port=self.server.server_port
            allowed={f'127.0.0.1:{port}',f'localhost:{port}'}
            require(self.headers.get('Host') in allowed, '仅允许本机访问')
            origin=self.headers.get('Origin')
            require(not origin or origin in {f'http://{host}' for host in allowed}, '拒绝跨站请求')
            if mutate:
                require(self.headers.get('X-FilmOS')=='local', '请从本地看板保存')

        def do_GET(self):
            try:
                self.boundary()
                url=urlparse(self.path)
                if url.path=='/api/excerpts/meta':
                    return self.send_json(200,excerpt_index().meta)
                if url.path=='/api/excerpts':
                    params={k:v[0] for k,v in parse_qs(url.query).items()}
                    require(params.get('page','1').isdigit(), '页码必须为正整数')
                    return self.send_json(200,excerpt_index().query(params))
                if url.path=='/api/meta':
                    from app.library import library_stats
                    return self.send_json(200,library_stats(list(store.poems.values())))
                if url.path=='/api/library': return self.send_json(200,list(store.poems.values()))
                if url.path=='/api/state': return self.send_json(200,store.read())
                if url.path=='/api/export':
                    return self.reply(200,store.export(parse_qs(url.query).get('id',[''])[0]),'application/zip')
                if url.path=='/api/media':
                    path=store.asset_path(parse_qs(url.query).get('path',[''])[0])
                    require(path.is_file(),'素材不存在')
                else:
                    static={'/':'index.html','/app.js':'app.js','/excerpts.js':'excerpts.js','/style.css':'style.css'}
                    if url.path not in static: return self.send_json(404,{'error':'未找到'})
                    path=WEB/static[url.path]
                self.reply(200,path.read_bytes(),mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
            except Invalid as exc: self.send_json(400,{'error':str(exc)})
            except (OSError,ValueError): self.send_json(500,{'error':'文件读取失败，请检查本地资料，未自动重置'})

        def do_POST(self):
            try:
                self.boundary(True)
                url=urlparse(self.path)
                size=int(self.headers.get('Content-Length','0'))
                require(0<size<=200*1024*1024,'文件为空或超过200MB；大文件可手动放入资产库后填写路径')
                if url.path=='/api/state':
                    require(size<=5*1024*1024, '资料体积过大')
                    payload=json.loads(self.rfile.read(size))
                    require(isinstance(payload,dict) and 'data' in payload and 'version' in payload,'保存请求不完整')
                    self.send_json(200,store.save(payload['data'],payload['version']))
                elif url.path=='/api/assets':
                    name=parse_qs(url.query).get('name',[''])[0]
                    self.send_json(201,{'path':store.import_asset(name,self.rfile.read(size))})
                else: self.send_json(404,{'error':'未找到'})
            except Conflict as exc: self.send_json(409,{'error':str(exc)})
            except (Invalid,ValueError,TypeError) as exc: self.send_json(400,{'error':str(exc)})
            except OSError: self.send_json(500,{'error':'文件保存失败；请保留页面内容并检查磁盘'})

        def log_message(self, format, *args):
            pass
    return Handler


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--project',type=Path,default=PROJECT,help='测试时指定独立数据目录')
    args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(Store(args.project)))
    print(f'FilmOS: http://127.0.0.1:{args.port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
