import streamlit as st
import pandas as pd
import plotly.express as px
import ast

# ===== 데이터 불러오기 =====

def load_data():
    assess_value = pd.read_excel("assess_value.xlsx")
    fire = pd.read_excel("fire.xlsx")
    singleFire = pd.read_excel("singleFire.xlsx")

    # 날짜 처리
    singleFire["Started"] = pd.to_datetime(singleFire["Started"], errors="coerce")
    singleFire["year"] = singleFire["Started"].dt.year
    singleFire["month"] = singleFire["Started"].dt.month

    # County list 변환
    singleFire["Counties"] = singleFire["Counties"].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else []
    )

    # 카운티별 평균 NetTotal
    avg_netTotal = assess_value.groupby("County")["NetTotal"].mean().reset_index()

    # 화재별 평균 재산 가치
    def merge_county(counties):
        values = []
        for county in counties:
            match = avg_netTotal.loc[avg_netTotal["County"] == county, "NetTotal"]
            if not match.empty:
                values.append(match.iloc[0])
        return sum(values)/len(values) if values else None

    singleFire["NetAverage"] = singleFire["Counties"].apply(merge_county)

    # Property Loss Score
    singleFire["StructuresDestroyed"] = singleFire["StructuresDestroyed"].fillna(0)
    singleFire["StructuresDamaged"] = singleFire["StructuresDamaged"].fillna(0)
    singleFire["PropertyLossScore"] = (
        singleFire["StructuresDestroyed"] + singleFire["StructuresDamaged"]
    )
    return singleFire

df = load_data()

# ===== Sidebar =====
st.sidebar.header("Filter Options")
year_filter = st.sidebar.multiselect("Select Year", sorted(df["year"].dropna().unique()))
county_filter = st.sidebar.multiselect("Select County", sorted(set(sum(df["Counties"], []))))

filtered = df.copy()
if year_filter:
    filtered = filtered[filtered["year"].isin(year_filter)]
if county_filter:
    filtered = filtered[filtered["Counties"].apply(lambda x: any(c in x for c in county_filter))]

# ===== KPI =====
st.title("🔥 California Wildfire Dashboard")

col1, col2, col3 = st.columns(3)
col1.metric("Total Fires", len(filtered))
col2.metric("Total Acres Burned", f"{filtered['AcresBurned'].sum():,.0f}")
col3.metric("Total Structures Destroyed", int(filtered["StructuresDestroyed"].sum()))

# ===== Annual Trend =====
st.subheader("Annual Trend")
annual = filtered.groupby("year").agg(
    Fires=("Name", "count"),
    AcresBurned=("AcresBurned", "sum"),
    PropertyLoss=("PropertyLossScore", "sum")
).reset_index()

fig1 = px.line(annual, x="year", y=["Fires","AcresBurned"],
               markers=True, labels={"value":"Count / Acres"})
st.plotly_chart(fig1, use_container_width=True)

# ===== Seasonality =====
st.subheader("Seasonality (Monthly Fires)")
monthly = filtered.groupby("month").size().reset_index(name="count")
fig2 = px.bar(monthly, x="month", y="count", labels={"month":"Month","count":"Fire Count"})
st.plotly_chart(fig2, use_container_width=True)

# ===== Map =====
st.subheader("Fire Map")
if "Latitude" in filtered.columns and "Longitude" in filtered.columns:
    fig_map = px.scatter_mapbox(filtered, lat="Latitude", lon="Longitude",
                                size="AcresBurned", color="PropertyLossScore",
                                hover_name="Name", mapbox_style="carto-positron", zoom=4)
    st.plotly_chart(fig_map, use_container_width=True)

# ===== Top 5 Fires =====
st.subheader("Top 5 Fires by Property Loss")
top5 = filtered.nlargest(5, "PropertyLossScore")[["Name","year","AcresBurned","PropertyLossScore","NetAverage"]]
st.dataframe(top5)
