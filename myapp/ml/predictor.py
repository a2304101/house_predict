import os
import numpy as np
import lightgbm as lgb
import pandas as pd
from pathlib import Path
#BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_DIR = Path(__file__).resolve().parent.parent.parent
#MODEL_PATH = r"F:/桃竹苗/final/m/lgb_full_train_final.txt"
MODEL_PATH = BASE_DIR / "m" / "lgb_full_train_final.txt"
MODEL = lgb.Booster(model_file=MODEL_PATH)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

def predict_price(df):
    expected_cols = MODEL.feature_name()

    missing = set(expected_cols) - set(df.columns)
    extra = set(df.columns) - set(expected_cols)

    if missing:
        raise ValueError(f"缺少模型欄位: {missing}")

    df = df[expected_cols]

    preds = np.expm1(MODEL.predict(df))
    return float(preds[0])
