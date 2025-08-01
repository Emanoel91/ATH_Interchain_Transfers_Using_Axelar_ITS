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


# --- Load Data ----------------------------------------------------------------------------------------
transfer_metrics = load_transfer_metrics(start_date, end_date)
transfer_metrics.index = transfer_metrics.index.str.lower()
# ------------------------------------------------------------------------------------------------------

# --- Row 1: Metrics ---
st.markdown("## 🚀 ATH Token Transfer Overview")

k1, k2, k3, k4 = st.columns(4)

volume_b = transfer_metrics['transfers_volume_ath'] / 1_000_000_000  # تبدیل به بیلیارد
k1.metric("Volume of Transfers ($ATH)", f"{volume_b:.2f} B ATH")
# -- k1.metric("Volume of Transfers ($ATH)", f"{transfer_metrics['transfers_volume_ath']:,} ATH")
k2.metric("Volume of Transfers ($USD)", f"${transfer_metrics['transfers_volume_usd']:,}")
k3.metric("Number of Transfers", f"{transfer_metrics['transfers_count']:,}")
k4.metric("Number of Senders", f"{transfer_metrics['senders_count']:,}")

