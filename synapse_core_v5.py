#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
synapse_core_v5.py — Núcleo Synapse con sanity checks de datos

- Usa modulo_ingesta_v5.obtener_datos_detallados()
- Evalúa si los sensores (datos de mercado) son fiables
- Si NO son fiables: no llama a Groq ni publica en X
- Si SÍ son fiables: genera contexto, llama a Groq y (opcional) publica en X

NOTA:
- La parte de Groq y Tweepy está en modo plantilla. Adapta los detalles
  usando el código que ya tienes en synapse_core.py (V4.7).
"""

from __future__ import annotations

import os
import sys
import time
from typing import Dict, Any, List, Tuple

# Módulo de ingesta V5 (el nuevo)
from modulo_ingesta_v5 import obtener_datos_detallados, QuoteData, IngestaError

# Si ya tienes tweepy y requests en V4.7, los puedes reusar:
# import tweepy
# import requests


# =====================================
# 1) Sanity checks de datos de mercado
# =====================================

def evaluar_sensores(quotes: Dict[str, QuoteData]) -> Dict[str, Any]:
    """
    Aplica reglas sencillas para decidir si los datos son fiables.

    Devuelve:
    {
        "ok": bool,
        "motivos": [str, ...],
        "resumen": str
    }
    """
    motivos: List[str] = []
    total = len(quotes)
    rotos = 0
    na_total = 0

    for sym, q in quotes.items():
        local_issues: List[str] = []

        # 1) Falta de precio
        if q.price is None:
            na_total += 1
            local_issues.append("precio ausente")

        # 2) Rango básico por tipo de activo
        if q.price is not None:
            if q.price <= 0:
                local_issues.append(f"precio no positivo ({q.price})")

            if sym == "SMR":
                # SMR acción pequeña
                if q.price > 500:
                    local_issues.append(f"precio SMR fuera de rango ({q.price})")
            elif sym in ("URA", "URNM", "XLU"):
                # ETFs
                if q.price > 1000:
                    local_issues.append(f"precio ETF fuera de rango ({q.price})")
            elif sym in ("^VIX", "^TNX"):
                # Índices/ratios, damos más margen pero cortamos por arriba
                if q.price > 100_000:
                    local_issues.append(f"precio índice desproporcionado ({q.price})")

        # 3) Volumen negativo
        if q.volume is not None and q.volume < 0:
            local_issues.append(f"volumen negativo ({q.volume})")

        if local_issues:
            rotos += 1
            motivos.append(f"{sym}: " + "; ".join(local_issues))

    # Regla global: si todos están sin precio -> KO directo
    if na_total == total:
        motivos.append("todos los tickers tienen precio ausente (N/A)")

    # Si más de la mitad tienen problemas -> KO
    if rotos > total / 2:
        motivos.append(
            f"{rotos}/{total} tickers presentan anomalías (umbral > 50%)"
        )

    ok = not motivos

    resumen = "OK: sensores estables"
    if not ok:
        resumen = f"KO: datos sospechosos ({len(motivos)} incidencias)"

    return {
        "ok": ok,
        "motivos": motivos,
        "resumen": resumen,
    }


# =====================================
# 2) Groq: plantilla de llamada
# =====================================

def llamar_groq(contexto_mercado: str) -> str:
    """
    Plantilla de llamada a Groq para generar el tweet.

    Adapta esta función usando el código de synapse_core.py (V4.7),
    donde ya tienes:
    - GROQ_API_KEY
    - Modelo a usar
    - Prompt base para el tweet cínico sobre SMR, URA, etc.

    De momento la dejo como stub que devuelve un texto fijo
    para probar el flujo sin gastar tokens.
    """
    # TODO: copiar aquí tu lógica real de llamada a Groq.
    # Ejemplo mínimo (falso) para pruebas:
    tweet_falso = (
        "Synapse V5: sensores OK pero Groq está en modo stub. "
        "Esta es una prueba sin publicación real."
    )
    return tweet_falso


# =====================================
# 3) Publicación en X (plantilla)
# =====================================

def publicar_en_x(tweet: str) -> None:
    """
    Plantilla para publicar en X usando Tweepy.
    Adapta con tus claves ya configuradas en V4.7.

    Si quieres, durante las pruebas puedes dejarla como no-op
    (solo imprimir en consola).
    """
    # Ejemplo no-op:
    print("\n=== [Simulación] Publicaría en X el siguiente tweet ===")
    print(tweet)
    print("=== [Fin simulación X] ===\n")

    # TODO: copiar aquí tu lógica real con Tweepy.


# =====================================
# 4) Flujo principal de Synapse V5
# =====================================

def ejecutar_sesion_synapse_v5() -> int:
    """
    Flujo completo:
    1) Ingesta V5
    2) Sanity checks
    3) Si KO: registrar evento y terminar sin Groq ni X
    4) Si OK: Groq + (opcional) X
    """
    print("[Synapse V5] Iniciando sesión...")

    # 1) Ingesta
    try:
        contexto, quotes, meta = obtener_datos_detallados()
    except IngestaError as e:
        sys.stderr.write(f"[Synapse V5] ERROR de ingesta: {e}\n")
        return 1

    print("[Synapse V5] Contexto de mercado:\n")
    print(contexto)

    # 2) Evaluar sensores
    eval_sensores = evaluar_sensores(quotes)
    print("\n[Synapse V5] Estado de sensores:", eval_sensores["resumen"])
    if eval_sensores["motivos"]:
        print("Detalles:")
        for m in eval_sensores["motivos"]:
            print("  -", m)

    if not eval_sensores["ok"]:
        # Aquí puedes:
        # - Guardar en YAML un evento tipo "datos corruptos"
        # - Hacer solo logging / debug
        print("\n[Synapse V5] Sesión marcada como NO FIABLE. "
              "No se llamará a Groq ni se publicará en X.")
        return 0

    # 3) Sensores OK -> llamada a Groq
    print("\n[Synapse V5] Sensores OK. Llamando a Groq...")
    tweet = llamar_groq(contexto_mercado=contexto)

    # 4) Publicación (de momento simulada)
    publicar_en_x(tweet)

    print("[Synapse V5] Sesión completada.")
    return 0


# =====================================
# 5) Main
# =====================================

if __name__ == "__main__":
    codigo = ejecutar_sesion_synapse_v5()
    sys.exit(codigo)
