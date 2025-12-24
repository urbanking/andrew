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
    school_data = {
        '송도고': len(xlsx_data['송도고']),
        '하늘고': len(xlsx_data['하늘고']),
        '아라고': len(xlsx_data['아라고']),
        '동산고': len(xlsx_data['동산고'])
    }
    ec_df = pd.DataFrame(list(ec_conditions.items()), columns=['학교명', 'EC 목표'])
    ec_df['개체수'] = ec_df['학교명'].map(school_data)
    ec_df['색상'] = ['#FF6347', '#2E8B57', '#4682B4', '#F]()_
