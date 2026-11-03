"""Calculadora IPv4."""

from flask import Flask, jsonify, render_template, request

from ipv4_calculator import IPv4InputError, calculate_ipv4

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "calculadora-ipv4"})


@app.post("/api/calculate")
def api_calculate():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"success": False, "error": "El cuerpo de la solicitud debe ser un objeto JSON."}), 400

    try:
        result = calculate_ipv4(
            cidr=payload.get("cidr"),
            ip=payload.get("ip"),
            prefix=payload.get("prefix"),
            mask=payload.get("mask"),
        )
        return jsonify({"success": True, "results": result})
    except IPv4InputError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception:
        app.logger.exception("Error inesperado al calcular la dirección IPv4")
        return jsonify({
            "success": False,
            "error": "Ocurrió un error interno al procesar la dirección. Verifique los datos e intente nuevamente.",
        }), 500


if __name__ == "__main__":
    # Servidor local de desarrollo
    app.run(host="127.0.0.1", port=5000, debug=True)
