import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import ast
from datetime import datetime
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# ===== call data and preprocessing =====

def date_convert(x):
    if pd.isna(x) or x =="":
        return np.nan
    else:
        return datetime.fromtimestamp(x)
    
def ready_data():
    assess_value = pd.read_excel("assess_value.xlsx")
    fire = pd.read_excel("fire.xlsx")
    singleFire = pd.read_excel("singleFire.xlsx")

    to_date2 = ['Updated', 'Started', 'ExtinguishedDate', 'ExtinguishedDateOnly', 'StartedDateOnly', 'ExpectedContainment']

    for col in to_date2:
        singleFire[col] = singleFire[col].apply(lambda x: int(x[6:-2])//1000)
        singleFire[col] = singleFire[col].replace(singleFire[singleFire[col] < 0][col].unique(), np.nan)
        singleFire[col] = singleFire[col].apply(date_convert)
    singleFire['Name'] = singleFire['Name'].apply(lambda x: x.strip())

    # miliseconds to datetime
    singleFire["Started"] = pd.to_datetime(singleFire["Started"], errors="coerce")
    singleFire["year"] = singleFire["Started"].dt.year
    singleFire["month"] = singleFire["Started"].dt.month

    # Counties preprocessing (str to list)
    singleFire["Counties"] = singleFire["Counties"].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else [])

    # average NetTotal per county
    avg_netTotal = assess_value.groupby("County")["NetTotal"].mean().reset_index()

    # 화재별 평균 재산 가치
    def merge_county(counties):
        value = 0
        if len(counties) != 0:
            for county in counties:
                # when NetTotal county is not in singleFire
                try:
                    netTotal = avg_netTotal[avg_netTotal['County'] == county]['NetTotal'].item()
                    value += netTotal
                except:
                    pass
            value /= len(counties)
            return value if value else np.nan

    singleFire["NetAverage"] = singleFire["Counties"].apply(merge_county)

    # propertyLoss
    singleFire["StructuresDestroyed"] = singleFire["StructuresDestroyed"].fillna(0)
    singleFire["StructuresDamaged"] = singleFire["StructuresDamaged"].fillna(0)
    singleFire["PropertyLoss"] = (singleFire["StructuresDestroyed"] + singleFire["StructuresDamaged"]) * singleFire['NetAverage']
    return singleFire

df = ready_data()
filtered = df.__deepcopy__()

# ===== Sidebar =====
st.sidebar.header("Filter Options")
year_filter = st.sidebar.multiselect("Select Year", sorted(filtered["year"].dropna().unique()))
county_filter = st.sidebar.multiselect("Select County", sorted(set(sum(filtered["Counties"], []))))

if year_filter:
    filtered = filtered[filtered["year"].isin(year_filter)]
if county_filter:
    filtered = filtered[filtered["Counties"].apply(lambda x: any(c in x for c in county_filter))]

# ===== KPI =====
st.title("CA fire Dashboard")

col1, col2, col3 = st.columns(3)
col1.metric("Total Fires", filtered.shape[0])
col2.metric("Total Acres Burned", f"{round(filtered['AcresBurned'].sum())}")
col3.metric("Total Structures Destroyed", int(filtered["StructuresDestroyed"].sum()))

# ===== Annual Trend =====
st.subheader("Annual Trend")
annual = filtered.groupby("year").agg(
    Fires=("Name", "count"),
    AcresBurned=("AcresBurned", "sum"),
    PropertyLoss=("PropertyLoss", "sum")
).reset_index()

# fig1 = px.line(annual, x="year", y=["Fires","AcresBurned"],
#                markers=True, labels={"value":"Count / Acres"})
# st.plotly_chart(fig1, use_container_width=True)
fig1 = px.line(annual, x="year", y="AcresBurned", markers=True, labels={"AcresBurned":"Acres"})
fig1.update_traces(name="Acres Burned", line=dict(color="blue"))

fig2 = px.line(annual, x="year", y="Fires", markers=True, labels={"Fires":"Count"})
fig2.update_traces(name="Fires", line=dict(color="red"), yaxis="y2")

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(x=annual["year"], y=annual["AcresBurned"],
                         mode="lines+markers", name="AcresBurned"), secondary_y=False)
fig.add_trace(go.Scatter(x=annual["year"], y=annual["Fires"],
                         mode="lines+markers", name="Fires"), secondary_y=True)

fig.update_layout(title="Annual Fires vs Acres Burned",
                  xaxis_title="Year")
fig.update_yaxes(title_text="Acres Burned", secondary_y=False)
fig.update_yaxes(title_text="Number of Fires", secondary_y=True)

st.plotly_chart(fig, use_container_width=True)

# ===== Seasonality =====
st.subheader("Seasonality (Monthly Fires)")
monthly = filtered.groupby("month").size().reset_index(name="count")
fig2 = px.bar(monthly, x="month", y="count", labels={"month":"Month","count":"Fire Count"})
st.plotly_chart(fig2, use_container_width=True)

# ===== Map =====
st.subheader("Interactive map")
fig = px.scatter_map(filtered, lat="Latitude", lon="Longitude", hover_name="Name", hover_data=["Started", "Updated", "AcresBurned", "County", "Location"],
                     color_discrete_sequence=["fuchsia"], zoom=3, height=300)
fig.update_layout(map_style="open-street-map")
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

st.subheader("Fire Map")
if "Latitude" in filtered.columns and "Longitude" in filtered.columns:
    fig_map = px.scatter_mapbox(filtered, lat="Latitude", lon="Longitude",
                                size="AcresBurned", color="PropertyLoss",
                                hover_name="Name", mapbox_style="carto-positron", zoom=4)
    st.plotly_chart(fig_map, use_container_width=True)

# # ===== Top 5 Fires =====
# st.subheader("Top 5 Fires by Property Loss")
# top5 = filtered.nlargest(5, "PropertyLoss")[["Name","year","AcresBurned","PropertyLoss","NetAverage"]]
# st.dataframe(top5)
