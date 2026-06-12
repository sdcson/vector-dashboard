# =================================================================================
# 5. 💡 [신규] 공공데이터포털 JSON API 기반 기상 상관분석 레이어
# =================================================================================
elif selected_tab == "☁️ 기상 요인 상관분석":
    st.header(f"☁️ 기후 요인 및 매개체 발생 상관분석")
    
    col_c1, col_c2, col_c3, col_c4 = st.columns([2, 3, 3, 3])
    with col_c1:
        years_list = ["2026년", "2025년", "2024년", "2023년", "2022년", "2021년", "2020년"]
        analysis_year = st.selectbox("분석 연도", years_list, index=years_list.index(selected_year))
    with col_c2:
        # 💡 분석 대상 항목 추가
        target_disease = st.selectbox("분석 대상 감시망", [
            "일본뇌염 매개모기 (Culex tritaeniorhynchus)", 
            "말라리아 매개모기 (Anopheles spp.)",
            "기후변화 모기",
            "참진드기",
            "털진드기",
            "어린이숲 참진드기"
        ])
    with col_c3:
        # 💡 대상별로 지점 리스트 분기 처리
        if "일본뇌염" in target_disease:
            spots_list = ["춘천시 산천리", "강릉시 산대월리", "횡성군 하대리"]
        elif "말라리아" in target_disease:
            spots_list = ["춘천시 중앙동", "춘천시 지내리", "철원군 대마리", "철원군 학사리", "화천군", "양구군", "인제군", "고성군"]
        elif "기후변화" in target_disease:
            spots_list = ["춘천시보건소", "백로서식지", "삼천동"]
        elif "참진드기" == target_disease:  # 권역 참진드기
            spots_list = ["화천군", "인제군"]
        elif "털진드기" in target_disease:
            spots_list = ["춘천시", "화천군", "인제군", "철원군", "기타지점"] # 필요한 지점으로 유연하게 조정 가능
        elif "어린이숲" in target_disease:
            spots_list = ["홍천", "정선", "춘천", "인제", "속초", "양양", "남산", "삼마치"]
            
        selected_spot = st.selectbox("조사지점 선택", spots_list)
    with col_c4:
        climate_factors = st.multiselect("비교할 기후 인자", ["평균기온(°C)", "누적강수량(mm)", "평균습도(%)"], default=["평균기온(°C)", "누적강수량(mm)"])
        
    st.markdown("---")
    
    def get_normalized_spot_for_analysis(raw_str, disease):
        l = str(raw_str).replace(" ", "")
        if "일본뇌염" in disease:
            if "산대" in l or "강릉" in l: return "강릉시 산대월리"
            if "하대" in l or "횡성" in l: return "횡성군 하대리"
            return "춘천시 산천리"
        elif "말라리아" in disease:
            if "화천" in l: return "화천군"
            if "양구" in l: return "양구군"
            if "인제" in l: return "인제군"
            if "고성" in l: return "고성군"
            if "중앙" in l: return "춘천시 중앙동"
            if "지내" in l: return "춘천시 지내리"
            if "학사" in l: return "철원군 학사리"
            return "철원군 대마리"
        else:
            # 새로 추가된 감시망들은 기본 문자열 반환 (부분 일치 검색 활용)
            return str(raw_str).strip()

    # 💡 대상 감시망별 데이터프레임 매핑 및 종(Species) 키워드 세팅
    if "일본뇌염" in target_disease:
        df_target = base_je_df.copy()
        species_keyword, target_name_kr = "tritaeniorhynchus", "작은빨간집모기"
    elif "말라리아" in target_disease:
        df_target = base_mal_df.copy()
        species_keyword, target_name_kr = "Anopheles", "얼룩날개모기류"
    elif "기후변화" in target_disease:
        df_target = base_cli_moq_df.copy()
        species_keyword, target_name_kr = "", "기후변화 모기 통합"
    elif "참진드기" == target_disease:
        df_target = base_cli_tick_df.copy()
        species_keyword, target_name_kr = "", "참진드기 통합"
    elif "털진드기" in target_disease:
        df_target = base_cli_mite_dist_df.copy()
        species_keyword, target_name_kr = "", "털진드기 통합"
    elif "어린이숲" in target_disease:
        df_target = base_forest_df.copy()
        species_keyword, target_name_kr = "", "어린이숲 참진드기"

    if not df_target.empty:
        # 어린이숲 데이터 구조 분기 방어
        if "어린이숲" not in target_disease:
            df_target = parse_vectornet_dataframe(df_target, analysis_year, selected_month)
            
        f_target = df_target[df_target["조사년도"] == analysis_year].copy()
        
        # 💡 어린이숲은 '채집지역2' 컬럼 사용, 나머지는 '지역2'
        loc_col = "채집지역2" if "어린이숲" in target_disease else "지역2"
        f_target["정규화_지점"] = f_target.get(loc_col, pd.Series([""]*len(f_target))).apply(lambda x: get_normalized_spot_for_analysis(x, target_disease))
        
        # 지점 필터
        if target_disease in ["일본뇌염 매개모기 (Culex tritaeniorhynchus)", "말라리아 매개모기 (Anopheles spp.)"]:
            spot_mask = f_target["정규화_지점"] == selected_spot
        else:
            spot_mask = f_target["정규화_지점"].str.contains(selected_spot, na=False) # 신규 추가 항목은 포함(contains) 조건 적용

        # 종(Species) 필터
        if species_keyword:
            species_mask = f_target["종"].str.contains(species_keyword, na=False, case=False)
        else:
            species_mask = pd.Series([True]*len(f_target)) # 종 지정이 없으면 모두 합산
            
        f_target = f_target[spot_mask & species_mask]
        val_col_target = "개체수" if "개체수" in f_target.columns else ("채집수" if "채집수" in f_target.columns else "개체수")
        
        # 결측치 방어를 위한 강제 숫자 변환
        f_target[val_col_target] = pd.to_numeric(f_target[val_col_target], errors='coerce').fillna(0)
        
        if "2026" in analysis_year: months = [f"{m:02d}월" for m in range(3, 6)]
        else: months = [f"{m:02d}월" for m in range(3, 11)]
            
        monthly_counts = {m: 0 for m in months}
        for _, row in f_target.iterrows():
            m_str = str(row.get("조사월", "")).strip()
            if m_str in monthly_counts: monthly_counts[m_str] += row.get(val_col_target, 0)
                
        plot_df = pd.DataFrame(list(monthly_counts.items()), columns=["조사월", "채집량(마리)"])
        
        with st.spinner(f"📡 {analysis_year} {selected_spot} 기상청 JSON 데이터를 불러오는 중입니다..."):
            bulk_weather = get_kma_weather_bulk(analysis_year, selected_spot)
            plot_df["평균기온(°C)"] = [bulk_weather.get(m, {}).get("temp", 0.0) for m in plot_df["조사월"]]
            plot_df["누적강수량(mm)"] = [bulk_weather.get(m, {}).get("precip", 0.0) for m in plot_df["조사월"]]
            plot_df["평균습도(%)"] = [bulk_weather.get(m, {}).get("humid", 0.0) for m in plot_df["조사월"]]
        
        st.markdown(f"##### 📊 {selected_spot} {target_name_kr} 계절적 변화 추이 ({analysis_year} {months[0]}~{months[-1]})")
        fig, ax1 = plt.subplots(figsize=(12, 5.5))
        
        bars = ax1.bar(plot_df["조사월"], plot_df["채집량(마리)"], color='#2b2d42', label=f'{target_name_kr} 채집량', alpha=0.85, width=0.5)
        ax1.set_ylabel('월별 총 채집량 (마리)', color='#2b2d42', fontweight='bold')
        ax1.tick_params(axis='y', labelcolor='#2b2d42')
        max_count = plot_df["채집량(마리)"].max()
        ax1.set_ylim(0, max_count * 1.2 if max_count > 0 else 10)
        
        for bar in bars:
            height = bar.get_height()
            if height > 0: ax1.text(bar.get_x() + bar.get_width()/2., height, f'{int(height)}', ha='center', va='bottom', fontsize=9)
        
        if climate_factors:
            ax2 = ax1.twinx()
            colors = {"평균기온(°C)": "#e63946", "누적강수량(mm)": "#457b9d", "평균습도(%)": "#2a9d8f"}
            markers = {"평균기온(°C)": "o", "누적강수량(mm)": "s", "평균습도(%)": "^"}
            offsets = {"평균기온(°C)": (0, 10), "누적강수량(mm)": (0, -15), "평균습도(%)": (0, 15)}
            
            for factor in climate_factors:
                color = colors.get(factor, 'black')
                ax2.plot(plot_df["조사월"], plot_df[factor], color=color, marker=markers.get(factor, 'o'), linestyle='-', linewidth=2.5, markersize=8, label=factor)
                for idx, val in enumerate(plot_df[factor]):
                    if pd.notna(val) and val != 0.0:
                        suffix = "°C" if "기온" in factor else ("mm" if "강수" in factor else "%")
                        ax2.annotate(f"{val}{suffix}", (idx, val), textcoords="offset points", xytext=offsets.get(factor, (0, 10)), ha='center', fontsize=8, color=color, fontweight='bold')
                
            ax2.set_ylabel('기상 관측 수치', fontweight='bold')
            lines_1, labels_1 = ax1.get_legend_handles_labels()
            lines_2, labels_2 = ax2.get_legend_handles_labels()
            ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper left', bbox_to_anchor=(0.02, 0.98))
        else:
            ax1.legend(loc='upper left')
            
        plt.grid(axis='y', linestyle='--', alpha=0.4)
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()
        
        st.markdown("##### 📝 월간 집계 상세 데이터")
        st.dataframe(plot_df, hide_index=True, use_container_width=True)
    else:
        st.info("💡 해당 연도의 데이터가 존재하지 않아 기후 분석을 생성할 수 없습니다.")