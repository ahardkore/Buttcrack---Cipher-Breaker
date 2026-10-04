import tempfile, unittest
from buttcrack.results_db import ResultDB
class ResultsDBTests(unittest.TestCase):
 def test_insert_and_recent(self):
  with tempfile.NamedTemporaryFile(suffix='.db') as f:
   db=ResultDB(f.name); db.add(ciphertext_hash='abc',attack='caesar',parameters={'shift':3},score=-5.2,candidate='XYZ')
   self.assertEqual(db.recent(1)[0][0], 'caesar')
if __name__=='__main__': unittest.main()
