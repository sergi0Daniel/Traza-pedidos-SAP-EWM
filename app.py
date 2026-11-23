"""TRAZA+ - seguimiento de pedidos de grifería dentro del centro de distribución.

Modo predeterminado: demostración con registros de ejemplo claramente identificados.
La conexión con SAP EWM solo se activa con endpoints y credenciales autorizados por TI.
La aplicación realiza consultas de lectura; no modifica pedidos ni ejecuta tareas en SAP.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from services.ewm_connector import EWMConnector, EWMConfigurationError, EWMConnectionError
from services.ai_service import AIService, AIConfigurationError, AIServiceError

load_dotenv()

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024
app.logger.setLevel(logging.INFO)

LOCK = RLock()
EWM = EWMConnector.from_environment()
AI = AIService.from_environment()

# Los umbrales de demostración solo ilustran la interfaz. Operaciones debe aprobar
# y configurar los límites reales antes de activar alertas sobre datos productivos.
DEMO_THRESHOLDS = {
    "Picking": 90,
    "Empaque": 105,
    "Zona de despacho": 90,
    "Cargue": 75,
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(value: datetime) -> str:
    return value.isoformat()


def make_demo_order(
    order_id: str,
    stage: str,
    elapsed_minutes: int,
    item_rows: list[dict[str, Any]],
    hu_rows: list[dict[str, Any]],
    events_spec: list[tuple[int, str, str, str]],
    location: str,
    client: str,
    delivery_id: str,
) -> dict[str, Any]:
    now = utc_now()
    stage_started = now - timedelta(minutes=elapsed_minutes)
    created = now - timedelta(minutes=max(elapsed_minutes + 120, 180))
    events = []
    for offset_minutes, label, event_stage, event_location in events_spec:
        event_time = created + timedelta(minutes=offset_minutes)
        events.append({
            "event_time": iso(event_time),
            "event": label,
            "stage": event_stage,
            "location": event_location,
            "status": "Registrado",
            "source": "DEMO",
        })
    events.append({
        "event_time": iso(stage_started),
        "event": f"Ingreso a etapa: {stage}",
        "stage": stage,
        "location": location,
        "status": "En proceso",
        "source": "DEMO",
    })
    events.sort(key=lambda x: x["event_time"])
    return {
        "order_id": order_id,
        "delivery_id": delivery_id,
        "client": client,
        "created_at": iso(created),
        "status": "Listo para cargue" if stage == "Puerta de embarque" else "En proceso",
        "stage": stage,
        "stage_started_at": iso(stage_started),
        "stage_elapsed_minutes": elapsed_minutes,
        "location": location,
        "priority": "Normal",
        "items": item_rows,
        "handling_units": hu_rows,
        "events": events,
        "data_origin": "Datos de demostración",
    }


def build_demo_orders() -> list[dict[str, Any]]:
    refs = [
        {"reference": "REF. 799860001", "description": "Grifería para lavamanos", "quantity": 2, "unit": "UN"},
        {"reference": "REF. O24380001", "description": "Grifería para ducha", "quantity": 1, "unit": "UN"},
    ]
    return [
        make_demo_order(
            "PD-45873", "Empaque", 165, refs,
            [
                {"hu_id": "HU-DEMO-87321", "location": "EM-01", "status": "En empaque", "contents": "REF. 799860001 · 2 UN"},
                {"hu_id": "HU-DEMO-87322", "location": "EM-02", "status": "En empaque", "contents": "REF. O24380001 · 1 UN"},
            ],
            [(0, "Pedido registrado", "Pedido registrado", "Recepción de pedidos"),
             (35, "Picking iniciado", "Picking", "PK-03"),
             (75, "Picking confirmado", "Picking finalizado", "PK-03")],
            "Estación de empaque EM-01", "Cliente de demostración A", "ENT-DEMO-45873",
        ),
        make_demo_order(
            "PD-45874", "Picking", 72,
            [{"reference": "REF. 799860001", "description": "Grifería para lavamanos", "quantity": 4, "unit": "UN"}],
            [{"hu_id": "HU-DEMO-87411", "location": "PK-03", "status": "Pendiente de empaque", "contents": "4 unidades"}],
            [(0, "Pedido registrado", "Pedido registrado", "Recepción de pedidos"),
             (30, "Picking iniciado", "Picking", "PK-03")],
            "Zona de picking PK-03", "Cliente de demostración B", "ENT-DEMO-45874",
        ),
        make_demo_order(
            "PD-45798", "Zona de despacho", 130,
            [{"reference": "REF. O24380001", "description": "Grifería para ducha", "quantity": 3, "unit": "UN"}],
            [{"hu_id": "HU-DEMO-79811", "location": "ST-02", "status": "En espera de cargue", "contents": "3 unidades"}],
            [(0, "Pedido registrado", "Pedido registrado", "Recepción de pedidos"),
             (25, "Picking confirmado", "Picking finalizado", "PK-01"),
             (60, "Empaque confirmado", "Empaque finalizado", "EM-02"),
             (85, "Traslado a staging", "Zona de despacho", "ST-02")],
            "Zona de despacho ST-02", "Cliente de demostración C", "ENT-DEMO-45798",
        ),
        make_demo_order(
            "PD-45795", "Cargue", 65,
            [{"reference": "REF. 799860001", "description": "Grifería para lavamanos", "quantity": 1, "unit": "UN"}],
            [{"hu_id": "HU-DEMO-79501", "location": "PU-03", "status": "En cargue", "contents": "1 unidad"}],
            [(0, "Pedido registrado", "Pedido registrado", "Recepción de pedidos"),
             (25, "Picking confirmado", "Picking finalizado", "PK-02"),
             (45, "Empaque confirmado", "Empaque finalizado", "EM-01"),
             (55, "Ingreso a zona de despacho", "Zona de despacho", "ST-01"),
             (60, "Puerta asignada", "Puerta de embarque", "PU-03")],
            "Puerta de embarque PU-03", "Cliente de demostración D", "ENT-DEMO-45795",
        ),
        make_demo_order(
            "PD-45763", "Empaque", 125,
            [{"reference": "REF. 799860001", "description": "Grifería para lavamanos", "quantity": 2, "unit": "UN"},
             {"reference": "REF. O24380001", "description": "Grifería para ducha", "quantity": 2, "unit": "UN"}],
            [{"hu_id": "HU-DEMO-76301", "location": "EM-02", "status": "En empaque", "contents": "2 unidades"}],
            [(0, "Pedido registrado", "Pedido registrado", "Recepción de pedidos"),
             (40, "Picking iniciado", "Picking", "PK-04"),
             (70, "Picking confirmado", "Picking finalizado", "PK-04")],
            "Estación de empaque EM-02", "Cliente de demostración E", "ENT-DEMO-45763",
        ),
    ]


DEMO_ORDERS = build_demo_orders()
LIVE_ORDERS: list[dict[str, Any]] = []
LIVE_LAST_SYNC: str | None = None
LIVE_ERROR: str | None = None


def is_live_mode() -> bool:
    return EWM.enabled


def current_orders() -> list[dict[str, Any]]:
    if is_live_mode():
        with LOCK:
            return [dict(order) for order in LIVE_ORDERS]
    return [dict(order) for order in DEMO_ORDERS]


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def elapsed_minutes(order: dict[str, Any]) -> int | None:
    start = parse_time(order.get("stage_started_at"))
    if not start:
        return None
    return max(0, int((utc_now() - start).total_seconds() // 60))


def thresholds() -> dict[str, int] | None:
    if not is_live_mode():
        return DEMO_THRESHOLDS
    raw = {
        "Picking": os.getenv("SLA_PICKING_MINUTES", "").strip(),
        "Empaque": os.getenv("SLA_EMPAQUE_MINUTES", "").strip(),
        "Zona de despacho": os.getenv("SLA_STAGING_MINUTES", "").strip(),
        "Cargue": os.getenv("SLA_LOADING_MINUTES", "").strip(),
    }
    if not any(raw.values()):
        return None
    try:
        return {k: int(v) for k, v in raw.items() if v}
    except ValueError:
        return None


def order_alert(order: dict[str, Any], limits: dict[str, int] | None) -> dict[str, Any] | None:
    if not limits:
        return None
    stage = order.get("stage", "")
    limit = limits.get(stage)
    elapsed = elapsed_minutes(order)
    if limit is None or elapsed is None or elapsed <= limit:
        return None
    return {
        "order_id": order.get("order_id"),
        "stage": stage,
        "location": order.get("location") or "Sin ubicación informada",
        "elapsed_minutes": elapsed,
        "limit_minutes": limit,
        "overdue_minutes": elapsed - limit,
        "level": "Demora",
        "note": "El tiempo registrado supera el límite configurado; requiere revisión operativa.",
    }


def all_alerts(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    limits = thresholds()
    if not limits:
        return []
    alerts = [alert for order in orders if (alert := order_alert(order, limits))]
    return sorted(alerts, key=lambda x: x["overdue_minutes"], reverse=True)


def summary(orders: list[dict[str, Any]]) -> dict[str, Any]:
    stage_names = ["Picking", "Empaque", "Zona de despacho", "Puerta de embarque", "Cargue", "Despachado"]
    stage_counts = {stage: 0 for stage in stage_names}
    for order in orders:
        stage = order.get("stage") or "Sin etapa"
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
    active = sum(1 for o in orders if o.get("stage") != "Despachado")
    shipped = sum(1 for o in orders if o.get("stage") == "Despachado")
    alerts = all_alerts(orders)
    durations = [elapsed_minutes(o) for o in orders if elapsed_minutes(o) is not None]
    return {
        "total_orders": len(orders),
        "active_orders": active,
        "shipped_orders": shipped,
        "delayed_orders": len(alerts),
        "loading_orders": sum(1 for o in orders if o.get("stage") in ("Cargue", "Puerta de embarque")),
        "stage_counts": stage_counts,
        "average_stage_minutes": round(sum(durations) / len(durations)) if durations else None,
        "alerts_configured": thresholds() is not None,
        "data_mode": "SAP EWM" if is_live_mode() else "Demostración",
        "last_sync": LIVE_LAST_SYNC if is_live_mode() else None,
        "warning": LIVE_ERROR if is_live_mode() else "Los registros visibles son de demostración y no provienen de SAP EWM.",
    }


def ai_context(orders: list[dict[str, Any]]) -> dict[str, Any]:
    """Minimiza los campos enviados al servicio IA; no incluye clientes ni nombres."""
    limits = thresholds()
    rows = []
    for o in orders:
        rows.append({
            "pedido": o.get("order_id"),
            "etapa": o.get("stage"),
            "estado": o.get("status"),
            "ubicacion_registrada": o.get("location"),
            "minutos_en_etapa": elapsed_minutes(o),
            "productos": [
                {"referencia": x.get("reference"), "cantidad": x.get("quantity")}
                for x in o.get("items", [])
            ],
            "eventos": [
                {"fecha_hora": e.get("event_time"), "evento": e.get("event"), "etapa": e.get("stage"), "ubicacion": e.get("location")}
                for e in o.get("events", [])
            ],
        })
    return {"origen": "SAP EWM" if is_live_mode() else "Datos de demostración", "pedidos": rows,
            "alertas_calculadas": all_alerts(orders), "umbrales_minutos": limits}


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def api_health():
    return jsonify({"ok": True, "mode": "sap_ewm" if is_live_mode() else "demo"})


@app.get("/api/summary")
def api_summary():
    return jsonify(summary(current_orders()))


@app.get("/api/orders")
def api_orders():
    orders = current_orders()
    query = request.args.get("q", "").strip().casefold()
    stage = request.args.get("stage", "").strip()
    status = request.args.get("status", "").strip()
    result = []
    for order in orders:
        searchable = [order.get("order_id"), order.get("delivery_id"), order.get("client")]
        searchable.extend(item.get("reference") for item in order.get("items", []))
        searchable.extend(hu.get("hu_id") for hu in order.get("handling_units", []))
        if query and not any(query in str(value or "").casefold() for value in searchable):
            continue
        if stage and order.get("stage") != stage:
            continue
        if status and order.get("status") != status:
            continue
        result.append(order)
    return jsonify({"orders": result, "total": len(result), "mode": "SAP EWM" if is_live_mode() else "Demostración"})


@app.get("/api/orders/<order_id>")
def api_order_detail(order_id: str):
    order = next((o for o in current_orders() if o.get("order_id", "").casefold() == order_id.casefold()), None)
    if not order:
        return jsonify({"error": "No se encontró el pedido en los registros disponibles."}), 404
    order = dict(order)
    order["elapsed_minutes"] = elapsed_minutes(order)
    order["alert"] = order_alert(order, thresholds())
    return jsonify(order)


@app.get("/api/alerts")
def api_alerts():
    limits = thresholds()
    if not limits:
        return jsonify({"alerts": [], "configured": False,
                        "message": "Los tiempos objetivo para datos de SAP EWM aún no han sido definidos por Operaciones."})
    return jsonify({"alerts": all_alerts(current_orders()), "configured": True,
                    "message": "Los tiempos de demostración son ilustrativos." if not is_live_mode() else "Alertas calculadas con los límites configurados por Operaciones."})


@app.get("/api/integration/status")
def api_integration_status():
    return jsonify(EWM.status())


@app.post("/api/integration/check")
def api_integration_check():
    try:
        return jsonify(EWM.check())
    except (EWMConfigurationError, EWMConnectionError) as exc:
        return jsonify({"connected": False, "status": "error", "message": str(exc)}), 400


@app.post("/api/integration/refresh")
def api_integration_refresh():
    global LIVE_ORDERS, LIVE_LAST_SYNC, LIVE_ERROR
    try:
        fetched = EWM.fetch_orders()
        with LOCK:
            LIVE_ORDERS = fetched
            LIVE_LAST_SYNC = iso(utc_now())
            LIVE_ERROR = None
        return jsonify({"ok": True, "orders_received": len(fetched), "last_sync": LIVE_LAST_SYNC,
                        "message": "Consulta completada. Verifica que los campos correspondan con los registros de SAP EWM."})
    except (EWMConfigurationError, EWMConnectionError) as exc:
        with LOCK:
            LIVE_ERROR = str(exc)
        return jsonify({"ok": False, "message": str(exc)}), 400


@app.get("/api/ai/status")
def api_ai_status():
    return jsonify(AI.status())


def run_ai(kind: str, question: str | None = None):
    context = ai_context(current_orders())
    try:
        text = AI.generate(kind=kind, context=context, question=question)
        return jsonify({"ok": True, "text": text, "source": context["origen"], "generated_at": iso(utc_now())})
    except (AIConfigurationError, AIServiceError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 503


@app.post("/api/ai/report")
def api_ai_report():
    payload = request.get_json(silent=True) or {}
    report_type = str(payload.get("report_type", "general")).strip()[:40]
    return run_ai("report", f"Tipo de informe solicitado: {report_type}.")


@app.post("/api/ai/delays")
def api_ai_delays():
    return run_ai("delays")


@app.post("/api/ai/ask")
def api_ai_ask():
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()
    if not question or len(question) > 500:
        return jsonify({"ok": False, "error": "Escribe una pregunta de máximo 500 caracteres."}), 400
    return run_ai("ask", question)


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({"error": "La solicitud supera el tamaño permitido."}), 413


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=debug)
