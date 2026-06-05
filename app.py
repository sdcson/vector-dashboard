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
# [파이썬 3.14 클라우드 환경용 - 안전한 한글 폰트 프로퍼티 로드]
# -----------------------------------------------------------------
@st.cache_resource
def get_korean_font_prop():
    """파이썬 3.14 최신 환경에서도 에러가 없도록 나눔고딕 폰트 속성을 안전하게 로드"""
    font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
    font_path = "NanumGothic.ttf"
    
    if not os.path.exists(font_path):
        try:
            urllib.request.urlretrieve(font_url, font_path)
        except Exception as e:
            return None
            
    return fm.FontProperties(fname=font_path)

# 한글 폰트 속성 획득
f_prop = get_korean_font_prop()

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
    """표준 단일 파서 (기후변화, 어린이숲 공백 트림)"""
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
# [💡 일본뇌염예측사업 VectorNet 양식 마스터 세션 백업본]
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
    
    for year in ["2026년", "2025년"]:
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
    locs = {
        "춘천시 중앙로 (우사 거점)": [37.8813, 127.7298], "춘천시 지내리 (우사 거점)": [37.9250, 127.7410],
        "철원군 대마리 (우사 거점)": [38.2543, 127.2145], "철원군 학사리 (우사 거점)": [38.2520, 127.4415],
        "화천군 거점 (우사 거점)": [38.1060, 127.7035], "양구군 거점 (우사 거점)": [38.1055, 127.9880],
        "인제군 거점 (우사 거점)": [38.0645, 128.1695], "고성군 거점 (우사 거점)": [38.3795, 128.4680]
    }
    data = []
    mal_species = ["얼룩날개모기류", "흰줄숲모기", "등줄숲모기", "한국숲모기", "토고숲모기", "금빛숲모기", "큰검정들모기", "반점날개집모기", "동양집모기", "빨간집모기", "작은빨간집모기", "줄다리집모기", "반점날개늪모기", "미동정"]
    for year in ["2026년", "2025년"]:
        for month_num in range(4, 11):
            month = f"{month_num:02d}월"
            for week_num in range(1, 5):
                week = f"{week_num}주"
                np.random.seed(month_num * 15 + week_num + 5)
                for name, coords in locs.items():
                    is_summer = month in ["06월", "07월", "08월", "09월"]
                    anopheles = int(np.random.poisson(75 if is_summer else 5))
                    row = {
                        "조사년도": year, "조사월": month, "조사주": week, "월": month_num, "주": week_num, "연중 주수": month_num*4 + week_num,
                        "지점명": name, "위도": coords[0], "경도": coords[1], "얼룩날개모기류": anopheles
                    }
                    etc_sum = 0
                    for sp in mal_species[1:]:
                        if sp == "빨간집모기": val = int(np.random.poisson(35 if is_summer else 10))
                        elif sp == "금빛숲모기": val = int(np.random.poisson(15 if is_summer else 2))
                        else: val = int(np.random.poisson(1 if is_summer else 0))
                        row[sp] = val
                        etc_sum += val
                    row["기타모기류"] = etc_sum
                    total = anopheles + etc_sum
                    row["합계"] = total
                    row["얼룩날개모기 비율"] = f"{((anopheles / total) * 100):.1f}%" if total > 0 else "0.0%"
                    row["말라리아원충감염조사"] = "음성"
                    data.append(row)
    return pd.DataFrame(data)

@st.cache_data
def get_climate_data():
    data = []
    for year in ["2026년", "2025년"]:
        np.random.seed(42)
        chuncheon_mosquito_locs = {
            "춘천시보건소": [37.8756, 127.7204, "도심"], "백로서식지": [37.8805, 127.7713, "철새도래지"],
            "주택": [37.8811, 127.7711, "철새도래지"], "종가오리": [37.8822, 127.7730, "철새도래지"]
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
                    # 💡 문법 오류 오타 수선 완료 ("조사월 : month_str" -> "조사월": month_str) ⭐️
                    data.append({"조사년도": year, "조사월": month_str, "월": month_num, "주차": week_num, "권역": "털진드기 발생감시", "지역2": "철원군", "환경": env, "위도": 38.239167, "경도": 127.220000, "종": "mite(털진드기)", "개체수": int(np.random.poisson(40))})
    return pd.DataFrame(data)

@st.cache_data
def get_forest_playground_actual_data():
    data = []
    idx = 1
    species_map = ["Haemaphysalis longicornis", "Haemaphysalis flava ", "Haemaphisalis japonica"]
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
                                            "Pool No.", 1, "리케치아 양성 Pools", 0, "라임 양성 pool", 0, "아나플라즈마 양성", 0,
                                            "Ehlichia", 0, "POWV", 0, "HRTV", 0, "Babesia", 0, "동시감염", 0, "SFTS_유전자검사", "음성"
                                        })
                                        idx += 1
    return pd.DataFrame(data)

# 상주 세션 초기화
if "mal_live_db" not in st.session_state: st.session_state.mal_live_db = get_malaria_actual_style_data()

base_je_df = rename_duplicate_columns(get_je_actual_style_data())
base_cli_df = rename_duplicate_columns(get_climate_data())
base_forest_df = rename_duplicate_columns(get_forest_playground_actual_data())

# -----------------------------------------------------------------
# [사이드바 공통 시간 필터 영역]
# -----------------------------------------------------------------
st.sidebar.markdown("### 📅 공통 시간 필터")
selected_year = st.sidebar.selectbox("조사년도 선택", ["2026년", "2025년"])
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
        st.markdown("##### 📄 질병보건통합관리시스템 일본뇌염 규격 헤더")
        vn_je_cols = ["번호", "사업명", "권역", "연도", "월", "주차", "수거일", "지역1", "지역2", "환경", "방법", "종", "개체수", "채집기간", "Index", "실험개체수", "Pool No.", "양성 Pools", "비고"]
        vn_je_tmpl = pd.DataFrame(columns=vn_je_cols)
        vn_je_tmpl.loc[0] = [1, "일본뇌염예측", "강원도보건환경연구원", 2026, 5, 22, "2026-05-26", "강원", "횡성군 하대리", "축사", "LED1", "Culex tritaeniorhynchus", 12, 1, 12, 12, 1, 0, "-"]
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
                        m_je = folium.Map(location=[float(spot_data['위도'].iloc[0]), float(spot_data['경도'].iloc[0])], zoom_start=11)
                        folium.Marker([float(spot_data['위도'].iloc[0]), float(spot_data['경도'].iloc[0])], tooltip=spot_name, icon=folium.Icon(color='red', icon='home')).add_to(m_je)
                        st_folium(m_je, key=f"map_je_final_{idx}_{selected_month}_{selected_week}", width="100%", height=380)
                    with c2:
                        val_col_je = "개체수" if "개체수" in spot_data.columns else "채집수"
                        sum_df = spot_data.groupby("종")[val_col_je].sum().reset_index()
                        fig, plt_ax = plt.subplots(figsize=(6, 5.2))
                        bar_colors = ['#ef233c' if str(s).strip() == "Culex tritaeniorhynchus" else '#b8c0cb' for s in sum_df["종"]]
                        bars = plt_ax.barh(sum_df["종"], sum_df[val_col_je].values, color=bar_colors, edgecolor='#2b2d42', height=0.7)
                        for bar in bars:
                            width = bar.get_width()
                            if width > 0: plt_ax.text(width + 0.5, bar.get_y() + bar.get_height()/2, f"{int(width)}마리", va='center', ha='left', fontsize=8, fontproperties=f_prop)
                        plt_ax.invert_yaxis()
                        plt_ax.set_xlabel("채집 개체 수 (마리)", fontproperties=f_prop)
                        if f_prop: plt_ax.set_yticklabels(sum_df["종"], fontproperties=f_prop, fontsize=8)
                        plt.tight_layout()
                        st.pyplot(fig)
                        plt.close()
                    st.dataframe(spot_data[["지점명", "환경", "종", val_col_je]], hide_index=True, use_container_width=True)
                else: st.info(f"💡 {spot_name} 지점의 해당 주차 데이터가 대장에 존재하지 않습니다.")
    else: st.info("💡 선택하신 기간의 일본뇌염 VectorNet 연동 데이터가 존재하지 않습니다.")

# --- 2. 말라리아 매개모기 감시 ---
elif selected_tab == "🔵 말라리아 매개모기 감시":
    st.header(f"🪖 접경지역 말라리아 매개모기 주별 감시 현황 [{selected_year} {selected_month} {selected_week}]")
    with st.expander("📝 🖥️ 말라리아 주차별 실시간 웹 직접 입력 대장"):
        target_species_mal = ["얼룩날개모기류", "흰줄숲모기", "등줄숲모기", "한국숲모기", "토고숲모기", "금빛숲모기", "큰검정들모기", "반점날개집모기", "동양집모기", "빨간집모기", "작은빨간집모기", "줄다리집모기", "반점날개늪모기", "미동정"]
        mal_spots_list = ["춘천시 중앙로 (우사 거점)", "춘천시 지내리 (우사 거점)", "철원군 대마리 (우사 거점)", "철원군 학사리 (우사 거점)", "화천군 거점 (우사 거점)", "양구군 거점 (우사 거점)", "인제군 거점 (우사 거점)", "고성군 거점 (우사 거점)"]
        with st.form("mal_web_input_form"):
            col_sel_spot_mal = st.selectbox("🎯 말라리아 거점 지점명 선택", mal_spots_list)
            form_cols_mal = st.columns(2)
            input_values_mal = {}
            for s_idx, sp in enumerate(target_species_mal):
                with form_cols_mal[s_idx % 2]:
                    existing_mal_df = st.session_state.mal_live_db[(st.session_state.mal_live_db["조사년도"] == selected_year) & (st.session_state.mal_live_db["조사월"] == selected_month) & (st.session_state.mal_live_db["조사주"] == selected_week) & (st.session_state.mal_live_db["지점명"] == col_sel_spot_mal)]
                    default_val_mal = int(existing_mal_df[sp].iloc[0]) if not existing_mal_df.empty and sp in existing_mal_df.columns else 0
                    input_values_mal[sp] = st.number_input(f"🦟 {sp} (마리)", min_value=0, max_value=9999, value=default_val_mal, step=1, key=f"in_mal_{sp}")
            submit_save_mal = st.form_submit_button("💾 말라리아 웹 데이터 최종 보관 및 저장")
            if submit_save_mal:
                current_mal_db = st.session_state.mal_live_db.copy()
                match_condition_mal = (current_mal_db["조사년도"] == selected_year) & (current_mal_db["조사월"] == selected_month) & (current_mal_db["조사주"] == selected_week) & (current_mal_db["지점명"] == col_sel_spot_mal)
                anopheles_val = input_values_mal["얼룩날개모기류"]
                etc_sum_val = sum([v for k, v in input_values_mal.items() if k != "얼룩날개모기류"])
                total_sum_val = anopheles_val + etc_sum_val
                if current_mal_db[match_condition_mal].shape[0] > 0:
                    target_idx = current_mal_db[match_condition_mal].index[0]
                    for sp, val in input_values_mal.items(): current_mal_db.at[target_idx, sp] = val
                    current_mal_db.at[target_idx, "기타모기류"] = etc_sum_val
                    current_mal_db.at[target_idx, "합계"] = total_sum_val
                st.session_state.mal_live_db = current_mal_db
                st.success("✅ 말라리아 웹 데이터 대장 갱신 완료!")
        st.download_button("📥 웹 입력 완료된 말라리아 장부 백업 다운로드 (.csv)", convert_df_to_csv(st.session_state.mal_live_db), "말라리아_웹입력_백업.csv", "text/csv")
    f_mal = st.session_state.mal_live_db[(st.session_state.mal_live_db["조사년도"] == selected_year) & (st.session_state.mal_live_db["조사월"] == selected_month) & (st.session_state.mal_live_db["조사주"] == selected_week)]
    if not f_mal.empty:
        mal_sub_tabs = st.tabs([f"📍 {spot.split(' (')[0]}" for spot in mal_spots_list])
        for idx, spot_name in enumerate(mal_spots_list):
            with mal_sub_tabs[idx]:
                spot_data_mal = f_mal[f_mal["지점명"] == spot_name]
                if not spot_data_mal.empty:
                    c1, c2 = st.columns([5, 5])
                    with c1:
                        m_mal = folium.Map(location=[float(spot_data_mal['uid' if 'uid' in spot_data_mal else '위도'].iloc[0]), float(spot_data_mal['경도'].iloc[0])], zoom_start=11)
                        folium.Marker([float(spot_data_mal['위도'].iloc[0]), float(spot_data_mal['경도'].iloc[0])], tooltip=spot_name, icon=folium.Icon(color='blue', icon='flag')).add_to(m_mal)
                        st_folium(m_mal, key=f"map_mal_live_{idx}_{selected_month}", width="100%", height=400)
                    with c2:
                        graph_series_mal = spot_data_mal[target_species_mal].iloc[0]
                        fig, plt_ax = plt.subplots(figsize=(6, 5.2))
                        bar_colors_mal = ['#1d3557' if sp == "얼룩날개모기류" else '#c4cbde' for sp in target_species_mal]
                        bars = plt_ax.barh(target_species_mal, graph_series_mal.values, color=bar_colors_mal, edgecolor='#2b2d42', height=0.7)
                        for bar in bars:
                            width = bar.get_width()
                            if width > 0: plt_ax.text(width + 0.5, bar.get_y() + bar.get_height()/2, f"{int(width)}마리", va='center', ha='left', fontsize=8, fontproperties=f_prop)
                        plt_ax.invert_yaxis()
                        if f_prop: plt_ax.set_yticklabels(target_species_mal, fontproperties=f_prop, fontsize=8)
                        st.pyplot(fig)
                        plt.close()
                    st.dataframe(spot_data_mal, hide_index=True, use_container_width=True)

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
        st.download_button(f"📥 [{selected_zone}] VectorNet 표준 예시파일 다운로드 (.csv)", convert_df_to_csv(vn_tmpl), f"VectorNet_{selected_zone}_양식.csv", "text/csv")
        cli_file = st.file_uploader(f"질병청 VectorNet [{selected_zone}] 엑셀/CSV 파일 드롭 업로드", type=["csv", "xlsx", "xls"], key="cli_up")
        df_cli = base_cli_df if cli_file is None else rename_duplicate_columns(smart_load_uploaded_file(cli_file))

    if not df_cli.empty:
        if "연도" in df_cli.columns: df_cli["조사년도"] = df_cli["연도"].astype(str).map(lambda x: f"{x}년" if '년' not in str(x) else x)
        else: df_cli["조사년도"] = selected_year
        if "월" in df_cli.columns: df_cli["조사월"] = df_cli["월"].astype(str).map(lambda x: f"{int(float(x)):02d}월" if x.replace('.','',1).isdigit() else x if '월' in x else f"{x}월")
        else: df_cli["조사월"] = selected_month
        h_coords = {"춘천시보건소": [37.8756, 127.7204], "백로서식지": [37.8805, 127.7713], "주택": [37.8811, 127.7711], "종가오리": [37.8822, 127.7730], "인제군": [38.0650, 128.1611], "화천군": [38.1062, 127.7034], "철원군": [38.244278, 127.220583]}
        if "지역2" in df_cli.columns:
            df_cli["위도"] = df_cli["지역2"].map(lambda x: h_coords[str(x).strip()][0] if str(x).strip() in h_coords else 38.0)
            df_cli["경도"] = df_cli["지역2"].map(lambda x: h_coords[str(x).strip()][1] if str(x).strip() in h_coords else 127.5)
            df_cli["지점명"] = df_cli["지역2"].astype(str) + " (" + df_cli["환경"].astype(str) + ")"
        else: df_cli["지점명"] = "감시 거점"

    m_data = df_cli[(df_cli["조사년도"] == selected_year) & (df_cli["조사월"] == selected_month)].copy()
    if "털진드기" in selected_zone and "종" in m_data.columns: m_data = m_data[m_data["종"].str.contains("mite|털진드기", case=False, na=False)]

    if not m_data.empty:
        monthly_summary = m_data.groupby(["지점명", "위도", "경도", "종", "환경"], as_index=False)["개체수" if "개체수" in m_data.columns else "채집수"].sum()
        val_col = "개체수" if "개체수" in monthly_summary.columns else "채집수"
        col_map, col_day = st.columns([5, 5])
        with col_map:
            m_center_lat = 38.24 if "털진드기" in selected_zone else 38.05
            m_cli = folium.Map(location=[m_center_lat, 127.5], zoom_start=11 if "털진드기" in selected_zone else 9)
            for _, r in monthly_summary.iterrows(): folium.Marker(location=[float(r['위도']), float(r['경도'])], tooltip=r['지점명'], popup=f"월간 누적 채집수: {r[val_col]}개체").add_to(m_cli)
            st_folium(m_cli, key=f"map_cli_final_{selected_zone}", width="100%", height=430)
        with col_day:
            fig, ax = plt.subplots(figsize=(6, 5.2))
            monthly_summary.set_index("지점명")[val_col].plot(kind='bar', ax=ax, color='#2a9d8f', edgecolor='black')
            if f_prop: ax.set_xticklabels(monthly_summary["지점명"], rotation=45, ha='right', fontsize=8, fontproperties=f_prop)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()
        st.dataframe(monthly_summary[["지점명", "환경", "종", val_col]], hide_index=True, use_container_width=True)
    else: st.info(f"💡 선택하신 기간의 [{selected_zone}] 데이터가 존재하지 않습니다.")

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
        m_forest['종명_한글'] = m_forest['종'].replace({"Haemaphysalis longicornis": "작은소피참진드기", "Haemaphysalis flava ": "개피참진드기", "Haemaphisalis japonica": "일본참진드기"})
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
                    if f_prop: ax.set_xticklabels(chart_df.index, rotation=45, ha='right', fontproperties=f_prop)
                    plt.tight_layout()
                    st.pyplot(fig)
                    plt.close()
                st.dataframe(forest_summary, hide_index=True, use_container_width=True)
            else: st.info("💡 요약 조건에 맞는 채집 수치 데이터가 존재하지 않습니다.")
        else: st.info("💡 관리지점 1~3 및 비관리지점 1~3 범위에 매칭되는 채집 데이터가 없습니다.")
    else: st.info("💡 선택하신 연도와 월에 해당하는 어린이 숲 체험장 조사 내역이 없습니다.")