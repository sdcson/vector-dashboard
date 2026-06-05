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
    """말라리아, 기후변화, 어린이숲용 표준 1시트 단일 파서"""
    if uploaded_file is None:
        return pd.DataFrame()
    file_name = uploaded_file.name.lower()
    if file_name.endswith('.xlsx') or file_name.endswith('.xls'):
        try:
            uploaded_file.seek(0)
            raw_excel = pd.read_excel(uploaded_file, sheet_name=0, header=None)
            skip_rows_idx = 0
            for r_idx in range(min(10, len(raw_excel))):
                row_str_list = [str(x) for x in raw_excel.iloc[r_idx].tolist()]
                if any(('조사' in s or '월' in s or '연번' in s or '지점' in s) for s in row_str_list):
                    skip_rows_idx = r_idx
                    break
            uploaded_file.seek(0)
            return pd.read_excel(uploaded_file, sheet_name=0, skiprows=skip_rows_idx)
        except Exception:
            uploaded_file.seek(0)
            return pd.read_excel(uploaded_file, sheet_name=0)
    else:
        encodings = ['utf-8', 'cp949', 'euc-kr']
        for enc in encodings:
            try:
                uploaded_file.seek(0)
                raw_csv = pd.read_csv(uploaded_file, encoding=enc, header=None, nrows=10)
                skip_rows_idx = 0
                for r_idx in range(len(raw_csv)):
                    row_str_list = [str(x) for x in raw_csv.iloc[r_idx].tolist()]
                    if any(('조사' in s or '월' in s or '연번' in s or '지점' in s) for s in row_str_list):
                        skip_rows_idx = r_idx
                        break
                uploaded_file.seek(0)
                return pd.read_csv(uploaded_file, encoding=enc, skiprows=skip_rows_idx)
            except Exception:
                continue
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, encoding='utf-8', errors='replace')

# -----------------------------------------------------------------
# [감시 사업별 마스터 데이터베이스 구축 영역]
# -----------------------------------------------------------------
@st.cache_data
def get_je_actual_style_data():
    """일본뇌염 기본 마스터 DB 생성 (초기값 백업용)"""
    locs = {
        "춘천시 신북읍 산천리 (우사 거점)": [37.9250, 127.7410],
        "강릉시 사천면 산대월리 (우사 거점)": [37.7518, 128.8762],
        "횡성군 공근면 하대리 (우사 거점)": [37.4912, 127.9845]
    }
    data = []
    mosquito_species = [
        "작은빨간집모기", "이나토미집모기", "반점날개집모기", "동양집모기", "빨간집모기", 
        "줄다리집모기", "노랑늪모기", "반점날개늪모기", "얼룩날개모기류", "흰줄숲모기", 
        "금빛숲모기", "금빛어깨숲모기", "한국숲모기", "흰어깨숲모기", "등줄숲모기", "큰검정들모기", "긴얼룩다리모기"
    ]
    
    for year in ["2026년", "2025년"]:
        for month_num in range(4, 11):
            month = f"{month_num:02d}월"
            for week_num in range(1, 5):
                week = f"{week_num}주"
                np.random.seed(month_num * 20 + week_num)
                for name, coords in locs.items():
                    is_summer = month in ["07월", "08월", "09월"]
                    culex_tritaeniorhynchus = int(np.random.poisson(20 if is_summer else 0))
                    row = {
                        "조사년도": year, "조사월": month, "조사주": week, "월": month_num, "주": week_num, "연중 주수": month_num*4 + week_num,
                        "지점명": name, "위도": coords[0], "경도": coords[1], "작은빨간집모기": culex_tritaeniorhynchus
                    }
                    etc_total = 0
                    for sp in mosquito_species[1:]:
                        if sp in ["빨간집모기", "얼룩날개모기류"]:
                            val = int(np.random.poisson(45 if is_summer else 8))
                        elif sp in ["금빛숲모기", "흰줄숲모기"]:
                            val = int(np.random.poisson(25 if is_summer else 3))
                        else:
                            val = int(np.random.poisson(2 if is_summer else 0))
                        row[sp] = val
                        etc_total += val
                        
                    total = culex_tritaeniorhynchus + etc_total
                    row["합계"] = total
                    row["작은빨간집모기 비율"] = f"{((culex_tritaeniorhynchus / total) * 100):.1f}%" if total > 0 else "0.0%"
                    row["병원체검사"] = "음성" if culex_tritaeniorhynchus < 30 else "검사중"
                    row["비고"] = "-"
                    data.append(row)
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
                    total = anopheles + culex_pip
                    data.append({
                        "조사년도": year, "조사월": month, "조사주": week, "지점명": name, "위도": coords[0], "경도": coords[1],
                        "얼룩날개모기류": anopheles, "빨간집모기": culex_pip, "합계": total, "말라리아원충감염조사": "음성"
                    })
    return pd.DataFrame(data)

@st.cache_data
def get_climate_data():
    """기후변화 대응 매개체 DB 마스터 소스"""
    data = []
    for year in ["2026년", "2025년"]:
        np.random.seed(42)
        chuncheon_mosquito_locs = {
            "퇴계동주민센터 (도심지 발생감시)": [37.8645, 127.7261], "삼천동 숲속 (도심지 발생감시)": [37.8721, 127.7081],
            "종가오리식당 (철새도래지 발생감시)": [37.8822, 127.7730], "춘천시보건소 (도심지 발생감시)": [37.8756, 127.7204],
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

# 일본뇌염 웹 라이브 입력 데이터를 상주시키기 위한 세션 메모리 빌드
if "je_live_db" not in st.session_state:
    st.session_state.je_live_db = get_je_actual_style_data()

base_mal_df = rename_duplicate_columns(get_malaria_actual_style_data())
base_cli_df = rename_duplicate_columns(get_climate_data())
base_forest_df = rename_duplicate_columns(get_forest_playground_actual_data())

# -----------------------------------------------------------------
# [사이드바 공통 시간 필터 영역]
# -----------------------------------------------------------------
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

# --- 1. 일본뇌염 매개모기 감시 (💡 요구사항: 스마트 웹 직접 입력 양식 전면 개조 완료) ---
if selected_tab == "🔴 일본뇌염 매개모기 감시":
    st.header(f"🏠 우사 거점 일본뇌염 매개모기 주별 감시 현황 [{selected_year} {selected_month} {selected_week}]")
    
    # 💡 혁신 패치: 엑셀 파일 업로드를 제거하고, 웹 화면에서 데이터를 즉시 타이핑해 반영하는 제어판 구축
    with st.expander("📝 🖥️ 일본뇌염 주차별 실시간 웹 직접 입력 대장"):
        st.markdown("##### ✍️ 현재 선택된 필터 주차의 수치 바로 입력하기")
        st.caption("아래 지점별 입력창에 마리 수를 기입한 후 [웹 데이터 최종 보관 및 저장] 버튼을 누르시면 지도와 차트에 즉시 누적 반영됩니다.")
        
        target_species = [
            "작은빨간집모기", "이나토미집모기", "반점날개집모기", "동양집모기", "빨간집모기", 
            "줄다리집모기", "노랑늪모기", "반점날개늪모기", "얼룩날개모기류", "흰줄숲모기", 
            "금빛숲모기", "금빛어깨숲모기", "한국숲모기", "흰어깨숲모기", "등줄숲모기", "큰검정들모기", "긴얼룩다리모기"
        ]
        
        # 입력 폼 설계
        with st.form("je_web_input_form"):
            col_sel_spot = st.selectbox("🎯 채집 거점 지점명 선택", ["춘천시 신북읍 산천리 (우사 거점)", "강릉시 사천면 산대월리 (우사 거점)", "횡성군 공근면 하대리 (우사 거점)"])
            
            st.markdown(f"**🔢 {col_sel_spot.split(' (')[0]} 세부 모기 개체수 입력**")
            # 2열로 정렬하여 깔끔한 타자 필드 렌더링
            form_cols = st.columns(2)
            input_values = {}
            
            for s_idx, sp in enumerate(target_species):
                with form_cols[s_idx % 2]:
                    # 기존 저장 데이터가 있으면 기본값으로 바인딩
                    existing_df = st.session_state.je_live_db[
                        (st.session_state.je_live_db["조사년도"] == selected_year) & 
                        (st.session_state.je_live_db["조사월"] == selected_month) & 
                        (st.session_state.je_live_db["조사주"] == selected_week) & 
                        (st.session_state.je_live_db["지점명"] == col_sel_spot)
                    ]
                    default_val = int(existing_df[sp].iloc[0]) if not existing_df.empty and sp in existing_df.columns else 0
                    input_values[sp] = st.number_input(f"🦟 {sp} (마리)", min_value=0, max_value=9999, value=default_val, step=1, key=f"in_{sp}")
            
            submit_save = st.form_submit_button("💾 웹 데이터 최종 보관 및 저장")
            
            if submit_save:
                # 세션 데이터 프레임 카피 후 가공
                current_db = st.session_state.je_live_db.copy()
                
                # 기존 행 위치 인덱스 탐색
                match_condition = (
                    (current_db["조사년도"] == selected_year) & 
                    (current_db["조사월"] == selected_month) & 
                    (current_db["조사주"] == selected_week) & 
                    (current_db["지점명"] == col_sel_spot)
                )
                
                # 계산 필드 연산
                total_sum = sum(input_values.values())
                ratio_str = f"{((input_values['작은빨간집모기'] / total_sum) * 100):.1f}%" if total_sum > 0 else "0.0%"
                pathogen_res = "음성" if input_values['작은빨간집모기'] < 30 else "검사중"
                
                if current_db[match_condition].shape[0] > 0:
                    # 기존 기록 업데이트
                    target_idx = current_db[match_condition].index[0]
                    for sp, val in input_values.items():
                        current_db.at[target_idx, sp] = val
                    current_db.at[target_idx, "합계"] = total_sum
                    current_db.at[target_idx, "작은빨간집모기 비율"] = ratio_str
                    current_db.at[target_idx, "병원체검사"] = pathogen_res
                else:
                    # 새로운 행 추가 방어벽
                    lat_map = {"춘천": 37.9250, "강릉": 37.7518, "횡성": 37.4912}
                    lng_map = {"춘천": 127.7410, "강릉": 128.8762, "횡성": 127.9845}
                    region_key = "춘천" if "춘천" in col_sel_spot else ("강릉" if "강릉" in col_sel_spot else "횡성")
                    
                    new_row = {
                        "조사년도": selected_year, "조사월": selected_month, "조사주": selected_week,
                        "지점명": col_sel_spot, "위도": lat_map[region_key], "경도": lng_map[region_key],
                        "합계": total_sum, "작은빨간집모기 비율": ratio_str, "병원체검사": pathogen_res, "비고": "-"
                    }
                    for sp, val in input_values.items():
                        new_row[sp] = val
                    current_db = pd.concat([current_db, pd.DataFrame([new_row])], ignore_index=True)
                
                # 상주 세션 메모리에 영구 저장 보관
                st.session_state.je_live_db = current_db
                st.success(f"✅ {col_sel_spot.split(' (')[0]}의 [{selected_year} {selected_month} {selected_week}] 데이터가 웹 저장소에 성공적으로 동기화되었습니다!")
        
        # 현재 누적 보관된 전체 장부를 확인용 다운로드 파일 서식 바인딩
        st.markdown("##### 📊 현재까지 웹에 누적 적재된 보관 대장 현황")
        st.download_button("📥 웹 입력 완료된 일본뇌염 장부 백업 다운로드 (.csv)", convert_df_to_csv(st.session_state.je_live_db), "일본뇌염_웹입력_백업.csv", "text/csv")

    # 💡 실시간 표출 바인딩 유도
    f_je = st.session_state.je_live_db[
        (st.session_state.je_live_db["조사년도"] == selected_year) & 
        (st.session_state.je_live_db["조사월"] == selected_month) & 
        (st.session_state.je_live_db["조사주"] == selected_week)
    ]
    
    if not f_je.empty:
        je_spots = ["춘천시 신북읍 산천리 (우사 거점)", "강릉시 사천면 산대월리 (우사 거점)", "횡성군 공근면 하대리 (우사 거점)"]
        je_sub_tabs = st.tabs([f"📍 {spot.split(' (')[0]}" for spot in je_spots])
        
        for idx, spot_name in enumerate(je_spots):
            with je_sub_tabs[idx]:
                spot_data = f_je[f_je["지점명"] == spot_name]
                
                if not spot_data.empty:
                    c1, c2 = st.columns([5, 5])
                    with c1:
                        st.markdown(f"##### 🗺️ 지리정보 매핑 및 거점 단면")
                        m_je = folium.Map(location=[float(spot_data['위도'].iloc[0]), float(spot_data['경도'].iloc[0])], zoom_start=11)
                        folium.Marker([float(spot_data['위도'].iloc[0]), float(spot_data['경도'].iloc[0])], tooltip=spot_name, icon=folium.Icon(color='red', icon='home')).add_to(m_je)
                        st_folium(m_je, key=f"map_je_{idx}_{selected_year}_{selected_month}_{selected_week}", width="100%", height=400)
                    with c2:
                        st.markdown(f"##### 📊 {spot_name.split(' (')[0]} 17종 전수 채집 개체수 현황")
                        
                        # 안전 패딩 보정
                        for ts in target_species:
                            if ts not in spot_data.columns: spot_data[ts] = 0
                        if "합계" not in spot_data.columns: spot_data["합계"] = spot_data[target_species].sum(axis=1)
                        
                        graph_series = spot_data[target_species].iloc[0]
                        fig, plt_ax = plt.subplots(figsize=(6, 5.2))
                        bar_colors = ['#ef233c' if sp == "작은빨간집모기" else '#b8c0cb' for sp in target_species]
                        bars = plt_ax.barh(target_species, graph_series.values, color=bar_colors, edgecolor='#2b2d42', height=0.7)
                        
                        for bar in bars:
                            width = bar.get_width()
                            if width > 0:
                                plt_ax.text(width + 0.5, bar.get_y() + bar.get_height()/2, f"{int(width)}마리", va='center', ha='left', fontsize=8, fontproperties=f_prop)
                        
                        plt_ax.invert_yaxis()
                        plt_ax.set_xlabel("채집 개체 수 (마리)", fontproperties=f_prop)
                        if f_prop: plt_ax.set_yticklabels(target_species, fontproperties=f_prop, fontsize=8)
                        plt.tight_layout()
                        st.pyplot(fig)
                        plt.close()
                    
                    display_je_cols = [
                        "조사주", "작은빨간집모기", "이나토미집모기", "반점날개집모기", "동양집모기", "빨간집모기", 
                        "줄다리집모기", "노랑늪모기", "반점날개늪모기", "얼룩날개모기류", "흰줄숲모기", 
                        "금빛숲모기", "금빛어깨숲모기", "한국숲모기", "흰어깨숲모기", "등줄숲모기", "큰검정들모기", 
                        "긴얼룩다리모기", "합계", "작은빨간집모기 비율", "병원체검사", "비고"
                    ]
                    valid_disp = [c for c in display_je_cols if c in spot_data.columns]
                    st.dataframe(spot_data[valid_disp], hide_index=True, use_container_width=True)
                else:
                    st.info(f"💡 {spot_name} 지점의 해당 주차 데이터가 대장에 존재하지 않습니다.")
    else:
        st.info("💡 선택하신 기간의 일본뇌염 감시 데이터가 존재하지 않습니다.")

# --- 2. 말라리아 매개모기 감시 ---
elif selected_tab == "🔵 말라리아 매개모기 감시":
    st.header(f"🪖 접경지역 말라리아 매개모기 주별 감시 현황 [{selected_year} {selected_month} {selected_week}]")
    with st.expander("📥 [말라리아] 표준 입력 파일 업로드 및 샘플 양식 다운로드"):
        mal_tmpl = pd.DataFrame(columns=["조사년도", "조사월", "조사주", "지점명", "위도", "경도", "얼룩날개모기류", "빨간집모기", "합계", "말라리아원충감염조사"])
        mal_tmpl.loc[0] = ["2026년", "05월", "1주", "철원군 대마리 (우사 거점)", 38.2543, 127.2145, 45, 12, 57, "음성"]
        st.download_button("📥 말라리아 주별 전용 샘플양식 다운로드 (.csv)", convert_df_to_csv(mal_tmpl), "말라리아_표준양식.csv", "text/csv", key="dl_mal")
        
        mal_file = st.file_uploader("작성된 말라리아 파일 업로드 (.xlsx 및 .csv 지원)", type=["csv", "xlsx", "xls"], key="mal_up")
        df_mal = base_mal_df if mal_file is None else rename_duplicate_columns(smart_load_uploaded_file(mal_file))

    if not df_mal.empty and "조사년도" not in df_mal.columns: df_mal["조사년도"] = selected_year
    if not df_mal.empty and "조사월" not in df_mal.columns: df_mal["조사월"] = selected_month
    if not df_mal.empty and "조사주" not in df_mal.columns: df_mal["조사주"] = selected_week

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
        cli_file = st.file_uploader(f"작성된 [{selected_zone}] 파일 업로드 (.xlsx 및 .csv 지원)", type=["csv", "xlsx", "xls"], key="cli_up")
        df_cli = base_cli_df if cli_file is None else rename_duplicate_columns(smart_load_uploaded_file(cli_file))

    if not df_cli.empty and "조사년도" not in df_cli.columns: df_cli["조사년도"] = selected_year
    if not df_cli.empty and "조사월" not in df_cli.columns: df_cli["조사월"] = selected_month

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
        
        forest_file = st.file_uploader("작성된 어린이 숲체험장 파일 업로드 (.xlsx 및 .csv 지원)", type=["csv", "xlsx", "xls"], key="forest_up")
        df_forest = base_forest_df if forest_file is None else rename_duplicate_columns(smart_load_uploaded_file(forest_file))

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
        m_forest['gu분지점'] = m_forest.apply(
            lambda x: f"관리지점 {x['지점번호']}" if str(x['분류']).strip().lower() == "in" and x['지점번호'] <= 3 
            else (f"비관리지점 {x['지점번호']}" if str(x['분류']).strip().lower() == "out" and x['지점번호'] <= 3 else "기타 타지점"), axis=1
        )
        m_forest = m_forest[m_forest['gu분지점'] != "기타 타지점"].copy()
        
        if not m_forest.empty:
            h_coords = {"남산": [37.683361, 127.893111], "삼마치": [37.643444, 127.910306]}
            m_forest['위도'] = m_forest['채집지역2'].map(lambda x: h_coords[x][0] if x in h_coords else 37.66)
            m_forest['경도'] = m_forest['채집지역2'].map(lambda x: h_coords[x][1] if x in h_coords else 127.90)
            
            forest_summary = m_forest.pivot_table(
                index=["채집지역2", "gu분지점", "위도", "경도"],
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
                            popup_text += f"• {r['gu분지점']}: 월간 누적 {r['합계']}개체<br>"
                        folium.Marker(latlng, tooltip=f"홍천 {r_name} 유아숲체험원", popup=folium.Popup(popup_text, max_width=350), icon=folium.Icon(color='green', icon='tree')).add_to(m_f)
                    st_folium(m_f, key="map_forest_final", width="100%", height=430)
                    
                with col_f_graph:
                    st.markdown(f"##### 📊 [대조분석] 관리지점 1-3(In) vs 비관리지점 1-3(Out) 월간 비교")
                    fig, ax = plt.subplots(figsize=(6, 5))
                    chart_df = forest_summary.pivot_table(index="gu분지점", columns="채집지역2", values="합계", aggfunc="sum")
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
                display_cols = ["채집지역2", "gu분지점"] + avail_species + ["합계"]
                st.dataframe(forest_summary[display_cols].rename(columns={"채집지역2": "체험원명", "gu분지점": "구분지점"}), hide_index=True, use_container_width=True)
            else:
                st.info("💡 요약 조건에 맞는 채집 수치 데이터가 존재하지 않습니다.")
        else:
            st.info("💡 관리지점 1~3 및 비관리지점 1~3 범위에 매칭되는 채집 데이터가 없습니다.")
    else:
        st.info("💡 선택하신 연도와 월에 해당하는 어린이 숲 체험장 조사 내역이 없습니다.")