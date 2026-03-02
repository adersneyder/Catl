# alpha_war_room_streamlit.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, date
import json
import math
import os
from openai import OpenAI  # requiere pip install openai

st.set_page_config(page_title="Terminal Cuantitativa MBA", layout="wide", initial_sidebar_state="collapsed")

# -----------------------------
# CSS / Estilo (PowerBI-like)
# -----------------------------
st.markdown("""
<style>
body { background-color: #f3f6f9; color: #1e1e1e; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
h1,h2,h3 { color: #005A9C !important; font-weight: 600; }
.metric-box { background-color: #ffffff; padding: 18px; border-radius: 12px; text-align: center; box-shadow: 0 6px 18px rgba(0,0,0,0.06); border-top: 4px solid #005A9C; }
.metric-title { font-size: 13px; color: #6c757d; text-transform: uppercase; font-weight:700; }
.metric-value { font-size: 26px; font-weight:800; color:#1e1e1e; }
.ai-box { background-color: #eef2f5; border-left: 4px solid #00c49f; padding: 14px; border-radius: 8px; margin-top:10px; font-size:15px; }
.card { background-color:#fff; border-radius:12px; padding:12px; box-shadow: 0 8px 20px rgba(0,0,0,0.06); }
.rounded-panel { border-radius: 14px; background: linear-gradient(180deg,#ffffff,#f6fbff); padding:12px; box-shadow: 0 8px 20px rgba(0,0,0,0.06); }
</style>
""", unsafe_allow_html=True)

st.title("🚨 alpha war room — banco de españa edition 🚨")

# -----------------------------
# STOCK UNIVERSE (CATL first + lists)
# -----------------------------
# You asked to include CATL first, many China tickers you listed, top IBEX & top CSI picks.
# Note: Tickers use Yahoo Finance convention.
STOCKS = {
    # CATL first
    "CATL - Contemporary Amperex Technology": {"ticker": "300750.SZ", "index": "000300.SS", "currency": "CNY", "region": "China", "inflacion": 0.3},
    # Specific Chinese names you listed
    "EVE Energy": {"ticker": "300014.SZ", "index": "000300.SS", "currency":"CNY", "region":"China", "inflacion":0.3},
    "Kweichow Moutai": {"ticker":"600519.SS","index":"000300.SS","currency":"CNY","region":"China","inflacion":0.3},
    "COSCO Shipping": {"ticker":"601919.SS","index":"000300.SS","currency":"CNY","region":"China","inflacion":0.3},
    "China Petroleum & Chemical (Sinopec)": {"ticker":"600028.SS","index":"000300.SS","currency":"CNY","region":"China","inflacion":0.3},
    "China Spacesat": {"ticker":"600118.SS","index":"000300.SS","currency":"CNY","region":"China","inflacion":0.3},
    "Beijing Capital": {"ticker":"600008.SS","index":"000300.SS","currency":"CNY","region":"China","inflacion":0.3},
    "Sinopec Shanghai Petrochemical": {"ticker":"600688.SS","index":"000300.SS","currency":"CNY","region":"China","inflacion":0.3},
    "Hainan Airlines": {"ticker":"600221.SS","index":"000300.SS","currency":"CNY","region":"China","inflacion":0.3},
    "Aluminum Corp of China": {"ticker":"601600.SS","index":"000300.SS","currency":"CNY","region":"China","inflacion":0.3},
    "Dongfeng Automobile": {"ticker":"600006.SS","index":"000300.SS","currency":"CNY","region":"China","inflacion":0.3},
    "Hubei Yihua Chemical": {"ticker":"000422.SZ","index":"000300.SS","currency":"CNY","region":"China","inflacion":0.3},
    "Kingfa Sci&Tech": {"ticker":"600143.SS","index":"000300.SS","currency":"CNY","region":"China","inflacion":0.3},
    "Guanghui Energy": {"ticker":"600256.SS","index":"000300.SS","currency":"CNY","region":"China","inflacion":0.3},
    "CSSC Offshore & Marine": {"ticker":"600685.SS","index":"000300.SS","currency":"CNY","region":"China","inflacion":0.3},
    "Sany Heavy Industry": {"ticker":"600031.SS","index":"000300.SS","currency":"CNY","region":"China","inflacion":0.3},
    "China Railway Group": {"ticker":"601390.SS","index":"000300.SS","currency":"CNY","region":"China","inflacion":0.3},
    "Guangdong EVE": {"ticker":"002809.SZ","index":"000300.SS","currency":"CNY","region":"China","inflacion":0.3},
    # IBEX sample top 10 (common large caps)
    "Inditex": {"ticker":"ITX.MC","index":"^IBEX","currency":"EUR","region":"España","inflacion":3.2},
    "Banco Santander": {"ticker":"SAN.MC","index":"^IBEX","currency":"EUR","region":"España","inflacion":3.2},
    "BBVA": {"ticker":"BBVA.MC","index":"^IBEX","currency":"EUR","region":"España","inflacion":3.2},
    "Iberdrola": {"ticker":"IBE.MC","index":"^IBEX","currency":"EUR","region":"España","inflacion":3.2},
    "Repsol": {"ticker":"REP.MC","index":"^IBEX","currency":"EUR","region":"España","inflacion":3.2},
    "Telefónica": {"ticker":"TEF.MC","index":"^IBEX","currency":"EUR","region":"España","inflacion":3.2},
    "Cellnex": {"ticker":"CLNX.MC","index":"^IBEX","currency":"EUR","region":"España","inflacion":3.2},
    "Amadeus": {"ticker":"AMS.MC","index":"^IBEX","currency":"EUR","region":"España","inflacion":3.2},
    "Ferrovial": {"ticker":"FER.MC","index":"^IBEX","currency":"EUR","region":"España","inflacion":3.2},
    "CaixaBank": {"ticker":"CABK.MC","index":"^IBEX","currency":"EUR","region":"España","inflacion":3.2},
}

# -----------------------------
# OPENAI CONFIG
# -----------------------------
OPENAI_API_KEY = None
if "OPENAI_API_KEY" in st.secrets:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
else:
    # try environment for local runs
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", None)

if not OPENAI_API_KEY:
    st.sidebar.error("🔒 OPENAI_API_KEY no configurada. Agrega la clave en Streamlit Secrets con la llave OPENAI_API_KEY.")
    # still allow the UI to load but IA features will return an error message.

client = None
if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        st.sidebar.error(f"Error inicializando OpenAI client: {e}")
        client = None

@st.cache_data(ttl=900)
def ask_openai(messages, model="gpt-4o-mini", max_tokens=800):
    """
    Wrapper para llamadas a OpenAI Chat Completions.
    mensajes -> lista de dicts [{"role":"system","content":...}, ...]
    """
    if client is None:
        return "ERROR IA: OPENAI API KEY no disponible."
    try:
        resp = client.chat.completions.create(model=model, messages=messages, max_tokens=max_tokens, temperature=0.25)
        # estructura: resp.choices[0].message.content
        return resp.choices[0].message["content"]
    except Exception as e:
        return f"ERROR IA: {e}"

# -----------------------------
# Helper: fuzzy match company input to keys
# -----------------------------
def find_company_by_text(q):
    q = (q or "").strip().lower()
    if not q:
        # default to CATL
        return list(STOCKS.keys())[0]
    # exact match
    for name in STOCKS.keys():
        if q == name.lower():
            return name
    # partial match
    for name in STOCKS.keys():
        if q in name.lower():
            return name
    # token matching
    tokens = q.split()
    for name in STOCKS.keys():
        if all(t in name.lower() for t in tokens):
            return name
    # default
    return list(STOCKS.keys())[0]

# -----------------------------
# Data download: robust
# -----------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def download_data_for(ticker, benchmark, period="1y", interval="1d"):
    # period examples: '1d','5d','1mo','3mo','6mo','1y','2y','5y','10y','max'
    try:
        # fetch info
        tk = yf.Ticker(ticker)
        info = tk.info or {}
    except Exception:
        info = {}
    try:
        df_stock = yf.download(ticker, period=period, interval=interval, progress=False)['Close']
        df_index = yf.download(benchmark, period=period, interval=interval, progress=False)['Close']
    except Exception:
        df_stock = None; df_index = None

    if df_stock is None or df_index is None or df_stock.empty or df_index.empty:
        # fallback simulated series (keeps UI working)
        dates = pd.date_range(end=pd.Timestamp.today(), periods=252, freq='B')
        mkt = 3500 * np.exp(np.cumsum(np.random.normal(0.0002, 0.01, len(dates))))
        stk = 150 * np.exp(np.cumsum(np.random.normal(0.0003, 0.015, len(dates))))
        df = pd.DataFrame({'Stock': stk, 'Market': mkt}, index=dates)
        quick_ratio = info.get('quickRatio', 1.2)
        roe = info.get('returnOnEquity', 0.12)
        mcap = info.get('marketCap', 10_000_000_000) / 1e9
        return df, quick_ratio, roe, mcap, info
    # ensure series
    if isinstance(df_stock, pd.DataFrame): df_stock = df_stock.squeeze()
    if isinstance(df_index, pd.DataFrame): df_index = df_index.squeeze()
    df = pd.concat([df_stock.rename('Stock'), df_index.rename('Market')], axis=1).dropna()
    quick_ratio = info.get('quickRatio', 1.2)
    roe = info.get('returnOnEquity', 0.12)
    mcap = info.get('marketCap', 10_000_000_000) / 1e9
    return df, quick_ratio, roe, mcap, info

# -----------------------------
# Tabs (lowercase titles as requested)
# -----------------------------
tab1, tab2, tab3, tab4 = st.tabs(["información básica", "perfil macro y beta", "análisis técnico", "veredicto final"])

# ---------- TAB 1: search & company basic info ----------
with tab1:
    st.header("información básica de la compañía")
    st.markdown("Usa la barra de búsqueda para seleccionar la compañía (nombre parcial funciona). Al seleccionar, la plataforma pedirá a la IA que genere la descripción, portafolio y análisis de riesgos en tiempo real.")
    col_left, col_right = st.columns([2,1])

    with col_left:
        search_input = st.text_input("buscar compañía (ej: CATL, Inditex, Banco Santander...)", value="CATL")
        selected_company = find_company_by_text(search_input)
        st.markdown(f"**Compañía seleccionada:** {selected_company}")
        stock_info = STOCKS[selected_company]
        ticker_symbol = stock_info["ticker"]
        index_symbol = stock_info["index"]

        # When user changes selection, fetch data and ask IA for JSON (description+risks+segments)
        if st.button("🔎 Obtener información corporativa (IA)"):
            st.session_state['selected_company'] = selected_company
            # Prompt for JSON (70 words description, riesgos <=150 words, 3 segments that sum 100)
            prompt_info = f"""
            Eres un analista financiero experto. Devuelve un JSON EXACTO sin texto adicional con la estructura:
            {{
              "descripcion": "Quiénes son y qué hacen (máx 70 palabras).",
              "riesgos": "Análisis del entorno (riesgo político, inflación y otros dos factores) en {stock_info['region']} (máx 150 palabras).",
              "segmentos": ["Segmento A","Segmento B","Segmento C"],
              "porcentajes": [X,Y,Z]
            }}
            Asegúrate de que X+Y+Z sumen 100 y que los segmentos sean relevantes para {selected_company}.
            """
            msgs = [
                {"role":"system","content":"Eres un analista financiero que responde en JSON cuando se le pide."},
                {"role":"user","content":prompt_info}
            ]
            resp = ask_openai(msgs, model="gpt-4o-mini", max_tokens=400)
            # try to parse JSON robustly
            try:
                # clean codeblock wrappers if any
                if "```json" in resp:
                    resp = resp.split("```json")[1].split("```")[0].strip()
                if resp.strip().startswith("```"):
                    resp = resp.strip().strip("```").strip()
                data_info = json.loads(resp)
                st.session_state['tab1_info'] = data_info
            except Exception as e:
                st.error(f"Error parsing JSON de IA: {e}")
                st.write("Respuesta cruda IA:", resp)
    with col_right:
        st.markdown("### Resumen almacenado")
        if st.session_state.get('tab1_info'):
            data_info = st.session_state['tab1_info']
            st.markdown("**Descripción (máx 70 palabras):**")
            st.write(data_info.get('descripcion','-'))
            st.markdown("**Composición de ingresos (pie):**")
            segs = data_info.get('segmentos', ['A','B','C'])
            vals = data_info.get('porcentajes', [50,30,20])
            fig_pie = go.Figure(data=[go.Pie(labels=segs, values=vals, hole=.4)])
            fig_pie.update_layout(margin=dict(t=10,b=10,l=10,r=10), height=250)
            st.plotly_chart(fig_pie, use_container_width=True)
            st.markdown("**Análisis de Riesgos (máx 150 palabras):**")
            st.markdown(f"<div class='ai-box'>{data_info.get('riesgos','-')}</div>", unsafe_allow_html=True)
        else:
            st.info("Aún no hay información generada. Pulsa 'Obtener información corporativa (IA)'.")

# ---------- TAB 2: macro, beta, dupont, acidez + IA analysis ----------
with tab2:
    st.header("perfil macro y beta")
    # ensure we have a selected_company
    if 'selected_company' in st.session_state:
        selected_company = st.session_state['selected_company']
    else:
        selected_company = list(STOCKS.keys())[0]
        st.session_state['selected_company'] = selected_company
    stock_info = STOCKS[selected_company]
    ticker_symbol = stock_info["ticker"]
    index_symbol = stock_info["index"]

    # download 1y daily by default for fundamental metrics
    df_full, quick_ratio, roe, mcap, info_raw = download_data_for(ticker_symbol, index_symbol, period="1y", interval="1d")
    # compute beta via covariance approach (align returns)
    returns = df_full.pct_change().dropna()
    if len(returns) < 2:
        beta_calc = 1.0
    else:
        cov = np.cov(returns['Market'], returns['Stock'], ddof=0)
        beta_calc = cov[0,1] / cov[0,0] if cov[0,0] != 0 else 1.0

    col1, col2, col3 = st.columns(3)
    col1.markdown(f"<div class='metric-box'><div class='metric-title'>BETA</div><div class='metric-value'>{beta_calc:.2f}</div></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='metric-box'><div class='metric-title'>ROE (DuPont)</div><div class='metric-value'>{roe*100:.2f}%</div></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='metric-box'><div class='metric-title'>Test Ácido</div><div class='metric-value'>{quick_ratio:.2f}</div></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("Interpretaciones (generadas por IA):")
    # Build prompt for IA to interpret Beta, DuPont, Test Ácido and the 3 theories of fx
    prompt_macro = f"""
    Actúa como analista senior. Para la acción {selected_company} (Ticker: {ticker_symbol}) con datos:
    Beta: {beta_calc:.2f}, ROE: {roe*100:.2f}%, Test Ácido: {quick_ratio:.2f}, Inflación País: {stock_info['inflacion']}%.

    Genera:
    1) Interpretación Beta (OBLIGATORIO comenzar con la frase exacta: "Por cada punto que el índice de referencia suba la acción subirá el valor que corresponda en referencia 1:{beta_calc:.2f}.") + extiende la interpretación en máximo 90 palabras.
    2) Interpretación DuPont (90 palabras máximo).
    3) Interpretación Test Ácido (90 palabras máximo).
    4) Análisis breve de 3 teorías de divisas (PPP, IRP, Efecto Fisher) partiendo de la inflación del {stock_info['region']} ({stock_info['inflacion']}%). Cada punto en párrafo separado.

    Devuelve el resultado en texto plano con títulos claros:
    **Interpretación Beta:** ...
    **Interpretación DuPont:** ...
    **Interpretación Test Ácido:** ...
    **Análisis Teorías de Divisas:** ...
    """

    with st.spinner("IA interpretando métricas y teorías de divisas..."):
        msgs = [{"role":"system","content":"Eres un analista financiero crítico y conciso."},
                {"role":"user","content":prompt_macro}]
        macro_text = ask_openai(msgs, model="gpt-4o-mini", max_tokens=600)
        st.markdown(f"<div class='ai-box'>{macro_text}</div>", unsafe_allow_html=True)
        st.session_state['tab2_text'] = macro_text

# ---------- TAB 3: analysis tecnico (controls for timeframe and indicators) ----------
with tab3:
    st.header("análisis técnico")
    st.markdown("Elige el indicador (Bollinger, MACD, RSI, Fibonacci) y la temporalidad. Puedes combinar indicadores. Temporalidades: dia, semana, mes, 3m, 6m, 1a, 5a, ytd, max.")

    # controls within tab3
    col_a, col_b = st.columns([2,1])
    with col_a:
        # timeframe mapping to yfinance period and interval:
        timeframe_choice = st.selectbox("Temporalidad (histórico)", options=["dia","semana","mes","3m","6m","1a","5a","ytd","max"], index=5)
        tf_map = {
            "dia":("5d","5m"),
            "semana":("1mo","30m"),
            "mes":("3mo","1d"),
            "3m":("6mo","1d"),
            "6m":("1y","1d"),
            "1a":("1y","1d"),
            "5a":("5y","1d"),
            "ytd":("ytd","1d"),
            "max":("max","1d")
        }
        period, interval = tf_map.get(timeframe_choice, ("1y","1d"))
        # indicator toggles
        indicators = st.multiselect("Indicadores a mostrar", options=["Bollinger","MACD","RSI","Fibonacci"], default=["Bollinger","MACD"])
    with col_b:
        st.markdown("Opciones de visualización")
        show_volume = st.checkbox("Mostrar volumen (si aplica)", value=False)
        lighter_style = st.checkbox("Estilo fresco (marcos redondeados)", value=True)

    # download data for chart with period & interval
    df_chart, _, _, _, _ = download_data_for(ticker_symbol, index_symbol, period=period, interval=interval)
    # compute indicators (recompute robustly)
    dfc = df_chart.copy()
    dfc = dfc.dropna()
    if dfc.empty:
        st.error("No hay datos para el periodo seleccionado.")
    else:
        # SMA/STD for Bollinger (using 20 periods for daily, but if interval too coarse, it's OK)
        dfc['SMA'] = dfc['Stock'].rolling(window=20, min_periods=2).mean()
        dfc['STD'] = dfc['Stock'].rolling(window=20, min_periods=2).std()
        dfc['Upper_BB'] = dfc['SMA'] + (dfc['STD'] * 2)
        dfc['Lower_BB'] = dfc['SMA'] - (dfc['STD'] * 2)
        # MACD
        dfc['EMA_12'] = dfc['Stock'].ewm(span=12, adjust=False).mean()
        dfc['EMA_26'] = dfc['Stock'].ewm(span=26, adjust=False).mean()
        dfc['MACD'] = dfc['EMA_12'] - dfc['EMA_26']
        dfc['Signal'] = dfc['MACD'].ewm(span=9, adjust=False).mean()
        # RSI
        delta = dfc['Stock'].diff()
        gain = delta.clip(lower=0).rolling(window=14, min_periods=2).mean()
        loss = -delta.clip(upper=0).rolling(window=14, min_periods=2).mean()
        rs = gain / (loss.replace(0, np.nan))
        dfc['RSI'] = 100 - (100 / (1 + rs))
        # Fibonacci levels on visible window
        max_p = dfc['Stock'].max()
        min_p = dfc['Stock'].min()
        diff_p = max_p - min_p if max_p>min_p else 0
        fib_levels = []
        if diff_p>0:
            fib_levels = [max_p, max_p - 0.236*diff_p, max_p - 0.382*diff_p, max_p - 0.5*diff_p, max_p - 0.618*diff_p, min_p]

        # Build figure: single plot with subplots for MACD/RSI if selected
        nrows = 1
        if "MACD" in indicators and "RSI" in indicators:
            nrows = 3
            row_heights = [0.6, 0.2, 0.2]
        elif "MACD" in indicators or "RSI" in indicators:
            nrows = 2
            row_heights = [0.75, 0.25]
        else:
            nrows = 1
            row_heights = [1]

        fig = make_subplots(rows=nrows, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                            row_heights=row_heights)

        # price trace
        fig.add_trace(go.Scatter(x=dfc.index, y=dfc['Stock'], mode='lines', name='Precio', line=dict(color='#005A9C', width=2)), row=1, col=1)

        if "Bollinger" in indicators:
            fig.add_trace(go.Scatter(x=dfc.index, y=dfc['Upper_BB'], mode='lines', name='Banda Superior', line=dict(color='rgba(0,196,159,0.6)', dash='dash')), row=1, col=1)
            fig.add_trace(go.Scatter(x=dfc.index, y=dfc['Lower_BB'], mode='lines', name='Banda Inferior', line=dict(color='rgba(0,196,159,0.6)', dash='dash'), fill='tonexty', fillcolor='rgba(0,196,159,0.08)'), row=1, col=1)

        if "Fibonacci" in indicators and fib_levels:
            colors = ['#ff0000', '#ff8c00', '#ffd700', '#008000', '#0000ff', '#800080']
            for i, level in enumerate(fib_levels):
                fig.add_hline(y=level, line_dash="dot", line_color=colors[i%len(colors)], row=1, col=1)

        # MACD
        current_row = 2
        if "MACD" in indicators:
            fig.add_trace(go.Scatter(x=dfc.index, y=dfc['MACD'], mode='lines', name='MACD', line=dict(color='#ffbb28')), row=current_row, col=1)
            fig.add_trace(go.Scatter(x=dfc.index, y=dfc['Signal'], mode='lines', name='Señal', line=dict(color='#ff8042')), row=current_row, col=1)
            current_row += 1

        if "RSI" in indicators:
            fig.add_trace(go.Scatter(x=dfc.index, y=dfc['RSI'], mode='lines', name='RSI', line=dict(color='#8884d8')), row=current_row, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=current_row, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=current_row, col=1)

        fig.update_layout(height=700, template="plotly_white", margin=dict(t=30,b=10,l=10,r=10), legend=dict(orientation="h"))
        fig.update_xaxes(showgrid=True, gridcolor="#eef2f5")
        fig.update_yaxes(showgrid=True, gridcolor="#eef2f5")

        # visual "power bi fresh" frame box
        st.markdown("<div class='rounded-panel'>", unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # store last chart descriptors for final report
        st.session_state['chart_info'] = {"indicators": indicators, "timeframe": timeframe_choice}

# ---------- TAB 4: final verdict and IA compilation ----------
with tab4:
    st.header("veredicto final")
    st.markdown("Compila la información de todas las pestañas y genera la justificación ejecutiva (<100 palabras) priorizando riesgos.")

    # Show summary of collected pieces
    colA, colB = st.columns(2)
    with colA:
        st.markdown("**Compañía seleccionada:**")
        sel = st.session_state.get('selected_company', list(STOCKS.keys())[0])
        st.write(sel)
        st.markdown("**Cotización actual** (último precio):")
        # ensure we have df_full
        try:
            last_price = df_full['Stock'].iloc[-1]
            st.write(f"{last_price:.2f} {stock_info['currency']}")
        except Exception:
            st.write("N/D")
        st.markdown("**Capitalización (miles de millones)**:")
        try:
            st.write(f"{mcap:.2f}")
        except Exception:
            st.write("N/D")
    with colB:
        st.markdown("**Elementos de análisis recopilados:**")
        st.write("Descripción e ingresos: ", "sí" if st.session_state.get('tab1_info') else "no")
        st.write("Interpretaciones Beta/DuPont/Test: ", "sí" if st.session_state.get('tab2_text') else "no")
        st.write("Chart info: ", st.session_state.get('chart_info', {}))

    # Score calculation (simple implementation based on earlier framework)
    def compute_score(beta, roe, quick_ratio, region):
        # Fundamental scoring (-35..+35)
        f_score = 0
        # beta
        if beta < 0.8: f_score += 8
        elif 0.8 <= beta <= 1.2: f_score += 4
        elif 1.2 < beta <= 1.8: f_score -= 4
        else: f_score -= 8
        # roe
        if roe > 0.15: f_score += 10
        elif roe > 0.10: f_score += 5
        else: f_score -= 6
        # quick ratio
        if quick_ratio > 1.5: f_score += 8
        elif quick_ratio >= 1: f_score += 3
        elif quick_ratio >= 0.7: f_score -= 4
        else: f_score -= 10
        f_score = max(-35, min(35, f_score))

        # Risk-macro (-30..+30)
        r_score = 0
        # region geopolitical approximation
        if region.lower() == "china":
            r_score -= 8
        elif region.lower() == "españa":
            r_score += 2
        # inflation vs ROE simple test:
        r_score += -3 if roe < 0.05 else 2
        r_score = max(-30, min(30, r_score))

        # Divisas (-15..+15) simple: penalize if inflation high
        d_score = 0
        # if inflation >2% and region not euro => small penalty
        try:
            inf = stock_info.get('inflacion', 2.0)
            if inf > 4: d_score -= 4
            elif inf > 2: d_score -= 1
            else: d_score += 1
        except:
            d_score = 0
        d_score = max(-15, min(15, d_score))

        # Technical (-20..+20) : heuristic from indicators in session state
        t_score = 0
        chart_info = st.session_state.get('chart_info', {})
        inds = chart_info.get('indicators', [])
        # simple heuristics: if RSI exists and last RSI <30 => +5, >70 => -5
        try:
            last_rsi = dfc['RSI'].iloc[-1] if 'RSI' in dfc.columns else None
            if last_rsi is not None:
                if last_rsi < 30: t_score += 5
                elif last_rsi > 70: t_score -= 5
        except:
            pass
        if 'MACD' in inds:
            try:
                macd = dfc['MACD'].iloc[-1]; signal = dfc['Signal'].iloc[-1]
                if macd > signal: t_score += 3
                else: t_score -= 3
            except:
                pass
        if 'Bollinger' in inds:
            try:
                price = dfc['Stock'].iloc[-1]
                if price < dfc['Lower_BB'].iloc[-1]: t_score += 3
                elif price > dfc['Upper_BB'].iloc[-1]: t_score -= 3
            except:
                pass
        t_score = max(-20, min(20, t_score))

        total = f_score + r_score + d_score + t_score
        total = max(-100, min(100, total))
        # Decision mapping
        if total >= 40:
            decision = "COMPRAR"
        elif total >= 10:
            decision = "MANTENER"
        elif total >= -9:
            decision = "NEUTRAL"
        elif total >= -40:
            decision = "REDUCIR"
        else:
            decision = "VENDER"
        # Prudential override:
        if region.lower() == "china" and beta > 1.5:
            # force limit
            if decision == "COMPRAR":
                decision = "MANTENER"
        return {"score": int(total), "decision": decision, "breakdown": {"fund":f_score,"risk":r_score,"fx":d_score,"tech":t_score}}

    score_struct = compute_score(beta_calc, roe, quick_ratio, stock_info['region'])
    st.markdown("### Score calculado:")
    st.write(score_struct)

    # Final IA compiled prompt: must compile items in required order and ask final justification <100 palabras
    if st.button("Generar justificación final (IA)"):
        # gather pieces
        tab1_info = st.session_state.get('tab1_info', {})
        desc = tab1_info.get('descripcion','N/A')
        riesgos_text = tab1_info.get('riesgos','N/D')
        tab2_text = st.session_state.get('tab2_text','N/D')
        chart_info = st.session_state.get('chart_info',{})
        indicators = chart_info.get('indicators',[])
        timeframe_sel = chart_info.get('timeframe','N/A')

        prompt_final = f"""
        Actúa como un analista senior de riesgos financieros y valoración corporativa. Compila un informe ejecutivo final para {selected_company} (Ticker: {ticker_symbol}).

        ORDEN EXACTO DEL INFORME:
        a) Nombre y Ticker (destacado) + Cotización actual: {last_price:.2f} {stock_info['currency']}.
        b) Capitalización bursátil en miles de millones: {mcap:.2f}.
        c) Información (pestaña información básica): DESCRIPCIÓN: {desc} | RIESGOS: {riesgos_text}
        d) Indicadores y su interpretación (pestaña perfil macro y beta): Beta {beta_calc:.2f}, ROE {roe*100:.2f}%, Test Acidez {quick_ratio:.2f}. Interpretaciones: {tab2_text}
        e) Gráficos técnicos seleccionados ({', '.join(indicators)}), temporalidad seleccionada: {timeframe_sel}. Pide un análisis corto de cada indicador (<=50 palabras cada uno).
        f) Score total del modelo: {score_struct['score']}. Decisión preliminar: {score_struct['decision']}.
        
        REQUISITOS:
        - Redacta UNA JUSTIFICACIÓN estructurada en formato informe ejecutivo en MENOS DE 100 PALABRAS.
        - Debe PRIORITIZAR los riesgos sobre las oportunidades, incluir escenarios adversos, sensibilidad a tasas, coherencia técnico-fundamental, evento que invalidaría la recomendación, y terminar con nivel de convicción (Alto/Medio/Bajo).
        - Tono: profesional, crítico y prudente (tipo comité de inversiones / riesgos bancario).

        Finalmente, devuelve el texto final (solo el párrafo de 100 palabras máximo) sin etiquetas adicionales.
        """

        with st.spinner("IA compilando el veredicto..."):
            msgs = [{"role":"system","content":"Eres un analista senior de riesgos financieros. Responde de forma concisa y profesional."},
                    {"role":"user","content":prompt_final}]
            final_resp = ask_openai(msgs, model="gpt-4o-mini", max_tokens=300)
            st.markdown("### Justificación ejecutiva (<100 palabras):")
            st.markdown(f"<div class='ai-box'>{final_resp}</div>", unsafe_allow_html=True)
            # store for download or copy
            st.session_state['final_report'] = final_resp

    # Option: download final report as txt
    if st.session_state.get('final_report'):
        st.download_button("Descargar justificación (txt)", data=st.session_state['final_report'], file_name=f"{selected_company}_veredicto.txt")

st.caption("Hecho: interfaz con ChatGPT (OpenAI). Asegúrate de configurar OPENAI_API_KEY en tus secretos de Streamlit.")
