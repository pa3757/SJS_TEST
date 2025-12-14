import pandas as pd
import sqlite3

# CSV 불러오기
df = pd.read_csv("flo_data_20k.csv")

# ID 컬럼 새로 생성 (1부터 시작)
df.insert(0, "id", range(1, len(df) + 1))

# SQLite 저장
conn = sqlite3.connect("flo_data.db")
df.to_sql("clients", conn, if_exists="replace", index=False)
conn.close()