import unittest
from pathlib import Path
from app.server import load_library, load_core_library
from app.library import text_clues, library_stats

class ExpansionTests(unittest.TestCase):
    def test_core_unchanged_and_high_school_visible(self):
        core=load_core_library()
        self.assertEqual(len(core),264)
        high=[p for p in core if p['stage']=='高中']
        self.assertEqual(len(high),74)
        self.assertEqual(sum(p['scope']=='课标推荐' for p in high),72)
        self.assertTrue({'蜀道难','师说','赤壁赋','春江花月夜'}.issubset({p['title'] for p in high}))
    def test_expansion_contains_large_traceable_classical_collection(self):
        poems=load_library()
        expanded=[p for p in poems if p['id'].startswith('EXT-')]
        self.assertGreater(len(expanded),20000)
        self.assertEqual(len({p['id'] for p in poems}),len(poems))
        self.assertTrue(all(p['text'] and p['sourceUrl'].startswith('https://') for p in expanded))
        self.assertTrue(all(p['stage']=='课外' and p['scope']=='典籍扩展' for p in expanded))
        self.assertTrue(all(p['status']!='已校定' for p in expanded))
        self.assertTrue(any('唐诗三百首' in p['collections'] for p in poems))
        self.assertTrue(any('古文观止' in p['collections'] for p in poems))
    def test_clues_are_evidence_not_mood_assertions(self):
        clues=text_clues('千山鸟飞绝，万径人踪灭。\n孤舟蓑笠翁，独钓寒江雪。')
        self.assertTrue(any(c['label']=='雪' for c in clues))
        self.assertTrue(all(c['evidence'] and c['kind']=='字词线索' for c in clues))
        self.assertTrue(any(c['label']=='鸟' and '鸟飞绝' in c['evidence'] for c in clues))
    def test_meta_counts_match_data_and_keep_school_separate(self):
        poems=load_library();meta=library_stats(poems)
        self.assertEqual(meta['total'],len(poems))
        self.assertEqual(meta['schoolCore'],207)
        self.assertGreaterEqual(meta['stages']['高中'],74)
        self.assertGreaterEqual(len(meta['facets']),40)
    def test_clues_avoid_obvious_ambiguous_single_words(self):
        self.assertFalse(any(c['label']=='豪情' for c in text_clues('万里悲秋常作客')))
        self.assertFalse(any(c['label']=='道路' for c in text_clues('道可道，非常道')))
        self.assertFalse(any(c['label']=='离别' for c in text_clues('别有洞天')))
