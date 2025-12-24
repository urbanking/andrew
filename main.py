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
ec_df['색상'] = ['#FF6347', '#2E8B57', '#4682B4', '#FFD700']  # 색상 지정, 문자열 끝을 닫는 부분 추가
st.dataframe(ec_df)
