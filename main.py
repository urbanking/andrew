import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import unicodedata
from pathlib import Path
import io
import time

# -----------------------------------------------------------------------------
# 1. Configuration & CSS (한글 폰트 설정)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    page_icon="🌱",
    layout="wide"
)

# Streamlit UI 한글 폰트 적용
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
/* 탭 텍스트 폰트 적용 */
.stTabs [data-baseweb="tab"] {
    font-family: 'Noto Sans KR', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# Plotly 그래프용 공통 폰트 설정
PLOTLY_FONT = dict(family="Noto Sans KR, Malgun Gothic, Apple SD Gothic Neo, sans-serif")

# -----------------------------------------------------------------------------
# 2. Helper Functions (파일 인식 및 정규화)
# -----------------------------------------------------------------------------
def normalize_str(s):
    """문자열을 NFC로 정규화하여 Mac/Windows 자소 분리 문제 해결"""
    return unicodedata.normalize('NFC', s) if s else s

def find_file_fuzzy(directory: Path, keyword: str, extension: str):
    """
    디렉토리 내에서 키워드와 확장자를 포함하는 파일을 NFC/NFD 무관하게 탐색
    """
    if not directory.exists():
        return None
    
    target_keyword = normalize_str(keyword)
    target_ext = normalize_str(extension).lower()

    for file_path in directory.iterdir():
        # 파일명 정규화
        f_name = normalize_str(file_path.name)
        
        # 키워드가 포함되어 있고 확장자가 일치하는지 확인
        if target_keyword in f_name and f_name.lower().endswith(target_ext):
            return file_path
    return None

# -----------------------------------------------------------------------------
# 3. Data Loading (캐싱 및 에러 처리)
# -----------------------------------------------------------------------------
SCHOOL_CONFIG = {
    "송도고": {"ec": 1.0, "color": "#1f77b4"},
    "하늘고": {"ec": 2.0, "color": "#2ca02c"}, # 최적 (초록)
    "아라고": {"ec": 4.0, "color": "#ff7f0e"},
    "동산고": {"ec": 8.0, "color": "#d62728"}
}

@st.cache_data
def load_data():
    """환경 데이터(CSV)와 생육 데이터(XLSX)를 로드하고 전처리"""
    data_dir = Path("data")
    
    if not data_dir.exists():
        st.error(f"❌ 'data' 폴더를 찾을 수 없습니다. 현재 경로: {Path.cwd()}")
        return None, None

    # 1) 환경 데이터 로드 (CSV)
    env_dfs = []
    
    for school_name, config in SCHOOL_CONFIG.items():
        # 파일 찾기: "송도고"가 포함된 csv
        csv_path = find_file_fuzzy(data_dir, school_name, ".csv")
        
        if csv_path:
            try:
                df = pd.read_csv(csv_path)
                # 컬럼 공백 제거 및 소문자 변환
                df.columns = df.columns.str.strip().str.lower()
                
                # 필수 컬럼 확인
                required_cols = ['time', 'temperature', 'humidity', 'ph', 'ec']
                if all(col in df.columns for col in required_cols):
                    df['school'] = school_name
                    df['target_ec'] = config['ec']
                    df['time'] = pd.to_datetime(df['time'], errors='coerce')
                    env_dfs.append(df)
                else:
                    st.warning(f"⚠️ {csv_path.name} 파일에 필수 컬럼이 부족합니다.")
            except Exception as e:
                st.error(f"❌ {csv_path.name} 로드 중 에러: {e}")
        else:
            # 파일을 못 찾았을 경우 경고 로그 (선택적)
            pass

    env_final = pd.concat(env_dfs, ignore_index=True) if env_dfs else pd.DataFrame()

    # 2) 생육 데이터 로드 (Excel)
    growth_final = pd.DataFrame()
    
    # "생육결과" 또는 "4개교" 키워드가 포함된 엑셀 파일 찾기
    xlsx_path = find_file_fuzzy(data_dir, "생육결과", ".xlsx")
    if not xlsx_path:
        xlsx_path = find_file_fuzzy(data_dir, "4개교", ".xlsx") # 대체 키워드

    if xlsx_path:
        try:
            # 모든 시트 읽기
            xls = pd.read_excel(xlsx_path, sheet_name=None, engine='openpyxl')
            
            growth_dfs = []
            for sheet_name, df in xls.items():
                norm_sheet = normalize_str(sheet_name)
                
                # 시트 이름이 학교명 중 하나와 매칭되는지 확인
                matched_school = None
                for school in SCHOOL_CONFIG.keys():
                    if school in norm_sheet:
                        matched_school = school
                        break
                
                if matched_school:
                    # 컬럼 이름 표준화 (공백 제거)
                    df.columns = df.columns.str.replace(" ", "").str.strip()
                    
                    # 필요한 컬럼 매핑 및 이름 변경
                    # 예상 컬럼: 개체번호, 잎수(장), 지상부길이(mm), 지하부길이(mm), 생중량(g)
                    # 유연하게 처리하기 위해 rename 사용
                    rename_map = {
                        '잎수(장)': 'leaves', '잎수': 'leaves',
                        '지상부길이(mm)': 'height_top', '지상부길이': 'height_top',
                        '지하부길이(mm)': 'height_root', '지하부길이': 'height_root',
                        '생중량(g)': 'biomass', '생중량': 'biomass',
                        '개체번호': 'id'
                    }
                    df = df.rename(columns=rename_map)
                    
                    df['school'] = matched_school
                    df['target_ec'] = SCHOOL_CONFIG[matched_school]['ec']
                    growth_dfs.append(df)
            
            if growth_dfs:
                growth_final = pd.concat(growth_dfs, ignore_index=True)
                
        except Exception as e:
            st.error(f"❌ 생육 데이터 로드 중 에러: {e}")
    else:
        st.warning("⚠️ 생육 결과 엑셀 파일을 찾을 수 없습니다.")

    return env_final, growth_final

# -----------------------------------------------------------------------------
# 4. Main Application Logic
# -----------------------------------------------------------------------------
def main():
    st.title("🌱 극지식물 최적 EC 농도 연구")
    
    # 데이터 로딩
    with st.spinner("데이터를 불러오는 중입니다..."):
        env_df, growth_df = load_data()

    # 데이터 로드 실패 시 중단
    if (env_df is None or env_df.empty) and (growth_df is None or growth_df.empty):
        st.error("데이터 로드에 실패했습니다. `data` 폴더와 파일명을 확인해주세요.")
        return

    # --- Sidebar ---
    st.sidebar.header("🔍 필터 설정")
    school_list = ["전체"] + list(SCHOOL_CONFIG.keys())
    selected_school = st.sidebar.selectbox("학교(조건) 선택", school_list)

    # 필터링
    if selected_school != "전체":
        filtered_env = env_df[env_df['school'] == selected_school] if not env_df.empty else pd.DataFrame()
        filtered_growth = growth_df[growth_df['school'] == selected_school] if not growth_df.empty else pd.DataFrame()
    else:
        filtered_env = env_df
        filtered_growth = growth_df

    # --- Tabs ---
    tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

    # =========================================================================
    # Tab 1: 실험 개요
    # =========================================================================
    with tab1:
        st.markdown("### 📌 연구 배경 및 목적")
        st.info(
            """
            **극지 식물의 대량 증식을 위한 최적의 양액 농도(EC) 규명**
            * 각기 다른 EC 농도(1.0, 2.0, 4.0, 8.0)를 설정한 4개 학교의 환경 데이터와 식물 생육 데이터를 비교 분석합니다.
            * **목표:** 최적의 생육을 보이는 EC 농도 구간을 도출하여 스마트팜 재배 가이드라인을 제시합니다.
            """
        )

        st.markdown("### 🏫 학교별 실험 조건")
        
        # 조건 요약 테이블 생성
        summary_data = []
        for school, conf in SCHOOL_CONFIG.items():
            count = len(growth_df[growth_df['school'] == school]) if not growth_df.empty else 0
            summary_data.append({
                "학교명": school,
                "목표 EC (dS/m)": conf['ec'],
                "실험 개체수": f"{count}개",
                "비고": "최적 예상" if conf['ec'] == 2.0 else "-"
            })
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

        st.markdown("### 🔑 주요 지표 (Overall)")
        m1, m2, m3, m4 = st.columns(4)
        
        total_samples = len(growth_df) if not growth_df.empty else 0
        avg_temp = env_df['temperature'].mean() if not env_df.empty else 0
        avg_hum = env_df['humidity'].mean() if not env_df.empty else 0
        
        # 생중량이 가장 높은 그룹 찾기
        best_ec_school = "-"
        if not growth_df.empty:
            best_school_grp = growth_df.groupby('school')['biomass'].mean().idxmax()
            best_ec_val = SCHOOL_CONFIG[best_school_grp]['ec']
            best_ec_school = f"{best_ec_val} ({best_school_grp})"

        m1.metric("총 실험 개체수", f"{total_samples}개")
        m2.metric("전체 평균 온도", f"{avg_temp:.1f} °C")
        m3.metric("전체 평균 습도", f"{avg_hum:.1f} %")
        m4.metric("현재 최적 EC", best_ec_school, delta="생중량 기준")

    # =========================================================================
    # Tab 2: 환경 데이터
    # =========================================================================
    with tab2:
        if env_df.empty:
            st.warning("환경 데이터가 없습니다.")
        else:
            st.subheader("🏫 학교별 환경 평균 비교")
            
            # 평균 계산
            env_avg = env_df.groupby('school')[['temperature', 'humidity', 'ph', 'ec', 'target_ec']].mean().reset_index()
            
            # 서브플롯 생성
            fig_env = make_subplots(
                rows=2, cols=2,
                subplot_titles=("평균 온도 (°C)", "평균 습도 (%)", "평균 pH", "목표 EC vs 실측 EC"),
                vertical_spacing=0.15
            )

            # 색상 매핑 리스트
            colors = [SCHOOL_CONFIG[s]['color'] for s in env_avg['school']]

            # 1. 온도
            fig_env.add_trace(
                go.Bar(x=env_avg['school'], y=env_avg['temperature'], name="온도", marker_color=colors, showlegend=False),
                row=1, col=1
            )
            # 2. 습도
            fig_env.add_trace(
                go.Bar(x=env_avg['school'], y=env_avg['humidity'], name="습도", marker_color=colors, showlegend=False),
                row=1, col=2
            )
            # 3. pH
            fig_env.add_trace(
                go.Bar(x=env_avg['school'], y=env_avg['ph'], name="pH", marker_color=colors, showlegend=False),
                row=2, col=1
            )
            # 4. EC (이중 막대)
            fig_env.add_trace(
                go.Bar(x=env_avg['school'], y=env_avg['target_ec'], name="목표 EC", marker_color='lightgray'),
                row=2, col=2
            )
            fig_env.add_trace(
                go.Bar(x=env_avg['school'], y=env_avg['ec'], name="실측 EC", marker_color=colors),
                row=2, col=2
            )

            fig_env.update_layout(height=600, font=PLOTLY_FONT)
            st.plotly_chart(fig_env, use_container_width=True)

            st.divider()
            
            st.subheader(f"📈 시계열 변화 ({selected_school})")
            
            if not filtered_env.empty:
                # 데이터가 너무 많으면 다운샘플링 (예: 1시간 단위)
                # filtered_env_resampled = filtered_env.set_index('time').groupby(['school']).resample('1H').mean().reset_index()
                # 여기선 간단히 원본 사용 (성능 이슈 시 위 주석 해제하여 사용)
                
                # 시계열 차트 3개 (온도, 습도, EC)
                fig_ts = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                     subplot_titles=("온도 변화", "습도 변화", "EC 변화"))

                schools_to_plot = filtered_env['school'].unique()
                
                for school in schools_to_plot:
                    subset = filtered_env[filtered_env['school'] == school].sort_values('time')
                    c = SCHOOL_CONFIG[school]['color']
                    
                    fig_ts.add_trace(go.Scatter(x=subset['time'], y=subset['temperature'], name=f"{school} 온도", line=dict(color=c), legendgroup=school), row=1, col=1)
                    fig_ts.add_trace(go.Scatter(x=subset['time'], y=subset['humidity'], name=f"{school} 습도", line=dict(color=c), legendgroup=school, showlegend=False), row=2, col=1)
                    fig_ts.add_trace(go.Scatter(x=subset['time'], y=subset['ec'], name=f"{school} EC", line=dict(color=c), legendgroup=school, showlegend=False), row=3, col=1)
                    
                    # 목표 EC 라인 추가 (마지막 그래프)
                    target = SCHOOL_CONFIG[school]['ec']
                    fig_ts.add_hline(y=target, line_dash="dot", line_color=c, annotation_text=f"{school} 목표", row=3, col=1)

                fig_ts.update_layout(height=800, font=PLOTLY_FONT)
                st.plotly_chart(fig_ts, use_container_width=True)
            else:
                st.info("선택한 학교의 시계열 데이터가 없습니다.")

            # Expander & Download
            with st.expander("💾 환경 데이터 원본 보기 및 다운로드"):
                st.dataframe(filtered_env.head(100))
                
                # CSV 다운로드
                csv_buffer = filtered_env.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="CSV 다운로드",
                    data=csv_buffer,
                    file_name="environmental_data.csv",
                    mime="text/csv"
                )

    # =========================================================================
    # Tab 3: 생육 결과
    # =========================================================================
    with tab3:
        if growth_df.empty:
            st.warning("생육 데이터가 없습니다.")
        else:
            # 그룹핑
            growth_avg = growth_df.groupby('school').agg({
                'biomass': 'mean',
                'leaves': 'mean',
                'height_top': 'mean',
                'id': 'count'
            }).reset_index()
            
            # 정렬 (EC 순서대로: 송도 -> 하늘 -> 아라 -> 동산)
            sort_order = ["송도고", "하늘고", "아라고", "동산고"]
            growth_avg['school'] = pd.Categorical(growth_avg['school'], categories=sort_order, ordered=True)
            growth_avg = growth_avg.sort_values('school')

            # --- 핵심 결과 카드 ---
            max_bio_idx = growth_avg['biomass'].idxmax()
            best_school = growth_avg.loc[max_bio_idx, 'school']
            best_bio = growth_avg.loc[max_bio_idx, 'biomass']
            best_ec = SCHOOL_CONFIG[str(best_school)]['ec']
            
            st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #2ca02c; margin-bottom: 20px;">
                <h3 style="margin:0; color: #2ca02c;">🥇 최적 생육 조건: {best_school} (EC {best_ec})</h3>
                <p style="margin:5px 0 0 0; font-size: 1.1em;">
                    평균 생중량 <strong>{best_bio:.2f}g</strong>으로 가장 우수한 성장을 보였습니다.
                </p>
            </div>
            """, unsafe_allow_html=True)

            # --- 2x2 서브플롯 (생육 비교) ---
            st.subheader("📊 EC 농도별 생육 지표 비교")
            
            fig_growth = make_subplots(
                rows=2, cols=2,
                subplot_titles=("평균 생중량 (g) ⭐", "평균 잎 수 (장)", "평균 지상부 길이 (mm)", "실험 개체 수"),
                vertical_spacing=0.15
            )

            # 색상 배열 생성 (하늘고 강조)
            bar_colors = []
            for s in growth_avg['school']:
                # 하늘고(EC 2.0)이면 진한 색, 아니면 투명도 조절
                base_color = SCHOOL_CONFIG[str(s)]['color']
                bar_colors.append(base_color)

            # X축 공통
            x_ax = growth_avg['school']

            # 1. 생중량
            fig_growth.add_trace(go.Bar(x=x_ax, y=growth_avg['biomass'], marker_color=bar_colors, name="생중량"), row=1, col=1)
            # 2. 잎 수
            fig_growth.add_trace(go.Bar(x=x_ax, y=growth_avg['leaves'], marker_color=bar_colors, name="잎 수"), row=1, col=2)
            # 3. 지상부 길이
            fig_growth.add_trace(go.Bar(x=x_ax, y=growth_avg['height_top'], marker_color=bar_colors, name="지상부 길이"), row=2, col=1)
            # 4. 개체 수
            fig_growth.add_trace(go.Bar(x=x_ax, y=growth_avg['id'], marker_color='gray', name="개체 수"), row=2, col=2)

            fig_growth.update_layout(height=600, showlegend=False, font=PLOTLY_FONT)
            st.plotly_chart(fig_growth, use_container_width=True)

            # --- 분포 및 상관관계 ---
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("📦 학교별 생중량 분포")
                fig_box = px.box(
                    filtered_growth, x='school', y='biomass', 
                    color='school',
                    color_discrete_map={k: v['color'] for k, v in SCHOOL_CONFIG.items()},
                    category_orders={"school": sort_order}
                )
                fig_box.update_layout(font=PLOTLY_FONT)
                st.plotly_chart(fig_box, use_container_width=True)

            with c2:
                st.subheader("🔗 잎 수 vs 생중량 상관관계")
                fig_scat = px.scatter(
                    filtered_growth, x='leaves', y='biomass', 
                    color='school', size='height_top',
                    color_discrete_map={k: v['color'] for k, v in SCHOOL_CONFIG.items()},
                    hover_data=['id']
                )
                fig_scat.update_layout(font=PLOTLY_FONT)
                st.plotly_chart(fig_scat, use_container_width=True)

            # Expander & Download (Excel)
            with st.expander("💾 생육 데이터 원본 보기 및 다운로드"):
                st.dataframe(filtered_growth)
                
                # Excel Download Logic (BytesIO 필수)
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    filtered_growth.to_excel(writer, index=False, sheet_name='Data')
                
                buffer.seek(0)
                
                st.download_button(
                    label="Excel 다운로드",
                    data=buffer,
                    file_name="growth_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

if __name__ == "__main__":
    main()
