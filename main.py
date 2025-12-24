import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import unicodedata
import io
from plotly.subplots import make_subplots

# 한글 폰트 깨짐 방지
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# 데이터 로딩 함수 (파일 경로 인식 오류 방지 및 캐싱)
@st.cache_data
def load_data():
    # 데이터 파일 경로 설정
    data_path = Path('data')
    
    # 파일명 NFC 형식으로 변환하여 리스트에 저장
    files = [file for file in data_path.iterdir() if unicodedata.normalize('NFC', file.name) == file.name]
    
    # CSV 파일 로딩
    csv_files = {file.stem: pd.read_csv(file) for file in files if file.suffix == '.csv'}
    
    # Excel 파일 로딩 (여기서는 4개의 시트 로딩)
    xlsx_files = [file for file in files if file.suffix == '.xlsx']
    
    if len(xlsx_files) > 1:
        xlsx_file = xlsx_files[0]  # 중복된 엑셀 파일이 있으면 첫 번째 파일을 사용
    elif len(xlsx_files) == 1:
        xlsx_file = xlsx_files[0]
    else:
        st.error("엑셀 파일이 없습니다.")
        return None, None
    
    sheet_names = pd.ExcelFile(xlsx_file).sheet_names
    xlsx_data = {sheet: pd.read_excel(xlsx_file, sheet_name=sheet) for sheet in sheet_names}
    
    return csv_files, xlsx_data

# 데이터 로딩
csv_files, xlsx_data = load_data()

if csv_files is None or xlsx_data is None:
    st.error("데이터 로딩에 실패했습니다.")
    st.stop()

# 사이드바 학교 선택
school_options = ['전체', '송도고', '하늘고', '아라고', '동산고']
selected_school = st.sidebar.selectbox('학교 선택', school_options)

# Tab 1: 실험 개요
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# Tab 1 내용
with tab1:
    st.header("극지식물 최적 EC 농도 연구")
    st.subheader("연구 배경 및 목적")
    st.write("""
        본 연구는 극지식물의 최적 EC 농도를 찾기 위한 실험으로, 각기 다른 EC 조건에서의 생육 결과를 비교하고, 
        환경 데이터를 바탕으로 최적의 EC 농도를 도출하는 것을 목표로 합니다.
    """)

    # 학교별 EC 조건 표
    st.write("학교별 EC 조건")
    ec_conditions = {
        '송도고': 1.0,
        '하늘고': 2.0,
        '아라고': 4.0,
        '동산고': 8.0
    }
    
    # CSV 파일에서 각 학교의 데이터 로드
    school_data = {school: len(csv_files[f"{school}_환경데이터"]) if f"{school}_환경데이터" in csv_files else 0 for school in ec_conditions}
    
    ec_df = pd.DataFrame(list(ec_conditions.items()), columns=['학교명', 'EC 목표'])
    ec_df['개체수'] = ec_df['학교명'].map(school_data)
    ec_df['색상'] = ['#FF6347', '#2E8B57', '#4682B4', '#FFD700']  # 색상 지정
    st.dataframe(ec_df)

    # 주요 지표 카드
    total_plants = sum(school_data.values())
    avg_temp = sum([csv['temperature'].mean() for csv in csv_files.values()]) / len(csv_files)
    avg_humidity = sum([csv['humidity'].mean() for csv in csv_files.values()]) / len(csv_files)
    optimal_ec = ec_conditions[selected_school] if selected_school != '전체' else 2.0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 개체수", total_plants)
    with col2:
        st.metric("평균 온도 (°C)", round(avg_temp, 2))
    with col3:
        st.metric("평균 습도 (%)", round(avg_humidity, 2))
    with col4:
        st.metric("최적 EC", optimal_ec)

# Tab 2: 환경 데이터
with tab2:
    st.header("환경 데이터")
    
    if selected_school != '전체' and f"{selected_school}_환경데이터" in csv_files:
        school_csv = csv_files[f"{selected_school}_환경데이터"]
        
        # 평균 온도, 습도, pH, EC 비교 (2x2 서브플롯)
        fig = make_subplots(rows=2, cols=2, subplot_titles=["평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"])
        
        # 온도, 습도, pH 막대 그래프
        fig.add_trace(go.Bar(x=school_csv['time'], y=school_csv['temperature'], name='온도'), row=1, col=1)
        fig.add_trace(go.Bar(x=school_csv['time'], y=school_csv['humidity'], name='습도'), row=1, col=2)
        fig.add_trace(go.Bar(x=school_csv['time'], y=school_csv['ph'], name='pH'), row=2, col=1)
        
        # 목표 EC vs 실측 EC 비교
        fig.add_trace(go.Bar(x=school_csv['time'], y=school_csv['ec'], name='실측 EC'), row=2, col=2)
        fig.add_trace(go.Scatter(x=school_csv['time'], y=[optimal_ec] * len(school_csv), mode='lines', name='목표 EC', line=dict(color='red', dash='dash')), row=2, col=2)
        
        fig.update_layout(title="학교별 환경 평균 비교", showlegend=True)
        st.plotly_chart(fig)
    
    else:
        st.error(f"선택한 학교({selected_school})에 대한 데이터가 없습니다. 다른 학교를 선택해 주세요.")

# Tab 3: 생육 결과
with tab3:
    st.header("생육 결과")
    
    # EC별 평균 생중량 비교 (엑셀 컬럼명 확인)
    ec_growth_data = {}
    for school in xlsx_data:
        if '생중량' in xlsx_data[school].columns:
            ec_growth_data[school] = xlsx_data[school]['생중량'].mean()
        else:
            st.warning(f"{school} 시트에 '생중량' 컬럼이 없습니다. 다른 컬럼을 사용할 수 있습니다.")
            continue
    
    if not ec_growth_data:
        st.error("생중량 데이터가 없습니다.")
    else:
        fig = make_subplots(rows=2, cols=2, subplot_titles=["평균 생중량", "평균 잎 수", "평균 지상부 길이", "개체수 비교"])
        
        # 평균 생중량
        for school, growth in ec_growth_data.items():
            fig.add_trace(go.Bar(x=[school], y=[growth], name=school), row=1, col=1)
        
        fig.update_layout(title="EC별 생육 비교", showlegend=True)
        st.plotly_chart(fig)
    
    # XLSX 다운로드
    buffer = io.BytesIO()
    ec_growth_df = pd.DataFrame(list(ec_growth_data.items()), columns=['학교', '평균 생중량'])
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        ec_growth_df.to_excel(writer, index=False, sheet_name="EC별 생육 결과")
    buffer.seek(0)
    
    st.download_button(
        label="EC별 생육 결과 다운로드",
        data=buffer,
        file_name="EC별_생육_결과.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
