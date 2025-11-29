#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PROYECTO: Synapse V4.6 (Módulo Social & Difusión)
PLATAFORMA: Termux (Android)
ARQUITECTO: Gemini AI
DESCRIPCIÓN: Agente autónomo que genera informes con Groq (Llama-3),
             los guarda en YAML, hace backup en GitHub y publica en X (Twitter).
"""

import os
import sys
import yaml
import datetime
import subprocess
import tweepy
from groq import Groq

# --- CONFIGURACIÓN Y CONSTANTES ---
ARCHIVO_LOG = "agenda.yaml"
MODELO_IA = "llama3-8b-8192" # Modelo rápido y eficiente para Termux

# --- 1. MÓDULO DE DATOS (INPUT) ---
def obtener_datos_entorno():
    """
    Simula la recolección de datos (Aquí iría tu scraper de noticias/crypto).
    Para esta versión V4.6, generamos datos de tiempo real para probar el flujo.
    """
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # AQUÍ PUEDES CONECTAR TU LÓGICA DE NOTICIAS REAL
    datos = f"Reporte de sistema Synapse. Hora: {ahora}. Estado: ACTIVO. Mercado: Monitoreando tendencias."
    return datos

# --- 2. MÓDULO DE INTELIGENCIA (GROQ) ---
def generar_informe_ia(contexto):
    print(">> 🧠 Consultando a Groq (Llama-3)...")
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("❌ ERROR: No se detectó GROQ_API_KEY.")
        return "Error: Sin API Key de Groq."

    try:
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Eres Synapse, un agente IA avanzado. Genera un reporte BREVE, técnico y futurista (Cyberpunk style) basado en los datos. Máximo 250 caracteres para caber en Twitter."
                },
                {
                    "role": "user",
                    "content": f"Datos del sistema: {contexto}",
                }
            ],
            model=MODELO_IA,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"❌ Error en Groq: {e}")
        return f"Error generando informe: {e}"

# --- 3. MÓDULO DE MEMORIA (YAML) ---
def guardar_log_yaml(informe):
    print(">> 💾 Guardando en agenda.yaml...")
    entrada = {
        "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "evento": "Informe Diario V4.6",
        "contenido": informe
    }
    
    try:
        # Si no existe, crea una lista vacía
        if not os.path.exists(ARCHIVO_LOG):
            with open(ARCHIVO_LOG, 'w') as f:
                yaml.dump([], f)

        # Leer contenido actual
        with open(ARCHIVO_LOG, 'r') as f:
            data = yaml.safe_load(f) or []

        # Añadir nueva entrada y guardar
        data.append(entrada)
        with open(ARCHIVO_LOG, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            
    except Exception as e:
        print(f"⚠️ Error guardando YAML: {e}")

# --- 4. MÓDULO DE DIFUSIÓN (TWITTER/X API V2) ---
def publicar_en_x(texto_informe):
    print("\n>> 🐦 Iniciando protocolo de difusión en X...")
    
    # Recuperar claves del entorno (.bashrc)
    ck = os.getenv("X_API_KEY")
    cs = os.getenv("X_API_SECRET")
    at = os.getenv("X_ACCESS_TOKEN")
    ats = os.getenv("X_ACCESS_SECRET")

    # Verificación de integridad
    if not all([ck, cs, at, ats]):
        print("❌ ERROR CRÍTICO: Faltan credenciales de Twitter en variables de entorno.")
        return

    try:
        # Autenticación Cliente V2
        client = tweepy.Client(
            consumer_key=ck,
            consumer_secret=cs,
            access_token=at,
            access_token_secret=ats
        )
        
        # Lógica de recorte de seguridad (Hard limit 280 chars)
        tweet = texto_informe
        if len(tweet) > 280:
            print(f"✂️ Recortando tweet ({len(tweet)} chars)...")
            tweet = texto_informe[:275] + "..."
            
        # Publicación
        response = client.create_tweet(text=tweet)
        print(f"✅ TWEET PUBLICADO. ID: {response.data['id']}")
        
    except tweepy.errors.Forbidden as e:
        print(f"❌ Error 403 (Permisos): Revisa que tu App tenga WRITE en Twitter Dev.")
    except Exception as e:
        print(f"⚠️ Error general en Twitter: {e}")

# --- 5. MÓDULO DE PERSISTENCIA (GIT) ---
def git_push_automatico():
    print("\n>> 🚀 Iniciando Git Push...")
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"Synapse Auto-Update {datetime.datetime.now()}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ Git Push completado.")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Error en Git: {e}")

# --- ORQUESTADOR PRINCIPAL ---
def main():
    print("--- 🤖 INICIANDO SYNAPSE V4.6 ---")
    
    # 1. Obtener Datos
    datos = obtener_datos_entorno()
    
    # 2. Generar Informe con IA
    informe = generar_informe_ia(datos)
    print(f"\n📄 Informe Generado:\n{informe}\n")
    
    # 3. Guardar en Log Local
    guardar_log_yaml(informe)
    
    # 4. Publicar en Redes (NUEVO)
    publicar_en_x(informe)
    
    # 5. Backup en Nube
    git_push_automatico()
    
    print("\n--- ✅ CICLO TERMINADO ---")

if __name__ == "__main__":
    main()
