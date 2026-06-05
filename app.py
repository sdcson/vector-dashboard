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

# 페이지 설정 (가장 상단에 위치 필수)
st.set_page_config(page_title="강원특별자치도 매개체 감시 시스템", layout="wide")

# -----------------------------------------------------------------
# [💡 영구 차트 한글 깨짐 방지: 구글 나눔고딕 커널 엔진 강제 주입형 로더]
# -----------------------------------------------------------------
@st.cache_resource
def init_korean_font_and_get_prop():
    """
    스트림릿 클라우드 리눅스 환경에서 한글이 네모(□)로 파괴되는 버그를 영구 치료합니다.
    방화벽에 안전한 구글 공식 레포지토리에서 나눔고딕을 내려받아 Matplotlib 커널에 직접 등록합니다.
    """
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

# 전역 한글 글꼴 원천 주입기 기동
f_prop = init_korean_font_and_get_prop()

st.title("🔬 감염병 매개체 감시사업 통합 데이터 대시보드")
st.markdown("질병조사과 주요 감시사업별 맞춤형 시간 필터 및 표준 전용 업로드 양식을 제공하는 마스터 시스템입니다.")

# -----------------------------------------------------------------
# [중복 컬럼명을 안전하게 변환해 주는 방어 로직]
# -----------------------------------------------------------------
def rename_duplicate_columns(df):
    """업로드된 파일이나 DB 내부에서 동일한 컬럼명이 발견되면 숫자를 붙여 강제로 고유화함"""
    if df is None or df.empty:
        return df
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique():
        cols[cols == dup] = [f"{dup}.{i}" if i != 0 else dup for i in range(cols[cols == dup].shape[0])]
    df.columns = cols
    return df

def convert_df_to_csv(df):
    """라이브러리 없이 내장 기능만으로 한글 깨짐 없는 CSV 바이너리 변환 (UTF-8-SIG 사용)"""
    return df.to_csv(index=False).encode('utf-8-sig')


def smart_load_uploaded_file(uploaded_file):
    """표준 단일 파서 (기후변화, 어린이숲 공백 트림 및 중복 컬럼 전처리 복원)"""
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
# [일본뇌염예측사업 VectorNet 양식 마스터 세션 백업본]
# -----------------------------------------------------------------
@st.cache_data
def get_je_actual_style_data():
    data = []
    je_spots_map = {
        "춘천시 산천리": [37.9250, 127.7410],
        "강릉시 산대월리": [37.7518, 128.8762],
        "횡성군 하대리": [37.4912, 127.9845]
    }
    je_species_list = [
        "Culex tritaeniorhynchus", "Aedes vexans", "Culex pipiens", "Anopheles spp.", 
        "Armigeres subalbatus", "Ochlerotatus koreicus", "Culex vagans", "Culex orientalis", 
        "Mansonia uniformis", "Aedes albopictus", "Culex bitaeniorhynchus", "Ochlerotatus nipponicus", "Coquillettidia ochracea"
    ]
    
    for year in ["2026년", "2025년", "2024년", "2023년"]:
        for month_num in range(4, 11):
            month_str = f"{month_num:02d}월"
            for week_num in range(1, 5):
                np.random.seed(month_num * 25 + week_num)
                for loc2, coords in je_spots_map.items():
                    is_summer = month_str in ["07월", "08월", "09월"]
                    for idx_sp, sp in enumerate(je_species_list):
                        if sp == "Culex tritaeniorhynchus": cnt = int(np.random.poisson(22 if is_summer else 0))
                        elif sp in ["Aedes vexans", "Culex pipiens"]: cnt = int(np.random.poisson(140 if is_summer else 15))
                        else: cnt = int(np.random.poisson(3 if is_summer else 0))
                        if cnt > 0 or sp == "Culex tritaeniorhynchus":
                            data.append({
                                "조사년도": year, "조사월": month_str, "월": month_num, "주차": week_num,
                                "사업명": "일본뇌염예측", "권역": "강원도보건환경연구원", "지역2": loc2, "환경": "축사", "방법": "LED1",
                                "위도": coords[0], "경도": coords[1], "종": sp, "개체수": cnt
                            })
    return pd.DataFrame(data)

@st.cache_data
def get_malaria_actual_style_data():
    data = []
    mal_spots_map = {
        "춘천시 중앙로": [37.8813, 127.7298], "춘천시 지내리": [37.9250, 127.7410],
        "철원군 대마리": [38.2543, 127.2145], "철원군 학사리": [38.2520, 127.4415],
        "화천군": [38.1060, 127.7035], "양구군": [38.1055, 127.9880],
        "인제군": [38.0645, 128.1695], "고성군": [38.3795, 128.4680]
    }
    mal_species_list = [
        "Anopheles spp.", "Aedes vexans", "Culex pipiens", "Aedes albopictus", 
        "Aedes dorsalis", "Ochlerotatus koreicus", "Aedes togoi", "Armigeres subalbatus", 
        "Culex bitaeniorhynchus", "Culex orientalis", "Culex tritaeniorhynchus", "Culex vagans", "Mansonia uniformis", "미동정"
    ]
    
    for year in ["2026년", "2025년", "2024년"]:
        for month_num in range(4, 11):
            month_str = f"{month_num:02d}월"
            for week_num in range(1, 5):
                np.random.seed(month_num * 15 + week_num + 3)
                for loc2, coords in mal_spots_map.items():
                    is_summer = month_str in ["06월", "07월", "08월", "09월"]
                    for sp in mal_species_list:
                        if sp == "Anopheles spp.": cnt = int(np.random.poisson(80 if is_summer else 5))
                        elif sp in ["Culex pipiens", "Aedes vexans"]: cnt = int(np.random.poisson(40 if is_summer else 8))
                        else: cnt = int(np.random.poisson(2 if is_summer else 0))
                        if cnt > 0 or sp == "Anopheles spp.":
                            data.append({
                                "조사년도": year, "조사월": month_str, "월": month_num, "주차": week_num,
                                "사업명": "말라리아매개모기", "권역": "접경지역거점", "지역2": loc2, "환경": "우사", "방법": "유문등",
                                "위도": coords[0], "경도": coords[1], "종": sp, "개체수": cnt
                            })
    return pd.DataFrame(data)

@st.cache_data
def get_climate_data():
    data = []
    for year in ["2026년", "2025년"]:
        np.random.seed(42)
        chuncheon_mosquito_locs = {
            "춘천시보건소": [37.8756, 127.7204, "도심"], "백로서식지": [37.8805, 127.7713, "철새도래지"],
            "주택": [37.8811, 127.7711, "도심"], "종가오리": [37.8822, 127.7730, "철새도래지"]
        }
        inje_hwacheon_locs = {"인제군": [38.0650, 128.1611], "화천군": [38.1062, 127.7034]}
        for month_num in range(4, 11):
            month_str = f"{month_num:02d}월"
            for week_num in range(1, 5):
                for loc2, coords in chuncheon_mosquito_locs.items():
                    data.append({"조사년도": year, "조사월": month_str, "월": month_num, "주차": week_num, "권역": "모기 권역", "지역2": loc2, "환경": coords[2], "위도": coords[0], "경도": coords[1], "종": "Culex pipiens", "개체수": int(np.random.poisson(20))})
                    data.append({"조사년도": year, "조사월": month_str, "월": month_num, "주차": week_num, "권역": "모기 권역", "지역2": loc2, "환경": coords[2], "위도": coords[0], "경도": coords[1], "종": "Aedes vexans", "개체수": int(np.random.poisson(5))})
                for loc2, coords in inje_hwacheon_locs.items():
                    for env in ["초지", "잡목림", "산길", "무덤"]:
                        lat_offset = 0.0002 * ["초지", "잡목림", "산길", "무덤"].index(env)
                        data.append({"조사년도": year, "조사월": month_str, "월": month_num, "주차": week_num, "권역": "참진드기 권역", "지역2": loc2, "환경": env, "위도": coords[0]+lat_offset, "경도": coords[1], "종": "Haemaphysalis longicornis", "개체수": int(np.random.poisson(15))})
                for env in ["논", "밭", "저수지", "수로", "야산"]:
                    data.append({"조사년도": year, "조사월": month_str, "월": month_num, "주차": week_num, "권역": "털진드기 분포감시", "지역2": "철원군", "환경": env, "위도": 38.244278, "경도": 127.220583, "종": "mite(털진드기)", "개체수": int(np.random.poisson(35))})
                for env in ["논", "밭", "수로", "초지"]:
                    data.append({"조사년도": year, "조사월": month_str, "월": month_num, "주차": week_num, "권역": "털진드기 발생감시", "지역2": "철원군", "환경": env, "위도": 38.239167, "경도": 127.220000, "종": "mite(털진드기)", "개체수": int(np.random.poisson(40))})
    return pd.DataFrame(data)

@st.cache_data
def get_forest_playground_actual_data():
    data = []
    idx = 1
    species_map = ["Haemaphysalis longicornis", "Haemaphysalis flava ", "Haemaphysalis japonica"]
    stages = ["Female", "Male", "Nymph", "Larvae"]
    for year in ["2026년", "2025년"]:
        for month_int in range(4, 11): 
            month_str = f"{month_int:02d}월"
            for week in ["1주", "2주", "3주", "4주"]:
                np.random.seed(month_int * 15 + len(week))
                for region in ["남산", "삼마치"]:
                    course = 1 if region == "남산" else 2
                    for spot_num in range(1, 4): 
                        for classification in ["In", "Out"]:
                            for sp in species_map:
                                for stg in stages:
                                    cnt = int(np.random.poisson(25 if stg=="Larvae" and month_int in [8,9] else 3))
                                    if cnt > 0:
                                        data.append({
                                            "연번": idx, "조사년도": year, "월": month_int, "조사월": month_str, "조사주": week,
                                            "채집일": f"2026-{month_int:02d}-12", "채집지역2": region, "코스번호": course,
                                            "지점번호": spot_num, "분류": classification, "종": sp, "Stage": stg, "개체수": cnt,
                                            "Pool No.": 1, "리케치아 양성 Pools": 0, "라임 양성 pool": 0, "아나플라즈마 양성": 0,
                                            "Ehlichia": 0, "POWV": 0, "HRTV": 0, "Babesia": 0, "동시감염": 0, "SFTS_유전자검사": "음성"
                                        })
                                        idx += 1
    return pd.DataFrame(data)

# 💡 [NameError 완전 박멸 트랙]: 4대 마스터 DB 캐싱 변수 선언부를 조건문 가동 한참 전인 최상단으로 안전 긴급 견인!! ⭐️
base_je_df = rename_duplicate_columns(get_je_actual_style_data())
base_mal_df = rename_duplicate_columns(get_malaria_actual_style_data())
base_cli_df = rename_duplicate_columns(get_climate_data())
base_forest_df = rename_duplicate_columns(get_forest_playground_actual_data())

# -----------------------------------------------------------------
# [사이드바 공통 시간 필터 영역]
# -----------------------------------------------------------------
st.sidebar.markdown("### 📅 공통 시간 필터")
selected_year = st.sidebar.selectbox("조사년도 선택", ["2026년", "2025년", "2024년", "2023년", "2022년"])
selected_month = st.sidebar.selectbox("조사월 선택", ["05월", "04월", "06월", "07월", "08월", "09월", "10월", "11월", "12월"])

if "current_tab" not in st.session_state: st.session_state.current_tab = "🔴 일본뇌염 매개모기 감시"
if st.session_state.current_tab in ["🔴 일본뇌염 매개모기 감시", "🔵 말라리아 매개모기 감시"]:
    selected_week = st.sidebar.selectbox("조사주 선택 (주별 감시 전용)", ["1주", "2주", "3주", "4주"])
else:
    st.sidebar.info("💡 선택하신 사업은 '월별 통합 데이터 제공 포맷'으로 가동되어 주차 필터가 자동으로 마스킹됩니다.")
    selected_week = "전체"

tabs = ["🔴 일본뇌염 매개모기 감시", "🔵 말라리아 매개모기 감시", "🟢 기후변화 대응 매개체 감시", "🟡 참진드기조사(어린이숲체험장)"]
selected_tab = st.radio("📡 감시사업 카테고리 탭 선택", tabs, horizontal=True)
st.session_state.current_tab = selected_tab

st.markdown("---")

# --- 1. 일본뇌염 매개모기 감시 ---
if selected_tab == "🔴 일본뇌염 매개모기 감시":
    st.header(f"🏠 우사 거점 일본뇌염 매개모기 주별 감시 현황 [{selected_year} {selected_month} {selected_week}]")
    with st.expander("📥 [일본뇌염 예측사업] 질병청 VectorNet 표준 서식 파일 업로드 및 양식"):
        vn_je_cols = ["번호", "사업명", "권역", "연도", "월", "주차", "수거일", "지역1", "지역2", "환경", "방법", "종", "개체수", "채집기간", "Index", "실험개체수", "Pool No.", "양성 Pools", "비고"]
        vn_je_tmpl = pd.DataFrame(columns=vn_je_cols)
        vn_je_tmpl.loc[0] = [1, "일본뇌염예측", "강원도보건환경연구원", 2025, 5, 22, "2025-05-26", "강원", "횡성군 하대리", "축사", "LED1", "Culex tritaeniorhynchus", 12, 1, 12, 12, 1, 0, "-"]
        st.download_button("📥 [일본뇌염] VectorNet 오리지널 서식양식 다운로드 (.csv)", convert_df_to_csv(vn_je_tmpl), "VectorNet_일본뇌염_양식.csv", "text/csv")
        je_file = st.file_uploader("질병청 VectorNet 일본뇌염 예측 결과 파일 업로드 (.xlsx / .csv)", type=["csv", "xlsx", "xls"], key="je_up")
        df_je = base_je_df if je_file is None else rename_duplicate_columns(smart_load_uploaded_file(je_file))

    if not df_je.empty:
        if "연도" in df_je.columns: df_je["조사년도"] = df_je["연도"].astype(str).str.extract(r'(\d+)')[0].map(lambda x: f"{x}년" if pd.notna(x) else selected_year)
        else: df_je["조사년도"] = selected_year
        if "월" in df_je.columns: df_je["조사월"] = df_je["월"].astype(str).str.extract(r'(\d+)')[0].map(lambda x: f"{int(x):02d}월" if pd.notna(x) else selected_month)
        else: df_je["조사월"] = selected_month
        df_je["조사주"] = selected_week
        
        je_coords_map = {"횡성군 하대리": [37.4912, 127.9845], "강릉시 산대월리": [37.7518, 128.8762], "춘천시 산천리": [37.9250, 127.7410]}
        if "지역2" in df_je.columns:
            df_je["지역2_정규화"] = df_je["지역2"].astype(str).str.strip()
            df_je["위도"] = df_je["지역2_정규화"].map(lambda x: je_coords_map[x][0] if x in je_coords_map else (37.9250 if "춘천" in x else (37.7518 if "강릉" in x else 37.4912)))
            df_je["경도"] = df_je["지역2_정규화"].map(lambda x: je_coords_map[x][1] if x in je_coords_map else (127.7410 if "춘천" in x else (128.8762 if "강릉" in x else 127.9845)))
            df_je["지점명"] = df_je["지역2_정규화"].map(lambda x: "춘천시 산천리 (우사 거점)" if "춘천" in x else ("강릉시 산대월리 (우사 거점)" if "강릉" in x else "횡성군 하대리 (우사 거점)"))
        else: df_je["지점명"] = "춘천시 산천리 (우사 거점)"

    f_je = df_je[(df_je["조사년도"] == selected_year) & (df_je["조사월"] == selected_month) & (df_je["조사주"] == selected_week)]
    if not f_je.empty:
        je_spots = ["춘천시 산천리 (우사 거점)", "강릉시 산대월리 (우사 거점)", "횡성군 하대리 (우사 거점)"]
        je_sub_tabs = st.tabs([f"📍 {spot.split(' (')[0]}" for spot in je_spots])
        for idx, spot_name in enumerate(je_spots):
            with je_sub_tabs[idx]:
                spot_data = f_je[f_je["지점명"] == spot_name]
                if not spot_data.empty:
                    c1, c2 = st.columns([5, 5])
                    with c1:
                        st.markdown(f"##### 🗺️ 거점센터 매핑 및 단면")
                        m_je = folium.Map(location=[float(spot_data['위도'].iloc[0]), float(spot_data['경도'].iloc[0])], zoom_start=11)
                        folium.Marker([float(spot_data['위도'].iloc[0]), float(spot_data['경도'].iloc[0])], tooltip=spot_name, icon=folium.Icon(color='red', icon='home')).add_to(m_je)
                        st_folium(m_je, key=f"map_je_final_{idx}_{selected_month}_{selected_week}", width="100%", height=380)
                    with c2:
                        st.markdown(f"##### 📊 {spot_name.split(' (')[0]} 종별 채집량 분포 (개체수)")
                        val_col_je = "개체수" if "개체수" in spot_data.columns else "채집수"
                        sum_df = spot_data.groupby("종")[val_col_je].sum().reset_index()
                        fig, plt_ax = plt.subplots(figsize=(6, 5.2))
                        bar_colors = ['#ef233c' if str(s).strip() == "Culex tritaeniorhynchus" else '#b8c0cb' for s in sum_df["종"]]
                        bars = plt_ax.barh(sum_df["종"], sum_df[val_col_je].values, color=bar_colors, edgecolor='#2b2d42', height=0.7)
                        for bar in bars:
                            width = bar.get_width()
                            if width > 0: plt_ax.text(width + 0.5, bar.get_y() + bar.get_height()/2, f"{int(width)}마리", va='center', ha='left', fontsize=8)
                        plt_ax.invert_yaxis()
                        st.pyplot(fig)
                        plt.close()
                    st.dataframe(spot_data[["지점명", "환경", "종", val_col_je]], hide_index=True, use_container_width=True)
                else: st.info(f"💡 {spot_name} 지점의 해당 주차 데이터가 대장에 존재하지 않습니다.")
    else: st.info("💡 선택하신 기간의 일본뇌염 VectorNet 연동 데이터가 존재하지 않습니다.")

# --- 2. 말라리아 매개모기 감시 ---
elif selected_tab == "🔵 말라리아 매개모기 감시":
    st.header(f"🪖 접경지역 말라리아 매개모기 주별 감시 현황 [{selected_year} {selected_month} {selected_week}]")
    with st.expander("📥 [말라리아 예측사업] 질병청 VectorNet 표준 서식 파일 업로드 및 양식"):
        vn_mal_cols = ["번호", "사업명", "권역", "연도", "월", "주차", "수거일", "지역1", "지역2", "환경", "방법", "종", "개체수", "채집기간", "Index", "실험개체수", "Pool No.", "양성 Pools", "비고"]
        vn_mal_tmpl = pd.DataFrame(columns=vn_mal_cols)
        vn_mal_tmpl.loc[0] = [1, "말라리아매개모기", "접경지역거점", 2025, 5, 22, "2025-05-26", "강원", "철원군 대마리", "우사", "유문등", "Anopheles spp.", 45, 1, 45, 45, 1, 0, "-"]
        st.download_button("📥 [말라리아] VectorNet 오리지널 서식양식 다운로드 (.csv)", convert_df_to_csv(vn_mal_tmpl), "VectorNet_말라리아_양식.csv", "text/csv")
        mal_file = st.file_uploader("질병청 VectorNet 말라리아 결과 파일 업로드 (.xlsx / .csv)", type=["csv", "xlsx", "xls"], key="mal_up")
        # 💡 보정 통과: 이제 무조건 base_mal_df가 먼저 선언되어 있으므로 NameError가 영구 진압되었습니다!
        df_mal = base_mal_df if mal_file is None else rename_duplicate_columns(smart_load_uploaded_file(mal_file))

    if not df_mal.empty:
        if "연도" in df_mal.columns: df_mal["조사년도"] = df_mal["연도"].astype(str).str.extract(r'(\d+)')[0].map(lambda x: f"{x}년" if pd.notna(x) else selected_year)
        else: df_mal["조사년도"] = selected_year
        if "월" in df_mal.columns: df_mal["조사월"] = df_mal["월"].astype(str).str.extract(r'(\d+)')[0].map(lambda x: f"{int(x):02d}월" if pd.notna(x) else selected_month)
        else: df_mal["조사월"] = selected_month
        df_mal["조사주"] = selected_week
        
        mal_coords_map = {
            "춘천시 중앙로": [37.8813, 127.7298], "춘천시 지내리": [37.9250, 127.7410],
            "철원군 대마리": [38.2543, 127.2145], "철원군 학사리": [38.2520, 127.4415],
            "화천군": [38.1060, 127.7035], "양구군": [38.1055, 127.9880],
            "인제군": [38.0645, 128.1611], "고성군": [38.3795, 128.4680]
        }
        if "지역2" in df_mal.columns:
            df_mal["지역2_정규화"] = df_mal["지역2"].astype(str).str.strip()
            df_mal["위도"] = df_mal["지역2_정규화"].map(lambda x: mal_coords_map[x][0] if x in mal_coords_map else (38.2543 if "철원" in x else 38.0))
            df_mal["경도"] = df_mal["지역2_정규화"].map(lambda x: mal_coords_map[x][1] if x in mal_coords_map else (127.2145 if "철원" in x else 127.5))
            df_mal["지점명"] = df_mal["지역2_정규화"].map(lambda x: f"{x} (우사 거점)" if "거점" not in x else x)
        else: df_mal["지점명"] = "춘천시 중앙로 (우사 거점)"

    f_mal = df_mal[(df_mal["조사년도"] == selected_year) & (df_mal["조사월"] == selected_month) & (df_mal["조사주"] == selected_week)]
    if not f_mal.empty:
        mal_spots_list = ["춘천시 중앙로 (우사 거점)", "춘천시 지내리 (우사 거점)", "철원군 대마리 (우사 거점)", "철원군 학사리 (우사 거점)", "화천군 (우사 거점)", "양구군 (우사 거점)", "인제군 (우사 거점)", "고성군 (우사 거점)"]
        mal_sub_tabs = st.tabs([f"📍 {spot.split(' (')[0]}" for spot in mal_spots_list])
        for idx, spot_name in enumerate(mal_spots_list):
            with mal_sub_tabs[idx]:
                short_name = spot_name.split(" (")[0]
                spot_data_mal = f_mal[f_mal["지점명"].str.contains(short_name, na=False)]
                if not spot_data_mal.empty:
                    c1, c2 = st.columns([5, 5])
                    with c1:
                        st.markdown(f"##### 🗺️ 거점센터 매핑 및 단면")
                        m_mal = folium.Map(location=[float(spot_data_mal['위도'].iloc[0]), float(spot_data_mal['경도'].iloc[0])], zoom_start=11)
                        folium.Marker([float(spot_data_mal['위도'].iloc[0]), float(spot_data_mal['경도'].iloc[0])], tooltip=spot_name, icon=folium.Icon(color='blue', icon='flag')).add_to(m_mal)
                        st_folium(m_mal, key=f"map_mal_final_node_{idx}_{selected_month}_{selected_week}", width="100%", height=380)
                    with c2:
                        st.markdown(f"##### 📊 {short_name} 종별 채집량 분포 (개체수)")
                        val_col_mal = "개체수" if "개체수" in spot_data_mal.columns else "채집수"
                        sum_df_mal = spot_data_mal.groupby("종")[val_col_mal].sum().reset_index()
                        fig, plt_ax = plt.subplots(figsize=(6, 5.2))
                        bar_colors_mal = ['#1d3557' if str(s).strip() == "Anopheles spp." else '#c4cbde' for s in sum_df_mal["종"]]
                        bars = plt_ax.barh(sum_df_mal["종"], sum_df_mal[val_col_mal].values, color=bar_colors_mal, edgecolor='#2b2d42', height=0.7)
                        for bar in bars:
                            width = bar.get_width()
                            if width > 0: plt_ax.text(width + 0.5, bar.get_y() + bar.get_height()/2, f"{int(width)}마리", va='center', ha='left', fontsize=8)
                        plt_ax.invert_yaxis()
                        st.pyplot(fig)
                        plt.close()
                    st.dataframe(spot_data_mal[["지점명", "환경", "종", val_col_mal]], hide_index=True, use_container_width=True)
                else: st.info(f"💡 {short_name} 지점의 해당 주차 데이터가 대장에 존재하지 않습니다.")

# --- 3. 기후변화 대응 매개체 감시 ---
elif selected_tab == "🟢 기후변화 대응 매개체 감시":
    st.header(f"🌍 기후변화 대응 감염병 매개체 월간 통합 현황")
    selected_zone = st.radio("📡 모니터링 매개체 권역 선택", ["모기 권역", "참진드기 권역", "털진드기 분포감시", "털진드기 발생감시"], horizontal=True)
    with st.expander(f"📥 [{selected_zone}] VectorNet 오리지널 서식 파일 업로드 및 가이드"):
        vn_cols = ["번호", "사업명", "권역", "연도", "월", "주차", "수거일", "지역1", "지역2", "환경", "방법", "종", "개체수"]
        vn_tmpl = pd.DataFrame(columns=vn_cols)
        if selected_zone == "모기 권역": vn_tmpl.loc[0] = [1, "기후변화매개체감시거점센터", "강원1권", 2026, 5, 22, "2026-05-28", "강원", "춘천시보건소", "도심", "DMS1", "Culex pipiens", 24]
        elif selected_zone == "참진드기 권역": vn_tmpl.loc[0] = [1, "기후변화매개체감시거점센터", "강원1권", 2026, 5, 21, "2026-05-19", "강원", "화천군", "무덤", "Trap", "Haemaphysalis longicornis", 5]
        else: vn_tmpl.loc[0] = [1, "기후변화매개체감시거점센터", "강원1권", 2026, 4, 17, "2026-04-21", "강원", "철원군", "야산", "Sherman trap", "mite(털진드기)", 89]
        st.download_button(f"📥 [{selected_zone}] 국가 감시망 전용 표준 서식 예시 다운로드 (.csv)", convert_df_to_csv(vn_tmpl), f"VectorNet_{selected_zone}_실무양식.csv", "text/csv")
        cli_file = st.file_uploader("질병청 VectorNet [{selected_zone}] 엑셀/CSV 파일 드롭 업로드", type=["csv", "xlsx", "xls"], key="cli_up")
        df_cli = base_cli_df if cli_file is None else rename_duplicate_columns(smart_load_uploaded_file(cli_file))

    if not df_cli.empty:
        if "연도" in df_cli.columns: df_cli["조사년도"] = df_cli["연도"].astype(str).str.extract(r'(\d+)')[0].map(lambda x: f"{x}년" if pd.notna(x) else selected_year)
        elif "월" in df_cli.columns and "월.1" in df_cli.columns: df_cli["조사년도"] = df_cli["월"].astype(str).str.extract(r'(\d+)')[0].map(lambda x: f"{x}년" if pd.notna(x) else selected_year)
        else: df_cli["조사년도"] = selected_year
            
        if "월.1" in df_cli.columns: df_cli["조사월"] = df_cli["월.1"].astype(str).str.extract(r'(\d+)')[0].map(lambda x: f"{int(x):02d}월" if pd.notna(x) else selected_month)
        elif "월" in df_cli.columns and "월.1" not in df_cli.columns: df_cli["조사월"] = df_cli["월"].astype(str).str.extract(r'(\d+)')[0].map(lambda x: f"{int(x):02d}월" if pd.notna(x) else selected_month)
        else: df_cli["조사월"] = selected_month
            
        h_coords = {
            "춘천시보건소": [37.8756, 127.7204], "백로서식지": [37.8805, 127.7713], "주택": [37.8811, 127.7711], "종가오리": [37.8822, 127.7730],
            "인제군": [38.0650, 128.1611], "화천군": [38.1062, 127.7034], "철원군": [38.244278, 127.220583]
        }
        
        target_loc_col = "지역2" if "지역2" in df_cli.columns else ("지역2.1" if "지역2.1" in df_cli.columns else "")
        if target_loc_col:
            df_cli["지역2_정외"] = df_cli[target_loc_col].astype(str).str.strip()
            df_cli["위도"] = df_cli["지역2_정외"].map(lambda x: h_coords[x][0] if x in h_coords else 38.0)
            df_cli["경도"] = df_cli["지역2_정외"].map(lambda x: h_coords[x][1] if x in h_coords else 127.5)
            df_cli["지점명"] = df_cli["지역2_정외"] + " (" + df_cli["환경"].astype(str) + ")"
        else: df_cli["지점명"] = "지정 감시소"

    m_data = df_cli[(df_cli["조사년도"] == selected_year) & (df_cli["조사월"] == selected_month)].copy()
    if "털진드기" in selected_zone and "종" in m_data.columns: m_data = m_data[m_data["종"].str.contains("mite|털진드기", case=False, na=False)]

    if not m_data.empty and "지역2_정외" in m_data.columns:
        if selected_zone == "모기 권역":
            allowed_spots = ["춘천시보건소", "백로서식지", "주택", "종가오리"]
            m_data = m_data[m_data["지역2_정외"].isin(allowed_spots)]
        elif selected_zone == "참진드기 권역":
            allowed_spots = ["화천군", "인제군"]
            m_data = m_data[m_data["지역2_정외"].isin(allowed_spots)]
        elif "털진드기" in selected_zone:
            m_data = m_data[m_data["지역2_정외"] == "철원군"]

    if not m_data.empty:
        val_col = "개체수" if "개체수" in m_data.columns else "채집수"
        monthly_summary = m_data.groupby(["지점명", "위도", "경도", "종", "환경"], as_index=False)[val_col].sum()
        
        col_map, col_day = st.columns([5, 5])
        with col_map:
            st.markdown(f"##### 📍 {selected_month} [{selected_zone}] 관할 지점 격리 매핑 GIS 지도")
            m_center_lat = 38.24 if "털진드기" in selected_zone else (37.88 if selected_zone == "모기 권역" else 38.08)
            m_center_lng = 127.22 if "털진드기" in selected_zone else (127.75 if selected_zone == "모기 권역" else 127.95)
            m_zoom = 11 if "털진드기" in selected_zone or selected_zone == "모기 권역" else 10
            m_cli = folium.Map(location=[m_center_lat, m_center_lng], zoom_start=m_zoom)
            for _, r in monthly_summary.iterrows(): folium.Marker(location=[float(r['위도']), float(r['경도'])], tooltip=r['지점명'], popup=f"월간 누적 채집수: {r[val_col]}개체").add_to(m_cli)
            st_folium(m_cli, key=f"map_climate_static_node_{selected_month}", width="100%", height=430)
            
        with col_day:
            st.markdown(f"##### 📊 {selected_month} 지점별/환경별 상세 밀도 비교 차트")
            fig, ax = plt.subplots(figsize=(6, 5.2))
            monthly_summary.set_index("지점명")[val_col].plot(kind='bar', ax=ax, color='#2a9d8f', edgecolor='black')
            plt.gcf().subplots_adjust(bottom=0.35)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()
        st.dataframe(monthly_summary.rename(columns={"지점명": "조사지점", "환경": "환경", "종": "채집종", val_col: "채집수(개체)"})[["조사지점", "환경", "채집종", "채집수(개체)"]], hide_index=True, use_container_width=True)
    else: st.info(f"💡 선택하신 {selected_year} {selected_month} 기간의 [{selected_zone}] 지정 지점 관할 데이터가 존재하지 않습니다.")

# --- 4. 참진드기조사 어린이숲체험장 ---
elif selected_tab == "🟡 참진드기조사(어린이숲체험장)":
    st.header(f"🌳 어린이 숲 체험장 참진드기 자체조사 월간 통합 현황")
    with st.expander("📥 [어린이 숲체험장] 표준 입력 파일 업로드 및 샘란 양식 다운로드"):
        template_columns = ["연번", "월", "채집일", "채집지역2", "코스번호", "지점번호", "분류", "종", "Stage", "개체수", "Pool No.", "리케치아 양성 Pools", "라임 양성 pool", "아나플라즈마 양성", "Ehlichia", "POWV", "HRTV", "Babesia", "동시감염"]
        forest_tmpl = pd.DataFrame(columns=template_columns)
        forest_tmpl.loc[0] = [1, 4, "2026-04-07", "남산", 1, 2, "Out", "Haemaphysalis flava ", "Female", 2, 1, 0, 0, 0, 0, 0, 0, 0, ""]
        st.download_button("📥 어린이숲체험장 전용 샘플양식 다운로드 (.csv)", convert_df_to_csv(forest_tmpl), "어린이숲체험장_표준양식.csv", "text/csv", key="dl_forest")
        forest_file = st.file_uploader("작성된 어린이 숲체험장 파일 업로드 (.xlsx 및 .csv 지원)", type=["csv", "xlsx", "xls"], key="forest_up")
        df_forest = base_forest_df if forest_file is None else rename_duplicate_columns(smart_load_uploaded_file(forest_file))

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
        m_forest['gu분지점'] = m_forest.apply(lambda x: f"관리지점 {x['지점번호']}" if str(x['분류']).strip().lower() == "in" and x['지점번호'] <= 3 else (f"비관리지점 {x['지점번호']}" if str(x['분류']).strip().lower() == "out" and x['지점번호'] <= 3 else "기타 타지점"), axis=1)
        m_forest = m_forest[m_forest['gu분지점'] != "기타 타지점"].copy()
        if not m_forest.empty:
            h_coords = {"남산": [37.683361, 127.893111], "삼마치": [37.643444, 127.910306]}
            m_forest['위도'] = m_forest['채집지역2'].map(lambda x: h_coords[x][0] if x in h_coords else 37.66)
            m_forest['경도'] = m_forest['채집지역2'].map(lambda x: h_coords[x][1] if x in h_coords else 127.90)
            forest_summary = m_forest.pivot_table(index=["채집지역2", "gu분지점", "위도", "경도"], columns="종명_한글", values="개체수", aggfunc="sum", fill_value=0).reset_index()
            if not forest_summary.empty:
                avail_species = [s for s in ["작은소피참진드기", "개피참진드기", "일본참진드기"] if s in forest_summary.columns]
                forest_summary['합계'] = forest_summary[avail_species].sum(axis=1)
                col_f_map, col_f_graph = st.columns([5, 5])
                with col_f_map:
                    m_f = folium.Map(location=[37.665, 127.900], zoom_start=11)
                    for r_name, latlng in h_coords.items():
                        r_summary = forest_summary[forest_summary["채집지역2"] == r_name]
                        popup_text = f"<b>🌲 홍천 {r_name} 유아숲체험원</b><br><hr style='margin:5px 0;'>"
                        for _, r in r_summary.iterrows(): popup_text += f"• {r['gu분지점']}: 월간 누적 {r['합계']}개체<br>"
                        folium.Marker(latlng, popup=folium.Popup(popup_text, max_width=350), icon=folium.Icon(color='green', icon='tree')).add_to(m_f)
                    st_folium(m_f, key="map_forest_final", width="100%", height=430)
                with col_f_graph:
                    fig, ax = plt.subplots(figsize=(6, 5))
                    chart_df = forest_summary.pivot_table(index="gu분지점", columns="채집지역2", values="합계", aggfunc="sum")
                    desired_order = ["관리지점 1", "관리지점 2", "관리지점 3", "비관리지점 1", "비관리지점 2", "비관리지점 3"]
                    chart_df = chart_df.reindex([o for o in desired_order if o in chart_df.index])
                    chart_df.plot(kind='bar', ax=ax, color=['#2b2d42', '#ef233c'], edgecolor='black')
                    plt.tight_layout()
                    st.pyplot(fig)
                    plt.close()
                st.dataframe(forest_summary, hide_index=True, use_container_width=True)
            else: st.info("💡 요약 조건에 맞는 채집 수치 데이터가 존재하지 않습니다.")
        else: st.info("💡 관리지점 1~3 및 비관리지점 1~3 범위에 맞물리는 채집 데이터가 없습니다.")
    else: st.info("💡 선택하신 연도와 월에 해당하는 어린이 숲 체험장 조사 내역이 없습니다.")