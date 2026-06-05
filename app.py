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

# -----------------------------------------------------------------
# [감시 사업별 마스터 데이터베이스 구축 영역]
# -----------------------------------------------------------------
@st.cache_data
def get_je_actual_style_data():
    """일본뇌염 마스터 DB 생성 (주별 데이터 제공 포맷)"""
    locs = {
        "춘천시 신북읍 산천리 (우사 거점)": [37.9250, 127.7410],
        "강릉시 사천면 산대월리 (우사 거점)": [37.7518, 128.8762],
        "횡성군 공근면 하대리 (우사 거점)": [37.4912, 127.9845]
    }
    data = []
    for year in ["2026년", "2025년"]:
        for month in ["04월", "05월", "06월", "07월", "08월", "09월", "10월"]:
            for week in ["1주", "2주", "3주", "4주"]:
                np.random.seed(int(month.replace("월","")) + int(week.replace("주","")))
                for name, coords in locs.items():
                    is_summer = month in ["07월", "08월", "09월"]
                    culex = int(np.random.poisson(15 if is_summer else 0)) 
                    pip = int(np.random.poisson(120 if is_summer else 15))        
                    vex = int(np.random.poisson(30 if is_summer else 5))          
                    total = culex + pip + vex
                    data.append({
                        "조사년도": year, "조사월": month, "조사주": week, "지점명": name, "위도": coords[0], "경도": coords[1],
                        "작은빨간집모기": culex, "빨간집모기": pip, "금빛숲모기": vex, "합계": total, "병원체검사": "음성"
                    })
    return pd.DataFrame(data)

@st.cache_data
def get_malaria_actual_style_data():
    """말라리아 마스터 DB 생성 (주별 데이터 제공 포맷)"""
    locs = {
        "춘천시 중앙로 (우사 거점)": [37.8813, 127.7298], "춘천시 지내리 (우사 거점)": [37.9250, 127.7410],
        "철원군 대마리 (우사 거점)": [38.2543, 127.2145], "철원군 학사리 (우사 거점)": [38.2520, 127.4415],
        "화천군 거점 (우사 거점)": [38.1060, 127.7035], "양구군 거점 (우사 거점)": [38.1055, 127.9880],
        "인제군 거점 (우사 거점)": [38.0645, 128.1695], "고성군 거점 (우사 거점)": [38.3795, 128.4680]
    }
    data = []
    for year in ["2026년", "2025년"]:
        for month in ["04월", "05월", "06월", "07월", "08월", "09월", "10월"]:
            for week in ["1주", "2주", "3주", "4주"]:
                np.random.seed(int(month.replace("월","")) + int(week.replace("주","")) + 10)
                for name, coords in locs.items():
                    is_summer = month in ["06월", "07월", "08월", "09월"]
                    anopheles = int(np.random.poisson(85 if is_summer else 12))  
                    culex_pip = int(np.random.poisson(40 if is_summer else 8))   
                    total = anopheles + culex_pip
                    data.append({
                        "조사년도": year, "조사월": month, "조사주": week, "지점명": name, "위도": coords[0], "경도": coords[1],
                        "얼룩날개모기류": anopheles, "빨간집모기": culex_pip, "합계": total, "말라리아원충감염조사": "음성"
                    })
    return pd.DataFrame(data)

@st.cache_data
def get_climate_data():
    """기후변화 대응 매개체 DB 마스터 소스 (24개 지점 안전 확보 노드)"""
    data = []
    for year in ["2026년", "2025년"]:
        np.random.seed(42)
        
        chuncheon_mosquito_locs = {
            "퇴계동주민센터 (도심지 발생감시)": [37.8645, 127.7261], "삼천동 숲속 (도심지 발생감시)": [37.8721, 127.7081],
            "종가오리식당 (철새도래지 발생감시)": [37.8822, 127.7730], "백로서식지 주변 주택 (철새도래지 발생감시)": [37.8811, 127.7711],
            "백로서식지 숲속 (철새도래지 발생감시)": [37.8805, 127.7713], "춘천시보건소 (도심지 발생감시)": [37.8756, 127.7204],
            "춘천시보건소 (도심지 일일감시-DMS)": [37.8751, 127.7202]
        }
        inje_hwacheon_locs = {
            "인제 남북리 (초지 환경)": [38.0650, 128.1611], "인제 남북리 (잡목림 환경)": [38.0652, 128.1612],
            "인제 남북리 (산길 환경)": [38.0655, 128.1615], "인제 남북리 (무덤 환경)": [38.0648, 128.1603],
            "화천 하리 (초지 환경)": [38.1062, 127.7034], "화천 하리 (잡목림 환경)": [38.1065, 127.7036],
            "화천 하리 (산길 환경)": [38.1069, 127.7040], "화천 하리 (무덤 환경)": [38.1058, 127.7028]
        }
        bunpo_locs = {
            "철원 관우리 (논 분포환경)": [38.244278, 127.220583], "철원 오덕리 (밭 분포환경)": [38.227800, 127.219700], 
            "철원 관우리 (저수지 분포환경)": [38.244100, 127.221100], "철원 관우리 (수로 분포환경)": [38.244500, 127.220100], 
            "철원 오덕리 (야산 분포환경)": [38.225000, 127.224700]
        }
        jeon_locs = {
            "철원 관우리 (논 발생환경)": [38.239167, 127.220000], "철원 관우리 (밭 발생환경)": [38.244278, 127.220583], 
            "철원 관우리 (수로 발생환경)": [38.237333, 127.227806], "철원 관우리 (초지 발생환경)": [38.239722, 127.220278]
        }

        for month in ["04월", "05월", "06월", "07월", "08월", "09월", "10월", "11월", "12월"]:
            for week in ["1주", "2주", "3주", "4주"]:
                for name, coords in chuncheon_mosquito_locs.items():
                    data.append({"조사년도": year, "조사월": month, "조사주": week, "권역": "모기 권역", "지점명": name, "위도": coords[0], "경도": coords[1], "채집종": "모기류 통합개체", "채집수": int(np.random.poisson(15))})
                for name, coords in inje_hwacheon_locs.items():
                    data.append({"조사년도": year, "조사월": month, "조사주": week, "권역": "참진드기 권역", "지점명": name, "위도": coords[0], "경도": coords[1], "채집종": "작은소피참진드기 등", "채집수": int(np.random.poisson(30))})
                for name, coords in bunpo_locs.items():
                    active = 25 if month in ["04월", "10월", "11월"] else 2
                    data.append({"조사년도": year, "조사월": month, "조사주": week, "권역": "털진드기 분포감시", "지점명": name, "위도": coords[0], "경도": coords[1], "채집종": "야생설치류 기생 털진드기", "채집수": int(np.random.poisson(active))})
                for name, coords in jeon_locs.items():
                    data.append({"조사년도": year, "조사월": month, "조사주": week, "권역": "털진드기 발생감시", "지점명": name, "위도": coords[0], "경도": coords[1], "채집종": "둥근혀털진드기 등", "채집수": int(np.random.poisson(35))})
                    
    return pd.DataFrame(data)

@st.cache_data
def get_forest_playground_actual_data():
    """어린이 숲 체험장 실제 원본 장부 규격 연동 DB"""
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
                                            "Pool No.": 1, "리케치아 양성 Pools": 0, "라임 양성 pool": 0, "아나플라즈마 양성": 0,
                                            "Ehlichia": 0, "POWV": 0, "HRTV": 0, "Babesia": 0, "동시감염": 0, "SFTS_유전자검사": "음성"
                                        })
                                        idx += 1
    return pd.DataFrame(data)

base_je_df = rename_duplicate_columns(get_je_actual_style_data())
base_mal_df = rename_duplicate_columns(get_malaria_actual_style_data())
base_cli_df = rename_duplicate_columns(get_climate_data())
base_forest_df = rename_duplicate_columns(get_forest_playground_actual_data())

# -----------------------------------------------------------------
# [사이드바 영역 - 💡 요구하신 공식 도청 포털 이미지 리소스로 패치 완비]
# -----------------------------------------------------------------
# state.gwd.go.kr 포털 웹 서버의 공식 고해상도 인증 스킨 배너 리소스를 직접 연동했습니다.
st.sidebar.image("https://state.gwd.go.kr/portal/images/common/logo.png", width=200, caption="강원특별자치도")
st.sidebar.markdown("### 📅 공통 시간 필터")

selected_year = st.sidebar.selectbox("조사년도 선택", ["2026년", "2025년"])
selected_month = st.sidebar.selectbox("조사월 선택", ["05월", "04월", "06월", "07월", "08월", "09월", "10월", "11월", "12월"])

if "current_tab" not in st.session_state:
    st.session_state.current_tab = "🔴 일본뇌염 매개모기 감시"

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
    with st.expander("📥 [일본뇌염] 표준 입력 파일 업로드 및 샘플 양식 다운로드"):
        je_tmpl = pd.DataFrame(columns=["조사년도", "조사월", "조사주", "지점명", "위도", "경도", "작은빨간집모기", "빨간집모기", "금빛숲모기", "합계", "병원체검사"])
        je_tmpl.loc[0] = ["2026년", "05월", "1주", "춘천시 신북읍 산천리 (우사 거점)", 37.9250, 127.7410, 0, 15, 2, 17, "음성"]
        st.download_button("📥 일본뇌염 주별 전용 샘플양식 다운로드 (.csv)", convert_df_to_csv(je_tmpl), "일본뇌염_표준양식.csv", "text/csv", key="dl_je")
        
        je_file = st.file_uploader("작성된 일본뇌염 파일 업로드", type=["csv", "xlsx"], key="je_up")
        df_je = base_je_df if je_file is None else rename_duplicate_columns(pd.read_csv(je_file) if je_file.name.endswith('.csv') else pd.read_excel(je_file))

    f_je = df_je[(df_je["조사년도"] == selected_year) & (df_je["조사월"] == selected_month) & (df_je["조사주"] == selected_week)]
    if not f_je.empty:
        c1, c2 = st.columns([5, 5])
        with c1:
            st.markdown(f"##### 📍 {selected_year} {selected_month} 주요 거점 우사 지리정보 (GIS)")
            m_je = folium.Map(location=[37.75, 128.3], zoom_start=8)
            for _, r in f_je.iterrows():
                if pd.notna(r['위도']) and pd.notna(r['경도']):
                    folium.Marker([float(r['위도']), float(r['경도'])], tooltip=r['지점명'], icon=folium.Icon(color='red')).add_to(m_je)
            st_folium(m_je, key="map_je", width="100%", height=400)
        with c2:
            fig, ax = plt.subplots(figsize=(6, 4.5))
            sizes = [f_je["작은빨간집모기"].sum(), f_je["빨간집모기"].sum(), f_je["금빛숲모기"].sum()]
            patches, texts, autotexts = ax.pie(sizes, labels=["작은빨간집모기", "빨간집모기", "금빛숲모기"], autopct='%1.1f%%', startangle=90, colors=['#e63946', '#f4a261', '#2a9d8f'])
            if f_prop:
                for t in texts: t.set_fontproperties(f_prop)
                for t in autotexts: t.set_fontproperties(f_prop)
            st.pyplot(fig)
            plt.close()
        st.dataframe(f_je[["지점명", "조사주", "작은빨간집모기", "빨간집모기", "금빛숲모기", "합계", "병원체검사"]], hide_index=True, use_container_width=True)

# --- 2. 말라리아 매개모기 감시 ---
elif selected_tab == "🔵 말라리아 매개모기 감시":
    st.header(f"🪖 접경지역 말라리아 매개모기 주별 감시 현황 [{selected_year} {selected_month} {selected_week}]")
    with st.expander("📥 [말라리아] 표준 입력 파일 업로드 및 샘플 양식 다운로드"):
        mal_tmpl = pd.DataFrame(columns=["조사년도", "조사월", "조사주", "지점명", "위도", "경도", "얼룩날개모기류", "빨간집모기", "합계", "말라리아원충감염조사"])
        mal_tmpl.loc[0] = ["2026년", "05월", "1주", "철원군 대마리 (우사 거점)", 38.2543, 127.2145, 45, 12, 57, "음성"]
        st.download_button("📥 말라리아 주별 전용 샘플양식 다운로드 (.csv)", convert_df_to_csv(mal_tmpl), "말라리아_표준양식.csv", "text/csv", key="dl_mal")
        
        mal_file = st.file_uploader("작성된 말라리아 파일 업로드", type=["csv", "xlsx"], key="mal_up")
        df_mal = base_mal_df if mal_file is None else rename_duplicate_columns(pd.read_csv(mal_file) if mal_file.name.endswith('.csv') else pd.read_excel(mal_file))

    f_mal = df_mal[(df_mal["조사년도"] == selected_year) & (df_mal["조사월"] == selected_month) & (df_mal["조사주"] == selected_week)]
    if not f_mal.empty:
        c1, c2 = st.columns([5, 5])
        with c1:
            m_mal = folium.Map(location=[38.15, 127.9], zoom_start=9)
            for _, r in f_mal.iterrows():
                if pd.notna(r['위도']) and pd.notna(r['경도']):
                    folium.CircleMarker([float(r['위도']), float(r['경도'])], radius=10, color="blue", fill=True).add_to(m_mal)
            st_folium(m_mal, key="map_mal", width="100%", height=400)
        with c2:
            fig, ax = plt.subplots(figsize=(6, 5))
            f_mal.set_index("지점명")["얼룩날개모기류"].plot(kind='barh', ax=ax, color='#1d3557')
            if f_prop: ax.set_yticklabels(f_mal["지점명"], fontproperties=f_prop)
            st.pyplot(fig)
            plt.close()
        st.dataframe(f_mal[["지점명", "조사주", "얼룩날개모기류", "빨간집모기", "합계", "말라리아원충감염조사"]], hide_index=True, use_container_width=True)

# --- 3. 기후변화 대응 매개체 감시 ---
elif selected_tab == "🟢 기후변화 대응 매개체 감시":
    st.header(f"🌍 기후변화 대응 감염병 매개체 월간 통합 현황")
    
    selected_zone = st.radio("📡 모니터링 매개체 권역 선택", ["전체 권역 보기", "모기 권역", "참진드기 권역", "털진드기 분포감시", "털진드기 발생감시"], horizontal=True)
    
    with st.expander(f"📥 [{selected_zone}] 전용 파일 업로드 및 샘플 양식 다운로드 Hub"):
        base_cols = ["조사년도", "조사월", "조사주", "권역", "지점명", "위도", "경도", "채집종", "채집수"]
        if selected_zone == "모기 권역":
            spec_tmpl = pd.DataFrame(columns=base_cols)
            spec_tmpl.loc[0] = ["2026년", "05월", "1주", "모기 권역", "춘천시보건소 (도심지 발생감시)", 37.8756, 127.7204, "모기류 통합개체", 18]
            st.download_button("📥 [모기 권역] 전용 샘플 양식 다운로드 (.csv)", convert_df_to_csv(spec_tmpl), "기후변화_모기권역_양식.csv", "text/csv")
        elif selected_zone == "참진드기 권역":
            spec_tmpl = pd.DataFrame(columns=base_cols)
            spec_tmpl.loc[0] = ["2026년", "05월", "1주", "참진드기 권역", "인제 남북리 (초지 환경)", 38.0650, 128.1611, "작은소피참진드기 등", 32]
            spec_tmpl.loc[1] = ["2026년", "05월", "1주", "참진드기 권역", "화천 하리 (잡목림 환경)", 38.1065, 127.7036, "작은소피참진드기 등", 21]
            st.download_button("📥 [참진드기 권역] 전용 샘플 양식 다운로드 (.csv)", convert_df_to_csv(spec_tmpl), "기후변화_참진드기권역_양식.csv", "text/csv")
        elif selected_zone == "털진드기 분포감시":
            spec_tmpl = pd.DataFrame(columns=base_cols)
            spec_tmpl.loc[0] = ["2026년", "05월", "1주", "털진드기 분포감시", "철원 관우리 (논 분포환경)", 38.244278, 127.220583, "야생설치류 기생 털진드기", 2]
            st.download_button("📥 [털진드기 분포감시] 전용 샘플 양식 다운로드 (.csv)", convert_df_to_csv(spec_tmpl), "기후변화_털진드기_분포감시_양식.csv", "text/csv")
        elif selected_zone == "털진드기 발생감시":
            spec_tmpl = pd.DataFrame(columns=base_cols)
            spec_tmpl.loc[0] = ["2026년", "05월", "1주", "털진드기 발생감시", "철원 관우리 (논 발생환경)", 38.239167, 127.220000, "둥근혀털진드기 등", 41]
            st.download_button("📥 [털진드기 발생감시] 전용 샘플 양식 다운로드 (.csv)", convert_df_to_csv(spec_tmpl), "기후변화_털진드기_발생감시_양식.csv", "text/csv")
        else:
            spec_tmpl = pd.DataFrame(columns=base_cols)
            spec_tmpl.loc[0] = ["2026년", "05월", "1주", "모기 권역", "춘천시보건소 (도심지 발생감시)", 37.8756, 127.7204, "모기류 통합개체", 14]
            st.download_button("📥 [전체 권역 통합] 일괄 백업용 샘플 양식 다운로드 (.csv)", convert_df_to_csv(spec_tmpl), "기후변화_전체통합_양식.csv", "text/csv")

        st.markdown("---")
        cli_file = st.file_uploader(f"작성된 [{selected_zone}] 파일 업로드", type=["csv", "xlsx"], key="cli_up")
        df_cli = base_cli_df if cli_file is None else rename_duplicate_columns(pd.read_csv(cli_file) if cli_file.name.endswith('.csv') else pd.read_excel(cli_file))

    m_data = df_cli[(df_cli["조사년도"] == selected_year) & (df_cli["조사월"] == selected_month)]
    if selected_zone != "전체 권역 보기":
        m_data = m_data[m_data["권역"] == selected_zone]

    if not m_data.empty:
        monthly_summary = m_data.groupby(["권역", "지점명", "위도", "경도", "채집종"], as_index=False)["채집수"].sum()
        
        if selected_zone == "전체 권역 보기":
            st.markdown("ℹ️ *[전체 권역 보기] 모드에서는 광역 모니터링을 위해 그래프를 제외하고 GIS 지도와 월간 요약 대장만 표출합니다.*")
            m_cli = folium.Map(location=[38.05, 127.85], zoom_start=9)
            for _, r in monthly_summary.iterrows():
                m_color = "purple" if "모기" in r['권역'] else ("darkgreen" if "참진드기" in r['권역'] else ("orange" if "분포" in r['권역'] else "blue"))
                folium.Marker(location=[float(r['위도']), float(r['경도'])], tooltip=r['지점명'], popup=f"월간누적: {r['채집수']}개체", icon=folium.Icon(color=m_color)).add_to(m_cli)
            st_folium(m_cli, key="map_cli_full", width="100%", height=480)
        else:
            col_map, col_day = st.columns([5, 5])
            with col_map:
                m_cli = folium.Map(location=[38.24, 127.23] if "털진드기" in selected_zone else [38.05, 127.85], zoom_start=12 if "털진드기" in selected_zone else 9)
                for _, r in monthly_summary.iterrows():
                    folium.Marker(location=[float(r['위도']), float(r['경도'])], tooltip=r['지점명'], popup=f"월간누적: {r['채집수']}개체").add_to(m_cli)
                st_folium(m_cli, key="map_cli_zone", width="100%", height=420)
            with col_day:
                fig, ax = plt.subplots(figsize=(6, 5.2))
                monthly_summary.set_index("지점명")["채집수"].plot(kind='bar', ax=ax, color='#2a9d8f')
                if f_prop:
                    ax.set_xticklabels(monthly_summary["지점명"], rotation=45, ha='right', fontsize=9, fontproperties=f_prop)
                    ax.set_ylabel("월간 총 채집량 (개체)", fontproperties=f_prop)
                plt.tight_layout()
                st.pyplot(fig)
                plt.close()
                
        st.markdown("##### 📋 기후변화 매개체 월간 누적 채집 내역 대장")
        st.dataframe(monthly_summary[["권역", "지점명", "채집종", "채집수"]], hide_index=True, use_container_width=True)
    else:
        st.info("데이터가 존재하지 않습니다.")

# --- 4. 참진드기조사 어린이숲체험장 ---
elif selected_tab == "🟡 참진드기조사(어린이숲체험장)":
    st.header(f"🌳 어린이 숲 체험장 참진드기 자체조사 월간 통합 현황")
    
    with st.expander("📥 [어린이 숲체험장] 표준 입력 파일 업로드 및 샘란 양식 다운로드"):
        template_columns = [
            "연번", "월", "채집일", "채집지역2", "코스번호", "지점번호", "분류", "종", "Stage", "개체수", 
            "Pool No.", "리케치아 양성 Pools", "라임 양성 pool", "아나플라즈마 양성", "Ehlichia", "POWV", "HRTV", "Babesia", "동시감염"
        ]
        forest_tmpl = pd.DataFrame(columns=template_columns)
        forest_tmpl.loc[0] = [1, 4, "2026-04-07", "남산", 1, 2, "Out", "Haemaphysalis flava ", "Female", 2, 1, 0, 0, 0, 0, 0, 0, 0, ""]
        st.download_button("📥 어린이숲체험장 전용 샘플양식 다운로드 (.csv)", convert_df_to_csv(forest_tmpl), "어린이숲체험장_표준양식.csv", "text/csv", key="dl_forest")
        
        forest_file = st.file_uploader("작성된 어린이 숲체험장 파일 업로드", type=["csv", "xlsx"], key="forest_up")
        df_forest = base_forest_df if forest_file is None else rename_duplicate_columns(pd.read_csv(forest_file) if forest_file.name.endswith('.csv') else pd.read_excel(forest_file))

    try:
        month_int = int(str(selected_month).replace("월",""))
        if "월" in df_forest.columns:
            df_forest["월_인덱스"] = df_forest["월"].astype(str).str.extract(r'(\d+)').astype(int)
            m_forest = df_forest[(df_forest["조사년도"] == selected_year) & (df_forest["월_인덱스"] == month_int)].copy()
        else:
            m_forest = pd.DataFrame()
    except Exception:
        m_forest = pd.DataFrame()

    if not m_forest.empty:
        m_forest['종명_한글'] = m_forest['종'].replace({
            "Haemaphysalis longicornis": "작은소피참진드기",
            "Haemaphysalis flava ": "개피참진드기",
            "Haemaphisalis japonica": "일본참진드기"
        })
        
        m_forest['지점번호'] = pd.to_numeric(m_forest['지점번호'], errors='coerce').fillna(0).astype(int)
        m_forest['구분지점'] = m_forest.apply(
            lambda x: f"관리지점 {x['지점번호']}" if str(x['분류']).strip().lower() == "in" and x['지점번호'] <= 3 
            else (f"비관리지점 {x['지점번호']}" if str(x['분류']).strip().lower() == "out" and x['지점번호'] <= 3 else "기타 타지점"), axis=1
        )
        m_forest = m_forest[m_forest['구분지점'] != "기타 타지점"].copy()
        
        if not m_forest.empty:
            h_coords = {"남산": [37.683361, 127.893111], "삼마치": [37.643444, 127.910306]}
            m_forest['위도'] = m_forest['채집지역2'].map(lambda x: h_coords[x][0] if x in h_coords else 37.66)
            m_forest['경도'] = m_forest['채집지역2'].map(lambda x: h_coords[x][1] if x in h_coords else 127.90)
            
            forest_summary = m_forest.pivot_table(
                index=["채집지역2", "구분지점", "위도", "경도"],
                columns="종명_한글", values="개체수", aggfunc="sum", fill_value=0
            ).reset_index()
            
            if not forest_summary.empty:
                avail_species = [s for s in ["작은소피참진드기", "개피참진드기", "일본참진드기"] if s in forest_summary.columns]
                forest_summary['합계'] = forest_summary[avail_species].sum(axis=1)
                
                col_f_map, col_f_graph = st.columns([5, 5])
                with col_f_map:
                    st.markdown(f"##### 📍 홍천군 유아숲체험원 지리정보 (지적 기반 매핑)")
                    m_f = folium.Map(location=[37.665, 127.900], zoom_start=11)
                    for r_name, latlng in h_coords.items():
                        r_summary = forest_summary[forest_summary["채집지역2"] == r_name]
                        popup_text = f"<b>🌲 홍천 {r_name} 유아숲체험원</b><br><hr style='margin:5px 0;'>"
                        for _, r in r_summary.iterrows():
                            popup_text += f"• {r['구분지점']}: 월간 누적 {r['합계']}개체<br>"
                        folium.Marker(latlng, tooltip=f"홍천 {r_name} 유아숲체험원", popup=folium.Popup(popup_text, max_width=350), icon=folium.Icon(color='green', icon='tree')).add_to(m_f)
                    st_folium(m_f, key="map_forest_final", width="100%", height=430)
                    
                with col_f_graph:
                    st.markdown(f"##### 📊 [대조분석] 관리지점 1-3(In) vs 비관리지점 1-3(Out) 월간 비교")
                    fig, ax = plt.subplots(figsize=(6, 5))
                    chart_df = forest_summary.pivot_table(index="구분지점", columns="채집지역2", values="합계", aggfunc="sum")
                    desired_order = ["관리지점 1", "관리지점 2", "관리지점 3", "비관리지점 1", "비관리지점 2", "비관리지점 3"]
                    chart_df = chart_df.reindex([o for o in desired_order if o in chart_df.index])
                    
                    chart_df.plot(kind='bar', ax=ax, color=['#2b2d42', '#ef233c'], edgecolor='black')
                    if f_prop:
                        ax.set_xticklabels(chart_df.index, rotation=45, ha='right', fontproperties=f_prop)
                        ax.set_ylabel("월간 누적 채집수 (개체)", fontproperties=f_prop)
                        ax.legend(prop=f_prop)
                    plt.tight_layout()
                    st.pyplot(fig)
                    plt.close()
                    
                st.markdown("---")
                st.markdown("##### 📋 어린이 숲 체험장 실제 원본 장부 피벗 변환 연동 대장 내역")
                display_cols = ["채집지역2", "구분지점"] + avail_species + ["합계"]
                st.dataframe(forest_summary[display_cols].rename(columns={"채집지역2": "체험원명"}), hide_index=True, use_container_width=True)
            else:
                st.info("💡 요약 조건에 맞는 채집 수치 데이터가 존재하지 않습니다.")
        else:
            st.info("💡 관리지점 1~3 및 비관리지점 1~3 범위에 매칭되는 채집 데이터가 없습니다.")
    else:
        st.info("💡 선택하신 연도와 월에 해당하는 어린이 숲 체험장 조사 내역이 없습니다.")