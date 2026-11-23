"""Conector REST preliminar para SAP EWM.

No presupone una ruta OData específica. TI debe facilitar el endpoint autorizado
 y definir el contrato JSON. El conector espera un JSON normalizado con una clave
 `orders` (o una lista directa) y realiza únicamente solicitudes GET.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import requests


class EWMConfigurationError(RuntimeError):
    pass


class EWMConnectionError(RuntimeError):
    pass


@dataclass
class EWMConnector:
    enabled: bool
    orders_url: str
    health_url: str
    auth_type: str
    token: str
    username: str
    password: str
    timeout: int
    ca_bundle: str | bool

    @classmethod
    def from_environment(cls) -> "EWMConnector":
        enabled = os.getenv("EWM_ENABLED", "false").strip().lower() == "true"
        auth_type = os.getenv("EWM_AUTH_TYPE", "none").strip().lower()
        ca_bundle_path = os.getenv("EWM_CA_BUNDLE", "").strip()
        return cls(
            enabled=enabled,
            orders_url=os.getenv("EWM_ORDERS_URL", "").strip(),
            health_url=os.getenv("EWM_HEALTH_URL", "").strip(),
            auth_type=auth_type,
            token=os.getenv("EWM_API_TOKEN", "").strip(),
            username=os.getenv("EWM_USERNAME", "").strip(),
            password=os.getenv("EWM_PASSWORD", ""),
            timeout=max(3, min(int(os.getenv("EWM_TIMEOUT_SECONDS", "15")), 60)),
            ca_bundle=ca_bundle_path if ca_bundle_path else True,
        )

    def status(self) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "connected": False, "status": "not_configured",
                    "system": "SAP EWM · PS4 / mandante 100 (por confirmar con TI)",
                    "message": "La conexión está desactivada. Se requiere endpoint y autorización de TI."}
        missing = []
        if not self.orders_url:
            missing.append("EWM_ORDERS_URL")
        if self.auth_type == "bearer" and not self.token:
            missing.append("EWM_API_TOKEN")
        if self.auth_type == "basic" and (not self.username or not self.password):
            missing.append("EWM_USERNAME / EWM_PASSWORD")
        if missing:
            return {"enabled": True, "connected": False, "status": "incomplete",
                    "message": "Falta configurar: " + ", ".join(missing)}
        return {"enabled": True, "connected": False, "status": "configured_not_tested",
                "message": "Configuración presente. Aún no se ha verificado la respuesta del servicio."}

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": "TRAZAplus/1.0"}
        if self.auth_type == "bearer":
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, url: str) -> requests.Response:
        if not url:
            raise EWMConfigurationError("TI debe proporcionar la URL del servicio de SAP EWM.")
        if self.auth_type not in {"none", "bearer", "basic"}:
            raise EWMConfigurationError("EWM_AUTH_TYPE debe ser none, bearer o basic. Confirma el método con TI.")
        auth = (self.username, self.password) if self.auth_type == "basic" else None
        try:
            response = requests.get(
                url,
                headers=self._headers(),
                auth=auth,
                timeout=self.timeout,
                verify=self.ca_bundle,
            )
        except requests.Timeout as exc:
            raise EWMConnectionError("SAP EWM no respondió dentro del tiempo de espera.") from exc
        except requests.RequestException as exc:
            raise EWMConnectionError("No fue posible establecer conexión con el endpoint. Revisa red, VPN, URL y certificado con TI.") from exc
        if response.status_code in (401, 403):
            raise EWMConnectionError("SAP EWM rechazó la autenticación o los permisos. Solicita revisión a TI.")
        if response.status_code == 404:
            raise EWMConnectionError("El servicio respondió 404. TI debe confirmar la URL y que el servicio esté publicado.")
        if not response.ok:
            raise EWMConnectionError(f"El servicio respondió con HTTP {response.status_code}.")
        return response

    def check(self) -> dict[str, Any]:
        if not self.enabled:
            raise EWMConfigurationError("La conexión está desactivada. Configura EWM_ENABLED=true solo después de la autorización de TI.")
        url = self.health_url or self.orders_url
        start = time.perf_counter()
        response = self._request(url)
        latency = round((time.perf_counter() - start) * 1000)
        return {"enabled": True, "connected": True, "status": "connected", "http_status": response.status_code,
                "latency_ms": latency, "message": "El endpoint respondió correctamente. Falta validar que los datos correspondan al proceso de trazabilidad."}

    def fetch_orders(self) -> list[dict[str, Any]]:
        if not self.enabled:
            raise EWMConfigurationError("La conexión SAP EWM está desactivada.")
        if not self.orders_url:
            raise EWMConfigurationError("Configura EWM_ORDERS_URL con la ruta que entregue TI.")
        response = self._request(self.orders_url)
        try:
            payload = response.json()
        except ValueError as exc:
            raise EWMConnectionError("El endpoint no devolvió JSON. Confirma con TI el formato de respuesta.") from exc
        rows = self._extract_orders(payload)
        if not rows:
            raise EWMConnectionError("La respuesta no contiene pedidos en el formato esperado. Se debe ajustar el mapeo con la documentación de TI.")
        normalised = [self._normalise_order(row) for row in rows]
        if any(not row.get("order_id") for row in normalised):
            raise EWMConnectionError("Uno o más registros no tienen identificador de pedido. Ajusta el mapeo de campos con TI.")
        return normalised

    @staticmethod
    def _extract_orders(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            # OData V2 y V4, además de algunos envoltorios REST habituales.
            if isinstance(payload.get("d"), dict) and isinstance(payload["d"].get("results"), list):
                return payload["d"]["results"]
            for key in ("orders", "value", "data", "results", "items"):
                if isinstance(payload.get(key), list):
                    return [row for row in payload[key] if isinstance(row, dict)]
        return []

    @staticmethod
    def _first(row: dict[str, Any], *keys: str, default: Any = "") -> Any:
        for key in keys:
            value = row.get(key)
            if value not in (None, ""):
                return value
        return default

    @classmethod
    def _normalise_order(cls, row: dict[str, Any]) -> dict[str, Any]:
        order_id = cls._first(row, "order_id", "OrderId", "OutboundDeliveryOrder", "WhseOutboundDeliveryOrder", "DocumentNumber")
        items = cls._first(row, "items", "Items", "to_Item", default=[])
        hus = cls._first(row, "handling_units", "HandlingUnits", "HUs", default=[])
        events = cls._first(row, "events", "Events", "tasks", "WarehouseTasks", default=[])
        norm_items = []
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            norm_items.append({
                "reference": cls._first(item, "reference", "Product", "ProductNumber", "Material", "MaterialNumber"),
                "description": cls._first(item, "description", "ProductDescription", "MaterialDescription"),
                "quantity": cls._first(item, "quantity", "ActualDeliveryQuantity", "DeliveryQuantity", "Quantity", default=0),
                "unit": cls._first(item, "unit", "DeliveryQuantityUnit", "UnitOfMeasure", default=""),
            })
        norm_hus = []
        for hu in hus if isinstance(hus, list) else []:
            if not isinstance(hu, dict):
                continue
            norm_hus.append({
                "hu_id": cls._first(hu, "hu_id", "HandlingUnit", "HUExternalID", "ExternalHandlingUnit"),
                "location": cls._first(hu, "location", "StorageBin", "WarehouseStorageBin"),
                "status": cls._first(hu, "status", "HandlingUnitStatus"),
                "contents": cls._first(hu, "contents", "ContentDescription"),
            })
        norm_events = []
        for event in events if isinstance(events, list) else []:
            if not isinstance(event, dict):
                continue
            norm_events.append({
                "event_time": cls._first(event, "event_time", "EventDateTime", "CreationDateTime", "CreatedAt"),
                "event": cls._first(event, "event", "EventDescription", "Activity", "WarehouseTaskType"),
                "stage": cls._first(event, "stage", "ProcessStage"),
                "location": cls._first(event, "location", "StorageBin", "WarehouseStorageBin", "DestinationStorageBin"),
                "status": cls._first(event, "status", "WarehouseTaskStatus", "ConfirmationStatus"),
                "source": "SAP EWM",
            })
        stage = cls._first(row, "stage", "ProcessStage", "CurrentStage", default="Sin etapa confirmada")
        return {
            "order_id": str(order_id),
            "delivery_id": cls._first(row, "delivery_id", "OutboundDelivery", "OutboundDeliveryOrder"),
            "client": "No consultado",
            "created_at": cls._first(row, "created_at", "CreationDateTime", "CreatedAt"),
            "status": cls._first(row, "status", "OverallWarehouseTaskStatus", "OverallStatus", default="No informado"),
            "stage": str(stage),
            "stage_started_at": cls._first(row, "stage_started_at", "StageStartDateTime", default=""),
            "stage_elapsed_minutes": None,
            "location": cls._first(row, "location", "StorageBin", "WarehouseStorageBin", "CurrentLocation", default="Sin ubicación informada"),
            "priority": cls._first(row, "priority", "DeliveryPriority", default="No informada"),
            "items": norm_items,
            "handling_units": norm_hus,
            "events": norm_events,
            "data_origin": "SAP EWM",
        }
