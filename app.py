import logging
import random
import time

from flask import Flask, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

REQUETES = Counter("app_requetes_total", "Nombre de requetes", ["route", "code"])
ERREURS = Counter("app_erreurs_total", "Nombre d'erreurs (code >= 500)", ["route"])
LATENCE = Histogram("app_latence_secondes", "Duree des requetes", ["route"])


@app.before_request
def debut():
    request._debut = time.time()


@app.after_request
def comptage(response):
    if request.path in ("/metrics", "/webhook-alerte"):
        return response
    route = request.url_rule.rule if request.url_rule else "inconnue"
    REQUETES.labels(route=route, code=response.status_code).inc()
    LATENCE.labels(route=route).observe(time.time() - request._debut)
    if response.status_code >= 500:
        ERREURS.labels(route=route).inc()
    return response


@app.errorhandler(Exception)
def exception_non_geree(e):
    # Les 404, 405... gardent leur code HTTP d'origine
    if hasattr(e, "code") and e.code and e.code < 500:
        return jsonify(erreur=str(e)), e.code
    app.logger.exception("Exception non geree")
    return jsonify(erreur="Erreur interne"), 500


@app.route("/")
def accueil():
    app.logger.info("Requete sur /")
    return "Bonjour, application supervisee !"


@app.route("/erreur")
def erreur():
    app.logger.error("Une erreur simulee s'est produite")
    return "Erreur simulee", 500


@app.route("/aleatoire")
def aleatoire():
    # /aleatoire?taux=30  ->  30% de chances d'echouer (defaut 30)
    taux = float(request.args.get("taux", 30))
    if random.random() * 100 < taux:
        app.logger.error("Echec aleatoire (taux=%s%%)", taux)
        return "Echec aleatoire", 500
    return "OK"


@app.route("/lent")
def lent():
    # /lent?max=2  ->  delai aleatoire entre 0 et 2 secondes
    time.sleep(random.uniform(0, float(request.args.get("max", 2))))
    return "Reponse lente"


@app.route("/exception")
def exception():
    return 1 / 0  # ZeroDivisionError -> capturee par errorhandler -> 500


@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.route("/webhook-alerte", methods=["POST"])
def webhook_alerte():
    data = request.get_json(silent=True) or {}
    for alert in data.get("alerts", []):
        labels = alert.get("labels", {})
        app.logger.warning(
            "NOTIFICATION GRAFANA [%s] %s",
            alert.get("status"),
            labels.get("alertname"),
        )
    return "", 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)