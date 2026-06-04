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
st.markdown("질병조사과 주요 감시사업별 년도별, 월별, 주별 채집 현황을 모니터링하고 데이터를 입력할 수 있는 시스템입니다.")

# -----------------------------------------------------------------
# [데이터 생성 및 관리 로직 영역 - 현업 장부 규격 완전 동기화]
# -----------------------------------------------------------------
def convert_df_to_csv(df):
    """라이브러리 없이 내장 기능만으로 한글 깨짐 없는 CSV 바이너리 변환 (UTF-8-SIG 사용)"""
    return df.to_csv(index=False).encode('utf-8-sig')

@st.cache_data
def get_je_actual_style_data():
    """일본뇌염 마스터 DB 생성"""
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
                    culex_tritaeniorhynchus = int(np.random.poisson(15 if is_summer else 0)) 
                    culex_pipiens = int(np.random.poisson(120 if is_summer else 15))        
                    aedes_vexans = int(np.random.poisson(30 if is_summer else 5))          
                    aedes_albopictus = int(np.random.poisson(20 if is_summer else 2))      
                    anopheles_spp = int(np.random.poisson(45 if is_summer else 8))         
                    etc_mosquito = int(np.random.poisson(10 if is_summer else 3))          
                    total = culex_tritaeniorhynchus + culex_pipiens + aedes_vexans + aedes_albopictus + anopheles_spp + etc_mosquito
                    data.append({
                        "조사년도": year, "조사월": month, "조사주": week, "지점명": name, "위도": coords[0], "경도": coords[1],
                        "작은빨간집모기": culex_tritaeniorhynchus, "빨간집모기": culex_pipiens, "금빛숲모기": aedes_vexans, 
                        "흰줄숲모기": aedes_albopictus, "얼룩날개모기류": anopheles_spp, "기타": etc_mosquito, "합계": total, 
                        "병원체검사": "음성" if culex_tritaeniorhynchus < 30 else "검사중"
                    })
    return pd.DataFrame(data)

@st.cache_data
def get_malaria_actual_style_data():
    """말라리아 마스터 DB 생성"""
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
                    aedes_vex = int(np.random.poisson(25 if is_summer else 3))   
                    aedes_alb = int(np.random.poisson(15 if is_summer else 1))   
                    etc_mos = int(np.random.poisson(10 if is_summer else 2))     
                    total = anopheles + culex_pip + aedes_vex + aedes_alb + etc_mos
                    data.append({
                        "조사년도": year, "조사월": month, "조사주": week, "지점명": name, "위도": coords[0], "경도": coords[1],
                        "얼룩날개모기류": anopheles, "빨간집모기": culex_pip, "금빛숲모기": aedes_vex, "흰줄숲모기": aedes_alb,
                        "기타모기류": etc_mos, "합계": total, "말라리아원충감염조사": "음성" if anopheles < 100 else "검사중"
                    })
    return pd.DataFrame(data)

@st.cache_data
def get_forest_playground_actual_data():
    """어린이 숲 체험장 참진드기 자체조사사업 마스터 DB"""
    locs = {
        "춘천시 집다리골 어린이숲체험장": [37.9620, 127.6740],
        "강릉시 솔향수목원 어린이숲체험장": [37.7015, 128.8510],
        "횡성군 청태산 어린이숲체험장": [37.5185, 128.2830],
        "고성군 화진포 어린이숲체험장": [38.4810, 128.4310]
    }
    data = []
    for year in ["2026년", "2025년"]:
        for month in ["04월", "05월", "06월", "07월", "08월", "09월", "10월", "11월"]:
            for week in ["1주", "2주", "3주", "4주"]:
                np.random.seed(int(month.replace("월","")) * 5)
                for name, coords in locs.items():
                    is_larva_season = month in ["08월", "09월"]
                    adult_f = int(np.random.poisson(1 if is_larva_season else 4))
                    adult_m = int(np.random.poisson(1 if is_larva_season else 3))
                    nymph = int(np.random.poisson(3 if is_larva_season else 18))
                    larva = int(np.random.poisson(120 if is_larva_season else 0))
                    total = adult_f + adult_m + nymph + larva
                    
                    data.append({
                        "조사년도": year, "조사월": month, "조사주": week, "지점명": name, "위도": coords[0], "경도": coords[1],
                        "성충_암": adult_f, "성충_수": adult_m, "약충": nymph, "유충": larva, "합계": total,
                        "SFTS_유전자검사": "음성" if total < 80 else "검사중"
                    })
    return pd.DataFrame(data)

@st.cache_data
def get_climate_data():
    """기후변화 매개체 샘플 데이터 생성 (철원군 학사리/오덕리 좌표 정밀 수정 완비)"""
    data = []
    for year in ["2026년", "2025년"]:
        np.random.seed(46 if year == "2025년" else 47)
        
        # 1. 모기 권역 (춘천 7개 거점)
        chuncheon_mosquito_locs = {
            "퇴계동주민센터 (도심지 발생감시)": [37.8645, 127.7261], "삼천동 숲속 (도심지 발생감시)": [37.8721, 127.7081],
            "종가오리식당 (철새도래지 발생감시)": [37.8822, 127.7730], "백로서식지 주변 주택 (철새도래지 발생감시)": [37.8811, 127.7711],
            "백로서식지 숲속 (철새도래지 발생감시)": [37.8805, 127.7713], "춘천시보건소 (도심지 발생감시)": [37.8756, 127.7204],
            "춘천시보건소 (도심지 일일감시-DMS)": [37.8751, 127.7202]
        }
        for name, coords in chuncheon_mosquito_locs.items():
            for month in ["04월", "05월", "06월", "07월", "08월", "09월", "10월"]:
                for week in ["1주", "2주", "3주", "4주"]:
                    data.append({
                        "조사년도": year, "권역": "모기 권역", "지점명": name, "위도": coords[0], "경도": coords[1], 
                        "조사월": month, "조사주": week, "채집종": "모기류 통합개체", "채집수": int(np.random.poisson(15))
                    })
                    
        # 2. 참진드기 권역 (인제/화천 4대 서식환경)
        inje_hwacheon_locs = {
            "인제 남북리 (초지 환경)": [38.0650, 128.1611], "인제 남북리 (잡목림 환경)": [38.0652, 128.1612],
            "인제 남북리 (산길 환경)": [38.0655, 128.1615], "인제 남북리 (무덤 환경)": [38.0648, 128.1603],
            "화천 하리 (초지 환경)": [38.1062, 127.7034], "화천 하리 (잡목림 환경)": [38.1065, 127.7036],
            "화천 하리 (산길 환경)": [38.1069, 127.7040], "화천 하리 (무덤 환경)": [38.1058, 127.7028]
        }
        for name, coords in inje_hwacheon_locs.items():
            for month in ["04월", "05월", "06월", "07월", "08월", "09월", "10월", "11월"]:
                for week in ["1주", "2주", "3주", "4주"]:
                    data.append({
                        "조사년도": year, "권역": "참진드기 권역", "지점명": name, "위도": coords[0], "경도": coords[1], 
                        "조사월": month, "조사주": week, "채집종": "작은소피참진드기 등", "채집수": int(np.random.poisson(30))
                    })
                    
        # 3. 털진드기 분포감시 (철원군 오덕리 및 관우리 일대 거점)
        bunpo_locs = {
            "철원 관우리 (논 분포환경)": [38.2375, 127.2261], 
            "철원 오덕리 (밭 분포환경)": [38.2278, 127.2197], 
            "철원 관우리 (저수지 분포환경)": [38.2368, 127.2270], 
            "철원 관우리 (수로 분포환경)": [38.2395, 127.2168], 
            "철원 오덕리 (야산 분포환경)": [38.2250, 127.2247]
        }
        for name, coords in bunpo_locs.items():
            for month in ["04월", "05월", "06월", "07월", "08월", "09월", "10월", "11월", "12월"]:
                for week in ["1주", "2주", "3주", "4주"]:
                    active_factor = 25 if month in ["04월", "10월", "11월"] else 2
                    data.append({
                        "조사년도": year, "권역": "털진드기 분포감시", "지점명": name, "위도": coords[0], "경도": coords[1], 
                        "조사월": month, "조사주": week, "채집종": "야생설치류 기생 털진드기", "채집수": int(np.random.poisson(active_factor))
                    })
                    
        # 4. 털진드기 발생감시 ⚠️ [오류 보정] 학사리 밭 거점의 위치를 철원 동부권 실제 김화 경작 단면인 [38.2520, 127.4415]로 정밀 정정 완료
        jeon_locs = {
            "철원 대마리 (논 발생환경)": [38.2543, 127.2145], 
            "철원 학사리 (밭 발생환경)": [38.2520, 127.4415], # 김화읍 학사리 실제 우사 및 서식환경 경계 좌표 매핑
            "철원 양지리 (수로 발생환경)": [38.2710, 127.2650], 
            "철원 이길리 (초지 발생환경)": [38.2830, 127.2280]
        }
        for name, coords in jeon_locs.items():
            for month in ["04월", "05월", "06월", "07월", "08월", "09월", "10월", "11월", "12월"]:
                for week in ["1주", "2주", "3주", "4주"]:
                    data.append({
                        "조사년도": year, "권역": "털진드기 발생감시", "지점명": name, "위度": coords[0], "경도": coords[1], 
                        "채집종": "둥근혀털진드기 등", "채집수": int(np.random.poisson(35))
                    })
    # 컬럼 표준화 정비 (생성 시 한자/구문 오차 원천 분쇄)
    df_res = pd.DataFrame(data)
    if "위度" in df_res.columns:
        df_res.rename(columns={"위度": "위도"}, inplace=True)
    return df_res

base_je_df = get_je_actual_style_data()
base_mal_df = get_malaria_actual_style_data()
base_forest_df = get_forest_playground_actual_data()
base_cli_df = get_climate_data()

# -----------------------------------------------------------------
# [사이드바 공통 시간 필터 영역]
# -----------------------------------------------------------------
st.sidebar.image("https://www.gangwon.to/img/kgw/sub/ci_01.png", width=200)
st.sidebar.markdown("### 📅 공통 시간 필터")

selected_year = st.sidebar.selectbox("조사년도 선택", ["2026년", "2025년"])
selected_month = st.sidebar.selectbox("조사월 선택", ["05월", "04월", "06월", "07월", "08월", "09월", "10월", "11월", "12월"])
selected_week = st.sidebar.selectbox("조사주 선택", ["1주", "2주", "3주", "4주"])

tab1, tab2, tab3, tab4 = st.tabs(["🔴 일본뇌염 매개모기 감시", "🔵 말라리아 매개모기 감시", "🟢 기후변화 대응 매개체 감시", "🟡 참진드기조사(어린이숲체험장)"])

# --- TAB 1: 일본뇌염 매개모기 감시 ---
with tab1:
    st.header(f"🏠 우사 거점 일본뇌염 매개모기 발생감시 [{selected_year}]")
    with st.expander("📥 현업 업로드 양식 매뉴얼 및 데이터 교체"):
        actual_template_csv = convert_df_to_csv(base_je_df)
        st.download_button(label="📥 [현업서식] 일본뇌염 주별 채집결과 양식 다운로드", data=actual_template_csv, file_name="일본뇌염_양식.csv", mime="text/csv")
        je_file = st.file_uploader("현업 엑셀 서식 파일 업로드", type=["csv", "xlsx"], key="je_actual_up")
        df_je = base_je_df if je_file is None else (pd.read_csv(je_file) if je_file.name.endswith('.csv') else pd.read_excel(je_file))
        st.dataframe(df_je.head(3), use_container_width=True)

    f_je = df_je[(df_je["조사년도"] == selected_year) & (df_je["조사월"] == selected_month) & (df_je["조사주"] == selected_week)]
    if not f_je.empty:
        c1, c2 = st.columns([5, 5])
        with c1:
            st.markdown(f"##### 📍 {selected_year} {selected_month} 주요 거점 우사 지리정보 (GIS)")
            m_je = folium.Map(location=[37.75, 128.3], zoom_start=8)
            for _, r in f_je.iterrows():
                popup_info = f"<b>{r['지점명']}</b><br>• 작은빨간집모기: {r['작은빨간집모기']}마리<br>• 합계: {r['합계']}마리"
                # 💡 무결성 정비 완료 (위도 인덱스 규 규격 완비)
                folium.Marker([float(r['위도']), float(r['경도'])], tooltip=r['지점명'], popup=folium.Popup(popup_info, max_width=280), icon=folium.Icon(color='red', icon='home')).add_to(m_je)
            st_folium(m_je, key=f"map_je_actual_{selected_year}", width="100%", height=420)
        with c2:
            st.markdown(f"##### 📊 [{selected_year} {selected_month}] 채집 모기 우점종 구성 비율")
            sizes = [f_je["작은빨간집모기"].sum(), f_je["빨간집모기"].sum(), f_je["금빛숲모기"].sum(), f_je["흰줄숲모기"].sum(), f_je["얼룩날개모기류"].sum(), f_je["기타"].sum()]
            if sum(sizes) > 0:
                fig, ax = plt.subplots(figsize=(6, 5))
                patches, texts, autotexts = ax.pie(sizes, labels=["작은빨간집모기", "빨간집모기", "금빛숲모기", "흰줄숲모기", "얼룩날개모기류", "기타"], autopct='%1.1f%%', startangle=90, colors=['#e63946', '#f4a261', '#2a9d8f', '#e76f51', '#457b9d', '#9a8c98'])
                if f_prop:
                    for t in texts: t.set_fontproperties(f_prop)
                    for t in autotexts: t.set_fontproperties(f_prop)
                st.pyplot(fig)
                plt.close()
        st.dataframe(f_je[["지점명", "작은빨간집모기", "빨간집모기", "금빛숲모기", "흰줄숲모기", "얼룩날개모기류", "기타", "합계", "병원체검사"]], hide_index=True, use_container_width=True)

# --- TAB 2: 말라리아 매개모기 감시 ---
with tab2:
    st.header(f"🪖 접경지역 말라리아 매개모기 발생감시 [{selected_year}]")
    with st.expander("📥 말라리아 현업 업로드 양식 매뉴얼 및 데이터 교체"):
        malaria_template_csv = convert_df_to_csv(base_mal_df)
        st.download_button(label="📥 [현업서식] 말라리아 주별 채집결과 양식 다운로드", data=malaria_template_csv, file_name="말라리아_양식.csv", mime="text/csv")
        mal_file = st.file_uploader("말라리아 현업 서식 파일 업로드", type=["csv", "xlsx"], key="mal_actual_up")
        df_mal = base_mal_df if mal_file is None else (pd.read_csv(mal_file) if mal_file.name.endswith('.csv') else pd.read_excel(mal_file))
        st.dataframe(df_mal.head(3), use_container_width=True)

    f_mal = df_mal[(df_mal["조사년도"] == selected_year) & (df_mal["조사월"] == selected_month) & (df_mal["조사주"] == selected_week)]
    if not f_mal.empty:
        c1, c2 = st.columns([5, 5])
        with c1:
            m_mal_map = folium.Map(location=[38.15, 127.9], zoom_start=9)
            for _, r in f_mal.iterrows():
                popup_text = f"<b>{r['지점명']}</b><br>• 얼룩날개모기류: {r['얼룩날개모기류']}마리"
                folium.CircleMarker([float(r['위도']), float(r['경도'])], radius=10, tooltip=r['지점명'], popup=folium.Popup(popup_text, max_width=280), color="blue", fill=True).add_to(m_mal_map)
            st_folium(m_mal_map, key=f"map_mal_actual_{selected_year}", width="100%", height=420)
        with c2:
            fig, ax = plt.subplots(figsize=(6, 5))
            f_mal.set_index("지점명")["얼룩날개모기류"].plot(kind='barh', ax=ax, color='#1d3557')
            if f_prop:
                ax.set_title("거점별 채집내역", fontproperties=f_prop)
                ax.set_yticklabels(f_mal["지점명"], fontproperties=f_prop)
            st.pyplot(fig)
            plt.close()
        st.dataframe(f_mal[["지점명", "얼룩날개모기류", "빨간집모기", "금빛숲모기", "흰줄숲모기", "기타모기류", "합계", "말라리아원충감염조사"]], hide_index=True, use_container_width=True)

# --- TAB 3: 기후변화 대응 매개체 감시 ---
with tab3:
    st.header(f"🌍 기후변화 대응 감염병 매개체 감시 거점 [{selected_year}]")
    with st.expander("📥 기후변화 매개체 데이터 파일 입력 및 검증"):
        cli_csv = convert_df_to_csv(base_cli_df)
        st.download_button(label="📥 기후변화 매개체 CSV 입력양식 다운로드", data=cli_csv, file_name="기후변화_매개체_입력양식.csv", mime="text/csv")
        cli_file = st.file_uploader("기후변화 매개체 CSV/엑셀 업로드", type=["csv", "xlsx"], key="cli_up")
        df_cli = base_cli_df if cli_file is None else (pd.read_csv(cli_file) if cli_file.name.endswith('.csv') else pd.read_excel(cli_file))
        st.dataframe(df_cli.head(3), use_container_width=True)

    selected_zone = st.radio("📡 모니터링 매개체 권역 선택", ["전체 권역 보기", "모기 권역", "참진드기 권역", "털진드기 분포감시", "털진드기 발생감시"], horizontal=True)
    f_cli = df_cli[(df_cli["조사년도"] == selected_year) & (df_cli["조사월"] == selected_month) & (df_cli["조사주"] == selected_week)]
    if selected_zone != "전체 권역 보기":
        f_cli = f_cli[f_cli["권역"] == selected_zone]

    if not f_cli.empty:
        col_map, col_day = st.columns([5, 5])
        with col_map:
            st.markdown(f"##### 📍 {selected_year} {selected_month} 매개체 생태 거점 현황 (GIS)")
            # 보정된 오덕리와 학사리가 모두 안정적으로 보이도록 중심 줌인 조정
            m_cli = folium.Map(location=[38.24, 127.30], zoom_start=11)
            for _, r in f_cli.iterrows():
                if "모기 권역" in r['권역']: m_color, m_icon = "purple", "flash"
                elif r['권역'] == "참진드기 권역": m_color, m_icon = "darkgreen", "leaf"
                elif r['권역'] == "털진드기 분포감시": m_color, m_icon = "orange", "home"
                elif r['권역'] == "털진드기 발생감시": m_color, m_icon = "blue", "flag"
                else: m_color, m_icon = "gray", "info-sign"
                folium.Marker(location=[float(r['위도']), float(r['경도'])], tooltip=f"[{r['권역']}] {r['지점명']}", popup=f"년도: {r['조사년도']}<br>{r['채집종']}: {r['채집수']}개체", icon=folium.Icon(color=m_color, icon=m_icon)).add_to(m_cli)
            st_folium(m_cli, key=f"map_cli_actual_{selected_year}_{selected_zone}", width="100%", height=450)
        with col_day:
            st.markdown(f"##### 📊 [{selected_year} {selected_month}] 지점별 채집 세부 분포량")
            fig, ax = plt.subplots(figsize=(6, 5.2))
            f_cli.set_index("지점명")["채집수"].plot(kind='bar', ax=ax, color='#2a9d8f')
            if f_prop:
                ax.set_xticklabels(f_cli["지점명"], rotation=45, ha='right', fontsize=9, fontproperties=f_prop)
                ax.set_ylabel("채집 개체 수 (개체)", fontproperties=f_prop)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()
        st.markdown("---")
        st.dataframe(f_cli[["조사년도", "권역", "지점명", "채집종", "채집수"]], hide_index=True, use_container_width=True)
    else:
        st.info("데이터가 존재하지 않습니다.")

# --- TAB 4: 참진드기조사(어린이숲체험장) ---
with tab4:
    st.header(f"🌳 어린이 숲 체험장 참진드기 자체조사사업 현황 [{selected_year}]")
    with st.expander("📥 어린이 숲 체험장 자체사업 업로드 양식 및 데이터 교체"):
        forest_template_csv = convert_df_to_csv(base_forest_df)
        st.download_button(label="📥 [자체서식] 어린이숲체험장 주별 결과 양식 다운로드", data=forest_template_csv, file_name="어린이숲체험장_양식.csv", mime="text/csv")
        forest_file = st.file_uploader("자체조사결과 엑셀/CSV 파일 업로드", type=["csv", "xlsx"], key="forest_actual_up")
        df_forest = base_forest_df if forest_file is None else (pd.read_csv(forest_file) if forest_file.name.endswith('.csv') else pd.read_excel(forest_file))
        st.dataframe(df_forest.head(3), use_container_width=True)

    f_forest = df_forest[(df_forest["조사년도"] == selected_year) & (df_forest["조사월"] == selected_month) & (df_forest["조사주"] == selected_week)]
    if not f_forest.empty:
        col_f_map, col_f_graph = st.columns([5, 5])
        with col_f_map:
            st.markdown(f"##### 📍 강원권 주요 어린이 숲 체험장 진드기 안전망 GIS")
            m_forest = folium.Map(location=[37.9, 128.2], zoom_start=8)
            for _, r in f_forest.iterrows():
                popup_forest_text = f"<b>{r['지점명']}</b><br>• 성충(암/수): {r['성충_암']}/{r['성충_수']}<br>• 합계: {r['합계']}개체"
                folium.Marker([float(r['위도']), float(r['경도'])], tooltip=r['지점명'], popup=folium.Popup(popup_forest_text, max_width=280), icon=folium.Icon(color='green', icon='tree-conifer')).add_to(m_forest)
            st_folium(m_forest, key=f"map_forest_actual_{selected_year}", width="100%", height=430)
        with col_f_graph:
            st.markdown(f"##### 📊 진드기 발육단계별 우점 구성 비율")
            stage_totals = [f_forest["성충_암"].sum() + f_forest["성충_수"].sum(), f_forest["약충"].sum(), f_forest["유충"].sum()]
            if sum(stage_totals) > 0:
                fig, ax = plt.subplots(figsize=(6, 5))
                patches, texts, autotexts = ax.pie(stage_totals, labels=["성충(Adult)", "약충(Nymph)", "유충(Larva)"], autopct='%1.1f%%', startangle=90, colors=['#2b2d42', '#8d99ae', '#ef233c'])
                if f_prop:
                    for t in texts: t.set_fontproperties(f_prop)
                    for t in autotexts: t.set_fontproperties(f_prop)
                st.pyplot(fig)
                plt.close()
        st.dataframe(f_forest[["지점명", "성충_암", "성충_수", "약충", "유충", "합계", "SFTS_유전자검사"]], hide_index=True, use_container_width=True)