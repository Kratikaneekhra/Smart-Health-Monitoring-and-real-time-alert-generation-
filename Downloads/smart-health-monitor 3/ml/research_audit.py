"""Lightweight dataset audit: python ml/research_audit.py [disease keys]"""
import os, sys
import pandas as pd
from backend.schemas import DISEASES
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for key in sys.argv[1:] or list(DISEASES):
    path=os.path.join(ROOT,'data','raw',DISEASES[key]['data_file'])
    if not os.path.exists(path):
        print(f'[{key}] file missing: {path}'); continue
    df=pd.read_csv(path)
    print(f'\n=== {key.upper()} ===\nRows: {len(df)} | columns: {len(df.columns)} | duplicate rows: {df.duplicated().sum()}')
    miss=df.isna().sum(); miss=miss[miss>0].sort_values(ascending=False)
    print('Missing values (top 15):\n',miss.head(15).to_string() if len(miss) else 'None')
    print('Column names:', list(df.columns))
