"""Integración opcional con OpenAI Responses API, desactivada por defecto.

Solo envía al proveedor los campos logísticos mínimos cuando la empresa autorice
expresamente el tratamiento de esos datos y se configure una clave válida.
"""
from __future__ import annotations

import os
from typing import Any

import requests


class AIConfigurationError(RuntimeError):
    pass


class AIServiceError(RuntimeError):
    pass


class AIService:
    def __init__(self, enabled: bool, data_approved: bool, api_key: str, model: str, timeout: int = 45):
        self.enabled = enabled
        self.data_approved = data_approved
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @classmethod
    def from_environment(cls) -> "AIService":
        return cls(
            enabled=os.getenv("AI_ENABLED", "false").strip().lower() == "true",
            data_approved=os.getenv("AI_DATA_APPROVED", "false").strip().lower() == "true",
            api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            model=os.getenv("OPENAI_MODEL", "").strip(),
            timeout=max(10, min(int(os.getenv("AI_TIMEOUT_SECONDS", "45")), 90)),
        )

    def status(self) -> dict[str, Any]:
        ready = self.enabled and self.data_approved and bool(self.api_key and self.model)
        return {
            "enabled": self.enabled,
            "data_approved": self.data_approved,
            "ready": ready,
            "status": "ready" if ready else "not_configured",
            "message": "Servicio de IA configurado." if ready else "La IA está pendiente de autorización empresarial y configuración técnica.",
        }

    def generate(self, kind: str, context: dict[str, Any], question: str | None = None) -> str:
        if not self.enabled:
            raise AIConfigurationError("La función de IA está desactivada. Debe ser aprobada y configurada por la empresa.")
        if not self.data_approved:
            raise AIConfigurationError("No se ha confirmado la autorización de la empresa para enviar datos logísticos al proveedor de IA.")
        if not self.api_key or not self.model:
            raise AIConfigurationError("Falta configurar OPENAI_API_KEY u OPENAI_MODEL en el entorno seguro del servidor.")

        task_text = {
            "report": "Redacta un informe operativo breve con resumen, hallazgos respaldados por los datos, limitaciones y recomendaciones de revisión. " + (question or ""),
            "delays": "Analiza las alertas calculadas por el sistema. Resume qué etapas y pedidos requieren revisión. No atribuyas causas que los datos no demuestren.",
            "ask": f"Responde la pregunta del usuario usando exclusivamente el conjunto de datos. Pregunta: {question}",
        }.get(kind)
        if not task_text:
            raise AIServiceError("Tipo de análisis no reconocido.")

        instructions = (
            "Eres un asistente de análisis logístico de trazabilidad de pedidos de grifería. "
            "Usa exclusivamente los datos JSON proporcionados. No inventes fechas, ubicaciones, cantidades, estados, "
            "tiempos ni causas. Si faltan datos, indícalo. Distingue hechos, interpretaciones y recomendaciones. "
            "No afirmes que un pedido fue cargado o salió si no hay un evento registrado que lo confirme. "
            "No declares que una novedad está resuelta. Redacta en español claro y profesional."
        )
        payload_text = task_text + "\n\nDatos autorizados:\n" + __import__("json").dumps(context, ensure_ascii=False, default=str)
        body = {"model": self.model, "instructions": instructions, "input": payload_text}
        try:
            response = requests.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=body,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise AIServiceError("No fue posible comunicarse con el servicio de IA.") from exc
        if not response.ok:
            raise AIServiceError(f"El servicio de IA respondió HTTP {response.status_code}. Revisa la configuración con TI.")
        try:
            data = response.json()
        except ValueError as exc:
            raise AIServiceError("El servicio de IA devolvió una respuesta no válida.") from exc

        output_text = data.get("output_text")
        if output_text:
            return str(output_text).strip()
        parts = []
        for output in data.get("output", []):
            for content in output.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    parts.append(content["text"])
        result = "\n".join(parts).strip()
        if not result:
            raise AIServiceError("La respuesta del servicio de IA no incluyó texto.")
        return result
