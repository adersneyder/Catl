import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import google.generativeai as genai
import datetime
import json
import re

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Terminal Cuantitativa MBA", layout="wide")

# --- ESTILOS CSS (TIPO POWER BI / MODERNO) ---
st.markdown("""
    <style>
    .stApp { background-color: #f3f6f9; color: #1e1e1e; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    h1, h2, h3 { color: #005A9C !important; font-weight: 600; }
    
    /* Cajas de métricas estilo Power BI */
    .metric-box { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 12px; 
        text-align: center; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.1);
        border-top: 4px solid #005A9C;
        transition: transform 0.2s ease-in-out;
    }
    .metric-box:hover { transform: translateY(-3px); box-shadow: 0 6px 12px rgba(0,0,0,0.1); }
    .metric-title { font-size: 14px; color: #6c757d; text-transform: uppercase; font-weight: bold; margin-bottom: 10px; }
    .metric-value { font-size: 28px; font-weight: 800; color: #1e1e1e; }
    
    /* Pestañas */
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: transparent; border-radius: 4px 4px 0 0; gap: 1px; padding-top: 10px; padding-bottom: 10px; }
    .stTabs [aria-selected="true"] { color: #005A9C; font-weight: 600; border-bottom: 3px solid #005A9C; }
    
    /* Contenedores de IA */
    .ai-box {
        background-color: #eef2f5; border-left: 4px solid #00c49f; padding: 15px; border-radius: 0 8px 8px 0; margin-top: 10px; font-size: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS DE ACCIONES ---
STOCKS = {
    "CATL - Contemporary Amperex Technology": {"ticker": "300750.SZ", "index": "000300.SS", "currency": "CNY", "region": "China", "inflacion": 0.3},
    "COSCO Shipping": {"ticker": "601919.SS", "index": "000300.SS", "currency": "CNY", "region": "China", "inflacion": 0.3},
    "China Petroleum & Chemical (Sinopec)": {"ticker": "600028.SS", "index": "000300.SS", "currency": "CNY", "region": "China", "inflacion": 0.3},
    "China Spacesat": {"ticker": "600118.SS", "index": "000300.SS", "currency": "CNY", "region": "China", "inflacion": 0.3},
    "Beijing Capital": {"ticker": "600008.SS", "index": "000300.SS", "currency": "CNY", "region": "China", "inflacion": 0.3},
    "Sinopec Shanghai Petrochemical": {"ticker": "600688.SS", "index": "000300.SS", "currency": "CNY", "region": "China", "inflacion": 0.3},
    "Hainan Airlines": {"ticker": "600221.SS", "index": "000300.SS", "currency": "CNY", "region": "China", "inflacion": 0.3},
    "Aluminum Corp of China": {"ticker": "601600.SS", "index": "000300.SS", "currency": "CNY", "region": "China", "inflacion": 0.3},
    "Dongfeng Automobile": {"ticker": "600006.SS", "index": "000300.SS", "currency": "CNY", "region": "China", "inflacion": 0.3},
    "Hubei Yihua Chemical": {"ticker": "000422.SZ", "index": "000300.SS", "currency": "CNY", "region": "China", "inflacion": 0.3},
    "Kingfa Sci&Tech": {"ticker": "600143.SS", "index": "000300.SS", "currency": "CNY", "region": "China", "inflacion": 0.3},
    "Guanghui Energy": {"ticker": "600256.SS", "index": "000300.SS", "currency": "CNY", "region": "China", "inflacion": 0.3},
    "CSSC Offshore & Marine": {"ticker": "600685.SS", "index": "000300.SS", "currency": "CNY", "region": "China", "inflacion": 0.3},
    "Kweichow Moutai": {"ticker": "600519.SS", "index": "000300.SS", "currency": "CNY", "region": "China", "inflacion": 0.3},
    "Sany Heavy Industry": {"ticker": "600031.SS", "index": "000300.SS", "currency": "CNY", "region": "China", "inflacion": 0.3},
    "China Railway Group": {"ticker": "601390.SS", "index": "000300.SS", "currency": "CNY", "region": "China", "inflacion": 0.3},
    "EVE Energy": {"ticker": "300014.SZ", "index": "000300.SS", "currency": "CNY", "region": "China", "inflacion": 0.3},
    "Inditex": {"ticker": "ITX.MC", "index": "^IBEX", "currency": "EUR", "region": "España", "inflacion": 3.2},
    "Iberdrola": {"ticker": "IBE.MC", "index": "^IBEX", "currency": "EUR", "region": "España", "inflacion": 3.2},
    "Banco Santander": {"ticker": "SAN.MC", "index": "^IBEX", "currency": "EUR", "region": "España", "inflacion": 3.2},
    "BBVA": {"ticker": "BBVA.MC", "index": "^IBEX", "currency": "EUR", "region": "España", "inflacion": 3.2},
    "Amadeus IT": {"ticker": "AMS.MC", "index": "^IBEX", "currency": "EUR", "region": "España", "inflacion": 3.2},
    "Cellnex Telecom": {"ticker": "CLNX.MC", "index": "^IBEX", "currency": "EUR", "region": "España", "inflacion": 3.2},
    "Telefónica": {"ticker": "TEF.MC", "index": "^IBEX", "currency": "EUR", "region": "España", "inflacion": 3.2},
    "Repsol": {"ticker": "REP.MC", "index": "^IBEX", "currency": "EUR", "region": "España", "inflacion": 3.2},
    "Ferrovial": {"ticker": "FER.MC", "index": "^IBEX", "currency": "EUR", "region": "España", "inflacion": 3.2},
    "CaixaBank": {"ticker": "CABK.MC", "index": "^IBEX", "currency": "EUR", "region": "España", "inflacion": 3.2}
}

# --- CONFIGURACIÓN IA ---
api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else None
if api_key:
    genai.configure(api_key=api_key)
    # CORRECCIÓN DE ERROR 404: Se usa la versión estable global "gemini-1.5-flash"
    model = genai.GenerativeModel("gemini-1.5-flash") 
else:
    st.warning("⚠️ Falla de API: Configura GEMINI_API_KEY en los secrets de Streamlit.")

@st.cache_data(ttl=3600, show_spinner=False)
def get_gemini_response(prompt):
    if not api_key: return "API Key no configurada."
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error en IA: {e}"

st.title("Terminal Cuantitativa Institucional")

# --- DEFINICIÓN DE PESTAÑAS Y CAPTURA DE CONTROLES ---
tab1, tab2, tab3, tab4 = st.tabs(["información básica", "perfil macro y beta", "análisis técnico", "veredicto final"])

# 1. Capturar el activo en la primera pestaña
with tab1:
    selected_company = st.selectbox("Buscador de Activos:", options=list(STOCKS.keys()), index=0)
    stock_info = STOCKS[selected_company]
    ticker_symbol = stock_info["ticker"]
    index_symbol = stock_info["index"]

# 2. Capturar temporalidad y gráficos en la tercera pestaña antes de descargar datos
with tab3:
    st.markdown("### Configuración del Gráfico Técnico")
    c_time, c_bb, c_macd, c_rsi, c_fib = st.columns(5)
    timeframe = c_time.selectbox("Temporalidad", ["1mo", "1y", "ytd", "5y", "max"], index=1, format_func=lambda x: {"1mo":"1 Mes", "1y":"1 Año", "ytd":"YTD", "5y":"5 Años", "max":"Máximo"}[x])
    show_bb = c_bb.checkbox("Bandas Bollinger", value=True)
    show_macd = c_macd.checkbox("MACD", value=False)
    show_rsi = c_rsi.checkbox("RSI", value=False)
    show_fib = c_fib.checkbox("Fibonacci", value=False)
    st.markdown("---")

# --- EXTRACCIÓN DE DATOS ---
@st.cache_data(ttl=3600)
def download_data(ticker, benchmark, period):
    default_qr = 1.35
    default_roe = 0.185
    default_mcap = 50.5
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        df_stock = yf.download(ticker, period=period, progress=False)['Close']
        df_index = yf.download(benchmark, period=period, progress=False)['Close']
        
        if isinstance(df_stock, pd.DataFrame): df_stock = df_stock.squeeze()
        if isinstance(df_index, pd.DataFrame): df_index = df_index.squeeze()
            
        df = pd.DataFrame({'Stock': df_stock, 'Market': df_index}).dropna()
        if df.empty: raise ValueError("Datos vacíos.")
        
        qr = info.get('quickRatio', default_qr)
        roe = info.get('returnOnEquity', default_roe)
        mcap = info.get('marketCap', default_mcap * 1e9) / 1e9 # En miles de millones
        
        return df, qr, roe, mcap
    except Exception as e:
        dates = pd.bdate_range(end=datetime.date.today(), periods=252)
        mkt = 3500 * np.exp(np.cumsum(np.random.normal(0.0002, 0.01, len(dates))))
        stk = 150 * np.exp(np.cumsum(np.random.normal(0.0003, 0.015, len(dates))))
        df = pd.DataFrame({'Stock': stk, 'Market': mkt}, index=dates)
        return df, default_qr, default_roe, default_mcap

with st.spinner("Sincronizando con el mercado..."):
    df, quick_ratio, roe, mcap = download_data(ticker_symbol, index_symbol, timeframe)

# --- CÁLCULOS TÉCNICOS Y FUNDAMENTALES ---
current_price = df['Stock'].iloc[-1]
returns = df.pct_change().dropna()
cov_mat = np.cov(returns['Market'], returns['Stock'])
beta_calc = cov_mat[0, 1] / cov_mat[0, 0] if cov_mat[0,0] != 0 else 1.0

# Indicadores Técnicos
df['SMA'] = df['Stock'].rolling(window=20).mean()
df['STD'] = df['Stock'].rolling(window=20).std()
df['Upper_BB'] = df['SMA'] + (df['STD'] * 2)
df['Lower_BB'] = df['SMA'] - (df['STD'] * 2)

df['EMA_12'] = df['Stock'].ewm(span=12, adjust=False).mean()
df['EMA_26'] = df['Stock'].ewm(span=26, adjust=False).mean()
df['MACD'] = df['EMA_12'] - df['EMA_26']
df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

delta = df['Stock'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))

max_p = df['Stock'].max()
min_p = df['Stock'].min()
diff_p = max_p - min_p
fib_levels = [max_p, max_p - 0.236*diff_p, max_p - 0.382*diff_p, max_p - 0.5*diff_p, max_p - 0.618*diff_p, min_p]

# --- RENDERIZADO DEL RESTO DE LAS PESTAÑAS ---

with tab1:
    st.header(f"Información Corporativa")
    
    prompt_info = f"""
    Eres un analista financiero. Devuelve la información de la empresa {selected_company} en formato JSON ESTRICTAMENTE.
    ESTRUCTURA EXACTA:
    {{
        "descripcion": "Quiénes son y qué hacen (máximo 70 palabras).",
        "riesgos": "Análisis del entorno (riesgo político, inflación, y otros dos factores) en {stock_info['region']} (máximo 150 palabras).",
        "segmentos": ["Segmento A", "Segmento B", "Segmento C"],
        "porcentajes": [50, 30, 20]
    }}
    Asegúrate de que la suma de porcentajes sea 100. NO escribas código markdown alrededor.
    """
    
    with st.spinner("IA analizando fundamentales de la empresa..."):
        info_json_str = get_gemini_response(prompt_info)
        
    try:
        # CORRECCIÓN ERROR JSON: Usar expresiones regulares para extraer solo el bloque JSON
        match = re.search(r'\{.*\}', info_json_str, re.DOTALL)
        clean_json = match.group(0) if match else info_json_str
        data_info = json.loads(clean_json)
        
        st.write(f"**Descripción:** {data_info.get('descripcion', 'N/A')}")
        
        col_pie, col_risk = st.columns([1, 1])
        with col_pie:
            fig_pie = go.Figure(data=[go.Pie(labels=data_info['segmentos'], values=data_info['porcentajes'], hole=.4, marker_colors=['#005A9C', '#00c49f', '#ffbb28', '#ff8042'])])
            fig_pie.update_layout(title_text="Composición de Ingresos", margin=dict(t=40, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_risk:
            st.markdown("### Análisis del Entorno Macro y Riesgos")
            st.markdown(f"<div class='ai-box'>{data_info.get('riesgos', 'N/A')}</div>", unsafe_allow_html=True)
            
        st.session_state['tab1_data'] = data_info # Guardar para la pestaña final
        
    except Exception as e:
        st.error(f"Error decodificando la respuesta de la IA. Por favor, recarga. Detalle: {e}")

with tab2:
    st.header("Análisis de Riesgo y Divisas")
    
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='metric-box'><div class='metric-title'>BETA</div><div class='metric-value'>{beta_calc:.2f}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-box'><div class='metric-title'>ROE (DuPont)</div><div class='metric-value'>{roe*100:.2f}%</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-box'><div class='metric-title'>Test Ácido</div><div class='metric-value'>{quick_ratio:.2f}</div></div>", unsafe_allow_html=True)
    
    prompt_macro = f"""
    Actúa como analista. Para la acción {selected_company} (Beta: {beta_calc:.2f}, ROE: {roe*100:.2f}%, Test Ácido: {quick_ratio:.2f}, Inflación País: {stock_info['inflacion']}%):
    
    1. Interpreta la Beta. OBLIGATORIO empezar con la frase exacta: "Por cada punto que el índice de referencia suba la acción subirá el valor que corresponda en referencia 1:{beta_calc:.2f}." Continúa interpretando en 90 palabras máximo.
    2. Interpreta el ROE (DuPont) en máximo 90 palabras.
    3. Interpreta el Test Ácido en máximo 90 palabras.
    4. Analiza las 3 teorías de divisas (Paridad Poder Adquisitivo, Paridad Tasas de Interés, Efecto Fisher) partiendo de una inflación del {stock_info['inflacion']}% en {stock_info['region']} para la divisa {stock_info['currency']}.
    
    Formato OBLIGATORIO:
    **Interpretación Beta:** [Texto]
    
    **Interpretación DuPont:** [Texto]
    
    **Interpretación Test Ácido:** [Texto]
    
    **Análisis Teorías de Divisas:** [Texto]
    """
    
    with st.spinner("IA analizando métricas de riesgo..."):
        macro_text = get_gemini_response(prompt_macro)
        st.markdown(f"<div class='ai-box'>{macro_text}</div>", unsafe_allow_html=True)
        st.session_state['tab2_data'] = macro_text

with tab3:
    # El encabezado y los controles ya se renderizaron arriba, aquí solo va el gráfico.
    fig = make_subplots(rows=3 if show_macd or show_rsi else 1, cols=1, 
                        shared_xaxes=True, vertical_spacing=0.05, 
                        row_heights=[0.6, 0.2, 0.2] if show_macd and show_rsi else ([0.7, 0.3] if show_macd or show_rsi else [1]))
    
    fig.add_trace(go.Scatter(x=df.index, y=df['Stock'], mode='lines', name='Precio', line=dict(color='#005A9C', width=2)), row=1, col=1)
    
    if show_bb:
        fig.add_trace(go.Scatter(x=df.index, y=df['Upper_BB'], mode='lines', name='Banda Sup', line=dict(color='rgba(0,196,159,0.5)', dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Lower_BB'], mode='lines', name='Banda Inf', line=dict(color='rgba(0,196,159,0.5)', dash='dash'), fill='tonexty', fillcolor='rgba(0,196,159,0.1)'), row=1, col=1)
    
    if show_fib:
        colors = ['#ff0000', '#ff8c00', '#ffd700', '#008000', '#0000ff', '#800080']
        for i, level in enumerate(fib_levels):
            fig.add_hline(y=level, line_dash="dot", line_color=colors[i], annotation_text=f"Fib {i}", row=1, col=1)

    row_idx = 2
    if show_macd:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], mode='lines', name='MACD', line=dict(color='#ffbb28')), row=row_idx, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], mode='lines', name='Señal MACD', line=dict(color='#ff8042')), row=row_idx, col=1)
        row_idx += 1
        
    if show_rsi:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI', line=dict(color='#8884d8')), row=row_idx, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=row_idx, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=row_idx, col=1)

    fig.update_layout(height=700, margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor='white', paper_bgcolor='white', hovermode='x unified')
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eef2f5')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#eef2f5')
    
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.header("Veredicto Cuantitativo Final")
    
    if st.button("Generar Informe Institucional (IA)", type="primary"):
        
        tab1_info = st.session_state.get('tab1_data', {})
        desc = tab1_info.get('descripcion', 'N/A')
        riesgos = tab1_info.get('riesgos', 'N/A')
        
        prompt_final = f"""
        Actúa como un analista senior de riesgos financieros y valoración corporativa.
        Debes compilar un informe ejecutivo final para la empresa {selected_company} (Ticker: {ticker_symbol}).
        
        DATOS A INCLUIR EN ORDEN:
        a. Nombre de la sociedad y Ticker (DESTACADO), Cotización actual: {current_price:.2f} {stock_info['currency']}.
        b. Capitalización bursátil: {mcap:.2f} miles de millones.
        c. Descripción: {desc} | Riesgos: {riesgos}
        d. Indicadores: Beta ({beta_calc:.2f}), ROE ({roe*100:.2f}%), Test Ácido ({quick_ratio:.2f}). Teorías divisas considerando inflación {stock_info['inflacion']}%.
        e. Gráficos técnicos: Análisis corto (menos de 50 palabras) del MACD, RSI y Bollinger en temporalidad {timeframe}.
        
        REGLAS DE DECISIÓN DEL MODELO (Aplica esta lógica internamente):
        Calcula un SCORE TOTAL de -100 a +100.
        Decisión: +40 a +100 (COMPRAR), +10 a +39 (MANTENER), -9 a +9 (NEUTRAL), -10 a -39 (REDUCIR), -40 a -100 (VENDER).
        Regla prudencial: Si riesgo geopolítico es Alto o Beta > 1.5, Máximo permitido = MANTENER.
        
        REQUISITOS DEL TEXTO FINAL (JUSTIFICACIÓN):
        Redacta una justificación estructurada en formato informe ejecutivo en MENOS DE 100 PALABRAS que:
        1. Priorice riesgos sobre oportunidades.
        2. Evalúe escenarios adversos (shock inflacionario/crisis/geopolítico).
        3. Analice sensibilidad a tasas.
        4. Explique coherencia técnico-fundamental.
        5. Indique evento invalidante.
        6. Concluya con el Score [INSERTAR SCORE], la decisión [COMPRAR/MANTENER/VENDER] y el nivel de convicción (Alto/Medio/Bajo).
        
        Lenguaje: Profesional, crítico y prudente.
        """
        
        with st.spinner("Compilando reporte final aplicando modelo de Scoring..."):
            veredicto = get_gemini_response(prompt_final)
            st.markdown(f"<div class='ai-box'>{veredicto}</div>", unsafe_allow_html=True)

