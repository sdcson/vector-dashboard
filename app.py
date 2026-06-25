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
def get_kma_weather(year_str, month_str, week_str, loc_name):
    y = str(year_str).replace("년", "").strip()
    m = str(month_str).replace("월", "").strip().zfill(2)
    w_map = {"1주":("01","07"), "2주":("08","14"), "3주":("15","21"), "4주":("22","28"), "전체":("01","28")}
    d1, d2 = w_map.get(str(week_str).strip(), ("01","28"))
    tm1, tm2 = f"{y}{m}{d1}", f"{y}{m}{d2}"
    stn = get_kma_stn(loc_name)
            
    url = f"http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList?serviceKey={KMA_API_KEY}&pageNo=1&numOfRows=50&dataType=JSON&dataCd=ASOS&dateCd=DAY&startDt={tm1}&endDt={tm2}&stnIds={stn}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
            if items:
                df_w = pd.DataFrame(items)
                t_avg = pd.to_numeric(df_w.get('avgTa', 0), errors='coerce').mean()
                p_sum = pd.to_numeric(df_w.get('sumRn', 0), errors='coerce').fillna(0.0).sum()
                h_avg = pd.to_numeric(df_w.get('avgRhm', 0), errors='coerce').mean()
                w_avg = pd.to_numeric(df_w.get('avgWs', 0), errors='coerce').mean()
                return {
                    "temp": round(t_avg, 1) if not pd.isna(t_avg) else 0.0, 
                    "precip": round(p_sum, 1) if not pd.isna(p_sum) else 0.0, 
                    "humid": round(h_avg, 1) if not pd.isna(h_avg) else 0.0,
                    "wind": round(w_avg, 1) if not pd.isna(w_avg) else 0.0
                }
    except Exception: pass
    return {"temp": 0.0, "precip": 0.0, "humid": 0.0, "wind": 0.0}

@st.cache_data(ttl=3600)
def get_kma_weather_bulk(year_str, loc_name):
    y = str(year_str).replace("년", "").strip()
    stn = get_kma_stn(loc_name)
    if "2026" in year_str:
        tm1, tm2 = f"{y}0301", f"{y}0531"
        weather_dict = {f"{m:02d}월": {"temp": 0.0, "precip": 0.0, "humid": 0.0, "wind": 0.0} for m in range(3, 6)}
    else:
        tm1, tm2 = f"{y}0301", f"{y}1231"
        weather_dict = {f"{m:02d}월": {"temp": 0.0, "precip": 0.0, "humid": 0.0, "wind": 0.0} for m in range(3, 13)}
    
    url = f"http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList?serviceKey={KMA_API_KEY}&pageNo=1&numOfRows=400&dataType=JSON&dataCd=ASOS&dateCd=DAY&startDt={tm1}&endDt={tm2}&stnIds={stn}"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            data = res.json()
            items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
            if items:
                df_w = pd.DataFrame(items)
                df_w["month_str"] = df_w['tm'].str[5:7] + "월"
                df_w = df_w[df_w["month_str"].isin(weather_dict.keys())]
                
                df_w['avgTa'] = pd.to_numeric(df_w.get('avgTa', 0), errors='coerce')
                df_w['sumRn'] = pd.to_numeric(df_w.get('sumRn', 0), errors='coerce').fillna(0.0)
                df_w['avgRhm'] = pd.to_numeric(df_w.get('avgRhm', 0), errors='coerce')
                df_w['avgWs'] = pd.to_numeric(df_w.get('avgWs', 0), errors='coerce')
                
                grouped = df_w.groupby("month_str").agg({'avgTa': 'mean', 'sumRn': 'sum', 'avgRhm': 'mean', 'avgWs': 'mean'})
                
                for m_idx, row in grouped.iterrows():
                    weather_dict[m_idx] = {
                        "temp": round(row['avgTa'], 1) if not pd.isna(row['avgTa']) else 0.0, 
                        "precip": round(row['sumRn'], 1) if not pd.isna(row['sumRn']) else 0.0, 
                        "humid": round(row['avgRhm'], 1) if not pd.isna(row['avgRhm']) else 0.0,
                        "wind": round(row['avgWs'], 1) if not pd.isna(row['avgWs']) else 0.0
                    }
    except Exception: pass
    return weather_dict

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

# -----------------------------------------------------------------
# [💡 VectorNet 전용: 절대 주차(1~52주) -> 월별 주차(1~4주) 매핑 엔진]
# -----------------------------------------------------------------
def convert_absolute_to_monthly_week(row):
    y_str = row.get("조사년도", "2025")
    w_str = row.get("주차", row.get("조사주", "1"))
    try:
        y = int(str(y_str).replace("년", "").strip())
        w_digits = ''.join(filter(str.isdigit, str(w_str)))
        if not w_digits: return "1주"