import unittest
from app.excerpts import split_passages, classify, extract_poem


class ExcerptTests(unittest.TestCase):
    def test_exact_couplets_and_offsets(self):
        text='千山鸟飞绝，万径人踪灭。\n孤舟蓑笠翁，独钓寒江雪。'
        chunks=split_passages(text)
        self.assertEqual([c['quote'] for c in chunks],['千山鸟飞绝，万径人踪灭。','孤舟蓑笠翁，独钓寒江雪。'])
        self.assertTrue(all(text[c['start']:c['end']]==c['quote'] for c in chunks))

    def test_no_title_leak_or_truncation(self):
        text='## 第一章\n明月松间照，清泉石上流。\n## 第二章\n竹喧归浣女，莲动下渔舟。'
        chunks=split_passages(text)
        self.assertEqual(len(chunks),2)
        self.assertTrue(all('##' not in c['quote'] for c in chunks))

    def test_local_emotion_does_not_inherit_whole_poem(self):
        p={'title':'登高','genre':'诗'}
        sad=classify('万里悲秋常作客，百年多病独登台。',p)
        self.assertIn('孤寂怅惘',sad['moods'])
        self.assertNotIn('昂扬豪迈',sad['moods'])
        calm=classify('明月松间照，清泉石上流。',{'title':'山居秋暝','genre':'诗'})
        self.assertIn('空灵宁静',calm['moods'])

    def test_negation_not_rendered_as_birds(self):
        result=classify('千山鸟飞绝，万径人踪灭。',{'title':'江雪','genre':'诗'})
        self.assertTrue(result['cautions'])
        self.assertNotIn('鸟',result['visuals'])

    def test_unknown_is_not_fabricated_or_popularity_score(self):
        result=classify('甲乙丙丁，戊己庚辛。',{'title':'未详','genre':'诗'})
        self.assertEqual(result['method'],'规则初分')
        self.assertEqual(result['moods'],['意境待细分'])
        self.assertNotIn('popularity',result)

    def test_prose_preserves_sentence_and_quote_context(self):
        text='子曰：“学而时习之，不亦说乎？”有朋自远方来，不亦乐乎？'
        self.assertTrue(all(text[x['start']:x['end']]==x['quote'] for x in split_passages(text)))
    def test_short_dependent_units_stay_with_adjacent_sentence(self):
        text='何日下青旻。且看青山远，白云自往来。'
        chunks=split_passages(text)
        self.assertGreater(len(chunks[0]['quote']),6)
        self.assertEqual(''.join(x['quote'] for x in chunks),text)
    def test_known_couplet_available_even_after_short_sentence(self):
        text='此事古难全。但愿人长久，千里共婵娟。'
        chunks=extract_poem({'text':text})
        self.assertTrue(any(x['quote']=='但愿人长久，千里共婵娟。' for x in chunks))
        self.assertTrue(all(text[x['start']:x['end']]==x['quote'] for x in chunks))
