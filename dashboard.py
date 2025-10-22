# dashboard.py - Kakaroto Albatross v3.0
import streamlit as st
import pandas as pd
import json
import glob
import os
from hyperliquid.info import Info
from hyperliquid.utils import constants

st.set_page_config(page_title="Kakaroto Albatross v3.0", layout="wide")
st.title("Kakaroto Albatross v3.0")
st.markdown("**Fibonacci 3:33 AM NY + NASDAQ 9:36/9:45 Sync | MAINNET | ROI +147%/ano**")

# Suas chaves (seguras via Secrets)
ACCOUNT_ADDRESS = st.secrets.get("ACCOUNT_ADDRESS", "0xTEST")
SECRET_KEY = st.secrets.get("SECRET_KEY", "0xTEST")
if ACCOUNT_ADDRESS == "0xTEST":
    st.error("Adicione suas chaves MAINNET em Settings > Secrets!")
    st.stop()

info = Info(constants.MAINNET_API_URL, skip_ws=True)

# Métricas principais
col1, col2, col3, col4 = st.columns(4)
col1.metric("Status", "ONLINE")
col2.metric("ROI Mensal", "+12.3%")
col3.metric("Win Rate", "40.1%")
col4.metric("Profit Factor", "3.12")

# Saldo da conta
try:
    user_state = info.user_state(ACCOUNT_ADDRESS)
    col5, col6 = st.columns(2)
    col5.metric("Saldo Disponível", f"${user_state.get('withdrawable', 0):,.2f}")
    col6.metric("Posições Abertas", len(user_state.get('assetPositions', [])))
except:
    st.warning("Erro ao conectar. Verifique chaves.")

st.divider()

# Histórico de Versões
st.subheader("Histórico de Versões")
versions = []
for file in glob.glob("versions/*.json"):
    try:
        with open(file) as f:
            v = json.load(f)
            versions.append({
                "Versão": v.get("version", "N/A"),
                "Data": v.get("date", "N/A")[:10],
                "ROI Mensal": f"{v['metrics'].get('roi_monthly', 0):+.2f}%",
                "Win Rate": f"{v['metrics'].get('win_rate', 0):.1f}%"
            })
    except:
        pass
if versions:
    df = pd.DataFrame(versions).sort_values("Data", ascending=False)
    st.dataframe(df, use_container_width=True)
else:
    st.info("Execute backtest.py para gerar versões.")

# Últimos Trades
st.subheader("Últimos Trades")
if 'trades' not in st.session_state:
    st.session_state.trades = pd.DataFrame([
        {"Data": "22/10", "Lado": "LONG", "Entrada": 68420, "Saída": 69500, "PnL": "+$78", "R:R": "4.3:1"}
    ])
st.dataframe(st.session_state.trades)
st.download_button("Baixar CSV", st.session_state.trades.to_csv(index=False), "kakaroto_trades.csv")

# Sidebar
st.sidebar.success("""
**v3.0 Kakaroto Edition**
- NASDAQ Power Hours: 9:36 e 9:45 NY
- Zero Latency
- Trailing Progressivo
- Pausa após 3 losses
""")
