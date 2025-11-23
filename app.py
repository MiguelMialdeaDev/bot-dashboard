#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Web para Gestión de Bots
"""
from flask import Flask, render_template, jsonify, request
import subprocess
import psutil
import os
import json
from datetime import datetime
import sqlite3

app = Flask(__name__)

# Configuración de rutas
CRYPTO_BOT_PATH = r"C:\Users\Nicole\crypto-trading-bot"
WALLAPOP_BOT_PATH = r"C:\Users\Nicole\wallapop-bot"

# Almacenar PIDs de procesos
bot_processes = {
    "crypto": None,
    "wallapop": None
}


def find_bot_process(bot_name):
    """Busca el proceso de un bot por nombre de script y directorio"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and 'python' in proc.info['name'].lower():
                    cmdline_str = ' '.join(cmdline)
                    if 'start_continuous.py' in cmdline_str:
                        # Obtener el directorio de trabajo del proceso
                        try:
                            cwd = proc.cwd()
                            if bot_name == "crypto" and "crypto-trading-bot" in cwd:
                                return proc.info['pid']
                            elif bot_name == "wallapop" and "wallapop-bot" in cwd:
                                return proc.info['pid']
                        except (psutil.AccessDenied, AttributeError):
                            # Si no podemos obtener cwd, intentar buscar en cmdline
                            if bot_name == "crypto" and "crypto-trading-bot" in cmdline_str:
                                return proc.info['pid']
                            elif bot_name == "wallapop" and "wallapop-bot" in cmdline_str:
                                return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except:
        pass
    return None


def is_process_running(pid):
    """Verifica si un proceso está corriendo"""
    if pid is None:
        return False
    try:
        process = psutil.Process(pid)
        return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def get_bot_status(bot_name):
    """Obtiene el estado de un bot"""
    # Primero intentar con el PID guardado
    pid = bot_processes.get(bot_name)

    # Si no hay PID guardado o el proceso no está corriendo, buscar automáticamente
    if not is_process_running(pid):
        pid = find_bot_process(bot_name)
        if pid:
            bot_processes[bot_name] = pid

    running = is_process_running(pid)

    status = {
        "name": bot_name,
        "running": running,
        "pid": pid if running else None,
        "uptime": None,
        "memory": None
    }

    if running:
        try:
            process = psutil.Process(pid)
            status["uptime"] = int((datetime.now().timestamp() - process.create_time()))
            status["memory"] = process.memory_info().rss / 1024 / 1024  # MB
        except:
            pass

    return status


def get_crypto_stats():
    """Obtiene estadísticas del bot de crypto"""
    try:
        portfolio_file = os.path.join(CRYPTO_BOT_PATH, "data", "portfolio.json")
        if os.path.exists(portfolio_file):
            with open(portfolio_file, 'r') as f:
                data = json.load(f)
                return {
                    "balance": data.get("balance", 0),
                    "positions": len(data.get("positions", {})),
                    "total_trades": len(data.get("history", []))
                }
    except:
        pass
    return {"balance": 0, "positions": 0, "total_trades": 0}


def get_wallapop_stats():
    """Obtiene estadísticas del bot de wallapop"""
    try:
        db_file = os.path.join(WALLAPOP_BOT_PATH, "data", "gangas.db")
        if os.path.exists(db_file):
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            # Total gangas
            cursor.execute("SELECT COUNT(*) FROM gangas")
            total_gangas = cursor.fetchone()[0]

            # Gangas hoy
            cursor.execute("""
                SELECT COUNT(*) FROM gangas
                WHERE date(found_at) = date('now')
            """)
            gangas_hoy = cursor.fetchone()[0]

            conn.close()
            return {
                "total_gangas": total_gangas,
                "gangas_hoy": gangas_hoy
            }
    except:
        pass
    return {"total_gangas": 0, "gangas_hoy": 0}


def get_logs(bot_name, lines=50):
    """Obtiene últimas líneas de log"""
    try:
        if bot_name == "crypto":
            log_file = os.path.join(CRYPTO_BOT_PATH, "logs", "bot.log")
        else:
            log_file = os.path.join(WALLAPOP_BOT_PATH, "logs", "bot.log")

        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
    except:
        pass
    return "No hay logs disponibles"


@app.route('/')
def index():
    """Página principal del dashboard"""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """API: Estado de todos los bots"""
    crypto_status = get_bot_status("crypto")
    wallapop_status = get_bot_status("wallapop")

    crypto_stats = get_crypto_stats()
    wallapop_stats = get_wallapop_stats()

    return jsonify({
        "bots": {
            "crypto": {
                **crypto_status,
                "stats": crypto_stats
            },
            "wallapop": {
                **wallapop_status,
                "stats": wallapop_stats
            }
        },
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/start/<bot_name>', methods=['POST'])
def api_start(bot_name):
    """API: Iniciar un bot"""
    if bot_name not in ["crypto", "wallapop"]:
        return jsonify({"error": "Bot inválido"}), 400

    # Verificar si ya está corriendo
    if is_process_running(bot_processes.get(bot_name)):
        return jsonify({"error": "El bot ya está corriendo"}), 400

    try:
        if bot_name == "crypto":
            cwd = CRYPTO_BOT_PATH
        else:
            cwd = WALLAPOP_BOT_PATH

        # Verificar que el directorio existe
        if not os.path.exists(cwd):
            return jsonify({"error": f"Directorio no encontrado: {cwd}"}), 500

        # Iniciar proceso en background
        process = subprocess.Popen(
            ["python", "-u", "start_continuous.py"],
            cwd=os.path.abspath(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )

        bot_processes[bot_name] = process.pid

        return jsonify({
            "success": True,
            "pid": process.pid,
            "message": f"Bot {bot_name} iniciado"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/stop/<bot_name>', methods=['POST'])
def api_stop(bot_name):
    """API: Detener un bot"""
    if bot_name not in ["crypto", "wallapop"]:
        return jsonify({"error": "Bot inválido"}), 400

    pid = bot_processes.get(bot_name)
    if not is_process_running(pid):
        return jsonify({"error": "El bot no está corriendo"}), 400

    try:
        process = psutil.Process(pid)
        process.terminate()
        process.wait(timeout=10)
        bot_processes[bot_name] = None

        return jsonify({
            "success": True,
            "message": f"Bot {bot_name} detenido"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/logs/<bot_name>')
def api_logs(bot_name):
    """API: Obtener logs de un bot"""
    if bot_name not in ["crypto", "wallapop"]:
        return jsonify({"error": "Bot inválido"}), 400

    lines = request.args.get('lines', 50, type=int)
    logs = get_logs(bot_name, lines)

    return jsonify({
        "bot": bot_name,
        "logs": logs
    })


if __name__ == '__main__':
    import sys
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

    print("🚀 Iniciando Dashboard de Bots...")
    print("📍 http://localhost:5000")
    print("Presiona Ctrl+C para detener\n")

    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port)
