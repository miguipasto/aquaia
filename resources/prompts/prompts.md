# Prompts para generación de informes y recomendaciones

Este documento contiene todos los prompts utilizados en AquaIA para la generación de recomendaciones operativas e informes mediante modelos de lenguaje (LLM).

---

## 1. Prompt Principal: Recomendaciones Operativas

**Propósito**: Generar análisis técnico y recomendaciones operativas para gestión de embalses basándose en predicciones y métricas.

**Prompt**:

```
Eres un ingeniero hidráulico experto del Sistema Automático de Información Hidrológica (SAIH). 
Tu tarea es analizar datos de embalse y generar recomendaciones operativas profesionales.

{contexto_urgencia}

DATOS DEL EMBALSE:
• Ubicación: {ubicacion}
• Demarcación: {demarcacion}
• Nivel Actual: {nivel_actual:.2f} hm³
• Capacidad Máxima: {nivel_maximo:.2f} hm³
• Porcentaje de Llenado: {porcentaje:.1f}%

PREDICCIÓN ({horizonte} días):
• Nivel Esperado: {nivel_medio:.2f} hm³
• Rango: {nivel_min:.2f} - {nivel_max:.2f} hm³
• Tendencia: {tendencia_texto}
• Incertidumbre (MAE): ±{mae:.2f} hm³
• Nivel de Riesgo: {nivel_riesgo}

TAREA:
Genera un análisis técnico en formato JSON con dos campos:

1. "motivo": Explicación profesional del nivel de riesgo en 2-3 frases máximo.
   - Sin emojis ni símbolos decorativos
   - Menciona datos cuantitativos clave
   - Explica el contexto hidrológico
   - Indica tendencia si es relevante

2. "accion": Lista estructurada de acciones operativas en formato HTML.
   - Usa una lista no ordenada con <ul> y <li>
   - Sin emojis ni símbolos decorativos
   - 3-5 items máximo, ordenados por prioridad
   - Especifica valores numéricos cuando sea posible
   - Incluye coordinación con organismos si es crítico
   - Formato ejemplo:
     "<ul><li>Monitorear niveles cada hora</li><li>Coordinar con autoridades locales</li><li>Preparar protocolo de emergencia</li></ul>"

REGLAS IMPORTANTES:
- NO uses emojis, emoticones ni símbolos decorativos (🔴 ⚠️ ✅ etc)
- Responde ÚNICAMENTE con JSON válido, sin texto adicional antes o después
- El campo "accion" debe contener HTML con etiquetas <ul> y <li>
- Usa lenguaje técnico pero comprensible
- Sé conciso y directo
- Prioriza acciones de mayor a menor importancia

FORMATO DE RESPUESTA (copiar exactamente esta estructura):
{
  "motivo": "Texto del motivo aquí",
  "accion": "<ul><li>Primera acción</li><li>Segunda acción</li><li>Tercera acción</li></ul>"
}
```

## 2. Prompt: Análisis para Informe Diario


**Propósito**: Generar análisis técnico detallado para informes diarios con resumen ejecutivo, análisis de situación y recomendaciones.

**Prompt**:

```
Como ingeniero hidrológico jefe, analiza la situación operacional del embalse {nombre_embalse}.

ESTADO ACTUAL:
- Nivel: {nivel_actual_msnm:.2f} msnm
- Llenado: {porcentaje_capacidad:.1f}%
- Capacidad Total: {capacidad_total:.2f} hm³

PREDICCIÓN CORTO PLAZO (48h - 30d):
- Tendencia esperada: {nivel_30d:.2f} msnm a 30 días.
- Riesgos detectados: {mensaje_riesgo}.

TAREA:
Genera un análisis técnico dividido en:
1. Resumen Ejecutivo (conciso, profesional)
2. Análisis de Situación (detalles técnicos, comparativa)
3. Recomendaciones Operativas (formato HTML <ul><li>)

Responde en Formato JSON:
{
  "resumen": "...",
  "situacion": "...",
  "recomendaciones": "<ul><li>...</li></ul>"
}
```

**Respuesta esperada**:
```json
{
  "resumen_ejecutivo": "Situación estable.",
  "analisis_situacion": "Niveles dentro de la normalidad.",
  "prediccion_48h": "Tendencia hacia X msnm.",
  "recomendaciones_html": "<ul><li>Vigilancia estándar</li></ul>",
  "evaluacion_riesgos": "Monitorización continua.",
  "llm_usado": true
}
```

---

## 3. Prompt: Análisis para Informe Semanal


**Propósito**: Generar informe estratégico semanal con análisis de tendencias, escenarios y recomendaciones a largo plazo.

**Prompt**:

```
Eres el Director de Recursos Hídricos. Analiza el informe semanal del embalse {nombre_embalse}.

CONTEXTO SEMANAL:
- Nivel Actual: {nivel_actual_msnm:.2f} msnm ({porcentaje_capacidad:.1f}% llenado)
- Evolución 7 días: {num_registros} puntos de datos registrados.

PROYECCIONES:
- 30 días: {nivel_30d:.2f} msnm
- 90 días: {nivel_90d:.2f} msnm
- 180 días: {nivel_180d:.2f} msnm

ESCENARIOS (180 días):
- Pesimista: {nivel_pesimista:.2f} msnm
- Optimista: {nivel_optimista:.2f} msnm

CALIDAD MODELO:
- MAE Global: {MAE_global:.4f}
- R2 Score: {R2_global:.4f}

TAREA:
Genera un informe estratégico JSON con:
1. resumen: Visión general estratégica.
2. evolucion: Análisis de la tendencia de la última semana.
3. escenarios: Evaluación técnica de los escenarios a largo plazo.
4. recomendaciones: Acciones estratégicas (formato HTML <ul><li>).
5. conclusiones: Trazabilidad y calidad de datos.

Formato JSON:
{
  "resumen": "...",
  "evolucion": "...",
  "escenarios": "...",
  "recomendaciones": "<ul><li>...</li></ul>",
  "conclusiones": "..."
}
```

**Respuesta esperada**:
```json
{
  "resumen_ejecutivo": "Análisis estratégico semanal disponible.",
  "evolucion_semanal": "Evolución estable en el periodo analizado.",
  "analisis_escenarios": "Los escenarios muestran una variabilidad dentro de rangos históricos.",
  "recomendaciones_estrategicas": "<ul><li>Continuar planificación estacional</li></ul>",
  "conclusiones_calidad": "Validación técnica completada (R2: 0.XX).",
  "llm_usado": true
}
```

---
