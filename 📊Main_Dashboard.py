import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.express as px
import plotly.graph_objects as go

# --- Page Config: Tab Title & Icon -------------------------------------------------------------------------------------
st.set_page_config(
    page_title="ATH Interchain Transfers Using Axelar ITS",
    page_icon="https://pbs.twimg.com/profile_images/1869486848646537216/rs71wCQo_400x400.jpg",
    layout="wide"
)

# --- Title with Logo ---------------------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="display: flex; align-items: center; gap: 15px;">
        <img src="https://img.cryptorank.io/coins/aethir1731483767528.png" alt="Aethir Logo" style="width:60px; height:60px;">
        <h1 style="margin: 0;">ATH Interchain Transfers Using Axelar ITS</h1>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Builder Info ---------------------------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="margin-top: 20px; margin-bottom: 20px; font-size: 16px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://pbs.twimg.com/profile_images/1841479747332608000/bindDGZQ_400x400.jpg" style="width:25px; height:25px; border-radius: 50%;">
            <span>Built by: <a href="https://x.com/0xeman_raz" target="_blank">Eman Raz</a></span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Info Box --------------------------------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="background-color: #d9fd51; padding: 10px; border-radius: 1px; border: 1px solid #000000;">
        Aethir and Axelar have partnered to enhance the interoperability of Aethir's ATH token across multiple blockchains. 
        Aethir, a decentralized cloud infrastructure provider focused on gaming and AI, has integrated Axelar as its official 
        blockchain bridge platform to enable seamless cross-chain bridging of the ATH token between Ethereum mainnet and Arbitrum Layer-2 blockchain. 
        Axelar’s Interchain Token Service (ITS) supports this by allowing Aethir to deploy ERC-20 tokens across over many blockchains while maintaining 
        native token functionality. This partnership facilitates frictionless ATH token transfers for Aethir’s ecosystem, particularly for Checker Node 
        and Aethir Edge rewards (Arbitrum-based) and staking or exchange activities (Ethereum-based). 
        Axelar’s decentralized network, APIs, and development tools provide scalability and flexibility, enabling Aethir to potentially expand ATH to 
        additional blockchains. 
    </div>
    """,
    unsafe_allow_html=True
)

st.info(
    "📊Charts initially display data for a default time range. Select a custom range to view results for your desired period."

)

st.info(
    "⏳On-chain data retrieval may take a few moments. Please wait while the results load."
)

# --- Snowflake Connection --------------------------------------------------------------------------------------------------
conn = snowflake.connector.connect(
    user=st.secrets["snowflake"]["user"],
    password=st.secrets["snowflake"]["password"],
    account=st.secrets["snowflake"]["account"],
    warehouse="SNOWFLAKE_LEARNING_WH",
    database="AXELAR",
    schema="PUBLIC"
)

# --- Time Frame & Period Selection ---
timeframe = st.selectbox("Select Time Frame", ["month", "week", "day"])
start_date = st.date_input("Start Date", value=pd.to_datetime("2024-06-10"))
end_date = st.date_input("End Date", value=pd.to_datetime("2025-07-31"))

# --- Query Functions ---------------------------------------------------------------------------------------
# --- Row 1: Total Amounts Staked, Unstaked, and Net Staked ---

@st.cache_data
def load_transfer_metrics(start_date, end_date):
    query = f"""
        WITH tab1 AS (
            SELECT
                created_at,
                id AS tx_id,
                data:call.transaction.from::STRING AS sender_address,
                data:call.returnValues.destinationContractAddress::STRING AS receiver_address,
                data:amount::FLOAT AS amount,
                CASE
                    WHEN created_at::date BETWEEN '{start_date}' AND '2024-06-12' THEN (data:amount::FLOAT) * 0.084486
                    ELSE (TRY_CAST(data:value::float AS FLOAT))
                END AS amount_usd,
                data:symbol::STRING AS token_symbol,
                data:call.chain::STRING AS source_chain,
                data:call.returnValues.destinationChain::STRING AS destination_chain
            FROM axelar.axelscan.fact_gmp 
            WHERE data:symbol::STRING = 'ATH'
              AND created_at::date BETWEEN '{start_date}' AND '{end_date}'
        )
        SELECT 
            ROUND(SUM(amount)) AS transfers_volume_ath,
            ROUND(SUM(amount_usd)) AS transfers_volume_usd,
            COUNT(DISTINCT tx_id) AS transfers_count,
            COUNT(DISTINCT sender_address) AS senders_count
        FROM tab1
    """
    return pd.read_sql(query, conn).iloc[0]

# -- Row 2, 3 -----------------------------
@st.cache_data
def load_transfer_timeseries(start_date, end_date, timeframe):
    query = f"""
        WITH tab1 AS (
            SELECT
                created_at,
                id AS tx_id,
                data:call.transaction.from::STRING AS sender_address,
                data:call.returnValues.destinationContractAddress::STRING AS receiver_address,
                data:amount::FLOAT AS amount,
                CASE
                    WHEN created_at::date BETWEEN '2024-06-10' AND '2024-06-12' THEN (data:amount::FLOAT) * 0.084486
                    ELSE (TRY_CAST(data:value::float AS FLOAT))
                END AS amount_usd,
                data:symbol::STRING AS token_symbol,
                data:call.chain::STRING AS source_chain,
                data:call.returnValues.destinationChain::STRING AS destination_chain
            FROM axelar.axelscan.fact_gmp 
            WHERE data:symbol::STRING = 'ATH'
              AND created_at::date BETWEEN '{start_date}' AND '{end_date}'
        )
        SELECT 
            DATE_TRUNC('{timeframe}', created_at) AS "date",
            (source_chain || '➡' || destination_chain) AS "path",
            ROUND(SUM(amount)) AS "transfers_volume_ath",
            ROUND(SUM(amount_usd)) AS "transfers_volume_usd",
            COUNT(DISTINCT tx_id) AS "transfers_count",
            COUNT(DISTINCT sender_address) AS "senders_count"
        FROM tab1
        WHERE destination_chain <> 'Moonbeam'
        GROUP BY 1, 2
        ORDER BY 1
    """
    return pd.read_sql(query, conn)

# -- Row 4 ---------------------------

@st.cache_data
def load_path_summary(start_date, end_date):
    query = f"""
        WITH tab1 AS (
            SELECT
                created_at,
                id AS tx_id,
                data:call.transaction.from::STRING AS sender_address,
                data:call.returnValues.destinationContractAddress::STRING AS receiver_address,
                data:amount::FLOAT AS amount,
                CASE
                    WHEN created_at::date BETWEEN '2024-06-10' AND '2024-06-12' THEN (data:amount::FLOAT) * 0.084486
                    ELSE TRY_CAST(data:value::float AS FLOAT)
                END AS amount_usd,
                (data:gas:gas_used_amount)*(data:gas_price_rate:source_token.token_price.usd) AS fee,
                data:symbol::STRING AS token_symbol,
                data:call.chain::STRING AS source_chain,
                data:call.returnValues.destinationChain::STRING AS destination_chain
            FROM axelar.axelscan.fact_gmp 
            WHERE data:symbol::STRING = 'ATH'
              AND created_at::date BETWEEN '{start_date}' AND '{end_date}'
        )
        SELECT 
            (source_chain || '➡' || destination_chain) AS "path",
            ROUND(SUM(amount)) AS "transfers_volume_ath",
            ROUND(SUM(amount_usd)) AS "transfers_volume_usd",
            COUNT(DISTINCT tx_id) AS "transfers_count"
        FROM tab1
        WHERE destination_chain <> 'Moonbeam'
        GROUP BY 1
    """
    return pd.read_sql(query, conn)

# -- Row 5 -----------------------------------------------------
@st.cache_data
def load_transfer_volume_distribution(start_date, end_date, timeframe):
    query = f"""
        WITH tab1 AS (
            SELECT
                created_at AS date,
                id,
                CASE
                    WHEN sum(data:amount::FLOAT) <= 100 THEN 'V<=100 ATH'
                    WHEN sum(data:amount::FLOAT) > 100 AND sum(data:amount::FLOAT) <= 1000 THEN '100<V<=1k ATH'
                    WHEN sum(data:amount::FLOAT) > 1000 AND sum(data:amount::FLOAT) <= 10000 THEN '1k<V<=10k ATH'
                    WHEN sum(data:amount::FLOAT) > 10000 AND sum(data:amount::FLOAT) <= 20000 THEN '10k<V<=20k ATH'
                    WHEN sum(data:amount::FLOAT) > 20000 AND sum(data:amount::FLOAT) <= 50000 THEN '20k<V<=50k ATH'
                    WHEN sum(data:amount::FLOAT) > 50000 AND sum(data:amount::FLOAT) <= 100000 THEN '50k<V<=100k ATH'
                    WHEN sum(data:amount::FLOAT) > 100000 THEN 'V>100k ATH'
                END AS "Class"
            FROM axelar.axelscan.fact_gmp 
            WHERE data:symbol::STRING = 'ATH'
              AND created_at::date BETWEEN '{start_date}' AND '{end_date}'
            GROUP BY 1,2
        )
        SELECT date_trunc('{timeframe}', date) AS "Date", "Class", COUNT(DISTINCT id) AS "Transfers Count"
        FROM tab1
        GROUP BY 1,2
        ORDER BY 1
    """
    return pd.read_sql(query, conn)
# --------------------------------------------
@st.cache_data
def load_transfer_volume_distribution_total(start_date, end_date):
    query = f"""
        WITH tab1 AS (
            SELECT
                created_at AS date,
                id,
                CASE
                    WHEN sum(data:amount::FLOAT) <= 100 THEN 'V<=100 ATH'
                    WHEN sum(data:amount::FLOAT) > 100 AND sum(data:amount::FLOAT) <= 1000 THEN '100<V<=1k ATH'
                    WHEN sum(data:amount::FLOAT) > 1000 AND sum(data:amount::FLOAT) <= 10000 THEN '1k<V<=10k ATH'
                    WHEN sum(data:amount::FLOAT) > 10000 AND sum(data:amount::FLOAT) <= 20000 THEN '10k<V<=20k ATH'
                    WHEN sum(data:amount::FLOAT) > 20000 AND sum(data:amount::FLOAT) <= 50000 THEN '20k<V<=50k ATH'
                    WHEN sum(data:amount::FLOAT) > 50000 AND sum(data:amount::FLOAT) <= 100000 THEN '50k<V<=100k ATH'
                    WHEN sum(data:amount::FLOAT) > 100000 THEN 'V>100k ATH'
                END AS "Class"
            FROM axelar.axelscan.fact_gmp 
            WHERE data:symbol::STRING = 'ATH'
              AND created_at::date BETWEEN '{start_date}' AND '{end_date}'
            GROUP BY 1,2
        )
        SELECT "Class", COUNT(DISTINCT id) AS "Transfers Count"
        FROM tab1
        GROUP BY 1
    """
    return pd.read_sql(query, conn)

# -- Row 6 ----------------------------------------------
@st.cache_data
def load_transfer_table(start_date, end_date):
    query = f"""
        WITH tab1 AS (
            SELECT
                created_at,
                id AS tx_id,
                data:call.transaction.from::STRING AS sender_address,
                data:call.returnValues.destinationContractAddress::STRING AS receiver_address,
                data:amount::FLOAT AS amount,
                CASE
                    WHEN created_at::date BETWEEN '2024-06-10' AND '2024-06-12' THEN (data:amount::FLOAT) * 0.084486
                    ELSE (TRY_CAST(data:value::float AS FLOAT))
                END AS amount_usd,
                COALESCE(
                    ((data:gas:gas_used_amount) * (data:gas_price_rate:source_token.token_price.usd)),
                    TRY_CAST(data:fees:express_fee_usd::float AS FLOAT)
                ) AS fee,
                data:symbol::STRING AS token_symbol,
                data:call.chain::STRING AS source_chain,
                data:call.returnValues.destinationChain::STRING AS destination_chain
            FROM axelar.axelscan.fact_gmp
            WHERE data:symbol::STRING = 'ATH'
              AND created_at::date BETWEEN '{start_date}' AND '{end_date}'
        )
        SELECT 
            created_at AS "⏰Date", 
            ROUND(amount, 2) AS "💸Amount ATH", 
            ROUND(amount_usd, 2) AS "💰Amount USD", 
            source_chain AS "📤Source Chain", 
            destination_chain AS "📥Destination Chain", 
            sender_address AS "👥Sender", 
            ROUND(fee, 3) AS "⛽Fee USD", 
            tx_id AS "🔗TX ID"
        FROM tab1
        WHERE destination_chain <> 'Moonbeam'
        ORDER BY created_at DESC
        LIMIT 1000
    """
    return pd.read_sql(query, conn)

# -- Row 7 --------------------------
@st.cache_data
def load_weekly_breakdown(start_date, end_date):
    query = f"""
        SELECT 
            CASE 
                WHEN dayofweek(created_at) = 0 THEN '7 - Sunday'
                ELSE dayofweek(created_at) || ' - ' || dayname(created_at)
            END AS "Day Name",
            ROUND(SUM(data:amount::FLOAT)) AS "Transfers Volume ATH", 
            COUNT(DISTINCT id) AS "Transfers Count", 
            COUNT(DISTINCT data:call.transaction.from::STRING) AS "Users Count"
        FROM axelar.axelscan.fact_gmp
        WHERE data:symbol::STRING = 'ATH'
          AND created_at::date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY 1
        ORDER BY 1
    """
    return pd.read_sql(query, conn)

# --- Load Data ----------------------------------------------------------------------------------------
transfer_metrics = load_transfer_metrics(start_date, end_date)
transfer_metrics.index = transfer_metrics.index.str.lower()
df_timeseries = load_transfer_timeseries(start_date, end_date, timeframe)
df_path_summary = load_path_summary(start_date, end_date)
df_volume_distribution = load_transfer_volume_distribution(start_date, end_date, timeframe)
df_volume_distribution_total = load_transfer_volume_distribution_total(start_date, end_date)
transfer_table = load_transfer_table(start_date, end_date)
weekly_data = load_weekly_breakdown(start_date, end_date)
# ------------------------------------------------------------------------------------------------------

# --- Row 1: Metrics ---
st.markdown("## 🚀 ATH Token Transfer Overview")

k1, k2, k3, k4 = st.columns(4)

volume_b = transfer_metrics['transfers_volume_ath'] / 1_000_000_000  # تبدیل به بیلیارد
k1.metric("Volume of Transfers ($ATH)", f"{volume_b:.2f} B ATH")
# -- k1.metric("Volume of Transfers ($ATH)", f"{transfer_metrics['transfers_volume_ath']:,} ATH")
k2.metric("Volume of Transfers ($USD)", f"${int(transfer_metrics['transfers_volume_usd']):,}")
k3.metric("Number of Transfers", f"{int(transfer_metrics['transfers_count']):,}")
k4.metric("Number of Senders", f"{int(transfer_metrics['senders_count']):,}")

# --- Row 2,3 -------------------------------------------
st.markdown("### 📊 ATH Token Transfer Over Time")
df_agg = df_timeseries.groupby("date").agg({
    "transfers_count": "sum",
    "transfers_volume_usd": "sum"
}).reset_index()

custom_colors = {
    "arbitrum➡ethereum": "#cd00fc",
    "ethereum➡arbitrum": "#d9fd51"
}


fig1 = go.Figure()

for path in df_timeseries["path"].unique():
    data = df_timeseries[df_timeseries["path"] == path]
    fig1.add_trace(go.Bar(
        x=data["date"],
        y=data["transfers_count"],
        name=path,
        marker_color=custom_colors.get(path.lower(), None)
    ))

# اضافه کردن خط مجموع
fig1.add_trace(go.Scatter(
    x=df_agg["date"],
    y=df_agg["transfers_count"],
    mode="lines+markers",
    name="Total Transfers Count",
    line=dict(color="black", width=3)
))

fig1.update_layout(
    barmode="stack",
    title="Number of Interchain Transfers By Path Over Time",
    xaxis_title="Date",
    yaxis_title="Txns Count",
    legend=dict(
        orientation="h",       # افقی کردن لیجند
        yanchor="bottom",      # مرجع عمودی در پایین باشد
        y=1.02,                # کمی بالاتر از نمودار
        xanchor="center",      # مرجع افقی وسط باشد
        x=0.5                  # قرارگیری در وسط محور افقی
    )
)

fig2 = go.Figure()

for path in df_timeseries["path"].unique():
    data = df_timeseries[df_timeseries["path"] == path]
    fig2.add_trace(go.Bar(
        x=data["date"],
        y=data["transfers_volume_usd"],
        name=path,
        marker_color=custom_colors.get(path.lower(), None)
    ))

# اضافه کردن خط مجموع
fig2.add_trace(go.Scatter(
    x=df_agg["date"],
    y=df_agg["transfers_volume_usd"],
    mode="lines+markers",
    name="Total Transfers Volume",
    line=dict(color="black", width=3)
))

fig2.update_layout(
    barmode="stack",
    title="Volume of Interchain Transfers By Path Over Time",
    xaxis_title="Date",
    yaxis_title="$USD",
    legend=dict(
        orientation="h",       
        yanchor="bottom",      
        y=1.02,                
        xanchor="center",      
        x=0.5                  
    )
)

fig3 = px.bar(
    df_timeseries,
    x="date",
    y="senders_count",
    color="path",
    title="Number of $ATH Senders Over Time",
    color_discrete_sequence=["#cd00fc", "#d9fd51"],
    labels={
        "date": "Date",
        "senders_count": "Address count"
    }
)
fig3.update_layout(
    barmode="stack",
    legend=dict(
        title_text="",         # حذف عنوان لیجند
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="center",
        x=0.5
    )
)
        
df_norm = df_timeseries.copy()
df_norm["total"] = df_norm.groupby("date")["transfers_volume_ath"].transform("sum")
df_norm["share"] = df_norm["transfers_volume_ath"] / df_norm["total"]


fig4 = px.bar(
    df_norm,
    x="date",
    y="share",
    color="path",
    title="Share of Each Route from the Total Volume of Transfers",
    color_discrete_sequence=["#cd00fc", "#d9fd51"],
    labels={
        "date": "Date",
        "share": "% of Volume"
    }
)
fig4.update_layout(
    barmode="stack",
    yaxis_tickformat=".0%",
    legend=dict(
        title_text="",         # حذف عنوان لیجند (path)
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="center",
        x=0.5
    )
)

    
# ردیف اول: دو چارت نخست
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig1, use_container_width=True)
with col2:
    st.plotly_chart(fig2, use_container_width=True)

# ردیف دوم: دو چارت بعدی
col3, col4 = st.columns(2)
with col3:
    st.plotly_chart(fig3, use_container_width=True)
with col4:
    st.plotly_chart(fig4, use_container_width=True)

# -- Row 4 --------------------------------------------------

fig_donut1 = px.pie(
    df_path_summary,
    names="path",
    values="transfers_count",
    title="Total Number of Interchain Transfers By Path",
    hole=0.4,
    color="path",
    color_discrete_sequence=["#cd00fc", "#d9fd51"]
)

fig_donut2 = px.pie(
    df_path_summary,
    names="path",
    values="transfers_volume_ath",
    title="Total Volume of Interchain Transfers By Path ($ATH)",
    hole=0.4,
    color="path",
    color_discrete_sequence=["#cd00fc", "#d9fd51"]
)

fig_donut3 = px.pie(
    df_path_summary,
    names="path",
    values="transfers_volume_usd",
    title="Total Volume of Interchain Transfers By Path ($USD)",
    hole=0.4,
    color="path",
    color_discrete_sequence=["#cd00fc", "#d9fd51"]
)

col1, col2, col3 = st.columns(3)

with col1:
    st.plotly_chart(fig_donut1, use_container_width=True)

with col2:
    st.plotly_chart(fig_donut2, use_container_width=True)

with col3:
    st.plotly_chart(fig_donut3, use_container_width=True)

# --- Row 5 --------------------------------------------------------
color_scale = {
    'V<=100 ATH': '#d9fd51',        # lime-ish
    '100<V<=1k ATH': '#b1f85a',
    '1k<V<=10k ATH': '#8be361',
    '10k<V<=20k ATH': '#639d55',
    '20k<V<=50k ATH': '#4a7c42',
    '50k<V<=100k ATH': '#7a4c89',  # purple-ish
    'V>100k ATH': '#cd00fc'
}
fig_norm_stacked = px.bar(
    df_volume_distribution,
    x="Date",
    y="Transfers Count",
    color="Class",
    title="Distribution of Interchain Transfers Based on Volume Over Time",
    color_discrete_map=color_scale,
    text="Transfers Count",
)

fig_norm_stacked.update_layout(barmode='stack', uniformtext_minsize=8, uniformtext_mode='hide')
fig_norm_stacked.update_traces(textposition='inside')

# نرمالایز کردن محور y (100% stacked bar)
fig_norm_stacked.update_layout(yaxis=dict(tickformat='%'))
fig_norm_stacked.update_traces(hovertemplate='%{y} Transfers<br>%{x}<br>%{color}')

# نرمالایز کردن مقدارها
df_norm = df_volume_distribution.copy()
df_norm['total_per_date'] = df_norm.groupby('Date')['Transfers Count'].transform('sum')
df_norm['normalized'] = df_norm['Transfers Count'] / df_norm['total_per_date']

fig_norm_stacked = px.bar(
    df_norm,
    x='Date',
    y='normalized',
    color='Class',
    title="Distribution of Interchain Transfers Based on Volume Over Time",
    color_discrete_map=color_scale,
    text=df_norm['Transfers Count'].astype(str),
)

fig_norm_stacked.update_layout(barmode='stack')
fig_norm_stacked.update_traces(textposition='inside')
fig_norm_stacked.update_yaxes(tickformat='%')

fig_donut_volume = px.pie(
    df_volume_distribution_total,
    names="Class",
    values="Transfers Count",
    title="Distribution of Interchain Transfers Based on Volume",
    hole=0.5,
    color="Class",
    color_discrete_map=color_scale
)

fig_donut_volume.update_traces(textposition='outside', textinfo='percent+label', pull=[0.05]*len(df_volume_distribution_total))
fig_donut_volume.update_layout(showlegend=True, legend=dict(orientation="v", y=0.5, x=1.1))

col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(fig_norm_stacked, use_container_width=True)

with col2:
    st.plotly_chart(fig_donut_volume, use_container_width=True)

# -- Row 6 -----------------------------------------
# --- Add Row Number Starting From 1 ---
transfer_table.index = transfer_table.index + 1

# --- Section Header ---
st.markdown("### 🔎ATH Interchain Transfers Tracker (Recent Transactions Within the Default Time Frame)")

# --- Show Table ---
st.dataframe(transfer_table, use_container_width=True)

# --- Row 7 --------------------------------------------------------
# --- Chart 1: Bar chart for Transfers Volume ATH ---
bar_fig = px.bar(
    weekly_data,
    x="Day Name",
    y="Transfers Volume ATH",
    title="Volume of Interchain Transfers on Different Days of the Week",
    color_discrete_sequence=["#d9fd51"]
)
bar_fig.update_layout(
    xaxis_title=" ",
    yaxis_title="$ATH",
    bargap=0.2
)

# --- Chart 2: Clustered Bar Chart for Transfers Count & Users Count ---
clustered_fig = go.Figure()

clustered_fig.add_trace(go.Bar(
    x=weekly_data["Day Name"],
    y=weekly_data["Transfers Count"],
    name="Transfers Count",
    marker_color="#d9fd51"
))

clustered_fig.add_trace(go.Bar(
    x=weekly_data["Day Name"],
    y=weekly_data["Users Count"],
    name="Users Count",
    marker_color="#cd00fc"
))

clustered_fig.update_layout(
    barmode='group',
    title="Number of Interchain Transfers & Senders on Different Days of the Week",
    xaxis_title=" ",
    yaxis_title=" ",
    bargap=0.2,
    legend=dict(
        title_text="",         # حذف عنوان لیجند (path)
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="center",
        x=0.5
    )
)

# --- Display side by side ---
st.markdown("### 📅 ATH Interchain Transfer Pattern")
col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(bar_fig, use_container_width=True)

with col2:
    st.plotly_chart(clustered_fig, use_container_width=True)


# --- Links with Logos ---------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="font-size: 16px; background-color: #c3c3c3; color: #000; padding: 10px; border-radius: 5px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://axelarscan.io/logos/logo.png" alt="Axelar" style="width:20px; height:20px;">
            <a href="https://www.axelar.network/" target="_blank" style="color: #fff;">Axelar Website</a>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://axelarscan.io/logos/logo.png" alt="Axelar X" style="width:20px; height:20px;">
            <a href="https://x.com/axelar" target="_blank" style="color: #fff;">Axelar X Account</a>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://img.cryptorank.io/coins/aethir1731483767528.png" alt="Aethir" style="width:20px; height:20px;">
            <a href="https://aethir.com/" target="_blank" style="color: #fff;">Aethir Website</a>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://img.cryptorank.io/coins/aethir1731483767528.png" alt="Aethir X" style="width:20px; height:20px;">
            <a href="https://x.com/AethirCloud" target="_blank" style="color: #fff;">Aethir X Account</a>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
