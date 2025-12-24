import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
from pathlib import Path
import unicodedata
import openpyxl

# 데이터 로딩 최적화
@st.cache_data
def load_data(file_path):
    return pd.read_csv(file_path)

@st.cache_data
def load_excel_data(file_path, sheet_name):
    return pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")

# 파일 인식 및 경로 처리 (NFC / NFD 비교)
def get_files_in_directory(directory):
    files = []
    for file in Path(directory).iterdir():
        normalized_name = unicodedata.normalize('NFC', file.name)
        files.append(normalized_name)
    return files

# XLSX 다운로드 기능
def download_excel(df, filename="data.xlsx"):
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    return buffer

# 설정
st.set_page_config(page_title="극지식물 최적 EC 농도 연구", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# 사이드바
school = st.sidebar.selectbox("학교 선택", ["전체", "송도고", "하늘고", "아라고", "동산고"])

# Tab 설정
tabs = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# Tab 1: 실험 개요
with tabs[0]:
    st.title("극지식물 최적 EC 농도 연구")
    st.write("연구 배경 및 목적...")
    
    # 학교별 EC 조건 표
    school_ec_conditions = {
        "송도고": {"EC 목표": "1.0", "개체수": 29, "색상": "#f4a300"},
        "하늘고": {"EC 목표": "2.0", "개체수": 45, "색상": "#5db7f5"},
        "아라고": {"EC 목표": "4.0", "개체수": 106, "색상": "#ff6c91"},
        "동산고": {"EC 목표": "8.0", "개체수": 58, "색상": "#32cd32"}
    }
    
    data = school_ec_conditions.get(school, school_ec_conditions["송도고"])
    st.table(pd.DataFrame(data, index=[0]))

    # 주요 지표 카드
    st.metric(label="총 개체수", value=29 if school == "송도고" else 45)
    st.metric(label="평균 온도", value="25°C")  # 예시 값
    st.metric(label="평균 습도", value="60%")  # 예시 값
    st.metric(label="최적 EC", value="2.0")

# Tab 2: 환경 데이터
with tabs[1]:
    st.title("환경 데이터")
    
    # 데이터 로딩
    with st.spinner("데이터 로딩 중..."):
        try:
            data_files = get_files_in_directory("data")
            st.write("파일 로드 성공!")
        except Exception as e:
            st.error(f"파일 로드 실패: {e}")

    # EC별 생육 비교
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("온도 변화", "습도 변화", "pH 변화", "EC 목표 vs 실측 EC")
    )

    # 예시 데이터
    fig.add_trace(go.Bar(x=["송도고", "하늘고", "아라고", "동산고"], y=[30, 25, 27, 22]), row=1, col=1)
    fig.add_trace(go.Bar(x=["송도고", "하늘고", "아라고", "동산고"], y=[60, 70, 65, 50]), row=1, col=2)
    fig.add_trace(go.Bar(x=["송도고", "하늘고", "아라고", "동산고"], y=[6, 6.5, 7, 7.2]), row=2, col=1)
    fig.add_trace(go.Bar(x=["송도고", "하늘고", "아라고", "동산고"], y=[1.0, 2.0, 4.0, 8.0]), row=2, col=2)
    
    fig.update_layout(title_text="학교별 환경 데이터 비교", font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
    st.plotly_chart(fig)

# Tab 3: 생육 결과
with tabs[2]:
    st.title("생육 결과")
    
    # EC별 평균 생중량
    st.metric(label="EC별 평균 생중량", value="0.35g")  # 예시 값

    # EC별 생육 비교
    fig2 = make_subplots(
        rows=2, cols=2,
        subplot_titles=("생중량", "잎 수", "지상부 길이", "개체수")
    )
    fig2.add_trace(go.Bar(x=["송도고", "하늘고", "아라고", "동산고"], y=[0.35, 0.40, 0.45, 0.30]), row=1, col=1)
    fig2.add_trace(go.Bar(x=["송도고", "하늘고", "아라고", "동산고"], y=[3, 4, 5, 2]), row=1, col=2)
    fig2.add_trace(go.Bar(x=["송도고", "하늘고", "아라고", "동산고"], y=[20, 22, 25, 18]), row=2, col=1)
    fig2.add_trace(go.Bar(x=["송도고", "하늘고", "아라고", "동산고"], y=[29, 45, 106, 58]), row=2, col=2)

    fig2.update_layout(title_text="EC별 생육 비교", font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
    st.plotly_chart(fig2)
    
    # 생육 데이터 다운로드
    with st.expander("원본 데이터 다운로드"):
        buffer = download_excel(pd.DataFrame({"개체번호": [1, 2, 3], "생중량": [0.35, 0.40, 0.45]}), "생육결과.xlsx")
        st.download_button(
            label="엑셀 파일 다운로드",
            data=buffer,
            file_name="생육결과.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
