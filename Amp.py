import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.stats import linregress
import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Terminal Cuantitativa MBA", layout="wide", initial_sidebar_state="collapsed")

# Estilos CSS personalizados para simular una terminal tipo Bloomberg moderna
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    h1, h2, h3 { color: #58a6ff !important; }
    .metric-box { background-color: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); text-align: center; }
    .metric-value { font-size: 28px; font-weight: bold; color: #ffffff; }
    .highlight { color: #3fb950; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS DE ACCIONES (CSI 300 e IBEX 35) ---
# Puedes expandir este diccionario con más empresas
STOCKS = {
    "CATL - Contemporary Amperex Technology (300750.SZ)": {"ticker": "300750.SZ", "index": "000300.SS", "currency": "CNY", "region": "China"},
    "Kweichow Moutai (600519.SS)": {"ticker": "600519.SS", "index": "000300.SS", "currency": "CNY", "region": "China"},
    "BYD Company (002594.SZ)": {"ticker": "002594.SZ", "index": "000300.SS", "currency": "CNY", "region": "China"},
    "Inditex (ITX.MC)": {"ticker": "ITX.MC", "index": "^IBEX", "currency": "EUR", "region": "España"},
    "Iberdrola (IBE.MC)": {"ticker": "IBE.MC", "index": "^IBEX", "currency": "EUR", "region": "España"},
    "Banco Santander (SAN.MC)": {"ticker": "SAN.MC", "index": "^IBEX", "currency": "EUR", "region": "España"}
}

st.title("Terminal de Análisis de Riesgo y Financiero")
st.write("Datos en tiempo real integrados vía Yahoo Finance API.")

# --- BARRA DE BÚSQUEDA CON AUTOCOMPLETADO ---
selected_company = st.selectbox("Buscador de Activos (Escribe nombre o ticker):", options=list(STOCKS.keys()), index=0)
stock_info = STOCKS[selected_company]
ticker_symbol = stock_info["ticker"]
index_symbol = stock_info["index"]

# --- FUNCIÓN DE EXTRACCIÓN Y CÁLCULO DE DATOS EN TIEMPO REAL ---
@st.cache_data(ttl=3600) # Cachea los datos por 1 hora para no saturar la API
def get_financial_data(ticker, benchmark):
    stock = yf.Ticker(ticker)
    info = stock.info
    
    # Precios históricos (1 Año exacto)
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=365)
    
    df_stock = yf.download(ticker, start=start_date, end=end_date, progress=False)['Adj Close']
    df_index = yf.download(benchmark, start=start_date, end=end_date, progress=False)['Adj Close']
    
    # Unir datos y calcular rendimientos diarios
    df = pd.concat([df_stock, df_index], axis=1)
    df.columns = ['Stock', 'Market']
    df = df.dropna() # Limpiar días festivos no coincidentes
    returns = df.pct_change().dropna()
    
    # Regresión Lineal para Beta
    slope, intercept, r_value, p_value, std_err = linregress(returns['Market'], returns['Stock'])
    beta_calc = slope
    
    # Extracción de Fundamentales (Manejo de errores si YF no tiene el dato)
    quick_ratio = info.get('quickRatio', 'N/A')
    roe = info.get('returnOnEquity', 'N/A')
    market_cap = info.get('marketCap', 'N/A')
    short_name = info.get('shortName', ticker)
    summary = info.get('longBusinessSummary', 'Información no disponible.')
    
    return returns, df, beta_calc, quick_ratio, roe, market_cap, short_name, summary

# Cargar datos
with st.spinner(f"Extrayendo datos de mercado en tiempo real para {ticker_symbol}..."):
    returns, price_data, beta_calc, quick_ratio, roe, market_cap, short_name, summary = get_financial_data(ticker_symbol, index_symbol)

# Formateo de métricas
roe_display = f"{roe*100:.2f}%" if isinstance(roe, float) else "N/A"
qr_display = f"{quick_ratio:.2f}" if isinstance(quick_ratio, float) else "N/A"
mcap_display = f"{market_cap / 1e9:.2f} B" if isinstance(market_cap, (int, float)) else "N/A"

# --- CREACIÓN DE PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["1. Perfil y Riesgos", "2. Divisas y Beta Teórica", "3. Análisis y Veredicto (Tiempo Real)"])

# === PESTAÑA 1 ===
with tab1:
    st.header(f"Introducción: {short_name}")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.write(summary[:800] + "..." if len(summary) > 800 else summary)
    with col2:
        st.markdown(f"""
        <div class="metric-box">
            <p>Capitalización de Mercado ({stock_info['currency']})</p>
            <div class="metric-value">{mcap_display}</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.subheader("Análisis de Riesgo Geopolítico (Dinámico por Región)")
    if stock_info["region"] == "China":
        st.info("**Riesgo Arancelario:** Exposición a políticas proteccionistas (IRA en EE.UU., Battery Passport en Europa).\n\n**Cadena de Suministro:** Ventaja competitiva en control de minerales críticos, pero riesgo de sanciones de Occidente.")
    else:
        st.info("**Riesgo Energético:** Dependencia de la estabilidad de precios del gas natural y políticas del BCE.\n\n**Regulación UE:** Fuerte presión regulatoria sobre ESG y emisiones.")

# === PESTAÑA 2 ===
with tab2:
    st.header("Marco Macroeconómico: Circuito de Divisas")
    st.markdown("""
    Analizamos el entorno conectando tres teorías fundamentales:
    1. **Efecto Fisher:** Inflación $\\uparrow$ $\\rightarrow$ Tipos de interés nominales $\\uparrow$
    2. **Paridad de Poder Adquisitivo (PPA):** La moneda del país con mayor inflación tiende a depreciarse para igualar el coste de vida.
    3. **Paridad de Tipos de Interés (PTI):** La expectativa de depreciación de una moneda compensa el diferencial de tipos de interés, creando un equilibrio en los mercados *forward*.
    """)
    
    st.header("Marco Teórico: Ecuación de la Beta por Regresión OLS")
    st.markdown("""
    Para este análisis, la Beta se ha calculado mediante una regresión lineal entre los rendimientos diarios del activo y su índice de referencia (ej. CSI 300 o IBEX 35):
    $$R_i = \\alpha + \\beta R_m + \\epsilon$$
    Donde:
    * **$R_i$**: Rendimiento de la acción.
    * **$R_m$**: Rendimiento del mercado.
    * **$\\beta$**: Pendiente de la regresión (sensibilidad del activo frente al mercado).
    """)

# === PESTAÑA 3 ===
with tab3:
    st.header("Análisis Fundamental y Cuantitativo (Datos Vivos)")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='metric-box'><p>Beta (1 Año - Regresión)</p><div class='metric-value'>{beta_calc:.3f}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='metric-box'><p>Test Ácido (Liquidez)</p><div class='metric-value'>{qr_display}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='metric-box'><p>ROE (DuPont)</p><div class='metric-value'>{roe_display}</div></div>", unsafe_allow_html=True)

    # Gráfico Interactivo Plotly (Estilo Bloomberg)
    st.subheader("Rendimiento Normalizado a 1 Año (Base 100)")
    norm_stock = (price_data['Stock'] / price_data['Stock'].iloc[0]) * 100
    norm_market = (price_data['Market'] / price_data['Market'].iloc[0]) * 100
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=norm_stock.index, y=norm_stock, mode='lines', name=ticker_symbol, line=dict(color='#58a6ff', width=2)))
    fig.add_trace(go.Scatter(x=norm_market.index, y=norm_market, mode='lines', name=f"Mercado ({index_symbol})", line=dict(color='#8b949e', width=2, dash='dot')))
    fig.update_layout(
        plot_bgcolor='#0d1117', paper_bgcolor='#0d1117', font_color='#c9d1d9',
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#30363d'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

    # Motor de Veredicto Lógico
    st.subheader("Veredicto Final")
    try:
        if isinstance(roe, float) and isinstance(quick_ratio, float):
            if beta_calc > 1 and quick_ratio >= 1 and roe > 0.10:
                verdict = "COMPRAR (BUY)"
                color = "#3fb950"
                rationale = f"Solvencia fuerte (Test Ácido: {quick_ratio:.2f}). ROE robusto ({roe*100:.2f}%). Con una Beta de {beta_calc:.2f}, amplificará las ganancias si el ciclo de tipos de interés (Fisher) se estabiliza y la divisa se fortalece."
            elif beta_calc < 1 and quick_ratio >= 0.8:
                verdict = "MANTENER (HOLD)"
                color = "#d29922"
                rationale = "Activo defensivo por baja volatilidad. Mantener a la espera de claridad en la paridad de tipos de interés."
            else:
                verdict = "VENDER (SELL)"
                color = "#f85149"
                rationale = "Debilidad en métricas de liquidez o rentabilidad incapaz de justificar el riesgo de mercado."
        else:
             verdict = "REVISIÓN MANUAL REQUERIDA"
             color = "#8b949e"
             rationale = "Faltan datos financieros (ROE o Liquidez) en la API de origen para formular un veredicto puramente cuantitativo."
             
        st.markdown(f"<h2 style='text-align: center; color: {color} !important;'>{verdict}</h2>", unsafe_allow_html=True)
        st.write(f"**Justificación:** {rationale}")
    except Exception as e:
        st.error("Error calculando el veredicto con los datos actuales.")