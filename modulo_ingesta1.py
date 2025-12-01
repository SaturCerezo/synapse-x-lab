#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import random
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

import requests
import feedparser
from urllib.parse import quote

SNAPSHOT_FILE = "ultimo_snapshot.json"

TICKERS = [
    "SMR",
    "URA",
    "URNM",
    "XLU",
    "^TNX",
    "^VIX"
]

RSS_FEEDS = [
    "https://world-nuclear-news.org/Feeds/All-news"
]


@dataclass
class SnapshotMercado:
    timestamp: str
    usando_cache: bool

    smr_price: float
    smr_change_pct: float
    smr_volume: int

    ura_price: float
    ura_change_pct: float

    urnm_price: float
    urnm_change_pct: float

    xlu_price: float
    xlu_change_pct: float

    tnx_yield: float
    vix_value: float

    rss_titulares: List[str]


def fetch_with_retry(url: str, params=None, max_reintentos=3, timeout=8):
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 11; SynapseBot/5.6)"
    }
    backoff = 1.5

    for intento in range(1, max_reintentos + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout, headers=headers)

            if resp.status_code == 429:
                print("⛔ 429 Too Many Requests")
                raise requests.HTTPError("429 Too Many Requests")

            resp.raise_for_status()
            return resp

        except (requests.ConnectionError, requests.Timeout):
            print(f"🌐 Reintento {intento}/{max_reintentos}")
            if intento == max_reintentos:
                raise
            time.sleep(backoff ** intento + random.uniform(0, 0.5))

        except requests.HTTPError as e:
            print(f"⚠️ HTTP Error: {e}")
            raise


def _extraer_campo_embebido(html: str, campo: str, entero: bool = False):
    pattern = f'"{campo}":{{"raw":'
    i = html.find(pattern)
    if i == -1:
        return None

    j = i + len(pattern)
    k = j

    while k < len(html) and html[k] not in ",}":
        k += 1

    valor = html[j:k].strip()

    try:
        if entero:
            return int(float(valor))
        return float(valor)
    except:
        return None


def obtener_cotizaciones_yahoo_html(tickers: List[str]) -> Dict[str, Dict[str, Any]]:
    resultados = {}

    for sym in tickers:
        encoded = quote(sym, safe="")
        url = f"https://finance.yahoo.com/quote/{encoded}"

        print(f"🌐 Leyendo {sym} ...")
        resp = fetch_with_retry(url)
        html = resp.text

        price = _extraer_campo_embebido(html, "regularMarketPrice")
        change_pct = _extraer_campo_embebido(html, "regularMarketChangePercent")
        vol = _extraer_campo_embebido(html, "regularMarketVolume", entero=True)

        resultados[sym] = {
            "price": price or 0.0,
            "change_pct": change_pct or 0.0,
            "volume": vol or 0
        }

    return resultados


def obtener_titulares_rss(max_items=3):
    titulares = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_items]:
                if "title" in entry:
                    titulares.append(entry["title"])
        except:
            pass
    return titulares[:max_items]


def guardar_snapshot(snapshot: SnapshotMercado):
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(asdict(snapshot), f, ensure_ascii=False, indent=2)
    print("💾 Snapshot guardado.")


def cargar_snapshot():
    if not os.path.exists(SNAPSHOT_FILE):
        return None
    try:
        with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        print("♻️ Usando snapshot local.")
        return SnapshotMercado(**data)
    except:
        return None


def formatear_contexto_llm(s: SnapshotMercado):
    origen = "DATOS EN VIVO" if not s.usando_cache else "DATOS RECICLADOS"
    return (
        f"[{origen} @ {s.timestamp}]\n"
        f"SMR: {s.smr_price:.2f} ({s.smr_change_pct:+.2f}%) Vol: {s.smr_volume}\n"
        f"URA: {s.ura_price:.2f} ({s.ura_change_pct:+.2f}%)\n"
        f"URNM: {s.urnm_price:.2f} ({s.urnm_change_pct:+.2f}%)\n"
        f"XLU: {s.xlu_price:.2f} ({s.xlu_change_pct:+.2f}%)\n"
        f"TNX: {s.tnx_yield:.2f}\n"
        f"VIX: {s.vix_value:.2f}\n\n"
        f"[Titulares]\n" + "\n".join("- " + t for t in s.rss_titulares)
    )


def obtener_datos_reales():
    from datetime import datetime

    try:
        data = obtener_cotizaciones_yahoo_html(TICKERS)
        rss = obtener_titulares_rss()

        snap = SnapshotMercado(
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            usando_cache=False,
            smr_price=data["SMR"]["price"],
            smr_change_pct=data["SMR"]["change_pct"],
            smr_volume=data["SMR"]["volume"],
            ura_price=data["URA"]["price"],
            ura_change_pct=data["URA"]["change_pct"],
            urnm_price=data["URNM"]["price"],
            urnm_change_pct=data["URNM"]["change_pct"],
            xlu_price=data["XLU"]["price"],
            xlu_change_pct=data["XLU"]["change_pct"],
            tnx_yield=data["^TNX"]["price"],
            vix_value=data["^VIX"]["price"],
            rss_titulares=rss
        )

        guardar_snapshot(snap)
        return formatear_contexto_llm(snap)

    except Exception as e:
        print("🔥 Error en ingesta:", e)
        snap = cargar_snapshot()
        if snap:
            snap.usando_cache = True
            return formatear_contexto_llm(snap)
        return "Error: no se pudo obtener datos ni snapshot."


def crear_snapshot_demo():
    from datetime import datetime
    snap = SnapshotMercado(
        timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        usando_cache=True,
        smr_price=5,
        smr_change_pct=1.5,
        smr_volume=200000,
        ura_price=23,
        ura_change_pct=-0.5,
        urnm_price=30,
        urnm_change_pct=1.1,
        xlu_price=65,
        xlu_change_pct=-0.2,
        tnx_yield=4.5,
        vix_value=16,
        rss_titulares=["DEMO NOTICIA 1", "DEMO NOTICIA 2"]
    )
    guardar_snapshot(snap)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        crear_snapshot_demo()
    else:
        print("🔍 Probando obtener_datos_reales...\n")
        print(obtener_datos_reales())
