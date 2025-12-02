#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
modulo_ingesta_v5.py — Versión estable y limpia
------------------------------------------------
- Intenta JSON (API v7)
- Si no funciona → HTML fallback (fin-streamer + JSON embebido)
- Si no funciona → snapshot
- Compatible con obtener_datos_reales()
- Incluye modo debug (--debug-html)
- Maneja correctamente respuestas gzip (JSON + HTML)
"""

from __future__ import annotations

import json
import sys
import time
import re
import gzip
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import parse, request, error as urlerror


# =============================
# CONFIG
# =============================

TICKERS_POR_DEFECTO = ["SMR", "URA", "URNM", "XLU", "^TNX", "^VIX"]

YF_JSON_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
YF_HTML_URL = "https://finance.yahoo.com/quote"

SNAPSHOT_PATH = Path(__file__).with_name("ultimo_snapshot_v5.json")

HTTP_TIMEOUT = 8
RETRIES = 2
RETRY_SLEEP = 2


# =============================
# TIPOS
# =============================

class IngestaError(Exception):
    pass


@dataclass
class QuoteData:
    symbol: str
    price: Optional[float]
    change_pct: Optional[float]
    volume: Optional[int]
    currency: Optional[str]
    as_of: Optional[int]
    source: str


# =============================
# UTILIDAD HTTP (gzip-safe)
# =============================

def decode_http_body(content: bytes, headers: Dict[str, Any]) -> str:
    """
    Decodifica el cuerpo HTTP:
    - Si viene como gzip → lo descomprime.
    - Si no, intenta decodificar como UTF-8 ignorando errores.
    Robustez extra: aunque el header no diga gzip, si los primeros bytes
    tienen la firma de gzip, intenta descomprimir igualmente.
    """
    encoding = (headers.get("Content-Encoding") or "").lower()

    # Caso 1: el servidor indica gzip
    if "gzip" in encoding:
        try:
            return gzip.decompress(content).decode("utf-8", errors="ignore")
        except Exception:
            # Si falla la descompresión, seguimos probando con decode directo
            pass

    # Caso 2: no indica gzip pero la firma es de gzip
    if content[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(content).decode("utf-8", errors="ignore")
        except Exception:
            pass

    # Caso 3: texto plano (o algo que al menos decodifica)
    return content.decode("utf-8", errors="ignore")


# =============================
# RED — JSON
# =============================

def fetch_json(symbols: List[str]) -> Dict[str, Any]:
    query = parse.urlencode({"symbols": ",".join(symbols)})
    url = f"{YF_JSON_URL}?{query}"

    last_exc = None

    for _ in range(RETRIES):
        try:
            req = request.Request(
                url,
                headers={
                    "User-Agent": "SynapseV5-Termux",
                    "Accept-Encoding": "gzip, deflate, br",
                },
            )
            with request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                if resp.status != 200:
                    raise IngestaError(f"HTTP {resp.status}")
                text = decode_http_body(resp.read(), resp.headers)
                return json.loads(text)
        except Exception as e:
            last_exc = e
            time.sleep(RETRY_SLEEP)

    raise IngestaError(f"JSON fallo: {last_exc}")


def parse_json(raw: Dict[str, Any]) -> Dict[str, QuoteData]:
    results = raw.get("quoteResponse", {}).get("result", [])
    if not results:
        raise IngestaError("JSON sin resultados")

    out: Dict[str, QuoteData] = {}
    for item in results:
        sym = item.get("symbol")
        if not sym:
            continue

        out[sym] = QuoteData(
            symbol=sym,
            price=item.get("regularMarketPrice"),
            change_pct=item.get("regularMarketChangePercent"),
            volume=item.get("regularMarketVolume"),
            currency=item.get("currency"),
            as_of=item.get("regularMarketTime"),
            source="live_json",
        )

    return out


# =============================
# RED — HTML
# =============================

def fetch_html(symbol: str) -> str:
    url = f"{YF_HTML_URL}/{parse.quote(symbol)}"
    last_exc = None

    for _ in range(RETRIES):
        try:
            req = request.Request(
                url,
                headers={
                    "User-Agent": "SynapseV5-Termux",
                    "Accept-Encoding": "gzip, deflate, br",
                },
            )
            with request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                if resp.status != 200:
                    raise IngestaError(f"HTTP {resp.status}")
                text = decode_http_body(resp.read(), resp.headers)
                return text
        except Exception as e:
            last_exc = e
            time.sleep(RETRY_SLEEP)

    raise IngestaError(f"HTML fallo: {last_exc}")


def extract_float(pat: str, html: str) -> Optional[float]:
    m = re.search(pat, html)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def extract_int(pat: str, html: str) -> Optional[int]:
    m = re.search(pat, html)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def parse_html(sym: str, html: str) -> QuoteData:
    esc = re.escape(sym)

    # 1) fin-streamer
    price = extract_float(
        rf'data-symbol="{esc}".+?data-field="regularMarketPrice".+?value="([0-9eE.\-]+)"',
        html,
    )
    chg = extract_float(
        rf'data-symbol="{esc}".+?data-field="regularMarketChangePercent".+?value="([0-9eE.\-]+)"',
        html,
    )
    vol = extract_int(
        rf'data-symbol="{esc}".+?data-field="regularMarketVolume".+?value="([0-9]+)"',
        html,
    )

    # 2) JSON embebido
    if price is None:
        price = extract_float(
            r'"regularMarketPrice"\s*:\s*{\s*"raw":\s*([0-9eE.\-]+)', html
        )
    if chg is None:
        chg = extract_float(
            r'"regularMarketChangePercent"\s*:\s*{\s*"raw":\s*([0-9eE.\-]+)', html
        )
    if vol is None:
        vol = extract_int(r'"regularMarketVolume"\s*:\s*([0-9]+)', html)

    curr = None
    m_c = re.search(r'"currency"\s*:\s*"([A-Z]{3})"', html)
    if m_c:
        curr = m_c.group(1)

    as_of = extract_int(r'"regularMarketTime"\s*:\s*([0-9]+)', html)

    return QuoteData(
        symbol=sym,
        price=price,
        change_pct=chg,
        volume=vol,
        currency=curr,
        as_of=as_of,
        source="live_html",
    )


def fetch_html_quotes(symbols: List[str]) -> Dict[str, QuoteData]:
    out: Dict[str, QuoteData] = {}
    for sym in symbols:
        html = fetch_html(sym)
        out[sym] = parse_html(sym, html)
    return out


# =============================
# SNAPSHOT
# =============================

def save_snapshot(quotes: Dict[str, QuoteData]):
    SNAPSHOT_PATH.write_text(
        json.dumps({k: asdict(v) for k, v in quotes.items()}, indent=2)
    )


def load_snapshot() -> Optional[Dict[str, QuoteData]]:
    if not SNAPSHOT_PATH.exists():
        return None
    try:
        raw = json.loads(SNAPSHOT_PATH.read_text())
        out: Dict[str, QuoteData] = {}
        for sym, q in raw.items():
            out[sym] = QuoteData(
                symbol=sym,
                price=q.get("price"),
                change_pct=q.get("change_pct"),
                volume=q.get("volume"),
                currency=q.get("currency"),
                as_of=q.get("as_of"),
                source="snapshot",
            )
        return out
    except Exception:
        return None


# =============================
# CONTEXTO LLM
# =============================

def fmt_vol(v):
    if v is None:
        return "N/A"
    if v > 1_000_000:
        return f"{v/1_000_000:.2f}M"
    if v > 1000:
        return f"{v/1000:.2f}K"
    return str(v)


def generate_context(quotes: Dict[str, QuoteData], fuente: str) -> str:
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    out: List[str] = [
        "[Synapse V5 — Datos de mercado]",
        f"Fuente: {fuente}",
        f"Timestamp: {ts}",
        "",
    ]

    for sym, q in quotes.items():
        out.append(
            f"{sym}: "
            f"{q.price if q.price is not None else 'N/A'} "
            f"(Δ {q.change_pct if q.change_pct is not None else 'N/A'} %, "
            f"Vol {fmt_vol(q.volume)}, src {q.source})"
        )

    return "\n".join(out)


# =============================
# API PUBLICA
# =============================

def obtener_datos_detallados(symbols=None):
    if symbols is None:
        symbols = TICKERS_POR_DEFECTO

    # JSON
    try:
        raw = fetch_json(symbols)
        quotes = parse_json(raw)
        save_snapshot(quotes)
        fuente = "live_json"
    except Exception:
        # HTML
        try:
            quotes = fetch_html_quotes(symbols)
            save_snapshot(quotes)
            fuente = "live_html"
        except Exception:
            snap = load_snapshot()
            if not snap:
                raise IngestaError("Sin JSON, sin HTML y sin snapshot")
            quotes = snap
            fuente = "snapshot"

    return generate_context(quotes, fuente), quotes, {"fuente": fuente}


def obtener_datos_reales() -> str:
    ctx, _, _ = obtener_datos_detallados()
    return ctx


# =============================
# DEBUG
# =============================

def debug_html(sym: str):
    html = fetch_html(sym)
    path = Path(f"debug_{sym}.html")
    path.write_text(html, encoding="utf-8")
    print(f"Debug HTML guardado en {path}")


# =============================
# MAIN
# =============================

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--debug-html":
        sym = sys.argv[2] if len(sys.argv) > 2 else "SMR"
        debug_html(sym)
        sys.exit(0)

    try:
        ctx, quotes, meta = obtener_datos_detallados()
        print(ctx)
    except Exception as e:
        sys.stderr.write(f"ERROR: {e}\n")
        sys.exit(1)
