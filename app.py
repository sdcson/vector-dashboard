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
        
        w = int(w_digits)
        if w <= 5: 
            return f"{min(w, 4)}주"
        
        date_obj = pd.to_datetime(f'{y}-{w:02d}-1', format='%G-%V-%u')
        month_week = (date_obj.day - 1) // 7 + 1
        return f"{min(month_week, 4)}주"
    except Exception:
        return "1주"

# -----------------------------------------------------------------
# [💡 GitHub API 연동 데이터베이스 엔진 및 포맷터]
# -----------------------------------------------------------------
def get_github_credentials():
    try: return st.secrets["GITHUB_TOKEN"], st.secrets["GITHUB_REPO"]
    except Exception: return None, None

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
        except Exception: return fallback_df
    return fallback_df

def safe_parse_year_series(series, default_val):
    def _parse(val):
        if pd.isna(val) or val == "" or str(val).lower() in ['nan', '<na>']: return str(default_val)
        val_str = str(val).strip()
        if "년" in val_str: return val_str
        if val_str.replace('.', '', 1).isdigit(): return f"{int(float(val_str))}년"
        return f"{val_str}년"
    return series.apply(_parse)

def safe_parse_month_series(series, default_val):
    def _parse(val):
        if pd.isna(val) or val == "" or str(val).lower() in ['nan', '<na>']: return str(default_val)
        try: return f"{int(float(str(val).strip().replace('월', ''))):02d}월"
        except Exception: return str(default_val)
    return series.apply(_parse)

# 💡 [핵심 방어] 파일 업로드 시 모기종, 채집수 등의 열 이름을 무조건 표준으로 통일시킵니다.
def parse_vectornet_dataframe(df, default_year, default_month):
    df.columns = [str(c).strip() for c in df.columns]
    
    # 열 이름 강제 통일
    sp_cands = ["학명", "모기종", "종류", "종명", "매개체명"]
    for c in sp_cands:
        if c in df.columns and "종" not in df.columns:
            df.rename(columns={c: "종"}, inplace=True)
            break
            
    loc_cands = ["지역", "지점", "지점명", "채집장소", "시군구", "채집지역", "채집지", "채집지역2"]
    for c in loc_cands:
        if c in df.columns and "지역2" not in df.columns:
            df.rename(columns={c: "지역2"}, inplace=True)
            break
            
    val_cands = ["채집수", "총개체수", "합계", "마리수", "수량", "Count", "총합"]
    for c in val_cands:
        if c in df.columns and "개체수" not in df.columns:
            df.rename(columns={c: "개체수"}, inplace=True)
            break

    date_cols = ['수거일', '채집일', '조사일', '조사일자', '채집일자', '채집일시']
    found_col = next((c for c in date_cols if c in df.columns), None)
    
    if found_col:
        dt_series = pd.to_datetime(df[found_col], errors='coerce')
        valid_mask = dt_series.notna()
        df["조사년도"] = safe_parse_year_series(df["연도"] if "연도" in df.columns else df.get("년도", default_year), default_year)
        df["조사월"] = safe_parse_month_series(df.get("월", default_month), default_month)
        df["조사주"] = "1주"
        
        df.loc[valid_mask, "조사년도"] = dt_series[valid_mask].dt.year.apply(lambda x: f"{int(x)}년")
        df.loc[valid_mask, "조사월"] = dt_series[valid_mask].dt.month.apply(lambda x: f"{int(x):02d}월")
        df.loc[valid_mask, "조사주"] = dt_series[valid_mask].dt.day.apply(lambda x: f"{min((int(x) - 1) // 7 + 1, 4)}주")
        df["주차"] = df["조사주"]
    else:
        if "월.1" in df.columns and "월" in df.columns:
            df["조사년도"] = safe_parse_year_series(df["월"], default_year)
            df["조사월"] = safe_parse_month_series(df["월.1"], default_month)
        else:
            df["조사년도"] = safe_parse_year_series(df["연도"] if "연도" in df.columns else df.get("년도", default_year), default_year)
            df["조사월"] = safe_parse_month_series(df.get("월", default_month), default_month)
            
        if "주차" in df.columns:
            def _clean_w(w):
                s = str(w)
                if "1" in s: return "1주"
                if "2" in s: return "2주"
                if "3" in s: return "3주"
                if "4" in s or "5" in s: return "4주"
                return "1주"
            df["조사주"] = df["주차"].apply(_clean_w)
            df["주차"] = df["조사주"]
        else:
            df["조사주"] = "1주"
            df["주차"] = "1주"
    return df

def rename_duplicate_columns(df):
    if df is None or df.empty: return df
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique(): cols[cols == dup] = [f"{dup}.{i}" if i != 0 else dup for i in range(cols[cols == dup].shape[0])]
    df.columns = cols
    return df

def convert_df_to_csv(df): return df.to_csv(index=False).encode('utf-8-sig')

def merge_and_overwrite(old_df, new_df, keys):
    if new_df.empty: return old_df
    val_col = "개체수" if "개체수" in new_df.columns else ("채집수" if "채집수" in new_df.columns else "개체수")
    groupby_keys = [k for k in keys if k in new_df.columns]
    agg_dict = {col: ('sum' if col == val_col else 'first') for col in new_df.columns if col not in groupby_keys and col not in ['번호', '연번']}
    new_df_aggregated = new_df.groupby(groupby_keys, as_index=False).agg(agg_dict)
    if old_df.empty: return new_df_aggregated
    return pd.concat([old_df, new_df_aggregated], ignore_index=True).drop_duplicates(subset=groupby_keys, keep='last')

def smart_load_uploaded_file(uploaded_file):
    if uploaded_file is None: return pd.DataFrame()
    file_name = uploaded_file.name.lower()
    df_res = pd.DataFrame()
    if file_name.endswith(('.xlsx', '.xls')):
        try:
            uploaded_file.seek(0)
            raw_excel = pd.read_excel(uploaded_file, sheet_name=0, header=None)
            skip_rows_idx = next((r_idx for r_idx in range(min(10, len(raw_excel))) if any(('조사' in s or '월' in s or '연번' in s or '지점' in s or '번호' in s) for s in [str(x).strip() for x in raw_excel.iloc[r_idx]])), 0)
            uploaded_file.seek(0)
            df_res = pd.read_excel(uploaded_file, sheet_name=0, skiprows=skip_rows_idx)
        except Exception:
            uploaded_file.seek(0)
            df_res = pd.read_excel(uploaded_file, sheet_name=0)
    else:
        for enc in ['utf-8', 'cp949', 'euc-kr']:
            try:
                uploaded_file.seek(0)
                raw_csv = pd.read_csv(uploaded_file, encoding=enc, header=None, nrows=10)
                skip_rows_idx = next((r_idx for r_idx in range(len(raw_csv)) if any(('조사' in s or '월' in s or '연번' in s or '지점' in s or '번호' in s) for s in [str(x).strip() for x in raw_csv.iloc[r_idx]])), 0)
                uploaded_file.seek(0)
                df_res = pd.read_csv(uploaded_file, encoding=enc, skiprows=skip_rows_idx)
                break
            except Exception: continue
    if not df_res.empty: df_res.columns = [str(c).strip() for c in df_res.columns]
    return df_res

# -----------------------------------------------------------------
# [첨부파일 기반 정식 데이터 마스터 세션 빌더]
# -----------------------------------------------------------------
@st.cache_data
def get_je_actual_style_data():
    if os.path.exists('일본뇌염.xlsx - VectorNet.csv'):
        return parse_vectornet_dataframe(pd.read_csv('일본뇌염.xlsx - VectorNet.csv'), "2026년", "05월")
    return parse_vectornet_dataframe(pd.DataFrame(columns=["연도", "월", "주차", "사업명", "권역", "지역2", "환경", "방법", "종", "개체수"]), "2026년", "05월")

@st.cache_data
def get_malaria_actual_style_data():
    if os.path.exists('말라리아.xlsx - VectorNet.csv'):
        return parse_vectornet_dataframe(pd.read_csv('말라리아.xlsx - VectorNet.csv'), "2026년", "05월")
    return parse_vectornet_dataframe(pd.DataFrame(columns=["연도", "월", "주차", "사업명", "권역", "지역2", "환경", "방법", "종", "개체수"]), "2026년", "05월")

@st.cache_data
def get_cli_moq_data():
    if os.path.exists('권역모기.xlsx - VectorNet.csv'):
        return parse_vectornet_dataframe(pd.read_csv('권역모기.xlsx - VectorNet.csv'), "2026년", "05월")
    return parse_vectornet_dataframe(pd.DataFrame(columns=["연도", "월", "주차", "지역2", "환경", "종", "개체수"]), "2026년", "05월")

@st.cache_data
def get_cli_tick_data():
    if os.path.exists('권역 참진드기.xlsx - VectorNet.csv'):
        df = parse_vectornet_dataframe(pd.read_csv('권역 참진드기.xlsx - VectorNet.csv'), "2026년", "05월")
    else:
        df = parse_vectornet_dataframe(pd.DataFrame(columns=["월", "월.1", "주차", "지역2", "환경", "종", "개체수"]), "2026년", "05월")
    
    if not df.empty and "종" in df.columns: 
        df["종"] = df["종"].astype(str).apply(lambda x: "Larva" if "기타" in x else x.strip())
    return df

@st.cache_data
def get_cli_mite_dist_data():
    for name in ['털진드기 분포감시-1.xlsx - Sheet1.csv', '털진드기 분포감시.xlsx - VectorNet.csv']:
        if os.path.exists(name):
            return parse_vectornet_dataframe(pd.read_csv(name), "2026년", "04월")
    return pd.DataFrame(columns=["월", "월.1", "주차", "지역2", "환경", "종", "개체수", "방법"])

@st.cache_data
def get_cli_mite_gen_data():
    for name in ['털진드기 발생감시.xlsx - Sheet1.csv', '털진드기 발생감시.xlsx - VectorNet.csv']:
        if os.path.exists(name):
            return parse_vectornet_dataframe(pd.read_csv(name), "2025년", "12월")
    return pd.DataFrame(columns=["월", "월.1", "주차", "지역2", "환경", "종", "개체수", "방법"])

@st.cache_data
def get_forest_playground_actual_data():
    data = []
    idx = 1
    for year in ["2026년", "2025년", "2024년", "2023년", "2022년", "2021년", "2020년"]:
        seed_year = int(year.replace("년",""))
        regions = ["홍천", "정선"] if seed_year == 2025 else (["춘천", "인제"] if seed_year == 2024 else (["속초", "양양", "인제"] if seed_year == 2023 else ["남산", "삼마치"]))
        for month_int in range(3, 12): 
            for week in ["1주", "2주", "3주", "4주"]:
                np.random.seed(seed_year + month_int * 13 + len(week))
                for region in regions:
                    for spot_num in range(1, 4):
                        for sp in ["Hard tick", "Haemaphysalis longicornis", "Haemaphysalis flava ", "Haemaphysalis japonica", "Ixodes nipponensis"]:
                            cnt = int(np.random.poisson(20 if month_int in [8,9] else 2))
                            if cnt > 0:
                                data.append({"연번": idx, "조사년도": year, "월": month_int, "조사월": f"{month_int:02d}월", "조사주": week, "채집지역2": region, "지점번호": spot_num, "분류": "In", "종": sp, "Stage": "Nymph", "개체수": cnt, "is_uploaded": False})
                                idx += 1
    return pd.DataFrame(data)

base_je_df = rename_duplicate_columns(load_df_from_github("database_je.csv", get_je_actual_style_data()))
base_mal_df = rename_duplicate_columns(load_df_from_github("database_mal.csv", get_malaria_actual_style_data()))
base_cli_moq_df = rename_duplicate_columns(load_df_from_github("database_cli_moq.csv", get_cli_moq_data()))
base_cli_tick_df = rename_duplicate_columns(load_df_from_github("database_cli_tick.csv", get_cli_tick_data()))
base_cli_mite_dist_df = rename_duplicate_columns(load_df_from_github("database_cli_mite_dist.csv", get_cli_mite_dist_data()))
base_cli_mite_gen_df = rename_duplicate_columns(load_df_from_github("database_cli_mite_gen.csv", get_cli_mite_gen_data()))
base_forest_df = rename_duplicate_columns(load_df_from_github("database_forest.csv", get_forest_playground_actual_data()))

# -----------------------------------------------------------------
# [사이드바 시간 필터 패널]
# -----------------------------------------------------------------
st.sidebar.markdown("### 📅 통합 시간 동기화 필터")
selected_year = st.sidebar.selectbox("조사년도 선택", ["2026년", "2025년", "2024년", "2023년", "2022년", "2021년", "2020년"])
selected_month = st.sidebar.selectbox("조사월 선택", ["03월", "04월", "05월", "06월", "07월", "08월", "09월", "10월", "11월", "12월"], index=3)
selected_week = st.sidebar.selectbox("조사주 선택", ["1주", "2주", "3주", "4주", "전체"], index=1)

# =================================================================================
# 💡 [신규] 사이드바 챗봇 UI 및 AI 기반 하이브리드 검색 엔진
# =================================================================================
st.sidebar.markdown("---")
st.sidebar.markdown("### 💬 매개체감염병 AI 챗봇")

@st.cache_resource
def load_faq_ai_engine():
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        import os
        import pandas as pd
        
        file_loaded = False
        df_faq = pd.DataFrame()

        csv_candidates = [
            "매개체감염병_지식베이스_통합본_최종.csv", 
            "매개체감염병_지식베이스_카카오형식.xlsx - FAQ Set.csv",
            "매개체감염병_지식베이스_카카오형식.csv"
        ]
        
        for csv_file in csv_candidates:
            if os.path.exists(csv_file):
                try: 
                    df_faq = pd.read_csv(csv_file, encoding='utf-8-sig')
                except UnicodeDecodeError:
                    df_faq = pd.read_csv(csv_file, encoding='cp949')
                file_loaded = True
                break
        
        if not file_loaded:
            excel_name = "매개체감염병_지식베이스_카카오형식.xlsx"
            if os.path.exists(excel_name):
                try:
                    df_faq = pd.read_excel(excel_name, sheet_name="FAQ Set", engine="openpyxl")
                except ValueError:
                    df_faq = pd.read_excel(excel_name, sheet_name=0, engine="openpyxl") 
                file_loaded = True

        if df_faq.empty:
            st.sidebar.error("지식베이스 데이터를 찾을 수 없습니다. 파일 업로드를 확인해주세요.")
            return pd.DataFrame(), None, None

        df_faq["Question"] = df_faq["Question"].astype(str)
        df_faq["Answer"] = df_faq["Answer"].astype(str)
        
        vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))
        tfidf_matrix = vectorizer.fit_transform(df_faq["Question"])
        
        return df_faq, vectorizer, tfidf_matrix
    except Exception as e:
        st.sidebar.error(f"지식베이스 로드 실패: {e}")
        return pd.DataFrame(), None, None

df_faq, vectorizer, tfidf_matrix = load_faq_ai_engine()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "매개체감염병에 대해 질문해 주세요! (예: 일본뇌염, 말라리아 예방)"}]

if user_query := st.sidebar.chat_input("질문을 입력하세요..."):
    st.session_state.messages.append({"role": "user", "content": user_query})
    
    matched_answer = "질문의 의도를 파악하지 못했어요. 핵심 단어 위주로 다시 질문해 주시겠어요?"
    
    if not df_faq.empty:
        import re
        clean_query = re.sub(r'[^\w\s]', '', user_query).strip()
        
        if len(clean_query) >= 2:
            exact_match_df = df_faq[df_faq["Question"].str.contains(re.escape(clean_query), na=False, case=False)]
        else:
            exact_match_df = pd.DataFrame()
        
        if not exact_match_df.empty:
            matched_answer = exact_match_df.iloc[0]["Answer"]
        elif vectorizer is not None and tfidf_matrix is not None:
            from sklearn.metrics.pairwise import cosine_similarity
            query_vec = vectorizer.transform([user_query])
            similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
            
            best_idx = similarities.argmax()
            best_score = similarities[best_idx]
            
            if best_score > 0.25: 
                matched_answer = df_faq.iloc[best_idx]["Answer"]
            else:
                matched_answer = "지식베이스에서 정확히 일치하는 내용을 찾지 못했습니다. '일본뇌염 증상'처럼 핵심 단어를 포함해 질문해 보세요!"

    safe_answer = matched_answer.replace("~", r"\~")
    st.session_state.messages.append({"role": "assistant", "content": safe_answer})

chat_container = st.sidebar.container(height=450)

with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

tabs = ["🔴 일본뇌염 매개모기 감시", "🔵 말라리아 매개모기 감시", "🟢 기후변화 대응 매개체 감시", "🟡 참진드기조사(어린이숲체험장)", "☁️ 기상 요인 상관분석"]
selected_tab = st.radio("📡 감시사업 카테고리 선택", tabs, horizontal=True)

st.markdown("---")

# =================================================================================
# 1. 일본뇌염 레이어
# =================================================================================
if selected_tab == "🔴 일본뇌염 매개모기 감시":
    st.header(f"🏠 우사 거점 일본뇌염 매개모기 감시 현황 [{selected_year} {selected_month} {selected_week}]")
    
    c_up1, c_dl1 = st.columns([8, 4])
    with c_up1:
        je_file = st.file_uploader("질병청 VectorNet 일본뇌염 결과 파일 업로드", type=["csv", "xlsx", "xls"], key="je_up")
        if je_file is not None:
            uploaded_df = smart_load_uploaded_file(je_file)
            uploaded_df = parse_vectornet_dataframe(uploaded_df, selected_year, selected_month)
            base_je_df = merge_and_overwrite(base_je_df, rename_duplicate_columns(uploaded_df), keys=['조사년도', '조사월', '주차', '지역2', '종'])
            save_df_to_github(base_je_df, "database_je.csv", "Append JE data")
            st.success("✅ 실시간 원장 데이터베이스 누적 완료")
            st.cache_data.clear()
            
    df_je = base_je_df.copy()

    if not df_je.empty:
        df_je = parse_vectornet_dataframe(df_je, selected_year, selected_month)
        je_coords_map = {"횡성군 하대리": [37.4912, 127.9845], "강릉시 산대월리": [37.7518, 128.8762], "춘천시 산천리": [37.9250, 127.7410]}
        
        if "지역2" in df_je.columns:
            def normalize_je_spot(x):
                s = str(x)
                if "산대" in s or "강릉" in s: return "강릉시 산대월리"
                if "하대" in s or "횡성" in s: return "횡성군 하대리"
                if "산천" in s or "춘천" in s: return "춘천시 산천리"
                return s.strip()
            df_je["지역2_정규화"] = df_je["지역2"].map(normalize_je_spot)
            df_je["위도"] = df_je["지역2_정규화"].map(lambda x: je_coords_map.get(x, [37.9250, 127.7410])[0])
            df_je["경도"] = df_je["지역2_정규화"].map(lambda x: je_coords_map.get(x, [37.9250, 127.7410])[1])
            df_je["지점명"] = df_je["지역2_정규화"].map(lambda x: f"{x} (우사 거점)")
        else:
            df_je["지점명"] = "춘천시 산천리 (우사 거점)"

        if "주차" in df_je.columns:
            df_je["조사주"] = df_je.apply(convert_absolute_to_monthly_week, axis=1)
        else:
            df_je["조사주"] = "1주"

        if selected_week != "전체":
            f_je = df_je[(df_je["조사년도"] == selected_year) & (df_je["조사월"] == selected_month) & (df_je["조사주"] == selected_week)].copy()
        else:
            f_je = df_je[(df_je["조사년도"] == selected_year) & (df_je["조사월"] == selected_month)].copy()
        
        with c_dl1:
            st.markdown("<br>", unsafe_allow_html=True)
            if not f_je.empty:
                st.download_button("📥 필터 데이터 원본 추출", convert_df_to_csv(f_je), "일본뇌염.csv", "text/csv")

        if not f_je.empty:
            val_col_je = "개체수" if "개체수" in f_je.columns else "채집수"
            f_je[val_col_je] = pd.to_numeric(f_je[val_col_je], errors='coerce').fillna(0)
            
            je_spots = ["춘천시 산천리 (우사 거점)", "강릉시 산대월리 (우사 거점)", "횡성군 하대리 (우사 거점)"]
            je_sub_tabs = st.tabs(["📍 지점전체"] + [f"📍 {spot.split(' (')[0]}" for spot in je_spots])
            
            with je_sub_tabs[0]:
                c1, c2 = st.columns([5, 5])
                with c1:
                    st.markdown("##### 🗺️ GIS 거점센터 지도 (전체)")
                    m_je_all = folium.Map(location=[37.75, 128.3], zoom_start=8)
                    for target_spot_name, coords in je_coords_map.items():
                        folium.Marker([coords[0], coords[1]], tooltip=f"{target_spot_name} (우사 거점)", icon=folium.Icon(color='red', icon='home')).add_to(m_je_all)
                    st_folium(m_je_all, key="map_je_all", width="100%", height=380)
                
                # 💡 일본뇌염 전체 지점 정밀 핀셋 필터링
                with c2:
                    st.markdown("##### 📊 지점별 모기 종별 채집량 (전체)")
                    species_col_je = "종" if "종" in f_je.columns else None
                    if species_col_je:
                        je_species_series = f_je[species_col_je].astype(str).str.strip()
                        mask = je_species_series.str.contains(
                            r"\bCulex\s+tritaeniorhynchus\b|tritaeniorhynchus|작은빨간집",
                            case=False,
                            regex=True,
                            na=False,
                        )
                    else:
                        mask = pd.Series(False, index=f_je.index)
                    
                    f_je_filtered = f_je[mask].copy()
                        
                    if not f_je_filtered.empty and f_je_filtered[val_col_je].sum() > 0:
                        df_plot = f_je_filtered.copy()
                        df_plot["지점_클린"] = df_plot["지점명"].apply(lambda x: str(x).split(' (')[0])
                        pivot_df = df_plot.pivot_table(index='지점_클린', columns='종', values=val_col_je, aggfunc='sum').fillna(0)
                        clean_je_spots = [s.split(' (')[0] for s in je_spots]
                        pivot_df = pivot_df.reindex(clean_je_spots, fill_value=0)
                        
                        fig, ax1 = plt.subplots(figsize=(6, 5.2))
                        cmap = plt.get_cmap('Pastel2')
                        bar_colors = ['#ef233c' if 'tritaeniorhynchus' in str(c).lower() or '작은빨간집' in str(c) else cmap(i%8) for i, c in enumerate(pivot_df.columns)]
                        pivot_df.plot(kind='bar', stacked=True, ax=ax1, color=bar_colors, edgecolor='#2b2d42')
                        ax1.set_ylabel('총 개체수')
                        
                        for container in ax1.containers:
                            labels = [f'{int(v.get_height())}' if v.get_height() > 0 else '' for v in container]
                            ax1.bar_label(container, labels=labels, label_type='center', fontsize=8, fontweight='bold', color='white')
                            
                        plt.xticks(rotation=45, ha='right')
                        plt.legend(title="일본뇌염 매개모기(작은빨간집모기)", bbox_to_anchor=(1.05, 1), loc='upper left')
                        st.pyplot(fig)
                        plt.close()
                    else:
                        st.markdown(f"<div style='text-align: center; padding: 120px 0; color: #888; font-size: 1.1em; font-weight: bold;'>해당 주차({selected_week}) 전체 지점 채집량 0마리<br>🚫 작은빨간집모기 미검출</div>", unsafe_allow_html=True)

            for idx, spot_name in enumerate(je_spots):
                with je_sub_tabs[idx + 1]:
                    spot_data = f_je[f_je["지점명"].str.contains(spot_name.split(' (')[0], na=False)]
                    c1, c2 = st.columns([5, 5])
                    with c1:
                        st.markdown(f"##### 🗺️ {spot_name.split(' (')[0]} 거점 지도")
                        m_spot = folium.Map(location=je_coords_map.get(spot_name.split(' (')[0], [37.9, 127.7]), zoom_start=11)
                        folium.Marker(je_coords_map.get(spot_name.split(' (')[0], [37.9, 127.7]), tooltip=spot_name, icon=folium.Icon(color='red', icon='star')).add_to(m_spot)
                        st_folium(m_spot, key=f"map_je_spot_{idx}", width="100%", height=380)
                    with c2:
                        st.markdown(f"##### 📊 {spot_name.split(' (')[0]} 모기 종별 채집량")
                        if not spot_data.empty and spot_data[val_col_je].sum() > 0:
                            sum_df = spot_data.groupby("종")[val_col_je].sum().reset_index().sort_values(by=val_col_je)
                            fig, plt_ax = plt.subplots(figsize=(6, 5.2))
                            bar_colors = ['#ef233c' if 'tritaeniorhynchus' in str(s).lower() or '작은빨간집' in str(s) else '#c4cbde' for s in sum_df["종"]]
                            bars = plt_ax.barh(sum_df["종"], sum_df[val_col_je], color=bar_colors, edgecolor='#2b2d42')
                            for bar in bars:
                                plt_ax.text(bar.get_width()+0.5, bar.get_y()+bar.get_height()/2, f"{int(bar.get_width())}마리", va='center', fontsize=8)
                            plt_ax.set_xlabel('개체수 (마리)')
                            st.pyplot(fig)
                            plt.close()
                        else:
                            st.markdown(f"<div style='text-align: center; padding: 120px 0; color: #888; font-size: 1.1em; font-weight: bold;'>해당 주차({selected_week}) 채집량 0마리<br>🚫 모기 미검출</div>", unsafe_allow_html=True)
                            
                    if not spot_data.empty and spot_data[val_col_je].sum() > 0:
                        st.dataframe(spot_data.drop(columns=["위도", "경도", "지역2_정규화"], errors='ignore'), hide_index=True, use_container_width=True)
        else:
            st.warning(f"⚠️ 선택하신 [{selected_year} {selected_month} {selected_week}] 조건에 해당하는 채집 데이터가 없습니다. 상단에서 파일을 업로드해 주세요.")

# =================================================================================
# 2. 말라리아 레이어
# =================================================================================
elif selected_tab == "🔵 말라리아 매개모기 감시":
    st.header(f"🪖 접경지역 말라리아 매개모기 주별 감시 현황 [{selected_year} {selected_month} {selected_week}]")
    
    c_up2, c_dl2 = st.columns([8, 4])
    with c_up2:
        mal_file = st.file_uploader("질병청 VectorNet 말라리아 결과 파일 업로드", type=["csv", "xlsx", "xls"], key="mal_up")
        if mal_file is not None:
            uploaded_df_mal = smart_load_uploaded_file(mal_file)
            uploaded_df_mal = parse_vectornet_dataframe(uploaded_df_mal, selected_year, selected_month)
            base_mal_df = merge_and_overwrite(base_mal_df, rename_duplicate_columns(uploaded_df_mal), keys=['조사년도', '조사월', '주차', '지역2', '종'])
            save_df_to_github(base_mal_df, "database_mal.csv", "Update Malaria data")
            st.success("✅ 말라리아 새 데이터 반영 완료")
            st.cache_data.clear()
            
    df_mal = base_mal_df.copy()

    if not df_mal.empty:
        df_mal = parse_vectornet_dataframe(df_mal, selected_year, selected_month)
        mal_coords_map = {
            "춘천시 중앙동": [37.8813, 127.7298], "춘천시 지내리": [37.9250, 127.7410],
            "철원군 대마리": [38.2543, 127.2145], "철원군 학사리": [38.2520, 127.4415],
            "화천군": [38.1060, 127.7035], "양구군": [38.1055, 127.9880],
            "인제군": [38.0645, 128.1611], "고성군": [38.3795, 128.4680]
        }
        
        if "주차" in df_mal.columns: df_mal["조사주"] = df_mal.apply(convert_absolute_to_monthly_week, axis=1)
        else: df_mal["조사주"] = "1주"

        if "지역2" in df_mal.columns:
            def find_mal_coords(loc_str):
                l = str(loc_str).replace(" ", "")
                if "중앙" in l: return "춘천시 중앙동", mal_coords_map["춘천시 중앙동"]
                if "지내" in l: return "춘천시 지내리", mal_coords_map["춘천시 지내리"]
                if "학사" in l: return "철원군 학사리", mal_coords_map["철원군 학사리"]
                if "대마" in l: return "철원군 대마리", mal_coords_map["철원군 대마리"]
                if "화천" in l: return "화천군", mal_coords_map["화천군"]
                if "양구" in l: return "양구군", mal_coords_map["양구군"]
                if "인제" in l: return "인제군", mal_coords_map["인제군"]
                if "고성" in l: return "고성군", mal_coords_map["고성군"]
                return str(loc_str).strip(), [38.2, 127.5]
                
            res_tuples = df_mal["지역2"].map(find_mal_coords)
            df_mal["지역2_정규화"] = [x[0] for x in res_tuples]
            df_mal["위도"] = [x[1][0] for x in res_tuples]
            df_mal["경도"] = [x[1][1] for x in res_tuples]
            df_mal["지점명"] = df_mal["지역2_정규화"].map(lambda x: f"{x} (우사 거점)")
        else: 
            df_mal["지점명"] = "알수없음 (우사 거점)"

        f_mal = df_mal[(df_mal["조사년도"] == selected_year) & (df_mal["조사월"] == selected_month)].copy()
        if selected_week != "전체":
            f_mal = f_mal[f_mal["조사주"] == selected_week]
        
        with c_dl2:
            st.markdown("<br>", unsafe_allow_html=True)
            if not f_mal.empty:
                st.download_button("📥 데이터 원본 추출", convert_df_to_csv(f_mal), "말라리아.csv", "text/csv")

        if not f_mal.empty:
            val_col_mal = "개체수" if "개체수" in f_mal.columns else "채집수"
            f_mal[val_col_mal] = pd.to_numeric(f_mal[val_col_mal], errors='coerce').fillna(0)
            
            mal_spots_list = list(mal_coords_map.keys())
            mal_sub_tabs = st.tabs(["📍 지점전체"] + [f"📍 {spot.split(' (')[0]}" for spot in mal_spots_list])
            
            with mal_sub_tabs[0]:
                c1, c2 = st.columns([5, 5])
                with c1:
                    st.markdown("##### 🗺️ GIS 말라리아 거점 지도")
                    m_mal_all = folium.Map(location=[38.15, 127.8], zoom_start=9)
                    for target_mal_name, coords in mal_coords_map.items():
                        folium.Marker([coords[0], coords[1]], tooltip=f"{target_mal_name}", icon=folium.Icon(color='blue', icon='flag')).add_to(m_mal_all)
                    st_folium(m_mal_all, key="map_mal_all", width="100%", height=380)
                
                # 💡 말라리아 매개모기(Anopheles/얼룩날개) 핀셋 필터링 적용 (복구 완료)
                with c2:
                    st.markdown("##### 📊 지점별 모기 종별 채집량 (전체)")
                    species_col_mal = "종" if "종" in f_mal.columns else None
                    if species_col_mal:
                        mal_species_series = f_mal[species_col_mal].astype(str).str.strip()
                        mask_mal = mal_species_series.str.contains(
                            r"\bAnopheles\b|anopheles|얼룩날개",
                            case=False,
                            regex=True,
                            na=False,
                        )
                    else:
                        mask_mal = pd.Series(False, index=f_mal.index)
                    
                    f_mal_filtered = f_mal[mask_mal].copy()
                    
                    if not f_mal_filtered.empty and f_mal_filtered[val_col_mal].sum() > 0:
                        pivot_df = f_mal_filtered.pivot_table(index='지역2_정규화', columns='종', values=val_col_mal, aggfunc='sum').fillna(0)
                        pivot_df = pivot_df.reindex(mal_spots_list, fill_value=0)
                        
                        fig, ax1 = plt.subplots(figsize=(6, 5.2))
                        cmap = plt.get_cmap('Pastel2')
                        bar_colors = ['#1d3557' if 'anopheles' in str(c).lower() or '얼룩날개' in str(c) else cmap(i%8) for i, c in enumerate(pivot_df.columns)]
                        pivot_df.plot(kind='bar', stacked=True, ax=ax1, color=bar_colors, edgecolor='#2b2d42')
                        ax1.set_ylabel('총 개체수')
                        
                        for container in ax1.containers:
                            labels = [f'{int(v.get_height())}' if v.get_height() > 0 else '' for v in container]
                            ax1.bar_label(container, labels=labels, label_type='center', fontsize=8, fontweight='bold', color='white')
                            
                        plt.xticks(rotation=45, ha='right')
                        plt.legend(title="말라리아 매개모기(얼룩날개모기류)", bbox_to_anchor=(1.05, 1), loc='upper left')
                        st.pyplot(fig)
                        plt.close()
                    else:
                        st.markdown(f"<div style='text-align: center; padding: 120px 0; color: #888; font-size: 1.1em; font-weight: bold;'>해당 주차({selected_week}) 전체 지점 채집량 0마리<br>🚫 얼룩날개모기류 미검출</div>", unsafe_allow_html=True)

            for idx, spot_name in enumerate(mal_spots_list):
                with mal_sub_tabs[idx + 1]:
                    spot_data = f_mal[f_mal["지역2_정규화"] == spot_name].copy()
                    
                    c1, c2 = st.columns([5, 5])
                    with c1:
                        st.markdown(f"##### 🗺️ {spot_name} 거점 지도")
                        m_spot = folium.Map(location=mal_coords_map.get(spot_name, [38.2, 127.5]), zoom_start=11)
                        folium.Marker(mal_coords_map.get(spot_name, [38.2, 127.5]), tooltip=spot_name, icon=folium.Icon(color='purple', icon='star')).add_to(m_spot)
                        st_folium(m_spot, key=f"map_mal_spot_{idx}", width="100%", height=380)
                    with c2:
                        st.markdown(f"##### 📊 {spot_name} 모기 종별 전체 채집량")
                        if not spot_data.empty and spot_data[val_col_mal].sum() > 0:
                            sum_df = spot_data.groupby("종")[val_col_mal].sum().reset_index().sort_values(by=val_col_mal)
                            fig, plt_ax = plt.subplots(figsize=(6, 5.2))
                            
                            colors = ['#ef233c' if 'anopheles' in str(s).lower() or '얼룩날개' in str(s) else '#c4cbde' for s in sum_df["종"]]
                            bars = plt_ax.barh(sum_df["종"], sum_df[val_col_mal], color=colors, edgecolor='#2b2d42')
                            
                            for bar in bars:
                                h = bar.get_width()
                                plt_ax.text(h + 0.5, bar.get_y() + bar.get_height()/2, f'{int(h)}', ha='left', va='center', 
                                            fontsize=9, fontweight='bold', color='red' if h > 0 and 'anopheles' in str(bar.get_label()).lower() else 'black')
                            
                            plt_ax.set_xlabel('개체수 (마리)')
                            st.pyplot(fig)
                            plt.close()
                        else:
                            st.markdown(f"<div style='text-align: center; padding: 120px 0; color: #888; font-size: 1.1em; font-weight: bold;'>해당 주차({selected_week}) 채집량 0마리</div>", unsafe_allow_html=True)
                            
                    if not spot_data.empty and spot_data[val_col_mal].sum() > 0:
                        st.dataframe(spot_data.drop(columns=["위도", "경도"], errors='ignore'), hide_index=True, use_container_width=True)
        else:
            st.warning(f"⚠️ 선택하신 [{selected_year} {selected_month} {selected_week}] 조건에 해당하는 채집 데이터가 없습니다.")

# =================================================================================
# 3. 기후변화 대응 매개체 감시 레이어
# =================================================================================
elif selected_tab == "🟢 기후변화 대응 매개체 감시":
    st.header(f"🌍 기후변화 대응 감염병 매개체 감시 현황 [{selected_year} {selected_month} 월간 통합 결과]")
    selected_zone = st.radio("📡 모니터링 매개체 권역 선택", ["모기 권역", "참진드기 권역", "털진드기 분포감시", "털진드기 발생감시"], horizontal=True)
    
    c_up3, c_dl3 = st.columns([8, 4])
    with c_up3:
        cli_file = st.file_uploader(f"질병청 VectorNet [{selected_zone}] 결과 파일 업로드", type=["csv", "xlsx", "xls"], key=f"cli_up_{selected_zone}")
        if cli_file is not None:
            uploaded_df_cli = smart_load_uploaded_file(cli_file)
            uploaded_df_cli = parse_vectornet_dataframe(uploaded_df_cli, selected_year, selected_month)
            
            if selected_zone == "모기 권역":
                base_cli_moq_df = merge_and_overwrite(base_cli_moq_df, rename_duplicate_columns(uploaded_df_cli), keys=['조사년도', '조사월', '주차', '지역2', '종'])
                save_df_to_github(base_cli_moq_df, "database_cli_moq.csv", "Update Climate Mosquito")
            elif selected_zone == "참진드기 권역":
                base_cli_tick_df = merge_and_overwrite(base_cli_tick_df, rename_duplicate_columns(uploaded_df_cli), keys=['조사년도', '조사월', '주차', '지역2', '환경', '종'])
                save_df_to_github(base_cli_tick_df, "database_cli_tick.csv", "Update Climate Tick")
            elif selected_zone == "털진드기 분포감시":
                base_cli_mite_dist_df = merge_and_overwrite(base_cli_mite_dist_df, rename_duplicate_columns(uploaded_df_cli), keys=['조사년도', '조사월', '주차', '지역2', '환경', '종'])
                save_df_to_github(base_cli_mite_dist_df, "database_cli_mite_dist.csv", "Update Mite Dist")
            else:
                base_cli_mite_gen_df = merge_and_overwrite(base_cli_mite_gen_df, rename_duplicate_columns(uploaded_df_cli), keys=['조사년도', '조사월', '주차', '지역2', '환경', '종'])
                save_df_to_github(base_cli_mite_gen_df, "database_cli_mite_gen.csv", "Update Mite Gen")
                
            st.success(f"✅ {selected_zone} 새 데이터 반영 완료")
            st.cache_data.clear()

    if selected_zone == "모기 권역":
        df_zone = base_cli_moq_df.copy()
    elif selected_zone == "참진드기 권역":
        df_zone = base_cli_tick_df.copy()
    elif selected_zone == "털진드기 분포감시":
        df_zone = base_cli_mite_dist_df.copy()
    else:
        df_zone = base_cli_mite_gen_df.copy()
    
    if df_zone is not None and not df_zone.empty:
        try:
            df_zone = parse_vectornet_dataframe(df_zone, selected_year, selected_month)
        except Exception:
            pass
            
        m_data = df_zone[(df_zone["조사년도"] == selected_year) & (df_zone["조사월"] == selected_month)].copy()
        val_col = "개체수" if "개체수" in m_data.columns else ("채집수" if "채집수" in m_data.columns else "개체수")
        if val_col in m_data.columns:
            m_data[val_col] = pd.to_numeric(m_data[val_col], errors='coerce').fillna(0)

        if selected_zone == "모기 권역":
            master_spots_list = ["춘천시보건소", "퇴계동", "삼천동", "종가오리", "주택", "백로서식지", "일일감시(보건소)"]
            loc_col = "지역2"
            for col_name in ["지역2", "시군구", "채집지역", "지역"]:
                if col_name in m_data.columns:
                    loc_col = col_name
                    break
        elif selected_zone == "참진드기 권역":
            master_spots_list = ["화천 초지", "화천 잡목림", "화천 산길", "화천 무덤", "인제 초지", "인제 잡목림", "인제 산길", "인제 무덤"]
            loc_col = "지역2"
        elif selected_zone == "털진드기 분포감시":
            master_spots_list = ["논", "밭", "저수지", "수로", "야산"]
            loc_col = "환경" if "환경" in m_data.columns else "지역2"
        else: 
            master_spots_list = ["논", "밭", "수로", "초지"]
            loc_col = "환경" if "환경" in m_data.columns else "지역2"

        if selected_zone == "참진드기 권역" and "환경" in m_data.columns and loc_col in m_data.columns:
            def clean_region(val):
                s = str(val)
                if "화천" in s: return "화천"
                if "인제" in s: return "인제"
                return s.strip()
            def clean_env(val):
                s = str(val).replace(" ", "").strip() 
                if "잡목" in s or "관목" in s: return "잡목림"
                if "초지" in s or "풀밭" in s: return "초지"
                if "산길" in s: return "산길"
                if "무덤" in s or "묘지" in s: return "무덤"
                return s
            m_data["정규화_지역"] = m_data[loc_col].apply(clean_region)
            m_data["정규화_환경"] = m_data["환경"].apply(clean_env)
            m_data["복합_지점"] = m_data["정규화_지역"] + " " + m_data["정규화_환경"]
            loc_col = "복합_지점"

        display_spots = master_spots_list
        cli_sub_tabs = st.tabs(["📍 지점전체"] + [f"📍 {spot}" for spot in display_spots])
        
        zone_coords_map = {
            "춘천시보건소": [37.8813, 127.7298], "퇴계동": [37.8615, 127.7295], "삼천동": [37.8700, 127.7000],
            "종가오리": [37.9300, 127.7200], "주택": [37.8800, 127.7300], "백로서식지": [37.9000, 127.7500], 
            "일일감시(보건소)": [37.8813, 127.7298], "논": [37.8920, 127.7400], "밭": [37.8540, 127.7600], "저수지": [37.8300, 127.6800],
            "수로": [37.9100, 127.7100], "야산": [37.8200, 127.7800], "초지": [37.8600, 127.7900],
            "화천 초지": [38.1060, 127.7035], "화천 잡목림": [38.1150, 127.7200], "화천 산길": [38.1250, 127.6900], "화천 무덤": [38.0950, 127.7100],
            "인제 초지": [38.0694, 128.1701], "인제 잡목림": [38.0800, 128.1900], "인제 산길": [38.0550, 128.1500], "인제 무덤": [38.0750, 128.1400]
        }
        
        with cli_sub_tabs[0]:
            c1, c2 = st.columns([5, 5])
            with c1: 
                st.markdown(f"##### 🗺️ {selected_zone} 감시 지점 지도")
                m_zone = folium.Map(location=[38.0, 127.9], zoom_start=9)
                marker_color = 'orange' if '털진드기' in selected_zone else ('green' if '참진드기' in selected_zone else 'blue')
                spot_totals = {s: 0 for s in master_spots_list}
                if not m_data.empty and loc_col in m_data.columns:
                    for _, row in m_data.iterrows():
                        loc_val = str(row[loc_col]).strip()
                        for s in master_spots_list:
                            if s in loc_val:
                                spot_totals[s] += row.get(val_col, 0)

                for spot in display_spots:
                    coords = zone_coords_map.get(spot, [38.0, 127.9])
                    total_cnt = spot_totals.get(spot, 0)
                    folium.Marker(coords, tooltip=f"{spot} (총 {int(total_cnt)}마리)", icon=folium.Icon(color=marker_color, icon='info-sign')).add_to(m_zone)
                st_folium(m_zone, key=f"map_{selected_zone}_main", width="100%", height=380)
                
            with c2:
                st.markdown("##### 📊 지점별 통합 채집량")
                if not m_data.empty and "종" in m_data.columns and loc_col in m_data.columns:
                    def get_norm_spot(x):
                        for s in master_spots_list:
                            if s in str(x): return s
                        return "기타지점"
                    m_data["정규화_지점"] = m_data[loc_col].apply(get_norm_spot)
                    all_spot_clean = m_data[(m_data["종"] != "미채집") & (~m_data["종"].str.contains("미채집", na=False)) & (m_data[val_col] > 0)].copy()
                    
                    if not all_spot_clean.empty:
                        all_spot_clean["종"] = all_spot_clean["종"].astype(str).apply(lambda x: "Larva" if "기타" in x else x.strip())
                        pivot_df = all_spot_clean.pivot_table(index='정규화_지점', columns='종', values=val_col, aggfunc='sum').fillna(0)
                        pivot_df = pivot_df.reindex(master_spots_list, fill_value=0)
                        
                        fig, ax1 = plt.subplots(figsize=(6, 5.2))
                        pivot_df.plot(kind='bar', stacked=True, ax=ax1, edgecolor='#2b2d42')
                        ax1.set_ylabel('총 개체수')
                        
                        for container in ax1.containers:
                            labels = [f'{int(v.get_height())}' if v.get_height() > 0 else '' for v in container]
                            ax1.bar_label(container, labels=labels, label_type='center', fontsize=8, fontweight='bold')
                            
                        plt.xticks(rotation=45, ha='right')
                        st.pyplot(fig)
                        plt.close()
                    else:
                        st.markdown(f"<div style='text-align: center; padding: 120px 0; color: #888; font-size: 1.1em; font-weight: bold;'>해당 월({selected_month}) 전체 지점 채집량 0마리<br>🚫 매개체 미검출</div>", unsafe_allow_html=True)
                else:
                    st.info(f"📊 선택한 달({selected_month})의 데이터가 존재하지 않습니다.")
                    
        for idx, spot_name in enumerate(display_spots):
            with cli_sub_tabs[idx + 1]:
                if not m_data.empty and loc_col in m_data.columns:
                    spot_data = m_data[m_data[loc_col].astype(str).str.contains(spot_name, na=False)].copy()
                    if not spot_data.empty and spot_data[val_col].sum() > 0:
                        drop_cols = ["위도", "경도", "정규화_지점", "정규화_지역", "정규화_환경", "복합_지점"]
                        available_drop_cols = [c for c in drop_cols if c in spot_data.columns]
                        spot_data["종"] = spot_data["종"].astype(str).apply(lambda x: "Larva" if "기타" in x else x.strip())
                        st.dataframe(spot_data.drop(columns=available_drop_cols), hide_index=True, use_container_width=True)
                    else:
                        st.info(f"💡 {selected_year} {selected_month}에 {spot_name} 구역에서 채집된 데이터가 0마리입니다.")
                else:
                    st.info("데이터가 없습니다.")
    else:
        st.warning(f"⚠️ {selected_zone} 데이터베이스에 업로드된 자료가 없습니다.")

# =================================================================================
# 4. 참진드기조사 어린이숲체험장 레이어
# =================================================================================
elif selected_tab == "🟡 참진드기조사(어린이숲체험장)":
    st.header(f"🌳 어린이 숲 체험장 참진드기 자체조사 현황 [{selected_year} {selected_month}]")
    
    c_up4, c_dl4 = st.columns([8, 4])
    with c_up4:
        forest_file = st.file_uploader("어린이 숲 체험장 참진드기 결과 파일 업로드 (질병조사과 자체서식)", type=["csv", "xlsx", "xls"], key="forest_up")
        if forest_file is not None:
            uploaded_df_forest = smart_load_uploaded_file(forest_file)
            base_forest_df = merge_and_overwrite(base_forest_df, rename_duplicate_columns(uploaded_df_forest), keys=['조사년도', '월', '조사주', '채집지역2', '지점번호', '종'])
            save_df_to_github(base_forest_df, "database_forest.csv", "Update Forest Tick")
            st.success("✅ 어린이숲 참진드기 새 데이터 반영 완료")
            st.cache_data.clear()

    df_forest = base_forest_df.copy()

    try:
        month_int = int(str(selected_month).replace("월",""))
        m_forest = df_forest[(df_forest["조사년도"] == selected_year) & (df_forest["월"] == month_int)].copy()
        
        if "2025" in selected_year: valid_regions = ["홍천", "정선"]
        elif "2024" in selected_year: valid_regions = ["춘천", "인제"]
        elif "2023" in selected_year: valid_regions = ["속초", "양양", "인제"]
        else: valid_regions = ["남산", "삼마치"]
            
        m_forest = m_forest[m_forest['채집지역2'].isin(valid_regions)]
    except Exception:
        m_forest = pd.DataFrame()

    if not m_forest.empty:
        m_forest['종'] = m_forest['종'].astype(str).apply(lambda x: "Larva" if "기타" in x else x.strip())
        m_forest['종명_한글'] = m_forest['종'].replace({
            "Hard tick": "참진드기", 
            "Haemaphysalis longicornis": "작은소피참진드기", 
            "Haemaphysalis flava ": "개피참진드기", 
            "Haemaphysalis japonica": "일본참진드기"
        })
        
        def get_italic_eng_name(val):
            v = str(val).strip()
            italic_map = {
                "Hard tick": r"$\mathit{Hard\ tick}$", "Haemaphysalis longicornis": r"$\mathit{Haemaphysalis\ longicornis}$",
                "Haemaphysalis flava": r"$\mathit{Haemaphysalis\ flava}$", "Haemaphysalis japonica": r"$\mathit{Haemaphysalis\ japonica}$",
                "Ixodes nipponensis": r"$\mathit{Ixodes\ nipponensis}$", "참진드기": r"$\mathit{Hard\ tick}$",
                "작은소피참진드기": r"$\mathit{Haemaphysalis\ longicornis}$", "개피참진드기": r"$\mathit{Haemaphysalis\ flava}$",
                "일본참진드기": r"$\mathit{Haemaphysalis\ japonica}$"
            }
            if v in italic_map:
                return italic_map[v]
            return f"$\\mathit{{{v.replace(' ', r'\ ')}}}$"
            
        m_forest['종명_그래프_이탤릭'] = m_forest['종'].apply(get_italic_eng_name)
        
        def parse_management_zone(row):
            env = str(row.get('환경', '')).strip().upper()
            cls = str(row.get('분류', '')).strip().upper()
            point_raw = row.get('지점번호', row.get('지점', row.get('채집지점', '')))
            point_str = str(point_raw).replace(".0", "").strip()
            combined = env + " " + cls + " " + point_str
            is_managed = "비관리지역" if ("비관리" in combined or "OUT" in combined) else "관리지역"
            num = "1"
            if "3" in combined: num = "3"
            elif "2" in combined: num = "2"
            elif "1" in combined: num = "1"
            return f"{is_managed}{num}"
            
        m_forest["sebu"] = m_forest.apply(parse_management_zone, axis=1)
        m_forest["지점_세부구역"] = m_forest["채집지역2"] + " " + m_forest["sebu"]
        
        val_col = "개체수" if "개체수" in m_forest.columns else "채집수"
        m_forest[val_col] = pd.to_numeric(m_forest[val_col], errors='coerce').fillna(0)
        all_spot_clean = m_forest[(m_forest["종"] != "미채집") & (~m_forest["종"].str.contains("미채집", na=False)) & (m_forest[val_col] > 0)]
        
        col_f_map, col_f_graph = st.columns([5, 5])
        
        with col_f_map:
            st.markdown("##### 🗺️ 구역별 채집 지점 지도")
            m_forest_map = folium.Map(location=[37.85, 128.2], zoom_start=8)
            forest_coords_map = {
                "홍천": [37.6970, 127.8886], "정선": [37.3801, 128.6608], "춘천": [37.8813, 127.7298], "인제": [38.0694, 128.1701],
                "속초": [38.2070, 128.5918], "양양": [38.0754, 128.6189], "남산": [37.7170, 127.6400], "삼마치": [37.6480, 127.9150]
            }
            region_summary = m_forest.groupby("채집지역2")[val_col].sum().reset_index()
            for index, row in region_summary.iterrows():
                region = row["채집지역2"]
                total_count = row[val_col]
                if region in forest_coords_map:
                    folium.Marker(forest_coords_map[region], tooltip=f"{region} 숲체험장 (총 {int(total_count)}마리)", icon=folium.Icon(color='green', icon='tree')).add_to(m_forest_map)
            st_folium(m_forest_map, key="map_forest", width="100%", height=380)
            
            st.markdown("##### 📝 채집 상세 내역")
            display_df = m_forest[["채집지역2", "sebu", "종명_한글", val_col]].groupby(["채집지역2", "sebu", "종명_한글"]).sum().reset_index()
            display_df = display_df[display_df[val_col] > 0]
            st.dataframe(display_df, hide_index=True, use_container_width=True)
            
        with col_f_graph:
            st.markdown(f"##### 📊 {selected_year} {selected_month} 세부 지점별 참진드기 채집량")
            if not all_spot_clean.empty:
                forest_pivot = all_spot_clean.pivot_table(index="지점_세부구역", columns="종명_그래프_이탤릭", values=val_col, aggfunc="sum", fill_value=0)
                active_regions = sorted(all_spot_clean["채집지역2"].unique())
                expected_zones = ["관리지역1", "관리지역2", "관리지역3", "비관리지역1", "비관리지역2", "비관리지역3"]
                full_index = [f"{r} {z}" for r in active_regions for z in expected_zones]
                forest_pivot = forest_pivot.reindex(full_index, fill_value=0)
                
                fig, ax1 = plt.subplots(figsize=(7, 5.2))
                forest_pivot.plot(kind='bar', stacked=True, ax=ax1, edgecolor='#2b2d42', width=0.7)
                for container in ax1.containers:
                    labels = [f'{int(v.get_height())}' if v.get_height() > 0 else '' for v in container]
                    ax1.bar_label(container, labels=labels, label_type='center', fontsize=9, color='white', fontweight='bold')
                
                ax1.set_ylabel('채집 개체수 (마리)', fontweight='bold')
                ax1.set_xlabel('')
                plt.xticks(rotation=45, ha='right')
                plt.legend(title="Tick Species", bbox_to_anchor=(1.05, 1), loc='upper left')
                plt.tight_layout()
                st.pyplot(fig)
                plt.close()
            else:
                st.info("해당 연도/월에 채집된 진드기 데이터가 없습니다 (모두 미채집).")
    else:
        st.info("해당 연도/월에 어린이 숲 체험장 조사 데이터가 없습니다.")

# =================================================================================
# 5. ☁️ 기상 상관분석 레이어 
# =================================================================================
elif selected_tab == "☁️ 기상 요인 상관분석":
    st.header(f"☁️ 기후 요인 및 매개체 발생 상관분석")
    
    col_c1, col_c2, col_c3, col_c4 = st.columns([2, 3, 3, 3])
    with col_c1:
        years_list = ["2026년", "2025년", "2024년", "2023년", "2022년", "2021년", "2020년"]
        analysis_year = st.selectbox("분석 연도", years_list, index=years_list.index(selected_year))
    with col_c2:
        target_disease = st.selectbox("분석 대상 감시망", [
            "일본뇌염 매개모기 (Culex tritaeniorhynchus)", 
            "말라리아 매개모기 (Anopheles spp.)",
            "기후변화 모기 권역",
            "기후변화 참진드기 권역",
            "털진드기 발생감시",
            "어린이숲 체험장 참진드기"
        ])
    with col_c3:
        if "기후변화 참진드기" in target_disease:
            spots_list = ["화천군", "인제군"]
        elif "일본뇌염" in target_disease:
            spots_list = ["춘천시 산천리", "강릉시 산대월리", "횡성군 하대리"]
        elif "말라리아" in target_disease:
            spots_list = ["춘천시 중앙동", "춘천시 지내리", "철원군 대마리", "철원군 학사리", "화천군", "양구군", "인제군", "고성군"]
        elif "기후변화 모기" in target_disease:
            spots_list = ["춘천시보건소", "퇴계동", "삼천동", "종가오리", "주택", "백로서식지", "일일감시(보건소)"]
        elif "털진드기 발생" in target_disease:
            spots_list = ["철원군"]
        elif "어린이숲" in target_disease:
            if "2025" in analysis_year: spots_list = ["홍천", "정선"]
            elif "2024" in analysis_year: spots_list = ["춘천", "인제"]
            elif "2023" in analysis_year: spots_list = ["속초", "양양", "인제"]
            else: spots_list = ["남산", "삼마치"]
        else:
            spots_list = ["전체"]
            
        selected_spot = st.selectbox("조사지점 선택", spots_list)
    with col_c4:
        period_label = "7일" if "참진드기" in target_disease else "14일"
        climate_factors = st.multiselect(
            f"비교할 기후 인자 (채집일 과거 {period_label} 누적/평균)", 
            ["평균기온(°C)", "누적강수량(mm)", "평균습도(%)", "평균풍속(m/s)"], 
            default=["평균기온(°C)", "누적강수량(mm)", "평균습도(%)", "평균풍속(m/s)"]
        )
        
    st.markdown("---")

    df_target = pd.DataFrame()
    species_keyword = ""
    target_name_kr = ""
    
    is_tick_mode = ("참진드기" in target_disease)
    is_mite_gen_mode = ("털진드기 발생" in target_disease)
    is_weekly_mode = ("일본뇌염" in target_disease) or ("말라리아" in target_disease) or ("기후변화 모기" in target_disease) or is_mite_gen_mode

    # -------------------------------------------------------------------------
    # 1. 분석 대상 및 타겟 키워드 설정 (말라리아, 일본뇌염 정밀 필터링 키워드)
    # -------------------------------------------------------------------------
   if "일본뇌염" in target_disease and not f_target.empty:
            # 종 이름에서 공백을 전부 없애고 '작은빨간집모기' 또는 'tritaeniorhynchus'가 포함된 행만 강제 지정
            f_target = f_target[
                f_target[species_col].astype(str).str.replace(" ", "").str.contains('작은빨간집모기|tritaeniorhynchus', case=False, na=False)]
    elif "말라리아" in target_disease:
        df_target = base_mal_df.copy()
        # 💡 오직 얼룩날개모기류(Anopheles)만 잡는 정규식
        species_keyword = r"\bAnopheles\b|anopheles|얼룩날개"
        target_name_kr = "말라리아 매개모기(얼룩날개모기류)"
    elif "기후변화 모기" in target_disease:
        df_target = base_cli_moq_df.copy()
        target_name_kr = "기후변화 모기 통합"
    elif "기후변화 참진드기" in target_disease:
        df_target = base_cli_tick_df.copy()
        target_name_kr = "참진드기 통합"
    elif "털진드기 발생" in target_disease:
        df_target = base_cli_gen_df.copy() if "base_cli_gen_df" in locals() else base_cli_mite_gen_df.copy()
        target_name_kr = "털진드기 통합"
    elif "어린이숲" in target_disease:
        df_target = base_forest_df.copy()
        target_name_kr = "어린이숲 참진드기 통합"

    if not df_target.empty:
        year_str_val = str(analysis_year).replace("년", "").strip()
        year_col = "조사년도" if "조사년도" in df_target.columns else ("연도" if "연도" in df_target.columns else "년도")
        if year_col in df_target.columns:
            f_target = df_target[df_target[year_col].astype(str).str.contains(year_str_val, na=False)].copy()
        else:
            f_target = df_target.copy()
        
        def extract_month_safe(row):
            for col in ["조사월", "월", "채집월", "월별"]:
                if col in row.index and pd.notna(row[col]):
                    val = str(row[col]).replace("월", "").strip()
                    if val.replace(".", "").isdigit(): return f"{int(float(val)):02d}월"
            return ""
        def extract_day_safe(row):
            date_cols = ['수거일', '채집일', '조사일', '일', '조사일자', '채집일자', '채집일시']
            for col in date_cols:
                if col in row.index and pd.notna(row[col]):
                    try: return f"{pd.to_datetime(row[col]).day:02d}일"
                    except: pass
            return "15일"
            
        f_target["정규화_월"] = f_target.apply(extract_month_safe, axis=1)
        f_target["정규화_일"] = f_target.apply(extract_day_safe, axis=1)

        if is_weekly_mode:
            f_target["정규화_주차"] = f_target.apply(convert_absolute_to_monthly_week, axis=1)

        start_month = 8 if is_mite_gen_mode else 3  
        end_month = 12 if is_mite_gen_mode else (11 if "어린이숲" in target_disease else 10) 
        
        now_date = datetime.datetime.now()
        now_year = str(now_date.year)
        
        if now_year in analysis_year:
            target_end_month = now_date.month
            if target_end_month > (12 if is_mite_gen_mode else (11 if "어린이숲" in target_disease else 10)):
                target_end_month = (12 if is_mite_gen_mode else (11 if "어린이숲" in target_disease else 10))
            end_month = max(start_month, target_end_month)

            if is_weekly_mode:
                max_w_in_data = 4
                if now_date.month == end_month:
                    current_week = (now_date.day - 1) // 7 + 1
                    max_w_in_data = min(current_week, 4)
        else:
            max_w_in_data = 4

        # -------------------------------------------------------------------------
        # 2. 초강력 정밀 필터링 (합계 행 제거 & 특정 '종' 열에서만 핀셋 추출)
        # -------------------------------------------------------------------------
        # 1) 전체 데이터 중 '합계', '총계' 등의 글자가 들어간 뻥튀기 방지 행 삭제
        exclude_mask = f_target.astype(str).apply(lambda x: x.str.contains('합계|총계|누계', na=False, regex=True)).any(axis=1)
        f_target = f_target[~exclude_mask]

        # 2) 지점 마스킹
        loc_cols_cands = ["지역2", "지역", "지점", "지점명", "채집장소", "시군구", "채집지역2"]
        found_loc_col = next((c for c in f_target.columns if c in loc_cols_cands), None)
        
        if found_loc_col:
            if "일본뇌염" in target_disease:
                if "산천" in selected_spot: kw = "산천"
                elif "산대" in selected_spot: kw = "산대"
                elif "하대" in selected_spot: kw = "하대"
                else: kw = selected_spot
                spot_mask = f_target[found_loc_col].astype(str).str.contains(kw, na=False)
                
            elif "말라리아" in target_disease:
                if "중앙" in selected_spot: kw = "중앙"
                elif "지내" in selected_spot: kw = "지내"
                elif "학사" in selected_spot: kw = "학사"
                elif "대마" in selected_spot: kw = "대마"
                elif "화천" in selected_spot: kw = "화천"
                elif "양구" in selected_spot: kw = "양구"
                elif "인제" in selected_spot: kw = "인제"
                elif "고성" in selected_spot: kw = "고성"
                else: kw = selected_spot
                spot_mask = f_target[found_loc_col].astype(str).str.contains(kw, na=False)
                
            else:
                kw = selected_spot.replace("군","").replace("시","") if ("참진드기" in target_disease or "털진드기" in target_disease) else selected_spot
                spot_mask = f_target[found_loc_col].astype(str).str.contains(kw, na=False)
        else:
            spot_mask = pd.Series([True]*len(f_target))

        # 3) 💡 [핵심] 오직 '종' 관련 열에서만 핀셋 필터링 검사 수행
        if species_keyword:
            species_col = "종" if "종" in f_target.columns else None
            if not species_col:
                fallback_cols = ["학명", "모기종", "종명", "매개체명", "종류"]
                species_col = next((c for c in f_target.columns if c in fallback_cols), None)

            if species_col:
                species_mask = f_target[species_col].astype(str).str.strip().str.contains(
                    species_keyword, case=False, regex=True, na=False
                )
            else:
                species_mask = pd.Series(False, index=f_target.index)
        else:
            species_mask = pd.Series([True]*len(f_target))
            
        no_empty_mask = ~f_target.astype(str).apply(lambda x: x.str.contains("미채집", na=False, regex=False)).any(axis=1)
            
        # 모든 마스크 적용하여 최종 타겟 데이터 확정
        f_target = f_target[spot_mask & species_mask & no_empty_mask]
        
        # -------------------------------------------------------------------------
        # 3. 개체수 쉼표 제거 및 주차별 합산 (Grouping)
        # -------------------------------------------------------------------------
        val_col_target = "개체수" if "개체수" in f_target.columns else ("채집수" if "채집수" in f_target.columns else "개체수")
        
        # 쉼표 있는 숫자도 완벽하게 카운팅하도록 방어
        f_target[val_col_target] = pd.to_numeric(f_target[val_col_target].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
        valid_months = range(start_month, end_month + 1)
        periods_list = []
        if is_tick_mode:
            month_to_day = {}
            for _, row in f_target.iterrows():
                m = row["정규화_월"]
                if m and m not in month_to_day:
                    month_to_day[m] = row["정규화_일"]
            for m in valid_months:
                m_str = f"{m:02d}월"
                d_str = month_to_day.get(m_str, "15일")
                periods_list.append(f"{m_str}\n{d_str}")
                
        elif is_weekly_mode:
            for m in valid_months:
                for w in range(1, 5):
                    if now_year in analysis_year and m == end_month and w > max_w_in_data:
                        continue
                    periods_list.append(f"{m:02d}월\n{w}주")
        else:
            for m in valid_months: 
                periods_list.append(f"{m:02d}월")
            
        period_counts = {p: 0 for p in periods_list}
        
        for _, row in f_target.iterrows():
            m_str = row["정규화_월"]
            if not m_str: continue
            
            if is_tick_mode:
                d_str = row["정규화_일"]
                p_key = f"{m_str}\n{d_str}"
            elif is_weekly_mode:
                w_str = row.get("정규화_주차", "1주")
                p_key = f"{m_str}\n{w_str}"
            else:
                p_key = m_str
                
            # 타겟 모기 마리수 합산
            if p_key in period_counts: 
                period_counts[p_key] += row.get(val_col_target, 0)
                
        plot_df = pd.DataFrame(list(period_counts.items()), columns=["기간", "채집량(마리)"])
        
        window_days = 7 if is_tick_mode else (14 if is_weekly_mode else 14)
        
        with st.spinner(f"📡 {analysis_year} {selected_spot} 일별 기상 데이터를 불러와 {window_days}일 역산 누적 중입니다..."):
            kma_spot = selected_spot.replace("군","").replace("시","").split()[0]
            df_w_daily = get_kma_weather_daily(analysis_year, kma_spot)
            
            temps, precips, humids, winds = [], [], [], []
            y_int = int(analysis_year.replace("년", ""))
            
            for p in plot_df["기간"]:
                if is_tick_mode:
                    m_int = int(p.split("월")[0])
                    d_str = p.split("\n")[1].replace("일", "")
                    d_int = int(d_str) if d_str.isdigit() else 15
                elif is_weekly_mode:
                    m_int = int(p.split("월")[0])
                    w_str = p.split("\n")[1]
                    d_int = {"1주": 7, "2주": 14, "3주": 21, "4주": 28}.get(w_str, 28)
                else:
                    m_int = int(p.replace("월", ""))
                    d_int = calendar.monthrange(y_int, m_int)[1] 
                
                try:
                    target_date = pd.to_datetime(f"{y_int}-{m_int:02d}-{d_int:02d}")
                    start_date = target_date - pd.Timedelta(days=window_days)
                    
                    if not df_w_daily.empty:
                        mask = (df_w_daily['tm'] > start_date) & (df_w_daily['tm'] <= target_date)
                        period_w = df_w_daily[mask]
                        if not period_w.empty:
                            temps.append(period_w['avgTa'].mean())
                            precips.append(period_w['sumRn'].sum())
                            humids.append(period_w['avgRhm'].mean())
                            winds.append(period_w['avgWs'].mean())
                        else:
                            temps.append(0.0); precips.append(0.0); humids.append(0.0); winds.append(0.0)
                    else:
                        temps.append(0.0); precips.append(0.0); humids.append(0.0); winds.append(0.0)
                except Exception:
                    temps.append(0.0); precips.append(0.0); humids.append(0.0); winds.append(0.0)
                    
            plot_df["평균기온(°C)"] = [round(x, 1) for x in temps]
            plot_df["누적강수량(mm)"] = [round(x, 1) for x in precips]
            plot_df["평균습도(%)"] = [round(x, 1) for x in humids]
            plot_df["평균풍속(m/s)"] = [round(x, 1) for x in winds]
        
        sum_text = " (세부 환경 전체 합산)" if is_tick_mode or is_mite_gen_mode else ""
        
        if is_mite_gen_mode:
            st.markdown(f"##### 📊 {selected_spot} {target_name_kr}{sum_text} 계절적 변화 ({analysis_year} 8~12월)")
        else:
            st.markdown(f"##### 📊 {selected_spot} {target_name_kr}{sum_text} 계절적 변화 및 {window_days}일전 기상 영향 ({analysis_year})")
        
        fig, ax1 = plt.subplots(figsize=(14 if is_weekly_mode else 12, 5.5))
        
        bars = ax1.bar(plot_df["기간"], plot_df["채집량(마리)"], color='#2b2d42', label=f'{target_name_kr} 채집량', alpha=0.85, width=0.5)
        ax1.set_ylabel('총 채집량 합산 (마리)', color='#2b2d42', fontweight='bold')
        ax1.tick_params(axis='y', labelcolor='#2b2d42')
        max_count = plot_df["채집량(마리)"].max()
        ax1.set_ylim(0, max_count * 1.2 if max_count > 0 else 10)
        
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax1.text(bar.get_x() + bar.get_width()/2., height, f'{int(height)}', ha='center', va='bottom', fontsize=9)
        
        if climate_factors:
            ax2 = ax1.twinx()
            colors = {"평균기온(°C)": "#e63946", "누적강수량(mm)": "#457b9d", "평균습도(%)": "#2a9d8f", "평균풍속(m/s)": "#f4a261"}
            markers = {"평균기온(°C)": "o", "누적강수량(mm)": "s", "평균습도(%)": "^", "평균풍속(m/s)": "D"}
            offsets = {"평균기온(°C)": (0, 10), "누적강수량(mm)": (0, -15), "평균습도(%)": (0, 18), "평균풍속(m/s)": (12, 0)}
            
            for factor in climate_factors:
                color = colors.get(factor, 'black')
                ax2.plot(plot_df["기간"], plot_df[factor], color=color, marker=markers.get(factor, 'o'), linestyle='-', linewidth=2.5, markersize=8, label=factor)
                
                for idx, val in enumerate(plot_df[factor]):
                    if pd.notna(val) and val != 0.0:
                        suffix = "m/s" if "풍속" in factor else ("°C" if "기온" in factor else ("mm" if "강수" in factor else "%"))
                        ha_val = 'left' if "풍속" in factor else 'center'
                        
                        if is_weekly_mode and factor not in ["누적강수량(mm)", "평균풍속(m/s)"]:
                            continue
                            
                        ax2.annotate(f"{val}{suffix}", (idx, val), textcoords="offset points", xytext=offsets.get(factor, (0, 10)), ha=ha_val, va='center' if "풍속" in factor else 'bottom', fontsize=8, color=color, fontweight='bold')
                
            ax2.set_ylabel(f'{window_days}일 누적/평균 기상 관측 수치', fontweight='bold')
            lines_1, labels_1 = ax1.get_legend_handles_labels()
            lines_2, labels_2 = ax2.get_legend_handles_labels()
            ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper left', bbox_to_anchor=(0.02, 0.98))
        else:
            ax1.legend(loc='upper left')
            
        plt.grid(axis='y', linestyle='--', alpha=0.4)
        plt.xticks(rotation=0, ha='center', fontsize=8 if is_weekly_mode else 10)
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()
        
        st.markdown(f"##### 📝 집계 상세 데이터 (채집일 과거 {window_days}일 기준)")
        st.dataframe(plot_df, hide_index=True, use_container_width=True)
    else:
        st.info("💡 해당 감시망의 데이터가 존재하지 않아 기후 분석을 생성할 수 없습니다.")