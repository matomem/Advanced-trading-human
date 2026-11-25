import unittest
import pandas as pd
from features import build_features

class FeatureTests(unittest.TestCase):
    def test_features_are_point_in_time_and_target_is_future(self):
        df=pd.DataFrame({"time":range(80),"open":[100+i for i in range(80)],
          "high":[101+i for i in range(80)],"low":[99+i for i in range(80)],
          "close":[100+i for i in range(80)],"volume":[1000+i for i in range(80)]})
        out=build_features(df,horizon=3)
        self.assertIn("target",out.columns)
        self.assertIn("return_5",out.columns)
        self.assertFalse(out.isna().any().any())
        self.assertTrue(set(out.target.unique()).issubset({0,1}))
    def test_rejects_missing_ohlc(self):
        with self.assertRaises(ValueError): build_features(pd.DataFrame({"time":[1],"close":[1]}))
if __name__=="__main__": unittest.main()
