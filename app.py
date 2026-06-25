import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
from io import BytesIO
import matplotlib.font_manager as fm
import urllib.request
import os
import requests
import base64
import calendar
import datetime

# 페이지 설정
st.set_page_config(page_title="강원특별자치도 매개체 감시 시스템", layout="wide")

# -----------------------------------------------------------------
# [💡 영구 차트 한글 깨짐 방지: 구글 나눔고딕 커널 엔진]
# -----------------------------------------------------------------
@st.cache_resource
def init_korean_font_and_get_prop():
    font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
    font_path = "NanumGothic.ttf"
    
    if not os.path.exists(font_path):
        try:
            urllib.request.urlretrieve(font_url, font_path)
        except Exception:
            pass
            
    if os.path.exists(font_path):
        try:
            fm.fontManager.addfont(font_path)
            font_prop = fm.FontProperties(fname=font_path)
            plt.rcParams['font.family'] = font_prop.get_name()
            plt.rcParams['axes.unicode_minus'] = False
            return font_prop
        except Exception:
            return None
    return None

f_prop = init_korean_font_and_get_prop()

st.title("🔬 감염병 매개체 감시사업 통합 데이터")
st.markdown("질병조사과 주요 감시사업별 결과 및 기상 데이터(기온/강수량/습도/풍속) 교차 분석")

# -----------------------------------------------------------------
# [💡 공공데이터포털 JSON API 실시간 연동 모듈]
# -----------------------------------------------------------------
KMA_API_KEY = "c8d1bc45c0ea0b9b1599e0f08f84fe61a141e9a29276bb43ab140915baee2898"

def get_kma_stn(loc_name):
    stn_map = {
        "춘천": "101", "산천": "101", "중앙": "101", "지내": "101",
        "철원": "95", "대마": "95", "학사": "95",
        "강릉": "105", "산대월": "105", 
        "속초": "90", "고성": "90", 
        "홍천": "212", "삼마치": "212", "남산": "212",
        "인제": "211", "정선": "214", 
        "화천": "101", "양구": "101", 
        "횡성": "114", "하대": "114"
    }
    for k, v in stn_map.items():
        if k in str(loc_name): return v
    return "101" 

@st.cache_data(ttl=3600)
def get_kma_weather_daily(year_str, loc_name):
    y = str(year_str).replace("년", "").strip()
    stn = get_kma_stn(loc_name)
    
    now = datetime.datetime.now() - datetime.timedelta(days=2)
    if y == str(datetime.datetime.now().year):
        tm2 = now.strftime("%Y%m%d")
    else:
        tm2 = f"{y}1231"
        
    tm1 = f"{y}0215" 
    
    url = f"http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList?serviceKey={KMA_API_KEY}&pageNo=1&numOfRows=400&dataType=JSON&dataCd=ASOS&dateCd=DAY&startDt={tm1}&endDt={tm2}&stnIds={stn}"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            data = res.json()
            items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
            if items:
                df_w = pd.DataFrame(items)
                df_w['tm'] = pd.to_datetime(df_w['tm'])
                df_w['avgTa'] = pd.to_numeric(df_w.get('avgTa', 0), errors='coerce').fillna(0)
                df_w['sumRn'] = pd.to_numeric(df_w.get('sumRn', 0), errors='coerce').fillna(0)
                df_w['avgRhm'] = pd.to_numeric(df_w.get('avgRhm', 0), errors='coerce').fillna(0)
                df_w['avgWs'] = pd.to_numeric(df_w.get('avgWs', 0), errors='coerce').fillna(0)
                return df_w[['tm', 'avgTa', 'sumRn', 'avgRhm', 'avgWs']]
    except Exception: pass
    return pd.DataFrame(columns=['tm', 'avgTa', 'sumRn', 'avgRhm', 'avgWs'])

def convert_absolute_to_monthly_week(row):
    y_str = row.get("조사년도", "2025")
    w_str = row.get("주차", row.get("조사주", "1"))
    try:
        y = int(str(y_str).replace("년", "").strip())
        w_digits = ''.join(filter(str.isdigit, str(w_str)))
        if not w_digits: return "1주"
        
        w = int(w_digits)
        if w <= 5: 
            return f"{min(w, 4)}주"
        
        date_obj = pd.to_datetime(f'{y}-{w:02d}-1', format='%G-%V-%u')
        month_week = (date_obj.day - 1) // 7 + 1
        return f"{min(month_week, 4)}주"
    except Exception:
        return "1주"

def get_github_credentials():
    try: return st.secrets["GITHUB_TOKEN"], st.secrets["GITHUB_REPO"]
    except: return None, None

def save_df_to_github(df, filename_on_github, commit_message="Update"):
    token, repo = get_github_credentials()
    if not token or not repo: return False
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    base64_content = base64.b64encode(csv_bytes).decode('utf-8')
    url = f"https://api.github.com/repos/{repo}/contents/{filename_on_github}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    payload = {"message": commit_message, "content": base64_content, "branch": "main"}
    if sha: payload["sha"] = sha
    return requests.put(url, headers=headers, json=payload).status_code in [200, 201]

def load_df_from_github(filename_on_github, fallback_df):
    token, repo = get_github_credentials()
    if not token or not repo: return fallback_df
    url = f"https://api.github.com/repos/{repo}/contents/{filename_on_github}"
    res = requests.get(url, headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"})
    if res.status_code == 200:
        try: return pd.read_csv(BytesIO(base64.b64decode(res.json().get("content"))), encoding='utf-8-sig')
        except: return fallback_df
    return fallback_df

def safe_parse_year_series(series, default_val):
    def _parse(val):
        if pd.isna(val) or val == "" or str(val).lower() in ['nan', '<na>']: return str(default_val)
        val_str = str(val).strip()
        if "년" in val_str: return val_str
        return f"{int(float(val_str))}년" if val_str.replace('.', '', 1).isdigit() else f"{val_str}년"
    return series.apply(_parse)

def safe_parse_month_series(series, default_val):
    def _parse(val):
        if pd.isna(val) or val == "" or str(val).lower() in ['nan', '<na>']: return str(default_val)
        try: return f"{int(float(str(val).strip().replace('월', ''))):02d}월"
        except: return str(default_val)
    return series.apply(_parse)

def parse_vectornet_dataframe(df, default_year, default_month):
    df.columns = [str(c).strip() for c in df.columns]
    
    # 💡 [치명적 버그 해결] 엑셀 열 이름이 달라도 무조건 '종', '지역2', '개체수'로 통일하여 합산 버그 원천 차단
    for sp_cand in ["학명", "모기종", "종류", "종명"]:
        if sp_cand in df.columns and "종" not in df.columns:
            df.rename(columns={sp_cand: "종"}, inplace=True)
            break
            
    for loc_cand in ["지점", "지역", "채집장소", "시군구", "지점명", "채집지역2"]:
        if loc_cand in df.columns and "지역2" not in df.columns:
            df.rename(columns={loc_cand: "지역2"}, inplace=True)
            break
            
    for cnt_cand in ["채집수", "수량", "합계", "총계"]:
        if cnt_cand in df.columns and "개체수" not in df.columns:
            df.rename(columns={cnt_cand: "개체수"}, inplace=True)
            break

    date_cols = ['수거일', '채집일', '조사일', '조사일자', '채집일자', '채집일시']
    found_col = next((c for c in date_cols if c in df.columns), None)
    
    if found_col:
        dt_series = pd.to_datetime(df[found_col], errors='coerce')
        valid_mask = dt_series.notna()
        df