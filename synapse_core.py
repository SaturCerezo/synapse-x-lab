#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PROYECTO: Synapse V4.7 (Financial Core + Ingesta V5.6)
PLATAFORMA: Termux (Android)
DESCRIPCIÓN:
  Agente autónomo que:
    - Lee el mercado real (Yahoo HTML scraper + RSS) vía modulo_ingesta1.
    - Analiza con Groq (Llama 3.3 70B).
    - Guarda el análisis en YAML.
    - Publica en X (Twitter).
    - Hace backup automático con Git.
"""

import os
import sys
import yaml
import datetime
import subprocess
from typing import Optional

import tweepy
from groq import Groq

# --- IMPORT DE INGESTA (El Ojo que todo lo ve, HTML scraper + caché) ---
try:
    from modulo_ingesta1 import obtener_datos_reales
except ImportError:
    print("⚠️ ADVERTENCIA: No se encontró modulo_ingesta1.py. Usando modo simulación.")

    def obtener_datos_reales():
        return "Error: Módulo de datos no encontrado."


# --- CONFIGURACIÓN Y CONSTANTES ---
ARCHIVO_LOG = "agenda.yaml"
MODELO_IA = "llama-3.3-70b-versatile"  # Modelo Groq actual para análisis


# --- 0. VALIDACIÓN BÁSICA DE ENTORNO ---

def validar_entorno():
    """
    Comprueba que existan las variables de entorno críticas.
    Si falta algo, salimos pronto para no gastar llamadas a APIs.
    """
    errores = []

    if not os.getenv("GROQ_API_KEY"):
        errores.append("GROQ_API_KEY")

    x_vars = [
        "X_API_KEY",
        "X_API_SECRET",
        "X_ACCESS_TOKEN",
        "X_ACCESS_SECRET",
    ]
    faltan_x = [v for v in x_vars if not os.getenv(v)]
    if faltan_x:
        errores.extend(faltan_x)

    if errores:
        print("❌ ERROR: Faltan variables de entorno críticas:")
        for v in errores:
            print(f"   - {v}")
        print("   Revisa tu ~/.bashrc o ~/.profile en Termux.")
        sys.exit(1)


# --- 1. MÓDULO DE INTELIGENCIA (GROQ) ---

def generar_informe_ia(contexto_mercado: str) -> Optional[str]:
    """
    Llama a Groq para generar el tweet-análisis.
    Si algo falla (API key, modelo, red…), devuelve None.
    """
    print(">> 🧠 Synapse procesando datos de mercado con Llama-3...")
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        print("❌ ERROR: No se detectó GROQ_API_KEY.")
        return None

    system_prompt = (
        "Eres Synapse, una IA de análisis financiero de élite. "
        "TU ESTILO: Cínico, directo, basado en datos (Data-Driven). "
        "TU MISIÓN: Analizar el reporte de mercado que recibes. "
        "REGLAS: "
        "1. Si el volumen (Actividad) es alto, menciónalo como 'entrada de ballenas'. "
        "2. Compara el precio real con los titulares de las noticias (busca contradicciones). "
        "3. Usa emojis técnicos (☢️, 📉, 📈, 🏛️). "
        "4. NO uses hashtags genéricos. Usa tickers como $SMR o $URA. "
        "5. IMPORTANTE: Tu respuesta debe tener MENOS DE 280 CARACTERES."
    )

    try:
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "DATOS EN TIEMPO REAL O SNAPSHOT:\n"
                        f"{contexto_mercado}\n\n"
                        "Analiza y escribe el tweet (<= 280 caracteres):"
                    ),
                },
            ],
            model=MODELO_IA,
            temperature=0.6,
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Error en Groq: {e}")
        return None


# --- 2. MÓDULO DE MEMORIA (YAML) ---

def guardar_log_yaml(informe: str) -> None:
    """
    Añade una entrada al log YAML (agenda.yaml) con timestamp e informe.
    """
    print(">> 💾 Archivando análisis en agenda.yaml...")
    entrada = {
        "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "evento": "Análisis Mercado V4.7",
        "contenido": informe,
    }

    try:
        if not os.path.exists(ARCHIVO_LOG):
            with open(ARCHIVO_LOG, "w", encoding="utf-8") as f:
                yaml.dump([], f)

        with open(ARCHIVO_LOG, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []

        data.append(entrada)
        with open(ARCHIVO_LOG, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    except Exception as e:
        print(f"⚠️ Error guardando YAML: {e}")


# --- 3. MÓDULO DE DIFUSIÓN (TWITTER/X API V2) ---

def publicar_en_x(texto_informe: str) -> None:
    """
    Publica el informe en X (Twitter) usando la API v2 de Tweepy.
    """
    print("\n>> 🐦 Conectando con Neural Link (Twitter X)...")

    ck = os.getenv("X_API_KEY")
    cs = os.getenv("X_API_SECRET")
    at = os.getenv("X_ACCESS_TOKEN")
    ats = os.getenv("X_ACCESS_SECRET")

    if not all([ck, cs, at, ats]):
        print("❌ ERROR CRÍTICO: Faltan credenciales X_API_* en variables de entorno.")
        return

    try:
        client = tweepy.Client(
            consumer_key=ck,
            consumer_secret=cs,
            access_token=at,
            access_token_secret=ats,
        )

        tweet = texto_informe.replace('"', "").replace("'", "")

        if len(tweet) > 280:
            print(f"✂️ Recortando tweet ({len(tweet)} chars)...")
            tweet = tweet[:275] + "..."

        response = client.create_tweet(text=tweet)
        print(f"✅ TWEET ENVIADO. ID: {response.data['id']}")
        print(f"📜 Contenido: {tweet}")

    except tweepy.errors.Forbidden:
        print("❌ Error 403: Tu App de Twitter no tiene permisos de ESCRITURA (Write).")
    except Exception as e:
        print(f"⚠️ Error publicando en Twitter: {e}")


# --- 4. MÓDULO DE PERSISTENCIA (GIT) ---

def git_push_automatico() -> None:
    """
    Hace git add/commit/push solo si hay cambios pendientes.
    Evita ruido y errores cuando no hay nada nuevo.
    """
    print("\n>> 🚀 Sincronizando memoria con la Nube (Git)...")
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        if not status.stdout.strip():
            print("ℹ️ Sin cambios en el repo. No hay nada que commitear/pushear.")
            return

        subprocess.run(["git", "add", "."], check=True)
        mensaje = f"Synapse V4.7 Data Update {datetime.datetime.now().strftime('%H:%M')}"
        subprocess.run(["git", "commit", "-m", mensaje], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ Git Push completado.")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Error en Git: {e}")


# --- ORQUESTADOR PRINCIPAL ---

def main():
    print("--- ☢️ INICIANDO SYNAPSE V4.7 (FINANCIAL CORE) ---")

    # 0. Validar entorno
    validar_entorno()

    # 1. OBTENER DATOS REALES
    try:
        datos_mercado = obtener_datos_reales()
    except Exception as e:
        print(f"🔥 Error crítico leyendo mercado: {e}")
        datos_mercado = "Error de sensores. Mercado desconocido."

    # 2. PROCESAR CON IA
    informe_final = generar_informe_ia(datos_mercado)

    if informe_final is None:
        print("\n🧾 Synapse no ha podido generar informe (fallo en Groq).")
        guardar_log_yaml("Error: no se pudo generar informe (Groq).")
        # No publicar en X si falla la IA
    else:
        print("\n🧾 Informe generado por Synapse:")
        print(informe_final)

        guardar_log_yaml(informe_final)
        publicar_en_x(informe_final)

    # 3. BACKUP GIT
    git_push_automatico()

    print("\n--- ✅ PROTOCOLO FINALIZADO ---")


if __name__ == "__main__":
    main()

