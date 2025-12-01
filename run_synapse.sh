#!/data/data/com.termux/files/usr/bin/bash
# run_synapse.sh — Lanza un ciclo de Synapse con wake-lock controlado

cd /data/data/com.termux/files/home/synapse-x-lab || exit 1

termux-wake-lock

/usr/bin/env python3 synapse_core.py >> synapse.log 2>&1

termux-wake-unlock
