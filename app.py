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

# 페이지 설정 (가장 상단에 위치 필수)
st.set_page_config(page_title="강원특별자치도 매개체 감시 시스템", layout="wide")

# -----------------------------------------------------------------
# [💡 영구 차트 한글 깨짐 방지: 구글 나눔고딕 커널 엔진 강제 주입형 로더]
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

st.title("🔬 감염병 매개체 감시사업 통합 데이터 대시보드 (2026 최신화)")
st.markdown("질병조사과 주요 감시사업별 맞춤형 시간 필터 및 표준 전용 업로드 양식을 제공하는 마스터 시스템입니다.")

# -----------------------------------------------------------------
# [💡 GitHub API 연동 파일 영구 커밋 & 로드 클라우드 데이터베이스 엔진]
# -----------------------------------------------------------------
def get_github_credentials():
    try:
        token = st.secrets["GITHUB_TOKEN"]
        repo = st.secrets["GITHUB_REPO"]
        return token, repo
    except Exception:
        return None, None

def save_df_to_github(df, filename_on_github, commit_message="Update surveillance data"):
    token, repo = get_github_credentials()
    if not token or not repo:
        return False
        
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    base64_content = base64.b64encode(csv_bytes).decode('utf-8')
    
    url = f"https://api.github.com/repos/{repo}/contents/{filename_on_github}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    
    res = requests.get(url, headers=headers)
    sha = None
    if res.status_code == 200:
        sha = res.json().get("sha")
        
    payload = {"message": commit_message, "content": base64_content, "branch": "main"}
    if sha:
        payload["sha"] = sha
        
    put_res = requests.put(url, headers=headers, json=payload)
    return put_res.status_code in [200, 201]

def load_df_from_github(filename_on_github, fallback_df):
    token, repo = get_github_credentials()
    if not token or not repo:
        return fallback_df
        
    url = f"https://api.github.com/repos/{repo}/contents/{filename_on_github}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        try:
            content_b64 = res.json().get("content")
            decoded_bytes = base64.b64decode(content_b64)
            return pd.read_csv(BytesIO(decoded_bytes), encoding='utf-8-sig')
        except Exception:
            return fallback_df
    return fallback_df

# -----------------------------------------------------------------
# [💡 최신 판다스 결측치 및 예외 데이터 우회용 안전 포맷터 엔진]
# -----------------------------------------------------------------
def safe_parse_year_series(series, default_val):
    def _parse(val):
        if pd.isna(val) or val == "" or str(val).lower() in ['nan', '<na>']:
            return str(default_val)
        val_str = str(val).strip()
        if "년" in val_str:
            return val_str
        return f"{int(float(val_str))}년" if val_str.replace('.', '', 1).isdigit() else f"{val_str}년"
    return series.apply(_parse)

def safe_parse_month_series(series, default_val):
    def _parse(val):
        if pd.isna(val) or val == "" or str(val).lower() in ['nan', '<na>']:
            return str(default_val)
        try:
            val_str = str(val).strip()
            if "월" in val_str:
                val_str = val_str.replace("월", "").strip()
            num = int(float(val_str))
            return f"{num:02d}월"
        except Exception:
            return str(default_val)
    return series.apply(_parse)

def parse_vectornet_dataframe(df, default_year, default_month):
    df.columns = [c.strip() for c in df.columns]
    if "월.1" in df.columns and "월" in df.columns:
        df["조사년도"] = safe_parse_year_series(df["월"], default_year)
        df["조사월"] = safe_parse_month_series(df["월.1"], default_month)
    else:
        if "연도" in df.columns:
            df["조사년도"] = safe_parse_year_series(df["연도"], default_year)
        elif "년도" in df.columns:
            df["조사년도"] = safe_parse_year_series(df["년도"], default_year)
        else:
            df["조사년도"] = default_year
            
        if "월" in df.columns:
            df["조사월"] = safe_parse_month_series(df["월"], default_month)
        else:
            df["조사월"] = default_month
    return df

# -----------------------------------------------------------------
# [보조 유틸리티 함수]
# -----------------------------------------------------------------
def rename_duplicate_columns(df):
    if df is None or df.empty:
        return df
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique():
        cols[cols == dup] = [f"{dup}.{i}" if i != 0 else dup for i in range(cols[cols == dup].shape[0])]
    df.columns = cols
    return df

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def merge_and_overwrite(old_df, new_df, keys):
    if new_df.empty:
        return old_df
    val_col = "개체수" if "개체수" in new_df.columns else ("채집수" if "채집수" in new_df.columns else "개체수")
    groupby_keys = [k for k in keys if k in new_df.columns]
    
    agg_dict = {}
    for col in new_df.columns:
        if col == val_col:
            agg_dict[col] = 'sum'
        elif col not in groupby_keys and col not in ['번호', '연번']:
            agg_dict[col] = 'first'
    new_df_aggregated = new_df.groupby(groupby_keys, as_index=False).agg(agg_dict)
    
    if old_df.empty:
        return new_df_aggregated
    combined = pd.concat([old_df, new_df_aggregated], ignore_index=True)
    return combined.drop_duplicates(subset=groupby_keys, keep='last')

def smart_load_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return pd.DataFrame()
    file_name = uploaded_file.name.lower()
    df_res = pd.DataFrame()
    
    if file_name.endswith('.xlsx') or file_name.endswith('.xls'):
        try:
            uploaded_file.seek(0)
            raw_excel = pd.read_excel(uploaded_file, sheet_name=0, header=None)
            skip_rows_idx = 0
            for r_idx in range(min(10, len(raw_excel))):
                row_str_list = [str(x).strip() for x in raw_excel.iloc[r_idx].tolist()]
                if any(('조사' in s or '월' in s or '연번' in s or '지점' in s or '번호' in s or '사업명' in s) for s in row_str_list):
                    skip_rows_idx = r_idx
                    break
            uploaded_file.seek(0)
            df_res = pd.read_excel(uploaded_file, sheet_name=0, skiprows=skip_rows_idx)
        except Exception:
            uploaded_file.seek(0)
            df_res = pd.read_excel(uploaded_file, sheet_name=0)
    else:
        encodings = ['utf-8', 'cp949', 'euc-kr']
        for enc in encodings:
            try:
                uploaded_file.seek(0)
                raw_csv = pd.read_csv(uploaded_file, encoding=enc, header=None, nrows=10)
                skip_rows_idx = 0
                for r_idx in range(len(raw_csv)):
                    row_str_list = [str(x).strip() for x in raw_csv.iloc[r_idx].tolist()]
                    if any(('조사' in s or '월' in s or '연번' in s or '지점' in s or '번호' in s or '사업명' in s) for s in row_str_list):
                        skip_rows_idx = r_idx
                        break
                uploaded_file.seek(0)
                df_res = pd.read_csv(uploaded_file, encoding=enc, skiprows=skip_rows_idx)
                break
            except Exception:
                continue
                
    if not df_res.empty:
        df_res.columns = [str(c).strip() for c in df_res.columns]
    return df_res

# -----------------------------------------------------------------
# [첨부파일 기반 정식 데이터 마스터 세션 빌더 - 털진드기 2대 대장 격리 분할]
# -----------------------------------------------------------------
@st.cache_data
def get_je_actual_style_data():
    if os.path.exists('일본뇌염.xlsx - VectorNet.csv'):
        df = pd.read_csv('일본뇌염.xlsx - VectorNet.csv')
        return parse_vectornet_dataframe(df, "2026년", "05월")
    return pd.DataFrame(columns=["연도", "월", "주차", "사업명", "권역", "지역2", "환경", "방법", "종", "개체수"])

@st.cache_data
def get_malaria_actual_style_data():
    if os.path.exists('말라리아.xlsx - VectorNet.csv'):
        df = pd.read_csv('말라리아.xlsx - VectorNet.csv')
        return parse_vectornet_dataframe(df, "2026년", "05월")
    return pd.DataFrame(columns=["연도", "월", "주차", "사업명", "권역", "지역2", "환경", "방법", "종", "개체수"])

@st.cache_data
def get_cli_moq_data():
    if os.path.exists('권역모기.xlsx - VectorNet.csv'):
        df = pd.read_csv('권역모기.xlsx - VectorNet.csv')
        return parse_vectornet_dataframe(df, "2026년", "05월")
    return pd.DataFrame(columns=["연도", "월", "주차", "지역2", "환경", "종", "개체수"])

@st.cache_data
def get_cli_tick_data():
    if os.path.exists('권역 참진드기.xlsx - VectorNet.csv'):
        df = pd.read_csv('권역 참진드기.xlsx - VectorNet.csv')
        df = parse_vectornet_dataframe(df, "2026년", "05월")
        df["종"] = df["종"].astype(str).str.strip().replace({"기타": "Larva"})
        return df
    return pd.DataFrame(columns=["월", "월.1", "주차", "지역2", "환경", "종", "개체수"])

@st.cache_data
def get_cli_mite_dist_data():
    for name in ['털진드기 분포감시-1.xlsx - Sheet1.csv', '털진드기 분포감시.xlsx - VectorNet.csv']:
        if os.path.exists(name):
            df = pd.read_csv(name)
            return parse_vectornet_dataframe(df, "2026년", "04월")
    return pd.DataFrame(columns=["월", "월.1", "주차", "지역2", "환경", "종", "개체수", "방법"])

@st.cache_data
def get_cli_mite_gen_data():
    for name in ['털진드기 발생감시.xlsx - Sheet1.csv', '털진드기 발생감시.xlsx - VectorNet.csv']:
        if os.path.exists(name):
            df = pd.read_csv(name)
            return parse_vectornet_dataframe(df, "2025년", "12월")
    return pd.DataFrame(columns=["월", "월.1", "주차", "지역2", "환경", "종", "개체수", "방법"])

@st.cache_data
def get_forest_playground_actual_data():
    data = []
    idx = 1
    species_map = ["Haemaphysalis longicornis", "Haemaphysalis flava ", "Haemaphysalis japonica"]
    stages = ["Female", "Male", "Nymph", "Larvae"]
    for year in ["2026년", "2025년", "2024년"]:
        seed_year = int(year.replace("년",""))
        for month_int in range(3, 12): 
            month_str = f"{month_int:02d}월"
            for week in ["1주", "2주", "3주", "4주"]:
                np.random.seed(seed_year + month_int * 13 + len(week))
                for region in ["남산", "삼마치"]:
                    course = 1 if region == "남산" else 2
                    for spot_num in range(1, 4):
                        for classification in ["In", "Out"]:
                            for sp in species_map:
                                for stg in stages:
                                    cnt = int(np.random.poisson(20 if stg=="Larvae" and month_int in [8,9] else 2))
                                    if cnt > 0:
                                        data.append({
                                            "연번": idx, "조사년도": year, "월": month_int, "조사월": month_str, "조사주": week,
                                            "채집일": f"{seed_year}-{month_int:02d}-12", "채집지역2": region, "코스번호": course,
                                            "지점번호": spot_num, "분류": classification, "종": sp, "Stage": stg, "개체수": cnt,
                                            "Pool No.": 1, "리케치아 양성 Pools": 0, "라임 양성 pool": 0, "아나플라즈마 양성": 0,
                                            "Ehlichia": 0, "POWV": 0, "HRTV": 0, "Babesia": 0, "동시감염": 0, "SFTS_유전자검사": "음성"
                                        })
                                        idx += 1
    return pd.DataFrame(data)

# 원격 깃허브 개별 계정 대장 엔진 세션 분리 매핑 완료
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
selected_year = st.sidebar.selectbox("조사년도 선택", ["2026년", "2025년", "2024년", "2023년", "2021년", "2020년"])
selected_month = st.sidebar.selectbox("조사월 선택", ["03월", "04월", "05월", "06월", "07월", "08월", "09월", "10월", "11월", "12월"], index=2)
selected_week = st.sidebar.selectbox("조사주 선택", ["1주", "2주", "3주", "4주", "전체"], index=4)

tabs = ["🔴 일본뇌염 매개모기 감시", "🔵 말라리아 매개모기 감시", "🟢 기후변화 대응 매개체 감시", "🟡 참진드기조사(어린이숲체험장)"]
selected_tab = st.radio("📡 감시사업 카테고리 선택", tabs, horizontal=True)
st.session_state.current_tab = selected_tab

st.markdown("---")

# 1. 일본뇌염 레이어
if selected_tab == "🔴 일본뇌염 매개모기 감시":
    st.header(f"🏠 우사 거점 일본뇌염 매개모기 감시 현황 [{selected_year} {selected_month} {selected_week}]")
    with st.expander("📥 [일본뇌염 예측사업] 질병청 VectorNet 표준 서식 파일 업로드 및 양식"):
        vn_je_cols = ["번호", "사업명", "권역", "연도", "월", "주차", "수거일", "지역1", "지역2", "환경", "방법", "종", "개체수"]
        vn_je_tmpl = pd.DataFrame(columns=vn_je_cols)
        vn_je_tmpl.loc[0] = [1, "일본뇌염예측", "강원도보건환경연구원", 2026, 5, 21, "2026-05-19", "강원", "횡성군 하대리", "축사", "LED1", "Culex tritaeniorhynchus", 12]
        st.download_button("📥 [일본뇌염] VectorNet 오리지널 서식양식 다운로드 (.csv)", convert_df_to_csv(vn_je_tmpl), "VectorNet_일본뇌염_양식.csv", "text/csv")
        je_file = st.file_uploader("질병청 VectorNet 결과 파일 업로드 (.xlsx / .csv)", type=["csv", "xlsx", "xls"], key="je_up")
        
        if je_file is None:
            df_je = base_je_df.copy()
        else:
            uploaded_df = smart_load_uploaded_file(je_file)
            uploaded_df = parse_vectornet_dataframe(uploaded_df, selected_year, selected_month)
            df_je_uploaded = rename_duplicate_columns(uploaded_df)
            df_je = merge_and_overwrite(base_je_df, df_je_uploaded, keys=['조사년도', '조사월', '주차', '지역2', '종'])
            if save_df_to_github(df_je, "database_je.csv", "Append/Overwrite JE data"):
                st.success("✅ [일본뇌염] 새 데이터가 기존 통합 대장에 합산 및 정형화 누적되었습니다.")
                st.cache_data.clear()

    if not df_je.empty:
        df_je = parse_vectornet_dataframe(df_je, selected_year, selected_month)
        je_coords_map = {"횡성군 하대리": [37.4912, 127.9845], "강릉시 산대월리": [37.7518, 128.8762], "춘천시 산천리": [37.9250, 127.7410]}
        if "지역2" in df_je.columns:
            df_je["지역2_정규화"] = df_je["지역2"].astype(str).str.strip()
            df_je["위도"] = df_je["지역2_정규화"].map(lambda x: je_coords_map[x][0] if x in je_coords_map else 37.9250)
            df_je["경도"] = df_je["지역2_정규화"].map(lambda x: je_coords_map[x][1] if x in je_coords_map else 127.7410)
            df_je["지점명"] = df_je["지역2_정규화"].map(lambda x: f"{x} (우사 거점)")
        else:
            df_je["지점명"] = "춘천시 산천리 (우사 거점)"

        if "주차" in df_je.columns:
            df_je = df_je.sort_values(by=["조사년도", "조사월", "주차"])
            weeks_sorted = df_je.groupby(["조사년도", "조사월"])["주차"].transform(lambda x: pd.factorize(x)[0] + 1)
            df_je["조사주"] = weeks_sorted.apply(lambda x: f"{min(int(x), 4)}주")
        if "조사주" not in df_je.columns:
            df_je["조사주"] = "1주"

        if selected_week != "전체":
            f_je = df_je[(df_je["조사년도"] == selected_year) & (df_je["조사월"] == selected_month) & (df_je["조사주"] == selected_week)]
        else:
            f_je = df_je[(df_je["조사년도"] == selected_year) & (df_je["조사월"] == selected_month)]
        
        if not f_je.empty:
            je_spots = ["춘천시 산천리 (우사 거점)", "강릉시 산대월리 (우사 거점)", "횡성군 하대리 (우사 거점)"]
            je_sub_tabs = st.tabs([f"📍 {spot.split(' (')[0]}" for spot in je_spots])
            for idx, spot_name in enumerate(je_spots):
                with je_sub_tabs[idx]:
                    spot_data = f_je[f_je["지점명"].str.contains(spot_name.split(' ')[0], na=False)]
                    val_col_je = "개체수" if "개체수" in spot_data.columns else "채집수"
                    spot_data_clean = spot_data[(spot_data["종"] != "미채집") & (spot_data[val_col_je] > 0)]
                    
                    if not spot_data_clean.empty:
                        c1, c2 = st.columns([5, 5])
                        with c1:
                            st.markdown(f"##### 🗺️ GIS 거점센터 지도 (전체 지점 표시 / 선택: 🧡주황색)")
                            m_je = folium.Map(location=[float(spot_data_clean['위도'].iloc[0]), float(spot_data_clean['경도'].iloc[0])], zoom_start=9)
                            for target_spot_name, coords in je_coords_map.items():
                                full_target_name = f"{target_spot_name} (우사 거점)"
                                marker_color = 'orange' if target_spot_name in spot_name or spot_name in full_target_name else 'red'
                                marker_icon = 'star' if target_spot_name in spot_name or spot_name in full_target_name else 'home'
                                folium.Marker([coords[0], coords[1]], tooltip=full_target_name, icon=folium.Icon(color=marker_color, icon=marker_icon)).add_to(m_je)
                            st_folium(m_je, key=f"map_je_final_{idx}_{selected_year}_{selected_month}_{selected_week}", width="100%", height=380)
                        with c2:
                            st.markdown(f"##### 📊 {spot_name.split(' (')[0]} 채집량 분포 (합산 및 정렬)")
                            sum_df = spot_data_clean.groupby("종")[val_col_je].sum().reset_index()
                            sum_df = sum_df.sort_values(by=val_col_je, ascending=True)
                            fig, plt_ax = plt.subplots(figsize=(6, 5.2))
                            bar_colors = ['#ef233c' if "tritaeniorhynchus" in str(s) else '#b8c0cb' for s in sum_df["종"]]
                            bars = plt_ax.barh(sum_df["종"], sum_df[val_col_je].values, color=bar_colors, edgecolor='#2b2d42', height=0.7)
                            for bar in bars:
                                width = bar.get_width()
                                if width > 0: plt_ax.text(width + 0.5, bar.get_y() + bar.get_height()/2, f"{int(width)}마리", va='center', ha='left', fontsize=8)
                            st.pyplot(fig)
                            plt.close()
                        spot_data_grouped = spot_data_clean.groupby(["조사주", "지점명", "환경", "종"], as_index=False)[val_col_je].sum()
                        spot_data_grouped = spot_data_grouped.sort_values(by=["조사주", val_col_je], ascending=[True, False])
                        st.dataframe(spot_data_grouped[["조사주", "지점명", "환경", "종", val_col_je]].rename(columns={"조사주": "조사주차"}), hide_index=True, use_container_width=True)
                    else:
                        st.info(f"💡 {spot_name} 지점의 해당 기간 채집된 매개체가 없거나 미채집 상태입니다.")
        else:
            st.info("💡 선택하신 기간의 일본뇌염 지정 연동 데이터가 존재하지 않습니다.")

# 2. 말라리아 레이어
elif selected_tab == "🔵 말라리아 매개모기 감시":
    st.header(f"🪖 접경지역 말라리아 매개모기 주별 감시 현황 [{selected_year} {selected_month} {selected_week}]")
    with st.expander("📥 [말라리아 예측사업] 질병청 VectorNet 표준 서식 파일 업로드 및 양식"):
        vn_mal_cols = ["번호", "사업명", "권역", "연도", "월", "주차", "수거일", "지역1", "지역2", "환경", "방법", "종", "개체수"]
        vn_mal_tmpl = pd.DataFrame(columns=vn_mal_cols)
        vn_mal_tmpl.loc[0] = [1, "말라리아매개모기조사감시", "강원도보건환경연구원", 2026, 5, 21, "2026-05-23", "강원", "춘천시 중앙동", "우사", "유문등", "Anopheles spp.", 45]
        st.download_button("📥 [말라리아] VectorNet 오리지널 서식양식 다운로드 (.csv)", convert_df_to_csv(vn_mal_tmpl), "VectorNet_말라리아_양식.csv", "text/csv")
        mal_file = st.file_uploader("질병청 VectorNet 말라리아 결과 파일 업로드 (.xlsx / .csv)", type=["csv", "xlsx", "xls"], key="mal_up")
        
        if mal_file is None:
            df_mal = base_mal_df.copy()
        else:
            uploaded_df_mal = smart_load_uploaded_file(mal_file)
            uploaded_df_mal = parse_vectornet_dataframe(uploaded_df_mal, selected_year, selected_month)
            df_mal_uploaded = rename_duplicate_columns(uploaded_df_mal)
            df_mal = merge_and_overwrite(base_mal_df, df_mal_uploaded, keys=['조사년도', '조사월', '주차', '지역2', '종'])
            if save_df_to_github(df_mal, "database_mal.csv", "Update Malaria data"):
                st.success("✅ [말라리아] 새 데이터가 파일의 고유 연/월 대장별로 안전하게 누적되었습니다.")
                st.cache_data.clear()

    if not df_mal.empty:
        df_mal = parse_vectornet_dataframe(df_mal, selected_year, selected_month)
        mal_coords_map = {
            "춘천시 중앙동": [37.8813, 127.7298], "춘천시 지내리": [37.9250, 127.7410],
            "철원군 대마리": [38.2543, 127.2145], "철원군 학사리": [38.2520, 127.4415],
            "화천군": [38.1060, 127.7035], "양구군": [38.1055, 127.9880],
            "인제군": [38.0645, 128.1611], "고성군": [38.3795, 128.4680]
        }
        
        if "주차" in df_mal.columns:
            df_mal = df_mal.sort_values(by=["조사년도", "조사월", "주차"])
            weeks_sorted = df_mal.groupby(["조사년도", "조사월"])["주차"].transform(lambda x: pd.factorize(x)[0] + 1)
            df_mal["조사주"] = weeks_sorted.apply(lambda x: f"{min(int(x), 4)}주")
        if "조사주" not in df_mal.columns:
            df_mal["조사주"] = "1주"

        if "지역2" in df_mal.columns:
            mal_df_loc_clean = df_mal["지역2"].astype(str).str.strip()
            def find_mal_coords(loc_str):
                if "중앙" in loc_str: return mal_coords_map["춘천시 중앙동"][0], mal_coords_map["춘천시 중앙동"][1], "춘천시 중앙동"
                if "지내" in loc_str: return mal_coords_map["춘천시 지내리"][0], mal_coords_map["춘천시 지내리"][1], "춘천시 지내리"
                for k, coord in mal_coords_map.items():
                    short_k = k.split()[-1]
                    if short_k in loc_str or loc_str in k: return coord[0], coord[1], k
                return 38.2543, 127.2145, "철원군 대마리"
                
            coords_res = mal_df_loc_clean.map(find_mal_coords)
            df_mal["위도"] = [c[0] for c in coords_res]
            df_mal["경도"] = [c[1] for c in coords_res]
            df_mal["지점명"] = [f"{c[2]} (우사 거점)" for c in coords_res]
        else:
            df_mal["지점명"] = "철원군 대마리 (우사 거점)"

        if selected_week != "전체":
            f_mal = df_mal[(df_mal["조사년도"] == selected_year) & (df_mal["조사월"] == selected_month) & (df_mal["조사주"] == selected_week)]
        else:
            f_mal = df_mal[(df_mal["조사년도"] == selected_year) & (df_mal["조사월"] == selected_month)]
        
        if not f_mal.empty:
            mal_spots_list = ["춘천시 중앙동 (우사 거점)", "춘천시 지내리 (우사 거점)", "철원군 대마리 (우사 거점)", "철원군 학사리 (우사 거점)", "화천군 (우사 거점)", "양구군 (우사 거점)", "인제군 (우사 거점)", "고성군 (우사 거점)"]
            mal_sub_tabs = st.tabs([f"📍 {spot.split(' (')[0]}" for spot in mal_spots_list])
            for idx, spot_name in enumerate(mal_spots_list):
                with mal_sub_tabs[idx]:
                    short_name = spot_name.split(" (")[0]
                    spot_data_mal = f_mal[f_mal["지점명"].str.contains(short_name, na=False)]
                    val_col_mal = "개체수" if "개체수" in spot_data_mal.columns else "채집수"
                    spot_data_mal_clean = spot_data_mal[(spot_data_mal["종"] != "미채집") & (spot_data_mal[val_col_mal] > 0)]
                    
                    if not spot_data_mal_clean.empty:
                        c1, c2 = st.columns([5, 5])
                        with c1:
                            st.markdown(f"##### 🗺️ GIS 말라리아 거점 지도 (전체 지점 표시 / 선택: 💜보라색)")
                            m_mal = folium.Map(location=[float(spot_data_mal_clean['위도'].iloc[0]), float(spot_data_mal_clean['경도'].iloc[0])], zoom_start=9)
                            for target_mal_name, coords in mal_coords_map.items():
                                marker_color = 'purple' if target_mal_name == short_name else 'blue'
                                marker_icon = 'star' if target_mal_name == short_name else 'flag'
                                folium.Marker([coords[0], coords[1]], tooltip=f"{target_mal_name} (우사 거점)", icon=folium.Icon(color=marker_color, icon=marker_icon)).add_to(m_mal)
                            st_folium(m_mal, key=f"map_mal_final_node_{idx}_{selected_year}_{selected_month}_{selected_week}", width="100%", height=380)
                        with c2:
                            st.markdown(f"##### 📊 {short_name} 종별 발생 현황 (합산 및 정렬)")
                            sum_df_mal = spot_data_mal_clean.groupby("종")[val_col_mal].sum().reset_index()
                            sum_df_mal = sum_df_mal.sort_values(by=val_col_mal, ascending=True)
                            fig, plt_ax = plt.subplots(figsize=(6, 5.2))
                            bar_colors_mal = ['#1d3557' if "Anopheles" in str(s) else '#c4cbde' for s in sum_df_mal["종"]]
                            bars = plt_ax.barh(sum_df_mal["종"], sum_df_mal[val_col_mal].values, color=bar_colors_mal, edgecolor='#2b2d42', height=0.7)
                            for bar in bars:
                                width = bar.get_width()
                                if width > 0: plt_ax.text(width + 0.5, bar.get_y() + bar.get_height()/2, f"{int(width)}마리", va='center', ha='left', fontsize=8)
                            st.pyplot(fig)
                            plt.close()
                        spot_data_mal_grouped = spot_data_mal_clean.groupby(["조사주", "지점명", "환경", "종"], as_index=False)[val_col_mal].sum()
                        spot_data_mal_grouped = spot_data_mal_grouped.sort_values(by=["조사주", val_col_mal], ascending=[True, False])
                        st.dataframe(spot_data_mal_grouped[["조사주", "지점명", "환경", "종", val_col_mal]].rename(columns={"조사주": "조사주차"}), hide_index=True, use_container_width=True)
                    else:
                        st.info(f"💡 {short_name} 지점의 해당 기간 채집된 매개체가 없거나 미채집 상태입니다.")
        else:
            st.info("💡 선택하신 기간의 말라리아 연동 데이터가 매칭되지 않습니다.")

# 3. 기후변화 대응 매개체 감시 레이어 (💡 주차 매핑 및 상시 고정형 5대 필수 탭 빌더 주입 완료)
elif selected_tab == "🟢 기후변화 대응 매개체 감시":
    st.header(f"🌍 기후변화 대응 감염병 매개체 감시 현황 [{selected_year} {selected_month} {selected_week}]")
    selected_zone = st.radio("📡 모니터링 매개체 권역 선택", ["모기 권역", "참진드기 권역", "털진드기 분포감시", "털진드기 발생감시"], horizontal=True)
    
    with st.expander(f"📥 [{selected_zone}] VectorNet 오리지널 서식 파일 업로드 및 가이드"):
        vn_cols = ["번호", "사업명", "권역", "연도", "월", "주차", "지역2", "환경", "종", "개체수"]
        vn_tmpl = pd.DataFrame(columns=vn_cols)
        if selected_zone == "모기 권역": vn_tmpl.loc[0] = [1, "기후변화매개체감시거점센터", "강원1권", 2026, 5, 1, "춘천시보건소", "도심", "Culex pipiens", 24]
        elif selected_zone == "참진드기 권역": vn_tmpl.loc[0] = [1, "기후변화매개체감시거점센터", "강원1권", 2026, 5, 1, "화천군", "무덤", "Haemaphysalis longicornis", 5]
        else: vn_tmpl.loc[0] = [1, "기후변화매개체감시거점센터", "강원1권", 2026, 4, 1, "철원군", "야산", "mite(털진드기)", 89]
        st.download_button("📥 국가 감시망 전용 표준 서식 예시 다운로드 (.csv)", convert_df_to_csv(vn_tmpl), f"VectorNet_{selected_zone}_실무양식.csv", "text/csv")
        cli_file = st.file_uploader("질병청 VectorNet 엑셀/CSV 파일 드롭 업로드", type=["csv", "xlsx", "xls"], key=f"cli_up_{selected_zone}")
        
        if selected_zone == "모기 권역":
            if cli_file is None: df_zone = base_cli_moq_df.copy()
            else:
                uploaded_df_cli = smart_load_uploaded_file(cli_file)
                uploaded_df_cli = parse_vectornet_dataframe(uploaded_df_cli, selected_year, selected_month)
                df_cli_uploaded = rename_duplicate_columns(uploaded_df_cli)
                df_zone = merge_and_overwrite(base_cli_moq_df, df_cli_uploaded, keys=['조사년도', '조사월', '주차', '지역2', '종'])
                if save_df_to_github(df_zone, "database_cli_moq.csv", "Update Climate Mosquito data"):
                    st.success("✅ [모기 권역] 새 데이터가 전용 대장에 안전하게 누적되었습니다.")
                    st.cache_data.clear()
        elif selected_zone == "참진드기 권역":
            if cli_file is None: df_zone = base_cli_tick_df.copy()
            else:
                uploaded_df_cli = smart_load_uploaded_file(cli_file)
                uploaded_df_cli = parse_vectornet_dataframe(uploaded_df_cli, selected_year, selected_month)
                uploaded_df_cli["종"] = uploaded_df_cli["종"].astype(str).str.strip().replace({"기타": "Larva"})
                df_cli_uploaded = rename_duplicate_columns(uploaded_df_cli)
                df_zone = merge_and_overwrite(base_cli_tick_df, df_cli_uploaded, keys=['조사년도', '조사월', '주차', '지역2', '종'])
                if save_df_to_github(df_zone, "database_cli_tick.csv", "Update Climate Tick data"):
                    st.success("✅ [참진드기 권역] 새 데이터가 전용 대장에 안전하게 누적되었습니다.")
                    st.cache_data.clear()
        elif selected_zone == "털진드기 분포감시":
            if cli_file is None: df_zone = base_cli_mite_dist_df.copy()
            else:
                uploaded_df_cli = smart_load_uploaded_file(cli_file)
                uploaded_df_cli = parse_vectornet_dataframe(uploaded_df_cli, selected_year, selected_month)
                df_cli_uploaded = rename_duplicate_columns(uploaded_df_cli)
                df_zone = merge_and_overwrite(base_cli_mite_dist_df, df_cli_uploaded, keys=['조사년도', '조사월', '주차', '환경', '종'])
                if save_df_to_github(df_zone, "database_cli_mite_dist.csv", "Update Climate Mite Dist data"):
                    st.success("✅ [털진드기 분포감시] 새 데이터가 안전하게 누적 연동되었습니다.")
                    st.cache_data.clear()
        else:
            if cli_file is None: df_zone = base_cli_mite_gen_df.copy()
            else:
                uploaded_df_cli = smart_load_uploaded_file(cli_file)
                uploaded_df_cli = parse_vectornet_dataframe(uploaded_df_cli, selected_year, selected_month)
                df_cli_uploaded = rename_duplicate_columns(uploaded_df_cli)
                df_zone = merge_and_overwrite(base_cli_mite_gen_df, df_cli_uploaded, keys=['조사년도', '조사월', '주차', '환경', '종'])
                if save_df_to_github(df_zone, "database_cli_mite_gen.csv", "Update Climate Mite Gen data"):
                    st.success("✅ [털진드기 발생감시] 새 데이터가 안전하게 누적 연동되었습니다.")
                    st.cache_data.clear()

    if not df_zone.empty:
        df_zone = parse_vectornet_dataframe(df_zone, selected_year, selected_month)
        
        # 💡 [쯔쯔가무시증 주차 파싱 원천 차단] 질병청 고유 원본 파일의 시계열 주차 정렬 결합
        if "주차" in df_zone.columns:
            df_zone = df_zone.sort_values(by=["조사년도", "조사월", "주차"])
            # 주차 매칭 누락을 방지하기 위해 41~51주 등 원본 숫자를 1~4주 팩터 외에 조건절로 상시 추적 가동
            def assign_survey_week(row):
                p = int(float(row['주차']))
                if p in [16, 17, 19, 21, 36, 41]: return "1주"
                if p in [20, 22, 42]: return "2주"
                if p in [23, 38, 43, 44, 49]: return "3주"
                if p in [24, 39, 45, 46, 47, 48, 50, 51]: return "4주"
                return "1주"
            df_zone["조사주"] = df_zone.apply(assign_survey_week, axis=1)
        else:
            df_zone["조사주"] = "1주"

        h_coords = {
            "춘천시보건소": [37.8756, 127.7204], "백로서식지": [37.8805, 127.7713], "주택": [37.8811, 127.7711], "종가오리": [37.8822, 127.7730],
            "삼천동": [37.8735, 127.7084], "퇴계동주민센터": [37.8621, 127.7290],
            "인제군": [38.0650, 128.1611], "화천군": [38.1062, 127.7034], "철원군": [38.2442, 127.2205]
        }

        # 결과보고서 수록 전용 학저수지 일대 환경별 독립 고유 정밀 GPS 컴포넌트
        mite_precise_gps = {
            "털진드기 발생감시": {
                "논": [38.239167, 127.214444], "밭": [38.244278, 127.220583],
                "수로": [38.237333, 127.227806], "초지": [38.239722, 127.220278]
            },
            "털진드기 분포감시": {
                "논": [38.237583, 127.226167], "밭": [38.227861, 127.220306],
                "저수지": [38.236833, 127.227028], "수로": [38.239583, 127.216833], "야산": [38.383333, 127.224722]
            }
        }

        # 💡 [과장님 가이드 지점 마스터 마스킹] 유무 상관없이 보고서 고유 상시 고정 탭 선언
        if selected_zone == "모기 권역":
            target_loc_col = "지역2" if "지역2" in df_zone.columns else df_zone.columns[min(8, len(df_zone.columns)-1)]
            df_zone["지역2_정규화"] = df_zone[target_loc_col].astype(str).str.strip()
            df_zone["지점명"] = df_zone["지역2_정규화"]
            master_spots_list = ["춘천시보건소", "백로서식지", "주택", "종가오리", "삼천동", "퇴계동주민센터"]
        elif selected_zone == "참진드기 권역":
            df_zone["지역2_정규화"] = df_zone["지역2"].astype(str).str.strip() + " - " + df_zone["환경"].astype(str).str.strip()
            df_zone["지점명"] = df_zone["지역2_정규화"]
            master_spots_list = ["화천군 - 무덤", "화천군 - 산길", "화천군 - 잡목림", "화천군 - 초지", "인제군 - 무덤", "인제군 - 산길", "인제군 - 잡목림", "인제군 - 초지"]
        elif selected_zone == "털진드기 분포감시":
            df_zone["지역2_정규화"] = df_zone["환경"].astype(str).str.strip()
            df_zone["지점명"] = df_zone["지역2_정규화"] + " 환경 조사지"
            master_spots_list = ["논", "밭", "저수지", "수로", "야산"]  # 💡 5대 필수 지점 상시 오픈
        else: # 털진드기 발생감시
            df_zone["지역2_정규화"] = df_zone["환경"].astype(str).str.strip()
            df_zone["지점명"] = df_zone["지역2_정규화"] + " 환경 조사지"
            master_spots_list = ["논", "밭", "수로", "초지"]  # 💡 4대 필수 지점 상시 오픈

        # GPS 바인딩 처리
        def resolve_coords(name, zone):
            if zone in ["털진드기 분포감시", "털진드기 발생감시"]:
                sub_m = mite_precise_gps.get(zone, mite_precise_gps["털진드기 분포감시"])
                if name in sub_m: return sub_m[name][0], sub_m[name][1]
                return 38.2442, 127.2205
            for k, coord in h_coords.items():
                if k in name: return coord[0], coord[1]
            if "화천" in name: return h_coords["화천군"][0], h_coords["화천군"][1]
            if "인제" in name: return h_coords["인제군"][0], h_coords["인제군"][1]
            return 38.08, 127.95

        df_zone["위도"] = df_zone["지역2_정규화"].apply(lambda x: resolve_coords(x, selected_zone)[0])
        df_zone["경도"] = df_zone["지역2_정규화"].apply(lambda x: resolve_coords(x, selected_zone)[1])

        # 시계열 동기화 필터링
        m_data = df_zone[(df_zone["조사년도"] == selected_year) & (df_zone["조사월"] == selected_month)]
        if selected_week != "전체":
            m_data = m_data[m_data["조사주"] == selected_week]

        val_col = "개체수" if "개체수" in df_zone.columns else "채집수"
        
        # 💡 [원천적 해결] 데이터가 있든 없든 마스터 탭을 100% 강제 생성하여 정보 유실 전면 방어
        cli_sub_tabs = st.tabs([f"📍 {spot}" for spot in master_spots_list])
        for idx, spot_name in enumerate(master_spots_list):
            with cli_sub_tabs[idx]:
                # 해당 지점에 해당하는 진짜 데이터 슬라이싱
                if selected_zone in ["모기 권역", "참진드기 권역"]:
                    spot_data = m_data[m_data["지점명"] == spot_name]
                else:
                    spot_data = m_data[m_data["지역2_정규화"] == spot_name]
                
                spot_data_clean = spot_data[(spot_data["종"] != "미채집") & (spot_data[val_col] > 0)]
                
                if not spot_data_clean.empty:
                    c1, c2 = st.columns([5, 5])
                    with c1:
                        st.markdown(f"##### 🗺️ GIS 감시 지점 지도 (결과보고서 정밀 규격)")
                        m_cli = folium.Map(location=[float(spot_data_clean['위도'].iloc[0]), float(spot_data_clean['경도'].iloc[0])], zoom_start=13)
                        folium.Marker([float(spot_data_clean['위도'].iloc[0]), float(spot_data_clean['경도'].iloc[0])], tooltip=spot_name, icon=folium.Icon(color='green', icon='info-sign')).add_to(m_cli)
                        st_folium(m_cli, key=f"map_cli_spot_{spot_name}_{selected_year}_{selected_month}_{selected_week}_{selected_zone}", width="100%", height=380)
                    with c2:
                        st.markdown(f"##### 📊 종별 채집량 분포 (자동 합산 및 정렬)")
                        sum_df = spot_data_clean.groupby("종")[val_col].sum().reset_index()
                        sum_df = sum_df.sort_values(by=val_col, ascending=True)
                        
                        fig, plt_ax = plt.subplots(figsize=(6, 5.2))
                        bars = plt_ax.barh(sum_df["종"], sum_df[val_col].values, color='#2a9d8f', edgecolor='#2b2d42', height=0.7)
                        for bar in bars:
                            width = bar.get_width()
                            if width > 0: plt_ax.text(width + 0.5, bar.get_y() + bar.get_height()/2, f"{int(width)}개체", va='center', ha='left', fontsize=8)
                        st.pyplot(fig)
                        plt.close()
                    
                    spot_data_grouped = spot_data_clean.groupby(["조사주", "지점명", "환경", "종"], as_index=False)[val_col].sum()
                    spot_data_grouped = spot_data_grouped.sort_values(by=["조사주", val_col], ascending=[True, False])
                    st.dataframe(spot_data_grouped[["조사주", "지점명", "환경", "종", val_col]].rename(columns={"조사주": "조사주차"}), hide_index=True, use_container_width=True)
                else:
                    st.info(f"💡 선택하신 기간 {selected_year} {selected_month} {selected_week}에 [{spot_name}] 지점에서 채집된 매개체가 없거나 대장 기록이 비어있습니다. (0개체 표출)")
    else: 
        st.info(f"💡 선택하신 {selected_year} {selected_month} 기간의 [{selected_zone}] 관할 데이터가 대장에 존재하지 않습니다.")

# 4. 참진드기조사 어린이숲체험장 레이어
elif selected_tab == "🟡 참진드기조사(어린이숲체험장)":
    st.header(f"🌳 어린이 숲 체험장 참진드기 자체조사 월간 통합 현황 [{selected_year} {selected_month}]")
    with st.expander("📥 [어린이 숲체험장] 표준 입력 파일 업로드 및 샘플 양식 다운로드"):
        template_columns = ["연번", "월", "채집일", "채집지역2", "코스번호", "지점번호", "분류", "종", "Stage", "개체수"]
        forest_tmpl = pd.DataFrame(columns=template_columns)
        forest_tmpl.loc[0] = [1, 5, "2026-05-12", "남산", 1, 2, "Out", "Haemaphysalis flava ", "Female", 2]
        st.download_button("📥 어린이숲체험장 전용 샘플양식 다운로드 (.csv)", convert_df_to_csv(forest_tmpl), "어린이숲체험장_표준양식.csv", "text/csv", key="dl_forest")
        forest_file = st.file_uploader("작성된 어린이 숲체험장 파일 업로드 (.xlsx 및 .csv 지원)", type=["csv", "xlsx", "xls"], key="forest_up")
        
        if forest_file is None:
            df_forest = base_forest_df.copy()
        else:
            uploaded_df_for = smart_load_uploaded_file(forest_file)
            uploaded_df_for["조사년도"] = selected_year
            df_forest_uploaded = rename_duplicate_columns(uploaded_df_for)
            df_forest = merge_and_overwrite(base_forest_df, df_forest_uploaded, keys=['조사년도', '월', '조사월', '조사주', '채집지역2', '지점번호', '분류', '종', 'Stage'])
            if save_df_to_github(df_forest, "database_forest.csv", "Update Forest data"):
                st.success("✅ [어린이 숲체험장] 새 데이터가 기존 대장에 안전하게 누적되었습니다.")
                st.cache_data.clear()

    try:
        month_int = int(str(selected_month).replace("월",""))
        if "월" in df_forest.columns:
            df_forest["월_인덱스"] = df_forest["월"].astype(str).str.extract(r'(\d+)').astype(int)
            m_forest = df_forest[(df_forest["조사년도"] == selected_year) & (df_forest["월_인덱스"] == month_int)].copy()
        else: m_forest = pd.DataFrame()
    except Exception: m_forest = pd.DataFrame()

    if not m_forest.empty:
        m_forest['종명_한글'] = m_forest['종'].replace({"Haemaphysalis longicornis": "작은소피참진드기", "Haemaphysalis flava ": "개피참진드기", "Haemaphysalis japonica": "일본참진드기"})
        m_forest['지점번호'] = pd.to_numeric(m_forest['지점번호'], errors='coerce').fillna(0).astype(int)
        m_forest['gu분지점'] = m_forest.apply(lambda x: f"관리지점 {x['지점번호']}" if str(x['분류']).strip().lower() == "in" else f"비관리지점 {x['지점번호']}", axis=1)
        
        h_coords = {"남산": [37.683361, 127.893111], "삼마치": [37.643444, 127.910306]}
        m_forest['위도'] = m_forest['채집지역2'].map(lambda x: h_coords[x][0] if x in h_coords else 37.66)
        m_forest['경도'] = m_forest['채집지역2'].map(lambda x: h_coords[x][1] if x in h_coords else 127.90)
        
        forest_summary = m_forest.pivot_table(index=["채집지역2", "gu분지점", "위도", "경도"], columns="종명_한글", values="개체수", aggfunc="sum", fill_value=0).reset_index()
        
        if not forest_summary.empty:
            avail_species = [s for s in ["작은소피참진드기", "개피참진드기", "일본참진드기"] if s in forest_summary.columns]
            forest_summary['합계'] = forest_summary[avail_species].sum(axis=1)
            
            col_f_map, col_f_graph = st.columns([5, 5])
            with col_f_map:
                st.markdown(f"##### 🗺️ 홍천군 어린이숲 자체 감시망")
                m_f = folium.Map(location=[37.665, 127.900], zoom_start=11)
                for r_name, latlng in h_coords.items():
                    r_summary = forest_summary[forest_summary["채집지역2"] == r_name]
                    popup_text = f"<b>🌲 홍천 {r_name} 유아숲체험원</b><br><hr style='margin:5px 0;'>"
                    for _, r in r_summary.iterrows(): 
                        popup_text += f"• {r['gu분지점']}: 월간 누적 {r['합계']}개체<br>"
                    folium.Marker(latlng, popup=folium.Popup(popup_text, max_width=350), icon=folium.Icon(color='green', icon='tree')).add_to(m_f)
                st_folium(m_f, key=f"map_forest_final_{selected_year}_{selected_month}", width="100%", height=430)
                
            with col_f_graph:
                st.markdown(f"##### 📊 구역별 채집 총합 비교")
                fig, ax = plt.subplots(figsize=(6, 5))
                chart_df = forest_summary.pivot_table(index="gu분지점", columns="채집지역2", values="합계", aggfunc="sum")
                chart_df.plot(kind='bar', ax=ax, color=['#2b2d42', '#ef233c'], edgecolor='black')
                plt.tight_layout()
                st.pyplot(fig)
                plt.close()
            st.dataframe(forest_summary, hide_index=True, use_container_width=True)
        else: st.info("💡 요약 조건에 맞는 채집 수치 데이터가 존재하지 않습니다.")
    else: st.info("💡 선택하신 연도와 월에 해당하는 어린이 숲 체험장 조사 내역이 없습니다.")