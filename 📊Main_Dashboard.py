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
def load_transfer_fees(start_date, end_date, timeframe):
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
            DATE_TRUNC('{timeframe}', created_at) AS "date",
            (source_chain || '➡' || destination_chain) AS "path",
            ROUND(SUM(fee)) AS "transfer_fees",
            ROUND(AVG(fee), 3) AS "avg_fees"
        FROM tab1
        WHERE destination_chain <> 'Moonbeam'
        GROUP BY 1, 2
        ORDER BY 1
    """
    return pd.read_sql(query, conn)


# --- Load Data ----------------------------------------------------------------------------------------
transfer_metrics = load_transfer_metrics(start_date, end_date)
transfer_metrics.index = transfer_metrics.index.str.lower()
df_timeseries = load_transfer_timeseries(start_date, end_date, timeframe)
df_fees = load_transfer_fees(start_date, end_date, timeframe)
df_total_fees = df_fees.groupby("date").agg({"transfer_fees": "sum"}).reset_index()

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
    yaxis_title="Txns Count"
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
    yaxis_title="$USD"
)

fig3 = px.bar(
    df_timeseries,
    x="date",
    y="senders_count",
    color="path",
    title="Number of $ATH Senders Over Time",
    color_discrete_sequence=["#cd00fc", "#d9fd51"],
    labels={"senders_count": "Number of Senders"}
)
fig3.update_layout(barmode="stack")
    xaxis_title="Date",
    yaxis_title="Address count"

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
    labels={"share": "Share of Volume"}
)
fig4.update_layout(barmode="stack", yaxis_tickformat=".0%")
    xaxis_title="Date",
    yaxis_title="% of Volume"

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
custom_colors = {
    "arbitrum➡ethereum": "#cd00fc",
    "ethereum➡arbitrum": "#d9fd51"
}
fig_fee_bar = go.Figure()

# بارها به تفکیک مسیر
for path in df_fees["path"].unique():
    df_path = df_fees[df_fees["path"] == path]
    fig_fee_bar.add_trace(go.Bar(
        x=df_path["date"],
        y=df_path["transfer_fees"],
        name=path,
        marker_color=custom_colors.get(path.lower(), None)
    ))

# خط مجموع کل کارمزدها
fig_fee_bar.add_trace(go.Scatter(
    x=df_total_fees["date"],
    y=df_total_fees["transfer_fees"],
    mode="lines+markers",
    name="Total Transfer Fees",
    line=dict(color="black", width=3)
))

fig_fee_bar.update_layout(
    barmode="stack",
    title="💸 Total Transfer Fees By Path Over Time",
    xaxis_title="Date",
    yaxis_title="$USD",
)
fig_fee_avg = go.Figure()

for path in df_fees["path"].unique():
    df_path = df_fees[df_fees["path"] == path]
    fig_fee_avg.add_trace(go.Scatter(
        x=df_path["date"],
        y=df_path["avg_fees"],
        mode="lines+markers",
        name=path,
        line=dict(color=custom_colors.get(path.lower(), None), width=3)
    ))

fig_fee_avg.update_layout(
    title="Average Transfer Fees By Path Over Time",
    xaxis_title="Date",
    yaxis_title="$USD"
)

col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(fig_fee_bar, use_container_width=True)

with col2:
    st.plotly_chart(fig_fee_avg, use_container_width=True)

