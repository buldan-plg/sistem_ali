import subprocess
import tempfile
import os

TIMEOUT = 5  # detik


def run_code(language, code):
    """Jalankan kode berdasarkan bahasa yang dipilih."""
    runners = {
        "php":        run_php,
        "javascript": run_js,
        "python":     run_python,
    }

    runner = runners.get(language)
    if not runner:
        return f"❌ Bahasa '{language}' tidak didukung. Pilih: php, javascript, python."

    return runner(code)


# ─────────────────────────────────────────
def run_php(code):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".php", mode="w", encoding="utf-8") as f:
        f.write(code)
        filename = f.name

    try:
        result = subprocess.run(
            ["php", filename],
            capture_output=True, text=True, timeout=TIMEOUT
        )
        output = result.stdout or result.stderr
    except subprocess.TimeoutExpired:
        output = "⏱️ Waktu eksekusi habis! (Timeout)"
    except FileNotFoundError:
        output = "❌ PHP tidak terinstall di server."
    finally:
        os.remove(filename)

    return output.rstrip()


# ─────────────────────────────────────────
def run_js(code):
    try:
        result = subprocess.run(
            ["node", "-e", code],
            capture_output=True, text=True, timeout=TIMEOUT
        )
        output = result.stdout or result.stderr
    except subprocess.TimeoutExpired:
        output = "⏱️ Waktu eksekusi habis! (Timeout)"
    except FileNotFoundError:
        output = "❌ Node.js tidak terinstall di server."

    return output.rstrip()


# ─────────────────────────────────────────
def run_python(code):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode="w", encoding="utf-8") as f:
        f.write(code)
        filename = f.name

    try:
        result = subprocess.run(
            ["python", filename],
            capture_output=True, text=True, timeout=TIMEOUT
        )
        output = result.stdout or result.stderr
    except subprocess.TimeoutExpired:
        output = "⏱️ Waktu eksekusi habis! (Timeout)"
    except FileNotFoundError:
        output = "❌ Python3 tidak terinstall di server."
    finally:
        os.remove(filename)

    return output.rstrip()