import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from app.server import Store, load_library, load_core_library, Conflict, Invalid

ROOT = Path(__file__).resolve().parents[1]

class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name))
    def tearDown(self):
        self.temp.cleanup()
    def episode(self):
        return {'id':'e1','title':'清冷','mood':'清冷','notes':'','status':'active','shots':[{'id':'s1','poemId':'P043','quote':'孤舟蓑笠翁，独钓寒江雪。','idea':'','included':True,'versions':[],'imageId':'','videoId':''}]}
    def save_episode(self):
        snap=self.store.read(); state=snap['data']; state['episodes'].append(self.episode())
        return self.store.save(state,snap['version'])
    def test_real_corpus_and_drafts(self):
        poems=load_core_library(ROOT)
        self.assertEqual(len(poems),264)
        self.assertEqual(len({p['id'] for p in poems}),264)
        self.assertTrue(all(p['text'].strip() for p in poems))
        self.assertIn('独钓寒江雪',next(p for p in poems if p['id']=='P043')['text'])
        self.assertIn('富贵不能淫',next(p for p in poems if p['id']=='CZ-S005')['text'])
        self.assertEqual(sum(bool(p['draft']) for p in poems),14)
    def test_reader_excludes_catalogue_metadata(self):
        poems={p['id']:p for p in load_library(ROOT)}
        self.assertTrue(poems['CZ-004']['text'].startswith('东临碣石'))
        self.assertTrue(poems['GZ-048']['text'].startswith('风急天高'))
        self.assertTrue(poems['CZ-S005']['text'].startswith('景春曰'))
    def test_save_reload_and_stale_conflict(self):
        original=self.store.read(); current=self.save_episode()
        self.assertEqual(Store(Path(self.temp.name)).read()['data'],current['data'])
        with self.assertRaises(Conflict): self.store.save(original['data'],original['version'])
    def test_external_edit_detected(self):
        saved=self.save_episode()
        data=copy.deepcopy(saved['data']); data['episodes'][0]['title']='Codex修改'
        self.store.path.write_text(json.dumps(data))
        with self.assertRaises(Conflict): self.store.save(saved['data'],saved['version'])
    def test_quote_requires_source(self):
        snap=self.store.read(); bad=self.episode(); bad['shots'][0]['quote']='随便编的诗句'
        snap['data']['episodes']=[bad]
        with self.assertRaises(Invalid): self.store.save(snap['data'],snap['version'])
    def test_versions_append_only(self):
        snap=self.save_episode(); shot=snap['data']['episodes'][0]['shots'][0]
        shot['versions'].append({'id':'v1','kind':'image','prompt':'寒江孤舟','model':'待定','params':'未知','reference':'无','path':'','cost':'未知','reason':'待试'})
        snap=self.store.save(snap['data'],snap['version'])
        snap['data']['episodes'][0]['shots'][0]['versions'][0]['prompt']='覆盖旧提示词'
        with self.assertRaises(Invalid): self.store.save(snap['data'],snap['version'])
    def test_asset_boundary(self):
        with self.assertRaises(Invalid): self.store.asset_path('../outside.mp4')
        with self.assertRaises(Invalid): self.store.import_asset('bad.html',b'<script>')
        path=self.store.import_asset('镜头.mp4',b'test-video')
        self.assertEqual(self.store.asset_path(path).read_bytes(),b'test-video')
    def ready(self):
        snap=self.save_episode(); shot=snap['data']['episodes'][0]['shots'][0]
        path=self.store.import_asset('test.mp4',b'test-video')
        shot['versions']=[{'id':'v1','kind':'video','prompt':'缓慢推进','model':'测试','params':'未知','reference':'测试图片','path':path,'cost':'未知','reason':'测试'}]
        shot['videoId']='v1'
        return self.store.save(snap['data'],snap['version'])
    def test_archive_requires_videos(self):
        snap=self.save_episode(); snap['data']['episodes'][0]['status']='archived'
        with self.assertRaises(Invalid): self.store.save(snap['data'],snap['version'])
    def test_archived_episode_immutable_and_quote_reusable(self):
        snap=self.ready(); snap['data']['episodes'][0]['status']='archived'; snap=self.store.save(snap['data'],snap['version'])
        changed=copy.deepcopy(snap['data']); changed['episodes'][0]['title']='覆盖存档'
        with self.assertRaises(Invalid): self.store.save(changed,snap['version'])
        new=self.episode(); new['id']='e2'; new['shots'][0]['id']='s2'; snap['data']['episodes'].append(new)
        self.assertEqual(len(self.store.save(snap['data'],snap['version'])['data']['episodes']),2)
    def test_export_actual_video_and_order(self):
        self.ready()
        with zipfile.ZipFile(io.BytesIO(self.store.export('e1'))) as z:
            self.assertIn('01-P043.mp4',z.namelist())
            self.assertEqual(z.read('01-P043.mp4'),b'test-video')
            self.assertIn('孤舟',z.read('交付说明.md').decode())
    def test_excluded_candidate_is_retained_but_not_required_for_delivery(self):
        snap=self.ready(); candidate=self.episode()['shots'][0];candidate['id']='s2';candidate['included']=False
        snap['data']['episodes'][0]['shots'].append(candidate)
        snap['data']['episodes'][0]['status']='archived'
        result=self.store.save(snap['data'],snap['version'])
        self.assertEqual(len(result['data']['episodes'][0]['shots']),2)
        with zipfile.ZipFile(io.BytesIO(self.store.export('e1'))) as z:
            self.assertEqual(len(z.namelist()),2)
    def test_missing_media_cannot_export(self):
        snap=self.ready(); path=snap['data']['episodes'][0]['shots'][0]['versions'][0]['path']; self.store.asset_path(path).unlink()
        with self.assertRaises(Invalid): self.store.export('e1')


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from http.server import ThreadingHTTPServer
        import threading
        from app.server import make_handler
        cls.temp=tempfile.TemporaryDirectory()
        cls.store=Store(Path(cls.temp.name))
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.store))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.temp.cleanup()
    def request(self,path='/',body=None,headers=None):
        import http.client
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port)
        conn.request('POST' if body is not None else 'GET',path,body,headers or {})
        response=conn.getresponse();result=(response.status,response.read());conn.close();return result
    def test_static_and_catalogue(self):
        code,body=self.request();self.assertEqual(code,200);self.assertIn('<title>FilmOS · 古诗文资料库</title>',body.decode())
        code,body=self.request('/api/library');self.assertEqual(len(json.loads(body)),len(self.store.poems));self.assertTrue(set(p['id'] for p in load_core_library()).issubset({p['id'] for p in json.loads(body)}))
    def test_excerpt_filter_and_provenance(self):
        from urllib.parse import urlencode
        code,body=self.request('/api/excerpts/meta');self.assertEqual(code,200)
        self.assertEqual(json.loads(body)['poems'],len(self.store.poems))
        code,body=self.request('/api/excerpts?'+urlencode({'moods':'空灵宁静','q':'明月松间照'}))
        self.assertEqual(code,200);data=json.loads(body);self.assertGreater(data['total'],0)
        self.assertLessEqual(len(data['rows']),40)
        for row in data['rows']:
            self.assertIn('空灵宁静',row['moods'])
            self.assertEqual(self.store.poems[row['poemId']]['text'][row['start']:row['end']],row['quote'])
        code,_=self.request('/api/excerpts?page=invalid');self.assertEqual(code,400)
    def test_cross_origin_mutation_rejected(self):
        code,_=self.request('/api/state',b'{}',{'Origin':'https://example.com','X-FilmOS':'local'})
        self.assertEqual(code,400)
    def test_unknown_host_rejected(self):
        code,_=self.request(headers={'Host':'example.com'});self.assertEqual(code,400)
    def test_files_outside_allowlist_not_served(self):
        code,_=self.request('/AGENTS.md');self.assertEqual(code,404)
        code,_=self.request('/api/media?path=../../AGENTS.md');self.assertEqual(code,400)
    def test_save_conflict_and_asset_import(self):
        code,body=self.request('/api/state');snap=json.loads(body)
        snap['data']['classifications']['P043']={'theme':'测试','scene':'江面','imagery':'舟','mood':'清冷','notes':'仅测试','review':'draft'}
        payload=json.dumps(snap).encode()
        code,_=self.request('/api/state',payload,{'X-FilmOS':'local'});self.assertEqual(code,200)
        code,_=self.request('/api/state',payload,{'X-FilmOS':'local'});self.assertEqual(code,409)
        code,body=self.request('/api/assets?name=test.mp4',b'fixture',{'X-FilmOS':'local'});self.assertEqual(code,201)
        self.assertTrue(self.store.asset_path(json.loads(body)['path']).exists())

if __name__=='__main__': unittest.main()
