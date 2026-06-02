import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import os

st.set_page_config(page_title="축제 효과 분석 대시보드", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, '방문자분석.db')

@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df_fest = pd.read_sql("SELECT * FROM festival_visitors", conn)
    df_reg  = pd.read_sql("SELECT * FROM regional_visitors", conn)
    conn.close()

    pre_period = ['BEFORE_3M', 'BEFORE_2M', 'BEFORE_1M']
    pre_avg = (
        df_reg[df_reg['period'].isin(pre_period)]
        .groupby(['festival_name', 'festival_year'])['외지인방문자수']
        .mean()
        .reset_index()
    )
    pre_avg.rename(columns={'외지인방문자수': 'pre_avg_visitor'}, inplace=True)

    fest_curr = df_reg[df_reg['period'] == 'FESTIVAL'][
        ['festival_name', 'festival_year', '외지인방문자수']
    ]
    fest_curr = fest_curr.rename(columns={'외지인방문자수': 'curr_visitor'})

    after_6m = df_reg[df_reg['period'] == 'AFTER_6M'][
        ['festival_name', 'festival_year', '외지인방문자수']
    ]
    after_6m = after_6m.rename(columns={'외지인방문자수': 'after_6m_visitor'})

    m_df = pd.merge(pre_avg, fest_curr, on=['festival_name', 'festival_year'])
    m_df = pd.merge(m_df, after_6m, on=['festival_name', 'festival_year'])
    m_df = pd.merge(
        m_df,
        df_fest[['festival_name', 'festival_year', '외지인방문자수', '전체방문자수']],
        on=['festival_name', 'festival_year']
    )

    m_df['외지인_증감률']  = (m_df['curr_visitor'] - m_df['pre_avg_visitor']) / m_df['pre_avg_visitor'] * 100
    m_df['지속성_유지율']  = m_df['after_6m_visitor'] / m_df['pre_avg_visitor'] * 100
    m_df['종합점수']       = m_df['외지인_증감률'] * 0.5 + m_df['지속성_유지율'] * 0.5
    m_df['축제_외지인비율'] = m_df['외지인방문자수_y'] / m_df['전체방문자수'] * 100

    def classify_type(row):
        if row['외지인_증감률'] > 0 and row['축제_외지인비율'] > 50:
            return "🌍 지역 경제활성화형"
        elif row['외지인_증감률'] > 0:
            return "🔶 혼합형"
        else:
            return "🏘️ 동네 잔치형"

    def classify_grade(val):
        if val >= 120: return "🏆 강한 지속 효과"
        elif val >= 100: return "✅ 보통 지속 효과"
        elif val >= 80:  return "🔶 약한 회귀"
        else:            return "❌ 강한 회귀"

    m_df['축제유형']   = m_df.apply(classify_type, axis=1)
    m_df['지속성등급'] = m_df['지속성_유지율'].apply(classify_grade)

    return m_df, df_reg

df, df_reg_raw = load_data()

menu = st.sidebar.radio(
    "🔍 메뉴 선택",
    ["전체 개요", "효과성 분석", "지속성 분석", "종합 순위", "축제별 상세 분석"]
)

# ① 전체 개요
if menu == "전체 개요":
    st.title("📊 지역 축제 성과 요약")
    col1, col2, col3 = st.columns(3)
    col1.metric("분석 축제 수", f"{len(df)}개")
    col2.metric("🌍 경제활성화형", f"{len(df[df['축제유형'] == '🌍 지역 경제활성화형'])}개")
    col3.metric(
        "지속효과 보유",
        f"{len(df[df['지속성_유지율'] >= 100])}개",
        delta=f"{len(df[df['지속성_유지율'] >= 100]) / len(df) * 100:.1f}%"
    )

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("축제 유형 분포")
        fig = px.pie(
            df, names='축제유형', hole=0.4,
            color_discrete_sequence=['#10B981', '#3B82F6', '#EF4444'],
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("지속성 등급 분포")
        fig = px.bar(
            df['지속성등급'].value_counts().reset_index(),
            x='지속성등급', y='count', color='지속성등급',
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.info("💡 **인사이트:** 전체 축제 중 경제 활성화 효과를 거둔 비중과 지속성 등급 분포를 확인하세요.")

# ② 효과성 분석
elif menu == "효과성 분석":
    st.title("🚀 축제 유입 효과성 분석")
    year = st.selectbox("연도 선택", ["전체"] + sorted(df['festival_year'].unique().tolist()))
    plot_df = df if year == "전체" else df[df['festival_year'] == year]

    st.subheader(f"외지인 증감률 TOP 10 ({year})")
    top10 = plot_df.nlargest(10, '외지인_증감률').sort_values('외지인_증감률')
    fig = px.bar(
        top10, x='외지인_증감률', y='festival_name', orientation='h',
        color='외지인_증감률', color_continuous_scale=['#EF4444', '#10B981'],
        template="plotly_dark"
    )
    st.plotly_chart(fig, use_container_width=True)
    st.code("logic: (축제당월_외지인 - 축제전_평균) / 축제전_평균 * 100")

    col1, col2 = st.columns(2)
    col1.success("✅ 유입 효과 있음 (증감률 > 0)")
    col1.dataframe(
        plot_df[plot_df['외지인_증감률'] > 0][['festival_name', '외지인_증감률']],
        use_container_width=True
    )
    col2.error("❌ 유입 효과 없음 (증감률 ≤ 0)")
    col2.dataframe(
        plot_df[plot_df['외지인_증감률'] <= 0][['festival_name', '외지인_증감률']],
        use_container_width=True
    )

# ③ 지속성 분석
elif menu == "지속성 분석":
    st.title("⏳ 지역 방문 지속성 분석")
    year = st.selectbox("연도 선택", ["전체"] + sorted(df['festival_year'].unique().tolist()))
    plot_df = df if year == "전체" else df[df['festival_year'] == year]

    st.subheader(f"지속성 유지율 TOP 10 ({year})")
    top10 = plot_df.nlargest(10, '지속성_유지율').sort_values('지속성_유지율')
    fig = px.bar(
        top10, x='지속성_유지율', y='festival_name', orientation='h',
        color_discrete_sequence=['#3B82F6'], template="plotly_dark"
    )
    st.plotly_chart(fig, use_container_width=True)
    st.code("logic: AFTER_6M_외지인 / 축제전_평균 * 100")

    cols = st.columns(4)
    for i, g in enumerate(["🏆 강한 지속 효과", "✅ 보통 지속 효과", "🔶 약한 회귀", "❌ 강한 회귀"]):
        cols[i].write(f"**{g}**")
        cols[i].dataframe(
            plot_df[plot_df['지속성등급'] == g][['festival_name']],
            hide_index=True
        )

# ④ 종합 순위
elif menu == "종합 순위":
    st.title("🏆 종합 성과 랭킹")

    st.subheader("종합 점수 상위/하위 5")
    rank_df = df.sort_values('종합점수', ascending=False)[
        ['festival_name', 'festival_year', '외지인_증감률', '지속성_유지율', '종합점수']
    ]
    st.write("🔝 **TOP 5**")
    st.dataframe(rank_df.head(5).style.background_gradient(cmap='Blues'), use_container_width=True)
    st.write("🔻 **Bottom 5**")
    st.dataframe(rank_df.tail(5).style.background_gradient(cmap='Reds'), use_container_width=True)

    st.subheader("효과성 vs 지속성 분석")
    fig = px.scatter(
        df, x='외지인_증감률', y='지속성_유지율',
        color='축제유형', size='종합점수',
        hover_name='festival_name', template="plotly_dark",
        color_discrete_map={
            "🌍 지역 경제활성화형": "#10B981",
            "🔶 혼합형": "#F59E0B",
            "🏘️ 동네 잔치형": "#EF4444"
        }
    )
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 우상단에 위치할수록 단기 유입과 장기 유지가 모두 뛰어난 '모범 사례' 축제입니다.")

# ⑤ 축제별 상세 분석
elif menu == "축제별 상세 분석":
    target_fest = st.sidebar.selectbox("축제 선택", sorted(df['festival_name'].unique()))
    st.title(f"🔍 {target_fest} 심층 분석")

    f_df = df[df['festival_name'] == target_fest].sort_values('festival_year')

    cols = st.columns(len(f_df))
    for i, row in enumerate(f_df.itertuples()):
        with cols[i]:
            st.metric(f"{row.festival_year}년 종합점수", f"{row.종합점수:.1f}점")
            st.caption(f"분류: {row.축제유형}")

    st.subheader("축제 전/후 외지인 방문객 흐름")
    order = ['BEFORE_3M', 'BEFORE_2M', 'BEFORE_1M', 'FESTIVAL',
             'AFTER_1M', 'AFTER_2M', 'AFTER_3M', 'AFTER_6M']
    flow_df = df_reg_raw[df_reg_raw['festival_name'] == target_fest].copy()
    flow_df['period'] = pd.Categorical(flow_df['period'], categories=order, ordered=True)

    fig = px.line(
        flow_df.sort_values('period'),
        x='period', y='외지인방문자수', color='festival_year',
        markers=True, template="plotly_dark",
        title="시기별 방문자수 변화"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("연도별 지표 변화 요약")
    st.table(f_df[['festival_year', '외지인_증감률', '지속성_유지율', '축제_외지인비율', '지속성등급']])

