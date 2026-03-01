import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import google.generativeai as genai
import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Terminal Cuantitativa MBA", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    h1, h2, h3 { color: #58a6ff !important; }
    .metric-box { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 8px; text-align: center; }
    .metric-value { font-size: 24px; font-weight: bold; color: #ffffff; }
    /* Estilo para el st.metric de Streamlit */
    div[data-testid="stMetricValue"] { font-size: 36px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS DE ACCIONES ---
STOCKS = {
    "CATL - Contemporary Amperex Technology (300750.SZ)": {"ticker": "300750.SZ", "index": "000300.SS", "currency": "CNY", "region": "China"},
    "Kweichow Moutai (600519.SS)": {"ticker": "600519.SS", "index": "000300.SS", "currency": "CNY", "region": "China"},
    "BYD Company (002594.SZ)": {"ticker": "002594.SZ", "index": "000300.SS", "currency": "CNY", "region": "China"},
    "Inditex (ITX.MC)": {"ticker": "ITX.MC", "index": "^IBEX", "currency": "EUR", "region": "España"},
    "Iberdrola (IBE.MC)": {"ticker": "IBE.MC", "index": "^IBEX", "currency": "EUR", "region": "España"}
}

# --- BARRA LATERAL (CONTROLES DE TEMPORALIDAD) ---
st.sidebar.header("⚙️ Parámetros Técnicos")
st.sidebar.markdown("Ajusta la temporalidad de los indicadores en tiempo real:")

bb_window = st.sidebar.number_input("Períodos Bandas Bollinger (SMA)", min_value=5, max_value=100, value=20)
st.sidebar.markdown("---")
macd_fast = st.sidebar.number_input("MACD: Períodos Rápida (EMA)", min_value=1, max_value=50, value=12)
macd_slow = st.sidebar.number_input("MACD: Períodos Lenta (EMA)", min_value=5, max_value=100, value=26)
macd_signal = st.sidebar.number_input("MACD: Períodos Señal", min_value=1, max_value=50, value=9)

st.title("Terminal Cuantitativa y de Riesgo (AI-Powered)")

selected_company = st.selectbox("Buscador de Activos:", options=list(STOCKS.keys()), index=0)
stock_info = STOCKS[selected_company]
ticker_symbol = stock_info["ticker"]
index_symbol = stock_info["index"]

# --- EXTRACCIÓN DE DATOS (CASCADA DE RIESGOS: REAL -> PROXY -> SIMULACIÓN) ---
@st.cache_data(ttl=3600)
def download_data(ticker, benchmark):
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=365)
    
    # Valores fundamentales proxy en caso de fallo de YF
    default_qr = 1.35
    default_roe = 0.185
    
    # Mapeo de ETFs Proxy para mitigar riesgo de índices caídos
    PROXY_MAP = {
        "000300.SS": "ASHR", # ETF listado en EE.UU. que replica el CSI 300
        "^IBEX": "EWP"       # ETF listado en EE.UU. que replica a España
    }

    # === INTENTO 1: Datos Originales Completos ===
    try:
        stock = yf.Ticker(ticker)
        info = stock.info # <-- Punto crítico de bloqueo por IP
        
        df_stock = yf.download(ticker, start=start_date, end=end_date, progress=False)['Close']
        df_index = yf.download(benchmark, start=start_date, end=end_date, progress=False)['Close']
        
        if isinstance(df_stock, pd.DataFrame): df_stock = df_stock.squeeze()
        if isinstance(df_index, pd.DataFrame): df_index = df_index.squeeze()
            
        df = pd.DataFrame({'Stock': df_stock, 'Market': df_index}).dropna()
        if df.empty: raise ValueError("Datos vacíos.")
        
        qr = info.get('quickRatio', default_qr)
        roe = info.get('returnOnEquity', default_roe)
        name = info.get('shortName', ticker)
        
        return df, qr, roe, name

    except Exception as e1:
        # === INTENTO 2: Uso de ETF Proxy (Saltando .info) ===
        try:
            proxy_benchmark = PROXY_MAP.get(benchmark, benchmark)
            
            # Avisamos sutilmente al usuario
            st.toast(f"⚠️ Yahoo Finance limitó el acceso. Conectando a datos Proxy ({proxy_benchmark})...", icon="🔄")
            
            df_stock = yf.download(ticker, start=start_date, end=end_date, progress=False)['Close']
            df_index = yf.download(proxy_benchmark, start=start_date, end=end_date, progress=False)['Close']
            
            if isinstance(df_stock, pd.DataFrame): df_stock = df_stock.squeeze()
            if isinstance(df_index, pd.DataFrame): df_index = df_index.squeeze()
                
            df = pd.DataFrame({'Stock': df_stock, 'Market': df_index}).dropna()
            if df.empty: raise ValueError("Datos vacíos en Proxy.")
            
            return df, default_qr, default_roe, f"{ticker} (Datos de Respaldo)"

        except Exception as e2:
            # === INTENTO 3: Simulación Estadística (Movimiento Browniano) ===
            st.error("🛑 Bloqueo total de IP en Yahoo Finance. Activando motor estadístico (Movimiento Browniano)...")
            
            dates = pd.bdate_range(end=end_date, periods=252)
            np.random.seed(42) # Semilla fija para mantener consistencia gráfica
            
            mkt_returns = np.random.normal(0.0002, 0.01, 252)
            stk_returns = (mkt_returns * 1.5) + np.random.normal(0, 0.015, 252) # Forzar Beta ~1.5
            
            market_price = 3500 * np.exp(np.cumsum(mkt_returns))
            stock_price = 150 * np.exp(np.cumsum(stk_returns))
            
            df = pd.DataFrame({'Stock': stock_price, 'Market': market_price}, index=dates)
            
            return df, default_qr, default_roe, f"{ticker} (Modo Simulación ODS)"

with st.spinner("Sincronizando con el mercado..."):
    base_df, quick_ratio, roe, short_name = download_data(ticker_symbol, index_symbol)

# --- CÁLCULO DINÁMICO DE INDICADORES ---
df = base_df.copy()
returns = df.pct_change().dropna()

# Beta por matriz de covarianzas (Equivalente matemático a OLS)
cov_mat = np.cov(returns['Market'], returns['Stock'])
beta_calc = cov_mat[0, 1] / cov_mat[0, 0]

# Bandas de Bollinger Dinámicas
df['SMA'] = df['Stock'].rolling(window=bb_window).mean()
df['STD'] = df['Stock'].rolling(window=bb_window).std()
df['Upper_BB'] = df['SMA'] + (df['STD'] * 2)
df['Lower_BB'] = df['SMA'] - (df['STD'] * 2)

# MACD Dinámico
df['EMA_Fast'] = df['Stock'].ewm(span=macd_fast, adjust=False).mean()
df['EMA_Slow'] = df['Stock'].ewm(span=macd_slow, adjust=False).mean()
df['MACD'] = df['EMA_Fast'] - df['EMA_Slow']
df['Signal_Line'] = df['MACD'].ewm(span=macd_signal, adjust=False).mean()
df['MACD_Hist'] = df['MACD'] - df['Signal_Line']

# --- PESTAÑAS DE VISUALIZACIÓN ---
tab1, tab2, tab3 = st.tabs(["1. Perfil Macro y Beta", "2. Análisis Técnico Interactivo", "3. CONCLUSIÓN Y VEREDICTO (IA)"])

with tab1:
    st.header(f"Perfil de Riesgo e Información: {short_name}")
    
    # --- COTIZACIÓN EN TIEMPO REAL ---
    if len(df) > 1:
        current_price = df['Stock'].iloc[-1]
        prev_price = df['Stock'].iloc[-2]
        delta_pct = ((current_price / prev_price) - 1) * 100
        
        col_price, col_empty = st.columns([1, 2])
        with col_price:
            st.metric(
                label=f"Cotización Actual ({stock_info['currency']})", 
                value=f"{current_price:.2f}", 
                delta=f"{delta_pct:.2f}% (1D)"
            )
    st.markdown("---")
    
    st.write("La base macroeconómica (Teorías de Fisher, PPA y PTI) define el entorno en el que opera la compañía.")
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='metric-box'><p>Beta (1 Año)</p><div class='metric-value'>{beta_calc:.3f}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-box'><p>Test Ácido</p><div class='metric-value'>{quick_ratio}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-box'><p>ROE (DuPont)</p><div class='metric-value'>{roe*100:.2f}%</div></div>" if isinstance(roe, float) else "<div class='metric-box'><p>ROE (DuPont)</p><div class='metric-value'>N/A</div></div>", unsafe_allow_html=True)

with tab2:
    st.header(f"Gráficos Técnicos ({bb_window} periodos Bollinger | MACD {macd_fast}/{macd_slow}/{macd_signal})")
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3])
    
    fig.add_trace(go.Scatter(x=df.index, y=df['Stock'], mode='lines', name='Precio', line=dict(color='#c9d1d9')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Upper_BB'], mode='lines', name='Banda Superior', line=dict(color='rgba(88, 166, 255, 0.5)', dash='dash')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Lower_BB'], mode='lines', name='Banda Inferior', line=dict(color='rgba(88, 166, 255, 0.5)', dash='dash'), fill='tonexty', fillcolor='rgba(88, 166, 255, 0.1)'), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], mode='lines', name='MACD', line=dict(color='#58a6ff')), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal_Line'], mode='lines', name='Señal', line=dict(color='#f85149')), row=2, col=1)
    colors = ['#3fb950' if val >= 0 else '#f85149' for val in df['MACD_Hist']]
    fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='Histograma', marker_color=colors), row=2, col=1)

    fig.update_layout(height=600, plot_bgcolor='#0d1117', paper_bgcolor='#0d1117', font_color='#c9d1d9', margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.header("🤖 Veredicto Final del Analista (IA Cuantitativa)")
    st.write("Genera una evaluación que integra fundamentos corporativos, riesgo macroeconómico y posición técnica en base a la temporalidad seleccionada.")
    
    if st.button("Generar Conclusión Final con Gemini", type="primary"):
        current_price = df['Stock'].iloc[-1]
        bb_upper = df['Upper_BB'].iloc[-1]
        bb_lower = df['Lower_BB'].iloc[-1]
        macd_val = df['MACD'].iloc[-1]
        signal_val = df['Signal_Line'].iloc[-1]
        roe_val = f"{roe*100:.2f}%" if isinstance(roe, float) else "No disponible"
        
        prompt = f"""
        Actúa como el Jefe de Riesgos y Tesorería de PwC España. Realiza el veredicto de inversión para la acción {short_name} ({ticker_symbol}) como parte de una tesis de MBA.
        
        Debes sintetizar OBLIGATORIAMENTE las siguientes variables actuales:
        1. Fundamentos: ROE (Análisis DuPont) de {roe_val} y Test Ácido de {quick_ratio}.
        2. Riesgo y Macro: Beta de {beta_calc:.2f}. Considera el Efecto Fisher y la Paridad de Tipos de Interés (el activo opera en {stock_info['region']}, divisa {stock_info['currency']}).
        3. Análisis Técnico (Temporalidad seleccionada por el usuario):
           - Precio actual: {current_price:.2f}
           - Bandas de Bollinger ({bb_window} periodos): Banda Superior {bb_upper:.2f}, Inferior {bb_lower:.2f}.
           - MACD ({macd_fast}, {macd_slow}, {macd_signal}): Línea MACD {macd_val:.2f}, Señal {signal_val:.2f}.
        
        Estructura de tu respuesta (máximo 4-5 párrafos, tono profesional, analítico y directo):
        - Síntesis Fundamental (Liquidez y Rentabilidad).
        - Evaluación Macro y de Riesgo (Relación Beta/Divisas).
        - Posición Técnica Actual (Momento según BB y MACD).
        - VEREDICTO FINAL: Declara explícitamente si la recomendación es COMPRAR, MANTENER o VENDER, justificando el peso relativo de las variables anteriores. No des rodeos en el veredicto.
        """
        
        try:
            api_key = st.secrets.get("GEMINI_API_KEY")
            if not api_key:
                st.error("⚠️ Configura la GEMINI_API_KEY en los Secrets de Streamlit.")
            else:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                
                with st.spinner("La IA está sintetizando las variables y redactando el veredicto..."):
                    response = model.generate_content(prompt)
                    
                st.success("Análisis completado.")
                st.markdown("---")
                st.markdown(response.text)
                st.markdown("---")
                st.caption("Nota: Este análisis está generado por Inteligencia Artificial y no constituye asesoramiento financiero real.")
                
        except Exception as e:
            st.error(f"Error de conexión con la IA: {e}")
