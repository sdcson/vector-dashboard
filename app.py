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
st.markdown("질병조사과 주요 감시사업별 맞춤형 시간 필터(주별/월별) 현황을 모니터링하고 데이터를 관리하는 시스템입니다.")

# -----------------------------------------------------------------
# [중복 컬럼명을 안전하게 변환해 주는 방어 로직]
# -----------------------------------------------------------------
def rename_duplicate_columns(df):
    """업로드된 파일이나 DB 내부에서 동일한 컬럼명이 발견되면 숫자를 붙여 강제로 고유화함"""
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
        "철원군 대마리 (우사 거점)": [38.2543, 127.2145], "철원군 학사리 (우사 거점)": [38.2520, 127.4415]
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
    """기후변화 대응 매개체 DB (월별 데이터 집계 포맷 변환용 원천 소스)"""
    data = []
    for year in ["2026년", "2025년"]:
        np.random.seed(55)
        # 모기 및 진드기 거점 정의
        locs = {
            "춘천시보건소 (모기 권역)": ["모기 권역", 37.8756, 127.7204],
            "인제 남북리 (참진드기 권역)": ["참진드기 권역", 38.0650, 128.1611],
            "철원 관우리 482-9 (털진드기 분포감시)": ["털진드기 분포감시", 38.244278, 127.220583],
            "철원 학사리 (털진드기 발생감시)": ["털진드기 발생감시", 38.2520, 127.4415]
        }
        for month in ["04월", "05월", "06월", "07월", "08월", "09월", "10월", "11월", "12월"]:
            for week in ["1주", "2주", "3주", "4주"]: # 원본은 주별 적재되나 출력 시 월별 스크리닝 예정
                for name, info in locs.items():
                    data.append({
                        "조사년도": year, "조사월": month, "조사주": week, "권역": info[0], "지점명": name, "위도": info[1], "경도": info[2],
                        "채집종": "감시 매개체 통합종", "채집수": int(np.random.poisson(40))
                    })
    return pd.DataFrame(data)

@st.cache_data
def get_forest_playground_actual_data():
    """어린이 숲 체험장 실제 원본 장부 기반 마스터 DB (월별 데이터 제공 포맷)"""
    locs = {
        "홍천 삼마치 유아숲체험원": [37.643444, 127.910306],
        "홍천 남산 유아숲체험원": [37.683361, 127.893111]
    }
    data = []
    spot_list = ["관리지점 1", "관리지점 2", "관리지점 3", "비관리지점 1", "비관리지점 2", "비관리지점 3"]
    
    for year in ["2026년", "2025년"]:
        for month in ["04월", "05월", "06월", "07월", "08월", "09월", "10월"]:
            for week in ["1주", "2주", "3주", "4주"]:
                np.random.seed(int(month.replace("월","")) * 15 + int(week.replace("주","")))
                for name, coords in locs.items():
                    for spot in spot_list:
                        base_val = 15 if month in ["08월", "09월"] else 4
                        if "비관리" in spot:
                            base_val = int(base_val * 1.5)
                        
                        longicornis = int(np.random.poisson(base_val))
                        flava = int(np.random.poisson(base_val * 0.2))
                        total = longicornis + flava
                        
                        data.append({
                            "조사년도": year, "조사월": month, "조사주": week, "체험원명": name,
                            "위도": coords[0], "경도": coords[1], "구분지점": spot,
                            "작은소피참진드기": longicornis, "개피참진드기": flava, "합계": total, "SFTS_유전자검사": "음성"
                        })
    return pd.DataFrame(data)

base_je_df = rename_duplicate_columns(get_je_actual_style_data())
base_mal_df = rename_duplicate_columns(get_malaria_actual_style_data())
base_cli_df = rename_duplicate_columns(get_climate_data())
base_forest_df = rename_duplicate_columns(get_forest_playground_actual_data())

# -----------------------------------------------------------------
# [사이드바 공통 시간 필터 및 이원화 제어 영역]
# -----------------------------------------------------------------
st.sidebar.image("https://www.gangwon.to/img/kgw/sub/ci_01.png", width=200)
st.sidebar.markdown("### 📅 공통 시간 필터")

selected_year = st.sidebar.selectbox("조사년도 선택", ["2026년", "2025년"])
selected_month = st.sidebar.selectbox("조사월 선택", ["05월", "04월", "06월", "07월", "08월", "09월", "10월", "11월", "12월"])

# 💡 핵심 로직: 현재 활성화된 탭 세션을 추적하여 일본뇌염, 말라리아일때만 '주차 필터' 노출
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "🔴 일본뇌염 매개모기 감시"

if st.session_state.current_tab in ["🔴 일본뇌염 매개모기 감시", "🔵 말라리아 매개모기 감시"]:
    selected_week = st.sidebar.selectbox("조사주 선택 (주별 감시 전용)", ["1주", "2주", "3주", "4주"])
else:
    st.sidebar.info("💡 선택하신 사업은 '월별 통합 데이터 제공 포맷'으로 가동되어 주차 필터가 자동으로 마스킹됩니다.")
    selected_week = "전체"

# 상단 탭 정의
tabs = ["🔴 일본뇌염 매개모기 감시", "🔵 말라리아 매개모기 감시", "🟢 기후변화 대응 매개체 감시", "🟡 참진드기조사(어린이숲체험장)"]
selected_tab = st.radio("📡 감시사업 카테고리 탭 선택", tabs, horizontal=True)
st.session_state.current_tab = selected_tab

st.markdown("---")

# --- 1. 일본뇌염 매개모기 감시 (주별 확인 포맷) ---
if selected_tab == "🔴 일본뇌염 매개모기 감시":
    st.header(f"🏠 우사 거점 일본뇌염 매개모기 주별 감시 현황 [{selected_year} {selected_month} {selected_week}]")
    with st.expander("📥 데이터 교체 및 엑셀 업로드"):
        je_file = st.file_uploader("일본뇌염 주별 대장 업로드", type=["csv", "xlsx"], key="je_up")
        df_je = base_je_df if je_file is None else rename_duplicate_columns(pd.read_csv(je_file) if je_file.name.endswith('.csv') else pd.read_excel(je_file))

    f_je = df_je[(df_je["조사년도"] == selected_year) & (df_je["조사월"] == selected_month) & (df_je["조사주"] == selected_week)]
    if not f_je.empty:
        c1, c2 = st.columns([5, 5])
        with c1:
            m_je = folium.Map(location=[37.75, 128.3], zoom_start=8)
            for _, r in f_je.iterrows():
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

# --- 2. 말라리아 매개모기 감시 (주별 확인 포맷) ---
elif selected_tab == "🔵 말라리아 매개모기 감시":
    st.header(f"🪖 접경지역 말라리아 매개모기 주별 감시 현황 [{selected_year} {selected_month} {selected_week}]")
    with st.expander("📥 데이터 교체 및 엑셀 업로드"):
        mal_file = st.file_uploader("말라리아 주별 대장 업로드", type=["csv", "xlsx"], key="mal_up")
        df_mal = base_mal_df if mal_file is None else rename_duplicate_columns(pd.read_csv(mal_file) if mal_file.name.endswith('.csv') else pd.read_excel(mal_file))

    f_mal = df_mal[(df_mal["조사년도"] == selected_year) & (df_mal["조사월"] == selected_month) & (df_mal["조사주"] == selected_week)]
    if not f_mal.empty:
        c1, c2 = st.columns([5, 5])
        with c1:
            m_mal = folium.Map(location=[38.15, 127.9], zoom_start=9)
            for _, r in f_mal.iterrows():
                folium.CircleMarker([float(r['위도']), float(r['경도'])], radius=10, color="blue", fill=True).add_to(m_mal)
            st_folium(m_mal, key="map_mal", width="100%", height=400)
        with c2:
            fig, ax = plt.subplots(figsize=(6, 4.5))
            f_mal.set_index("지점명")["얼룩날개모기류"].plot(kind='barh', ax=ax, color='#1d3557')
            if f_prop: ax.set_yticklabels(f_mal["지점명"], fontproperties=f_prop)
            st.pyplot(fig)
            plt.close()
        st.dataframe(f_mal[["지점명", "조사주", "얼룩날개모기류", "빨간집모기", "합계", "말라리아원충감염조사"]], hide_index=True, use_container_width=True)

# --- 3. 기후변화 대응 매개체 감시 (⚠️ 월별 통합 포맷) ---
elif selected_tab == "🟢 기후변화 대응 매개체 감시":
    st.header(f"🌍 기후변화 대응 감염병 매개체 월간 통합 현황 [{selected_year} {selected_month} 전체 주차 누적]")
    with st.expander("📥 데이터 교체 및 엑셀 업로드"):
        cli_file = st.file_uploader("기후변화 대응 대장 업로드", type=["csv", "xlsx"], key="cli_up")
        df_cli = base_cli_df if cli_file is None else rename_duplicate_columns(pd.read_csv(cli_file) if cli_file.name.endswith('.csv') else pd.read_excel(cli_file))

    selected_zone = st.radio("📡 모니터링 매개체 권역 선택", ["전체 권역 보기", "모기 권역", "참진드기 권역", "털진드기 분포감시", "털진드기 발생감시"], horizontal=True)
    
    # 💡 월별 제공 포맷: 선택 월에 해당하는 1~4주차 데이터를 주차 구분 없이 집계(groupby) 처리
    m_data = df_cli[(df_cli["조사년도"] == selected_year) & (df_cli["조사월"] == selected_month)]
    if selected_zone != "전체 권역 보기":
        m_data = m_data[m_data["권역"] == selected_zone]

    if not m_data.empty:
        # 지점별로 월간 총합 계산
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
                m_cli = folium.Map(location=[38.24, 127.30], zoom_start=11)
                for _, r in monthly_summary.iterrows():
                    folium.Marker(location=[float(r['위도']), float(r['경도'])], tooltip=r['지점명'], popup=f"월간누적: {r['채집수']}개체").add_to(m_cli)
                st_folium(m_cli, key="map_cli_zone", width="100%", height=420)
            with col_day:
                fig, ax = plt.subplots(figsize=(6, 5))
                monthly_summary.set_index("지점명")["채집수"].plot(kind='bar', ax=ax, color='#2a9d8f')
                if f_prop:
                    ax.set_xticklabels(monthly_summary["지점명"], rotation=45, ha='right', fontsize=9, fontproperties=f_prop)
                    ax.set_ylabel("월간 총 채집량 (개체)", fontproperties=f_prop)
                plt.tight_layout()
                st.pyplot(fig)
                plt.close()
                
        st.markdown("##### 📋 기후변화 매개체 월간 누적 채집 내역 대장")
        st.dataframe(monthly_summary[["권역", "지점명", "채집종", "채집수"]], hide_index=True, use_container_width=True)

# --- 4. 참진드기조사 어린이숲체험장 (⚠️ 월별 통합 포맷) ---
elif selected_tab == "🟡 참진드기조사(어린이숲체험장)":
    st.header(f"🌳 어린이 숲 체험장 참진드기 자체조사 월간 통합 현황 [{selected_year} {selected_month} 전체 주차 누적]")
    with st.expander("📥 어린이 숲 체험장 자체사업 업로드 양식 및 데이터 교체"):
        forest_file = st.file_uploader("자체조사결과 엑셀/CSV 파일 업로드", type=["csv", "xlsx"], key="forest_up")
        df_forest = base_forest_df if forest_file is None else rename_duplicate_columns(pd.read_csv(forest_file) if forest_file.name.endswith('.csv') else pd.read_excel(forest_file))

    # 💡 월별 제공 포맷: 해당 월의 모든 주차 데이터를 병합 및 요약
    m_forest = df_forest[(df_forest["조사년도"] == selected_year) & (df_forest["조사월"] == selected_month)]
    
    if not m_forest.empty:
        # 관리 1-3, 비관리 1-3별로 월간 총합 집계
        forest_summary = m_forest.groupby(["체험원명", "구분지점", "위도", "경도"], as_index=False)[["작은소피참진드기", "개피참진드기", "일본참진드기", "합계"]].sum()
        
        col_f_map, col_f_graph = st.columns([5, 5])
        with col_f_map:
            st.markdown(f"##### 📍 홍천군 유아숲체험원 지리정보 (월간 데이터 매핑)")
            m_f = folium.Map(location=[37.665, 127.900], zoom_start=11)
            for name, group in forest_summary.groupby("체험원명"):
                lat, lng = float(group["위도"].iloc[0]), float(group["경도"].iloc[0])
                popup_text = f"<b>🌲 {name} 월간 현황</b><br><hr style='margin:5px 0;'>"
                for _, r in group.iterrows():
                    popup_text += f"• {r['구분지점']}: 누적 {r['합계']}개체<br>"
                folium.Marker([lat, lng], tooltip=name, popup=folium.Popup(popup_text, max_width=350), icon=folium.Icon(color='green', icon='tree')).add_to(m_f)
            st_folium(m_f, key="map_forest", width="100%", height=430)
            
        with col_f_graph:
            st.markdown(f"##### 📊 [대조분석] 관리지점 1-3 vs 비관리지점 1-3 월간 채집량 비교")
            fig, ax = plt.subplots(figsize=(6, 5))
            chart_df = forest_summary.pivot_table(index="구분지점", columns="체험원명", values="합계", aggfunc="sum")
            desired_order = ["관리지점 1", "관리지점 2", "관리지점 3", "비관리지점 1", "비관리지점 2", "비관리지점 3"]
            chart_df = chart_df.reindex(desired_order)
            chart_df.plot(kind='bar', ax=ax, color=['#2b2d42', '#ef233c'], edgecolor='black')
            if f_prop:
                ax.set_xticklabels(chart_df.index, rotation=45, ha='right', fontproperties=f_prop)
                ax.set_ylabel("월간 누적 채집수 (개체)", fontproperties=f_prop)
                ax.legend(prop=f_prop)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()
            
        st.markdown("---")
        st.markdown("##### 📋 어린이 숲 체험장 자체조사사업 월간 지점별/종별 통합 대장 내역")
        st.dataframe(forest_summary[["체험원명", "구분지점", "작은소피참진드기", "개피참진드기", "일본참진드기", "합계"]], hide_index=True, use_container_width=True)
    else:
        st.info("해당 월의 데이터가 존재하지 않습니다.")