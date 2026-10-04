import unittest
from buttcrack.scoring import score_all
class ScoringTests(unittest.TestCase):
 def test_named_scores_are_separate(self):
  scores=score_all('THE QUICK BROWN FOX')
  self.assertEqual(len(scores),7); self.assertEqual({s.name for s in scores}, {'MonogramScore','BigramScore','TrigramScore','QuadgramScore','DictionaryCoverage','LanguageDetector','RandomControl'})
if __name__=='__main__': unittest.main()
