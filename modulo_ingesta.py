import requests
import feedparser
import json
import time

# --- CONFIGURACIÓN ---
TIMEOUT_SEC = 20
# Simulamos ser un Chrome de Windows legítimo para que Yahoo nos abra la puerta
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Origin': 'https://finance.yahoo.com',
    'Referer': 'https://finance.yahoo.com/'
}

def obtener_datos_manuales(ticker):
    """
    Petición 'artesanal' al endpoint de gráficos (v8).
    Es el endpoint más robusto y difícil de bloquear.
    Calculamos manualmente si hay Ballenas (Volumen).
    """
    # Pedimos 5 días de historia para calcular el promedio de volumen
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
    
    try:
        # Pausa táctica para no saturar
        time.sleep(1)
        
        session = requests.Session()
        response = session.get(url, headers=HEADERS, timeout=TIMEOUT_SEC)
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        
        # 1. Extracción de Precios
        result = data['chart']['result'][0]
        meta = result['meta']
        precio_actual = meta['regularMarketPrice']
        precio_previo = meta['chartPreviousClose']
        cambio_pct = ((precio_actual - precio_previo) / precio_previo) * 100
        
        # 2. Cálculo Manual de Ballenas (Volumen)
        # Extraemos el array de volúmenes
        volumenes = result['indicators']['quote'][0]['volume']
        # Filtramos posibles valores None
        volumenes = [v for v in volumenes if v is not None]
        
        actividad = "NORMAL"
        if len(volumenes) >= 2:
            vol_hoy = volumenes[-1]
            # Calculamos la media de los días anteriores (sin contar hoy)
            vol_anteriores = volumenes[:-1]
            media_vol = sum(vol_anteriores) / len(vol_anteriores) if vol_anteriores else vol_hoy
            
            # Lógica: Si el volumen de hoy supera en 50% al promedio -> Ballenas
            if vol_hoy > (media_vol * 1.5):
                actividad = "🐳 ALTA (Acumulación Institucional)"
            elif vol_hoy < (media_vol * 0.5):
                actividad = "❄️ BAJA (Sin interés)"
                
        return {
            "precio": precio_actual,
            "pct": cambio_pct,
            "volumen": actividad
        }
        
    except Exception as e:
        # print(f"DEBUG: Error en {ticker}: {e}") # Descomentar para depurar
        return None

def generar_tablero_manual():
    """Itera sobre los activos usando la función manual"""
    activos = {
        "SMR": "☢️ NuScale",
        "^TNX": "🏛️ Bonos USA 10Y",
        "JPY=X": "💴 USD/JPY",
        "URA": "🪨 ETF Uranio"
    }
    
    reporte = []
    print("... Accediendo a Yahoo (Modo Manual V5.5) ...")
    
    for symbol, nombre in activos.items():
        datos = obtener_datos_manuales(symbol)
        
        if datos:
            flecha = "🟢" if datos['pct'] >= 0 else "🔴"
            linea = f"{flecha} {nombre}: ${datos['precio']:.2f} ({datos['pct']:+.2f}%)"
            
            # Solo para SMR mostramos el volumen
            if symbol == "SMR":
                linea += f"\n   ↳ ACTIVIDAD: {datos['volumen']}"
            
            # Alertas Macro
            if symbol == "^TNX" and datos['precio'] > 4.5:
                linea += " (⚠️ ALERTA: Deuda cara)"
                
            reporte.append(linea)
        else:
            reporte.append(f"⚠️ {nombre}: (Bloqueo o Sin Datos)")
            
    return "\n".join(reporte)

def obtener_noticias_google():
    """RSS Google (Micro y Macro)"""
    queries = [
        ("SMR/Nuclear", "NuScale+SMR+stock+news"),
        ("Fed/Macro", "Federal+Reserve+rates+decision")
    ]
    news_report = []
    for label, q in queries:
        try:
            url = f"https://news.google.com/rss/search?q={q}+when:2d&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(url)
            if feed.entries:
                news_report.append(f"📰 {label}: {feed.entries[0].title}")
        except: pass
    return "\n".join(news_report) if news_report else "(Sin noticias)"

def obtener_reddit_resiliente():
    """Reddit Simple"""
    headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)'}
    url = "https://www.reddit.com/search.json?q=NuScale+SMR+stock&sort=new&limit=3"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            posts = r.json()['data']['children']
            validos = [f"- r/{p['data']['subreddit']}: {p['data']['title']}" for p in posts][:2]
            return "\n".join(validos)
    except: pass
    return "(Reddit Silencioso)"

def obtener_datos_reales():
    """FACADE V5.5 MANUAL OVERRIDE"""
    tablero = generar_tablero_manual()
    noticias = obtener_noticias_google()
    social = obtener_reddit_resiliente()
    
    return (
        f"=== INFORME V5.5 (MANUAL) ===\n"
        f"{tablero}\n"
        f"=============================\n"
        f"🔮 CONTEXTO:\n{noticias}\n"
        f"=============================\n"
        f"🗣️ REDDIT:\n{social}"
    )

if __name__ == "__main__":
    print(obtener_datos_reales())
