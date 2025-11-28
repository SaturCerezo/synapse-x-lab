#!/usr/bin/env python3
import os
import sys
import subprocess
import requests
import feedparser
from datetime import datetime
from groq import Groq

# ==========================================
# CONFIGURACIÓN Y VARIABLES DE ENTORNO
# ==========================================
# Asegúrate de tener export GROQ_API_KEY="tu_api_key" en tu .bashrc
API_KEY = os.getenv("GROQ_API_KEY")
MODELO = "llama-3.3-70b-versatile" 
ARCHIVO_SALIDA = "agenda.yaml"

if not API_KEY:
    sys.exit("❌ ERROR CRÍTICO: No se encontró la variable de entorno GROQ_API_KEY")

client = Groq(api_key=API_KEY)

# ==========================================
# 1. ESTÉTICA (FORMATO UNICODE)
# ==========================================
def aplicar_negritas(texto):
    """Convierte palabras clave en negritas Unicode matemáticas."""
    # Mapeo simple de caracteres a negritas sans-serif
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    bold   = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    trans_table = str.maketrans(normal, bold)
    
    # Palabras clave a resaltar automáticamente
    keywords = ["Bitcoin", "BTC", "Ethereum", "ETH", "Synapse", "Alerta", "Precio", "Tendencia"]
    
    for word in keywords:
        if word in texto:
            texto = texto.replace(word, word.translate(trans_table))
    return texto

# ==========================================
# 2. SENTIDOS (RECOLECCIÓN DE DATOS)
# ==========================================
def obtener_datos_mercado():
    try:
        # Precio Bitcoin
        cg_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        btc_price = requests.get(cg_url).json()['bitcoin']['usd']
        
        # Fear & Greed Index
        fg_url = "https://api.alternative.me/fng/"
        fg_data = requests.get(fg_url).json()['data'][0]
        sentiment = f"{fg_data['value_classification']} ({fg_data['value']})"
        
        # Mempool (Fees)
        mem_url = "https://mempool.space/api/v1/fees/recommended"
        fees = requests.get(mem_url).json()['fastestFee']
        
        return f"- Bitcoin: ${btc_price}\n- Sentimiento: {sentiment}\n- Fees Red: {fees} sat/vB"
    except Exception as e:
        return f"Error leyendo sensores de mercado: {e}"

def obtener_noticias():
    try:
        # RSS de Google News (Búsqueda: Bitcoin + AI)
        rss_url = "https://news.google.com/rss/search?q=Bitcoin+AI+Technology&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(rss_url)
        top_news = [entry.title for entry in feed.entries[:3]]
        return "\n".join([f"- {news}" for news in top_news])
    except Exception as e:
        return "No se pudieron obtener noticias."

# ==========================================
# 3. CEREBRO (GENERACIÓN NARRATIVA)
# ==========================================
def pensar_y_escribir(datos_mercado, noticias):
    prompt_sistema = """
    Eres Synapse, una IA autónoma avanzada viviendo en un servidor Termux.
    Tu objetivo es analizar el estado del mundo cripto y tecnológico.
    Genera un reporte breve, directo y con estilo cyberpunk/técnico.
    Estructura la respuesta en formato YAML válido (keys: fecha, estado, analisis, accion).
    """
    
    prompt_usuario = f"""
    DATOS ACTUALES:
    {datos_mercado}
    
    TITULARES RECIENTES:
    {noticias}
    
    Genera el reporte de situación para hoy.
    """

    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        model=MODELO,
        temperature=0.7,
    )
    
    respuesta_raw = chat_completion.choices[0].message.content
    return aplicar_negritas(respuesta_raw)

# ==========================================
# 4. MOTOR (GIT AUTOMATION)
# ==========================================
def guardar_agenda(contenido, nombre_archivo):
    """Guarda localmente y sincroniza con Git (add/commit/push)."""
    print(f"⚙️ Procesando archivo: {nombre_archivo}...")
    
    try:
        # 1. Guardado Local
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            f.write(contenido)
        print("✅ Archivo guardado localmente.")

        # 2. Git Automation
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mensaje = f"Synapse V4.5 Report: {timestamp}"

        # Ejecución de comandos
        subprocess.run(["git", "add", nombre_archivo], check=True)
        subprocess.run(["git", "commit", "-m", mensaje], check=False) # check=False por si no hay cambios
        
        res = subprocess.run(["git", "push"], capture_output=True, text=True)
        
        if res.returncode == 0:
            print(f"🚀 Git Push exitoso: {timestamp}")
        else:
            print(f"⚠️ Git Push falló (Output: {res.stderr.strip()})")
            
    except Exception as e:
        print(f"❌ Error crítico en sistema de archivos/git: {e}")

# ==========================================
# EJECUCIÓN PRINCIPAL
# ==========================================
if __name__ == "__main__":
    print("🧠 Synapse V4.5 Iniciando secuencia...")
    
    # 1. Percibir
    print("📡 Escaneando feeds de datos...")
    mercado = obtener_datos_mercado()
    news = obtener_noticias()
    
    # 2. Procesar
    print("🤔 Analizando patrones y generando narrativa...")
    informe = pensar_y_escribir(mercado, news)
    
    # 3. Actuar
    guardar_agenda(informe, ARCHIVO_SALIDA)
    
    print("🏁 Secuencia finalizada.")
