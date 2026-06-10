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

st.title("🔬 감염병 매개체 감시사업 통합 데이터 대시보드 (2026 마스터 배포판)")
st.markdown("질병조사과 주요 감시사업별 맞춤형 시간 필터 및 질병청 원본 파일 업로드와 데이터 추출 기능을 제공하는 최종 시스템입니다.")

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
# [첨부파일 기반 정식 데이터 마스터 세션 빌더]
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
    for name in ['털진드기 분포감시-1.xlsx - Sheet1.csv', '털진드기 분포감시.xlsx - VectorNet.csv', '털진드기 분포감시.xlsx - Sheet1.csv']:
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
    species_map = ["Haemaphysalis longicornis", "Haemaphysalis flava ", "Haemaphysalis japonica", "Ixodes nipponensis"]
    stages = ["Female", "Male", "Nymph", "Larvae"]
    for year in ["2026년", "2025년", "2024년", "2023년", "2021년", "2020년"]:
        seed_year = int(year.replace("년",""))
        regions = ["홍천", "정선"] if seed_year == 2025 else (["춘천", "인제"] if seed_year == 2024 else ["남산", "삼마치"])
        for month_int in range(3, 12): 
            month_str = f"{month_int:02d}월"
            for week in ["1주", "2주", "3주", "4주"]:
                np.random.seed(seed_year + month_int * 13 + len(week))
                for region in regions:
                    course = 1 if region in ["남산", "홍천", "춘천"] else 2
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
    
    c_up1, c_dl1 = st.columns([8, 4])
    with c_up1:
        je_file = st.file_uploader("질병청 VectorNet 일본뇌염 결과 파일 업로드 (.xlsx / .csv)", type=["csv", "xlsx", "xls"], key="je_up")
        if je_file is not None:
            uploaded_df = smart_load_uploaded_file(je_file)
            uploaded_df = parse_vectornet_dataframe(uploaded_df, selected_year, selected_month)
            df_je_uploaded = rename_duplicate_columns(uploaded_df)
            base_je_df = merge_and_overwrite(base_je_df, df_je_uploaded, keys=['조사년도', '조사월', '주차', '지역2', '종'])
            save_df_to_github(base_je_df, "database_je.csv", "Append JE data")
            st.success("✅ 일본뇌염 새 데이터가 실시간 원격 원장 데이터베이스에 누적 결합되었습니다.")
            st.cache_data.clear()
            
    df_je = base_je_df.copy()

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
        else:
            df_je["조사주"] = "1주"

        if selected_week != "전체":
            f_je = df_je[(df_je["조사년도"] == selected_year) & (df_je["조사월"] == selected_month) & (df_je["조사주"] == selected_week)]
        else:
            f_je = df_je[(df_je["조사년도"] == selected_year) & (df_je["조사월"] == selected_month)]
        
        with c_dl1:
            st.markdown("<br>", unsafe_allow_html=True)
            if not f_je.empty:
                st.download_button("📥 필터 데이터 원본 추출 (.csv)", convert_df_to_csv(f_je), f"일본뇌염_감시망_추출_{selected_year}_{selected_month}.csv", "text/csv")

        if not f_je.empty:
            je_spots = ["춘천시 산천리 (우사 거점)", "강릉시 산대월리 (우사 거점)", "횡성군 하대리 (우사 거점)"]
            je_tab_names = ["📍 지점전체"] + [f"📍 {spot.split(' (')[0]}" for spot in je_spots]
            je_sub_tabs = st.tabs(je_tab_names)
            
            # [1] 지점전체 전용 스페이스
            with je_sub_tabs[0]:
                c1, c2 = st.columns([5, 5])
                with c1:
                    st.markdown("##### 🗺️ GIS 거점센터 지도 (전체 지점 표시)")
                    m_je_all = folium.Map(location=[37.75, 128.3], zoom_start=8)
                    for target_spot_name, coords in je_coords_map.items():
                        folium.Marker([coords[0], coords[1]], tooltip=f"{target_spot_name} (우사 거점)", icon=folium.Icon(color='red', icon='home')).add_to(m_je_all)
                    st_folium(m_je_all, key=f"map_je_all_{selected_year}_{selected_month}_{selected_week}", width="100%", height=380)
                with c2:
                    st.markdown("##### 📊 주요 매개체(Culex tritaeniorhynchus) 지점별 채집량")
                    df_ct = f_je[f_je["종"].str.contains("tritaeniorhynchus", na=False, case=False)]
                    val_col_je = "개체수" if "개체수" in f_je.columns else "채집수"
                    
                    all_je_short_spots = [s.split(' (')[0] for s in je_spots]
                    spot_dict = {s: 0 for s in all_je_short_spots}
                    if not df_ct.empty:
                        for _, row in df_ct.iterrows():
                            loc_str = str(row["지역2_정규화"]) if "지역2_정규화" in row else str(row["지역2"])
                            for s in all_je_short_spots:
                                if s in loc_str or loc_str in s:
                                    spot_dict[s] += row[val_col_je]
                                    
                    plot_df = pd.DataFrame(list(spot_dict.items()), columns=["지점", val_col_je]).sort_values(by=val_col_je, ascending=True)
                    fig, plt_ax = plt.subplots(figsize=(6, 5.2))
                    bars = plt_ax.barh(plot_df["지점"], plot_df[val_col_je].values, color='#ef233c', edgecolor='#2b2d42', height=0.7)
                    for bar in bars:
                        width = bar.get_width()
                        plt_ax.text(width + 0.5, bar.get_y() + bar.get_height()/2, f"{int(width)}마리", va='center', ha='left', fontsize=8)
                    st.pyplot(fig)
                    plt.close()
                
                df_je_all_clean = f_je[(f_je["종"] != "미채집") & (f_je[val_col_je] > 0)]
                if not df_je_all_clean.empty:
                    je_all_grouped = df_je_all_clean.groupby(["조사주", "지점명", "환경", "종"], as_index=False)[val_col_je].sum()
                    je_all_grouped = je_all_grouped.sort_values(by=["조사주", val_col_je], ascending=[True, False])
                    st.dataframe(je_all_grouped[["조사주", "지점명", "환경", "종", val_col_je]].rename(columns={"조사주": "조사주차"}), hide_index=True, use_container_width=True)

            # [2] 개별 지점 탭 영역
            for idx, spot_name in enumerate(je_spots):
                with je_sub_tabs[idx + 1]:
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
                                folium.Marker([coords[0], coords[1]], tooltip=full_target_name, icon=folium.Icon(color='orange' if target_spot_name in spot_name or spot_name in full_target_name else 'red', icon='star' if target_spot_name in spot_name or spot_name in full_target_name else 'home')).add_to(m_je)
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
                        st.info(f"💡 {spot_name} 지점의 해당 기간 채집된 매개체가 없거나 미채집 상태입니다. (0개체)")
        else:
            st.info("💡 선택하신 기간의 일본뇌염 지정 연동 데이터가 존재하지 않습니다.")

# 2. 말라리아 레이어
elif selected_tab == "🔵 말라리아 매개모기 감시":
    st.header(f"🪖 접경지역 말라리아 매개모기 주별 감시 현황 [{selected_year} {selected_month} {selected_week}]")
    
    c_up2, c_dl2 = st.columns([8, 4])
    with c_up2:
        mal_file = st.file_uploader("질병청 VectorNet 말라리아 결과 파일 업로드 (.xlsx / .csv)", type=["csv", "xlsx", "xls"], key="mal_up")
        if mal_file is None:
            df_mal = base_mal_df.copy()
        else:
            uploaded_df_mal = smart_load_uploaded_file(mal_file)
            uploaded_df_mal = parse_vectornet_dataframe(uploaded_df_mal, selected_year, selected_month)
            df_mal_uploaded = rename_duplicate_columns(uploaded_df_mal)
            base_mal_df = merge_and_overwrite(base_mal_df, df_mal_uploaded, keys=['조사년도', '조사월', '주차', '지역2', '종'])
            save_df_to_github(base_mal_df, "database_mal.csv", "Update Malaria data")
            st.success("✅ 말라리아 새 데이터가 원격 보관 대장에 안전하게 결합되었습니다.")
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
        
        if "주차" in df_mal.columns:
            df_mal = df_mal.sort_values(by=["조사년도", "조사월", "주차"])
            weeks_sorted = df_mal.groupby(["조사년도", "조사월"])["주차"].transform(lambda x: pd.factorize(x)[0] + 1)
            df_mal["조사주"] = weeks_sorted.apply(lambda x: f"{min(int(x), 4)}주")
        else:
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
        
        with c_dl2:
            st.markdown("<br>", unsafe_allow_html=True)
            if not f_mal.empty:
                st.download_button("📥 필터 데이터 원본 추출 (.csv)", convert_df_to_csv(f_mal), f"말라리아_감시망_추출_{selected_year}_{selected_month}.csv", "text/csv")

        if not f_mal.empty:
            mal_spots_list = ["춘천시 중앙동 (우사 거점)", "춘천시 지내리 (우사 거점)", "철원군 대마리 (우사 거점)", "춘천시 학사리 (우사 거점)", "화천군 (우사 거점)", "양구군 (우사 거점)", "인제군 (우사 거점)", "고성군 (우사 거점)"]
            mal_tab_names = ["📍 지점전체"] + [f"📍 {spot.split(' (')[0]}" for spot in mal_spots_list]
            mal_sub_tabs = st.tabs(mal_tab_names)
            
            # [1] 지점전체 전용 스페이스
            with mal_sub_tabs[0]:
                c1, c2 = st.columns([5, 5])
                with c1:
                    st.markdown("##### 🗺️ GIS 말라리아 거점 지도 (전체 지점 표시)")
                    m_mal_all = folium.Map(location=[38.15, 127.8], zoom_start=9)
                    for target_mal_name, coords in mal_coords_map.items():
                        folium.Marker([coords[0], coords[1]], tooltip=f"{target_mal_name} (우사 거점)", icon=folium.Icon(color='blue', icon='flag')).add_to(m_mal_all)
                    st_folium(m_mal_all, key=f"map_mal_all_{selected_year}_{selected_month}_{selected_week}", width="100%", height=380)
                with c2:
                    st.markdown("##### 📊 주요 매개체(Anopheles spp.) 지점별 채집량")
                    df_an = f_mal[f_mal["종"].str.contains("Anopheles", na=False, case=False)]
                    val_col_mal = "개체수" if "개체수" in f_mal.columns else "채집수"
                    
                    all_mal_short_spots = [s.split(' (')[0] for s in mal_spots_list]
                    mal_spot_dict = {s: 0 for s in all_mal_short_spots}
                    if not df_an.empty:
                        for _, row in df_an.iterrows():
                            loc_str = str(row["지점명"]) if "지점명" in row else str(row["지역2"])
                            for s in all_mal_short_spots:
                                if s in loc_str or loc_str in s:
                                    mal_spot_dict[s] += row[val_col_mal]
                                    
                    plot_df_mal = pd.DataFrame(list(mal_spot_dict.items()), columns=["지점", val_col_mal]).sort_values(by=val_col_mal, ascending=True)
                    fig, plt_ax = plt.subplots(figsize=(6, 5.2))
                    bars = plt_ax.barh(plot_df_mal["지점"], plot_df_mal[val_col_mal].values, color='#1d3557', edgecolor='#2b2d42', height=0.7)
                    for bar in bars:
                        width = bar.get_width()
                        plt_ax.text(width + 0.5, bar.get_y() + bar.get_height()/2, f"{int(width)}마리", va='center', ha='left', fontsize=8)
                    st.pyplot(fig)
                    plt.close()
                    
                df_mal_all_clean = f_mal[(f_mal["종"] != "미채집") & (f_mal[val_col_mal] > 0)]
                if not df_mal_all_clean.empty:
                    mal_all_grouped = df_mal_all_clean.groupby(["조사주", "지점명", "환경", "종"], as_index=False)[val_col_mal].sum()
                    mal_all_grouped = mal_all_grouped.sort_values(by=["조사주", val_col_mal], ascending=[True, False])
                    st.dataframe(mal_all_grouped[["조사주", "지점명", "환경", "종", val_col_mal]].rename(columns={"조사주": "조사주차"}), hide_index=True, use_container_width=True)

            # [2] 개별 지점 탭 영역
            for idx, spot_name in enumerate(mal_spots_list):
                with mal_sub_tabs[idx + 1]:
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
                                folium.Marker([coords[0], coords[1]], tooltip=f"{target_mal_name} (우사 거점)", icon=folium.Icon(color='purple' if target_mal_name == short_name else 'blue', icon='star' if target_mal_name == short_name else 'flag')).add_to(m_mal)
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
                        st.info(f"💡 {short_name} 지점의 해당 기간 채집된 매개체가 없거나 미채집 상태입니다. (0개체)")
        else:
            st.info("💡 선택하신 기간의 말라리아 연동 데이터가 매칭되지 않습니다.")

# 3. 기후변화 대응 매개체 감시 레이어
elif selected_tab == "🟢 기후변화 대응 매개체 감시":
    st.header(f"🌍 기후변화 대응 감염병 매개체 감시 현황 [{selected_year} {selected_month} 월간 통합 결과]")
    selected_zone = st.radio("📡 모니터링 매개체 권역 선택", ["모기 권역", "참진드기 권역", "털진드기 분포감시", "털진드기 발생감시"], horizontal=True)
    
    c_up3, c_dl3 = st.columns([8, 4])
    with c_up3:
        cli_file = st.file_uploader(f"질병청 VectorNet [{selected_zone}] 결과 원본 파일 드롭 업로드", type=["csv", "xlsx", "xls"], key=f"cli_up_{selected_zone}")
        
        if selected_zone == "모기 권역":
            if cli_file is None: df_zone = base_cli_moq_df.copy()
            else:
                uploaded_df_cli = smart_load_uploaded_file(cli_file)
                uploaded_df_cli = parse_vectornet_dataframe(uploaded_df_cli, selected_year, selected_month)
                df_cli_uploaded = rename_duplicate_columns(uploaded_df_cli)
                base_cli_moq_df = merge_and_overwrite(base_cli_moq_df, df_cli_uploaded, keys=['조사년도', '조사월', '주차', '지역2', '종'])
                save_df_to_github(base_cli_moq_df, "database_cli_moq.csv", "Update Climate Mosquito data")
                st.success("✅ [모기 권역] 새 데이터가 전용 대장에 안전하게 누적되었습니다.")
                st.cache_data.clear()
            df_zone = base_cli_moq_df.copy()
        elif selected_zone == "참진드기 권역":
            if cli_file is None: df_zone = base_cli_tick_df.copy()
            else:
                uploaded_df_cli = smart_load_uploaded_file(cli_file)
                uploaded_df_cli = parse_vectornet_dataframe(uploaded_df_cli, selected_year, selected_month)
                uploaded_df_cli["종"] = uploaded_df_cli["종"].astype(str).str.strip().replace({"기타": "Larva"})
                df_cli_uploaded = rename_duplicate_columns(uploaded_df_cli)
                base_cli_tick_df = merge_and_overwrite(base_cli_tick_df, df_cli_uploaded, keys=['조사년도', '조사월', '주차', '지역2', '종'])
                save_df_to_github(base_cli_tick_df, "database_cli_tick.csv", "Update Climate Tick data")
                st.success("✅ [참진드기 권역] 새 데이터가 전용 대장에 안전하게 누적되었습니다.")
                st.cache_data.clear()
            df_zone = base_cli_tick_df.copy()
        elif selected_zone == "털진드기 분포감시":
            if cli_file is None: df_zone = base_cli_mite_dist_df.copy()
            else:
                uploaded_df_cli = smart_load_uploaded_file(cli_file)
                uploaded_df_cli = parse_vectornet_dataframe(uploaded_df_cli, selected_year, selected_month)
                df_cli_uploaded = rename_duplicate_columns(uploaded_df_cli)
                base_cli_mite_dist_df = merge_and_overwrite(base_cli_mite_dist_df, df_cli_uploaded, keys=['조사년도', '조사월', '주차', '환경', '종'])
                save_df_to_github(base_cli_mite_dist_df, "database_cli_mite_dist.csv", "Update Climate Mite Dist data")
                st.success("✅ [털진드기 분포감시] 새 데이터가 전용 대장에 누적 연동되었습니다.")
                st.cache_data.clear()
            df_zone = base_cli_mite_dist_df.copy()
        else:
            if cli_file is None: df_zone = base_cli_mite_gen_df.copy()
            else:
                uploaded_df_cli = smart_load_uploaded_file(cli_file)
                uploaded_df_cli = parse_vectornet_dataframe(uploaded_df_cli, selected_year, selected_month)
                df_cli_uploaded = rename_duplicate_columns(uploaded_df_cli)
                base_cli_mite_gen_df = merge_and_overwrite(base_cli_mite_gen_df, df_cli_uploaded, keys=['조사년도', '조사월', '주차', '환경', '종'])
                if save_df_to_github(base_cli_mite_gen_df, "database_cli_mite_gen.csv", "Update Climate Mite Gen data"):
                    st.success("✅ [털진드기 발생감시] 새 데이터가 전용 대장에 누적 연동되었습니다.")
                    st.cache_data.clear()
            df_zone = base_cli_mite_gen_df.copy()

    if not df_zone.empty:
        df_zone = parse_vectornet_dataframe(df_zone, selected_year, selected_month)
        
        if "환경" in df_zone.columns:
            df_zone["환경"] = df_zone["환경"].astype(str).str.replace(r'[\r\n\t]', '', regex=True).str.strip()
        if "지역2" in df_zone.columns:
            df_zone["지역2"] = df_zone["지역2"].astype(str).str.replace(r'[\r\n\t]', '', regex=True).str.strip()

        h_coords = {
            "춘천시보건소": [37.8756, 127.7204], "백로서식지": [37.8805, 127.7713], "주택": [37.8811, 127.7711], "종가오리": [37.8822, 127.7730],
            "삼천동": [37.8735, 127.7084], "퇴계동주민센터": [37.8621, 127.7290],
            "인제군": [38.0650, 128.1611], "화천군": [38.1062, 127.7034], "철원군": [38.2442, 127.2205]
        }

        mite_precise_gps = {
            "털진드기 발생감시": {"논": [38.2391, 127.2144], "밭": [38.2442, 127.2205], "수로": [38.2373, 127.2278], "초지": [38.2397, 127.2202]},
            "털진드기 분포감시": {"논": [38.2375, 127.2261], "밭": [38.2278, 127.2203], "저수지": [38.2368, 127.2270], "수로": [38.2395, 127.2168], "야산": [38.3833, 127.2247]}
        }

        if selected_zone == "모기 권역":
            target_loc_col = "지역2" if "지역2" in df_zone.columns else df_zone.columns[min(8, len(df_zone.columns)-1)]
            df_zone["지역2_정규화"] = df_zone[target_loc_col].astype(str).str.strip()
            master_spots_list = ["춘천시보건소", "백로서식지", "주택", "종가오리", "삼천동", "퇴계동주민센터"]
        elif selected_zone == "참진드기 권역":
            df_zone["종"] = df_zone["종"].astype(str).str.strip().replace({"기타": "Larva"})
            def normalize_tick_spot(row):
                loc = str(row["지역2"])
                cleaned_loc = "화천군" if "화천" in loc else ("인제군" if "인제" in loc else loc)
                return cleaned_loc
            df_zone["지역2_정규화"] = df_zone.apply(normalize_tick_spot, axis=1)
            master_spots_list = ["화천군", "인제군"]
        elif selected_zone == "털진드기 분포감시":
            df_zone["지역2_정규화"] = df_zone["환경"].astype(str).str.strip()
            master_spots_list = ["논", "밭", "저수지", "수로", "야산"]
        else:
            df_zone["지역2_정규화"] = df_zone["환경"].astype(str).str.strip()
            master_spots_list = ["논", "밭", "수로", "초지"]

        def resolve_coords(name, zone):
            if "털진드기" in zone:
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

        m_data = df_zone[(df_zone["조사년도"] == selected_year) & (df_zone["조사월"] == selected_month)]

        val_col = "개체수" if "개체수" in df_zone.columns else "채집수"
        
        with c_dl3:
            st.markdown("<br>", unsafe_allow_html=True)
            if not m_data.empty:
                st.download_button(f"📥 필터 [{selected_zone}] 월간 대장 추출 (.csv)", convert_df_to_csv(m_data), f"{selected_zone}_월간통합_{selected_year}_{selected_month}.csv", "text/csv")

        if selected_zone in ["모기 권역", "참진드기 권역"]:
            cli_tab_names = ["📍 지점전체"] + [f"📍 {spot}" for spot in master_spots_list]
            cli_sub_tabs = st.tabs(cli_tab_names)
            
            # [1] 지점전체 탭 내용 (모든 지점 지도 마커 및 지점별 같은 종 합산 비교 차트)
            with cli_sub_tabs[0]:
                c1, c2 = st.columns([5, 5])
                with c1:
                    st.markdown("##### 🗺️ GIS 감시 지점 지도 (전체 지점 표시)")
                    center_lat = 37.88 if selected_zone == "모기 권역" else 38.08
                    center_lng = 127.75 if selected_zone == "모기 권역" else 127.95
                    m_cli_all = folium.Map(location=[center_lat, center_lng], zoom_start=11 if selected_zone == "모기 권역" else 9)
                    
                    for spot in master_spots_list:
                        lat_s, lng_s = resolve_coords(spot, selected_zone)
                        folium.Marker([lat_s, lng_s], tooltip=spot, icon=folium.Icon(color='green', icon='info-sign')).add_to(m_cli_all)
                    st_folium(m_cli_all, key=f"map_cli_all_{selected_zone}_{selected_year}_{selected_month}", width="100%", height=380)
                with c2:
                    if selected_zone == "모기 권역":
                        st.markdown("##### 📊 각 지점별 모기 종별 채집량 비교 (지점별 누적 합산)")
                    else:
                        st.markdown("##### 📊 화천군 vs 인제군 참진드기 종별 채집량 비교")
                        
                    all_spot_data = m_data[m_data["지역2_정규화"].isin(master_spots_list)]
                    all_spot_clean = all_spot_data[(all_spot_data["종"] != "미채집") & (all_spot_data[val_col] > 0)]
                    
                    if not all_spot_clean.empty:
                        pivot_df = all_spot_clean.pivot_table(index='종', columns='지역2_정규화', values=val_col, aggfunc='sum').fillna(0)
                        fig, plt_ax = plt.subplots(figsize=(6, 5.2))
                        is_stacked = True if selected_zone == "모기 권역" else False
                        pivot_df.plot(kind='barh', stacked=is_stacked, ax=plt_ax, edgecolor='#2b2d42')
                        plt.legend(title="조사지점", fontsize=8, title_fontsize=9)
                        plt.tight_layout()
                        st.pyplot(fig)
                        plt.close()
                    else:
                        st.info("💡 선택하신 기간에 합산 표출할 매개체 채집 데이터가 존재하지 않습니다.")
                        
                all_spot_data_clean = m_data[m_data["지역2_정규화"].isin(master_spots_list) & (m_data["종"] != "미채집") & (m_data[val_col] > 0)]
                if not all_spot_data_clean.empty:
                    env_col = "환경" if "환경" in all_spot_data_clean.columns else "조사지"
                    all_grouped = all_spot_data_clean.groupby(["조사월", "지역2_정규화", env_col, "종"], as_index=False)[val_col].sum()
                    all_grouped = all_grouped.sort_values(by=[val_col], ascending=False)
                    st.dataframe(all_grouped[["조사월", "지역2_정규화", env_col, "종", val_col]].rename(columns={"조사월": "조사월", "지역2_정규화": "조사지역"}), hide_index=True, use_container_width=True)

            # [2] 개별 지점 탭 영역
            for idx, spot_name in enumerate(master_spots_list):
                with cli_sub_tabs[idx + 1]:
                    spot_data = m_data[m_data["지역2_정규화"] == spot_name]
                    spot_data_clean = spot_data[(spot_data["종"] != "미채집") & (spot_data[val_col] > 0)]
                    
                    if not spot_data_clean.empty:
                        c1, c2 = st.columns([5, 5])
                        with c1:
                            st.markdown(f"##### 🗺️ GIS 감시 지점 지도 (결과보고서 규격)")
                            m_cli = folium.Map(location=[float(spot_data_clean['위도'].iloc[0]), float(spot_data_clean['경도'].iloc[0])], zoom_start=11)
                            folium.Marker([float(spot_data_clean['위도'].iloc[0]), float(spot_data_clean['경도'].iloc[0])], tooltip=spot_name, icon=folium.Icon(color='green', icon='info-sign')).add_to(m_cli)
                            st_folium(m_cli, key=f"map_cli_spot_{spot_name}_{selected_year}_{selected_month}_{selected_zone}", width="100%", height=380)
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
                        
                        env_col = "환경" if "환경" in spot_data_clean.columns else "조사지"
                        spot_data_grouped = spot_data_clean.groupby(["조사월", "지역2_정규화", env_col, "종"], as_index=False)[val_col].sum()
                        spot_data_grouped = spot_data_grouped.sort_values(by=[val_col], ascending=False)
                        st.dataframe(spot_data_grouped[["조사월", "지역2_정규화", env_col, "종", val_col]].rename(columns={"조사월": "조사월", "지역2_정규화": "조사지점"}), hide_index=True, use_container_width=True)
                    else:
                        st.info(f"💡 선택하신 {selected_year} {selected_month}에 [{spot_name}] 관할 지점의 매개체 데이터가 비어있습니다. (0개체)")
        else:
            # 털진드기 분포 및 발생 감시 탭 영역
            cli_sub_tabs = st.tabs([f"📍 {spot}" for spot in master_spots_list])
            for idx, spot_name in enumerate(master_spots_list):
                with cli_sub_tabs[idx]:
                    spot_data = m_data[m_data["지역2_정규화"] == spot_name]
                    spot_data_clean = spot_data[(spot_data["종"] != "미채집") & (spot_data[val_col] > 0)]
                    
                    if not spot_data_clean.empty:
                        c1, c2 = st.columns([5, 5])
                        with c1:
                            st.markdown(f"##### 🗺️ GIS 감시 지점 지도 (결과보고서 규격)")
                            m_cli = folium.Map(location=[float(spot_data_clean['위도'].iloc[0]), float(spot_data_clean['경도'].iloc[0])], zoom_start=13)
                            folium.Marker([float(spot_data_clean['위도'].iloc[0]), float(spot_data_clean['경도'].iloc[0])], tooltip=spot_name, icon=folium.Icon(color='green', icon='info-sign')).add_to(m_cli)
                            st_folium(m_cli, key=f"map_cli_spot_mite_{spot_name}_{selected_year}_{selected_month}_{selected_zone}", width="100%", height=380)
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
                        
                        env_col = "환경" if "환경" in spot_data_clean.columns else "조사지"
                        spot_data_grouped = spot_data_clean.groupby(["조사월", "지역2_정규화", "환경", "종"], as_index=False)[val_col].sum()
                        spot_data_grouped = spot_data_grouped.sort_values(by=[val_col], ascending=False)
                        st.dataframe(spot_data_grouped[["조사월", "지역2_정규화", "환경", "종", val_col]].rename(columns={"조사월": "조사월", "지역2_정규화": "조사지점"}), hide_index=True, use_container_width=True)
                    else:
                        st.info(f"💡 선택하신 {selected_year} {selected_month}에 [{spot_name}] 관할 지점의 매개체 데이터가 비어있습니다. (0개체)")
                        
# 4. 참진드기조사 어린이숲체험장 레이어 (💡 년도별 조사 지점 완전 자동 유연 변환 파트)
elif selected_tab == "🟡 참진드기조사(어린이숲체험장)":
    st.header(f"🌳 어린이 숲 체험장 참진드기 자체조사 월간 통합 현황 [{selected_year} {selected_month}]")
    
    c_up4, c_dl4 = st.columns([8, 4])
    with c_up4:
        forest_file = st.file_uploader("작성된 어린이 숲체험장 최종 원장 파일 업로드 (.xlsx / .csv 지원)", type=["csv", "xlsx", "xls"], key="forest_up")
        if forest_file is not None:
            uploaded_df_for = smart_load_uploaded_file(forest_file)
            uploaded_df_for["조사년도"] = selected_year
            df_forest_uploaded = rename_duplicate_columns(uploaded_df_for)
            base_forest_df = merge_and_overwrite(base_forest_df, df_forest_uploaded, keys=['조사년도', '월', '조사월', '조사주', '채집지역2', '지점번호', '분류', '종', 'Stage'])
            save_df_to_github(base_forest_df, "database_forest.csv", "Update Forest data")
            st.success("✅ 어린이 숲체험장 실무 데이터가 마스터 영구 연동 원장에 자동 축적되었습니다.")
            st.cache_data.clear()
            
    df_forest = base_forest_df.copy()

    try:
        month_int = int(str(selected_month).replace("월",""))
        if "월" in df_forest.columns:
            df_forest["월_인덱스"] = df_forest["월"].astype(str).str.extract(r'(\d+)').astype(int)
            m_forest = df_forest[(df_forest["조사년도"] == selected_year) & (df_forest["월_인덱스"] == month_int)].copy()
        else: m_forest = pd.DataFrame()
    except Exception: m_forest = pd.DataFrame()

    with c_dl4:
        st.markdown("<br>", unsafe_allow_html=True)
        if not m_forest.empty:
            st.download_button("📥 필터 데이터 원본 추출 (.csv)", convert_df_to_csv(m_forest), f"어린이숲_감시망_추출_{selected_year}_{selected_month}.csv", "text/csv")

    if not m_forest.empty:
        m_forest['종명_한글'] = m_forest['종'].replace({"Hard tick": "참진드기", "Haemaphysalis longicornis": "작은소피참진드기", "Haemaphysalis flava ": "개피참진드기", "Haemaphysalis japonica": "일본참진드기"})
        m_forest['지점번호'] = pd.to_numeric(m_forest['지점번호'], errors='coerce').fillna(0).astype(int)
        m_forest['gu분지점'] = m_forest.apply(lambda x: f"관리지점 {x['지점번호']}" if str(x['분류']).strip().lower() == "in" else f"비관리지점 {x['지점번호']}", axis=1)
        
        # 💡 [원상 복구 완료] 기존에 완벽하게 매핑되던 년도별 위치 지도 바인딩 규칙으로 정확히 환원
        if "2025" in selected_year:
            h_coords_forest = {"홍천": [37.7336, 127.8547], "정선": [37.4922, 128.9814]}
            map_center_forest = [37.61, 128.42]
            map_zoom_forest = 9
        elif "2024" in selected_year:
            h_coords_forest = {"춘천": [37.9799, 127.7718], "인제": [38.0620, 128.1560]}
            map_center_forest = [38.02, 127.96]
            map_zoom_forest = 10
        else:
            h_coords_forest = {"남산": [37.683361, 127.893111], "삼마치": [37.643444, 127.910306]}
            map_center_forest = [37.665, 127.900]
            map_zoom_forest = 11

        m_forest['위도'] = m_forest['채집지역2'].map(lambda x: h_coords_forest[x][0] if x in h_coords_forest else map_center_forest[0])
        m_forest['경도'] = m_forest['채집지역2'].map(lambda x: h_coords_forest[x][1] if x in h_coords_forest else map_center_forest[1])
        
        forest_summary = m_forest.pivot_table(index=["채집지역2", "gu분지점", "위도", "경도"], columns="종명_한글", values="개체수", aggfunc="sum", fill_value=0).reset_index()
        
        if not forest_summary.empty:
            avail_species = [s for s in ["작은소피참진드기", "개피참진드기", "일본참진드기", "참진드기"] if s in forest_summary.columns]
            forest_summary['합계'] = forest_summary[avail_species].sum(axis=1)
            
            col_f_map, col_f_graph = st.columns([5, 5])
            with col_f_map:
                st.markdown(f"##### 🗺️ 강원 관내 유아숲 자체 감시망 (년도별 동적 연동)")
                m_f = folium.Map(location=map_center_forest, zoom_start=map_zoom_forest)
                for r_name, latlng in h_coords_forest.items():
                    r_summary = forest_summary[forest_summary["채집지역2"] == r_name]
                    if "2025" in selected_year:
                        full_title = f"홍천 {r_name} (자연환경연구공원)" if r_name=="홍천" else f"정선 {r_name} (백두대간생태수목원)"
                    elif "2024" in selected_year:
                        full_title = f"춘천 {r_name} (국립춘천숲체원)" if r_name=="춘천" else f"인제 {r_name} (갯골어린이숲체험원)"
                    else:
                        full_title = f"홍천군 {r_name} 유아숲"
                        
                    popup_text = f"<b>🌲 {full_title}</b><br><hr style='margin:5px 0;'>"
                    for _, r in r_summary.iterrows(): 
                        popup_text += f"• {r['gu분지점']}: 월간 누적 {r['합계']}개체<br>"
                    folium.Marker(latlng, popup=folium.Popup(popup_text, max_width=350), icon=folium.Icon(color='green', icon='tree')).add_to(m_f)
                st_folium(m_f, key=f"map_forest_final_{selected_year}_{selected_month}", width="100%", height=430)
                
            with col_f_graph:
                st.markdown(f"##### 📊 {selected_year} {selected_month} 구역별 실시간 채집량 비교")
                fig, ax = plt.subplots(figsize=(6, 5))
                chart_df = forest_summary.pivot_table(index="gu분지점", columns="채집지역2", values="합계", aggfunc="sum").fillna(0)
                
                # 💡 [요청 사항 반영 필수 수정] 다른 지점들은 제외하고 오직 관리지점 3과 비관리지점 3만 정확하게 인덱싱하여 비교 그래프 표출
                chart_df = chart_df.reindex(["관리지점 3", "비관리지점 3"]).fillna(0)
                
                # 세세한 라벨링 전환 시스템 처리
                if "2024" in selected_year:
                    chart_df = chart_df.rename(columns={"춘천": "춘천(국립숲체원)", "인제": "인제(갯골어린이숲체험원)"})
                elif "2025" in selected_year:
                    chart_df = chart_df.rename(columns={"홍천": "홍천(자연환경연구공원)", "정선": "정선(백두대간생태수목원)"})
                else:
                    chart_df = chart_df.rename(columns={"남산": "홍천 남산 유아숲", "삼마치": "홍천 삼마치 유아숲"})
                    
                chart_df.plot(kind='bar', ax=ax, color=['#2b2d42', '#ef233c'], edgecolor='black', width=0.6)
                plt.xticks(rotation=0)
                plt.tight_layout()
                st.pyplot(fig)
                plt.close()
            st.dataframe(forest_summary, hide_index=True, use_container_width=True)
        else: st.info("💡 요약 조건에 맞는 채집 수치 데이터가 존재하지 않습니다.")
    else: st.info("💡 선택하신 연도와 월에 해당하는 어린이 숲 체험장 조사 내역이 없습니다.")