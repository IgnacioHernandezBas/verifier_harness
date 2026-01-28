# Claim Extraction (v2.2-pre)

**Autor:** Equipo Verifier Harness  
**Fecha:** 28 de enero de 2026

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Claims y Grounding Auditable](#3-claims-y-grounding-auditable)
4. [Eligibility Filter](#4-eligibility-filter)
5. [Pipeline de Extracción](#5-pipeline-de-extracción)
6. [Sistema de Scoring](#6-sistema-de-scoring)
7. [Validación Metodológica](#7-validación-metodológica)
8. [Críticas y Defensas](#8-críticas-y-defensas)
9. [Métricas](#9-métricas)
10. [Implementación y Avances 28/Ene](#10-implementación-y-avances-28ene)

---

## 1. Resumen Ejecutivo

### 1.1 Problema

Los agentes que generan parches siguen pasando tests existentes sin respetar el comportamiento descrito en el issue. Necesitamos claims auditables y grounded para detectar false acceptances.

### 1.2 Solución

Un pipeline modular que:
1. Prepara `instances.json` con contexto de código más archivos tocados.
2. Extrae claims con Qwen2.5-Coder + prompt reforzado.
3. Valida grounding multinivel y evidencia textual.
4. Filtra por scoring compuesto y reporta métricas de calidad.

### 1.3 Avance clave (27/01 run `claims_6199435`)

- **5 instancias elegibles / 5 totales.**
- **7 claims finales grounded (100% weak_file).**
- Evidence verified rate 100%, avg score 4.9, specificity 50%.
- Logs: `claim_extraction/scripts_slurm/logs/claims_6199435.err`.

---

## 2. Arquitectura del Sistema

(mismo esquema v2.1, con nuevas flechas para `touched_files_text` y prompt reforzado.)

---

## 3. Claims y Grounding Auditable

- Foco en helpers modificados (`_array_converter`, `_return_list_of_arrays`, `generate`, etc.).
- `touched_files_text` permite grounding `weak_file` incluso si la definición no aparece en el diff corto.
- Evidencia incluye `{type, path, snippet}` por símbolo.

Ejemplo Astropy (`astropy__astropy-7746`):
```json
{
  "target_symbols": ["wcs_pix2world","_array_converter","_return_list_of_arrays"],
  "grounding": {
    "status": "weak_file",
    "evidence": [
      {"path": "astropy/wcs/wcs.py", "snippet": "..._array_converter..."},
      {"path": "astropy/wcs/wcs.py", "snippet": "..._return_list_of_arrays..."}
    ]
  }
}
```

---

## 4. Eligibility Filter

Sin cambios: score ≥2 usando señales (excepción concreta, stacktrace, keywords, referencias, ejemplos). Las 5 instancias del batch cumplieron.

---

## 5. Pipeline de Extracción

1. **Prepare Instances**  
   - `build_instance_payload` ahora añade `touched_files_text` truncado a 60k chars.
2. **Prompt/Qwen**  
   - Nueva regla: “Prefer the most specific symbol actually modified…”  
   - Penaliza citar sólo APIs públicas.
3. **Grounding Runner**  
   - `process_instance(..., touched_files_text=...)` habilita weak_file real.
4. **Outputs**  
   - Claims por issue + `summary.json` consolidado.

---

## 6. Sistema de Scoring

`score = grounding + evidence + observable + confidence`

| Componente | Observado 27/Ene |
|------------|------------------|
| Grounding  | +1 (weak_file) para 7 claims |
| Evidence   | +2 (span directo) |
| Observable | Mayoría con retorno/exception |
| Confidence | Qwen tendió a `high` |

Threshold mantiene `score ≥ 2`. Promedio final 4.9.

---

## 7. Validación Metodológica

- Seguimos usando criterio `FAIL(C_bug) ∧ PASS(C_gold) ∧ MKR>0` para claims que pasan a etapa de test generation.
- Próximo paso: ampliar conjunto de 5 → 20 instancias para validar estabilidad de `touched_files_text`.

---

## 8. Críticas y Defensas

| Crítica | Respuesta 28/Ene |
|---------|------------------|
| “Grounding weak es ruido” | Ahora cada weak_file trae evidencia concreta (path+snippet). Planeamos sampleo manual. |
| “Claims siguen vagos” | Prompt actualizado detecta y marca `specificity=false`; se prioriza ajuste en GIVEN/THEN. |
| “¿Y strong grounding?” | En backlog: parsear definiciones anidadas para `diff_definition`. |

---

## 9. Métricas

De `claim_extraction/claims_out/summary.json`:

| Métrica | Valor |
|---------|-------|
| Eligibility rate | 100% |
| Grounding rate | 100% (7/7 weak_file) |
| Avg final claims/issue | 1.4 |
| Avg score | 4.9 |
| Specificity rate | 0.5 |
| Evidence verified rate | 1.0 |

Historial comparativo: v2.1 tenía 0 claims grounded en astropy; v2.2-pre con touched-files desbloqueó 1 claim válido.

---

## 10. Implementación y Avances 28/Ene

### 10.1 Código tocado

- `claim_extraction/prepare_instances.py`  
  - Nueva función `load_touched_file_texts`.  
  - `payload["touched_files_text"]` persistido.
- `claim_extraction/cli.py`  
  - Runner alimenta `process_instance` con los textos cargados.
- `claim_extraction/prompts/claim_prompt_v2_1.jinja`  
  - Se añadieron reglas de especificidad de símbolos.
- `claim_extraction/scripts_slurm/start_vllm_claim_extractor.sbatch`  
  - Fija `ROOT_DIR` y rutas absolutas de config/input/output/logs.

### 10.2 Ejecución más reciente

```
sbatch claim_extraction/scripts_slurm/start_vllm_claim_extractor.sbatch
Logs: claim_extraction/scripts_slurm/logs/claims_6199435.{out,err}
```

### 10.3 Próximos pasos

1. Mejorar plantilla Given/When para subir specificity >80%.
2. Implementar detección de definiciones en diff para habilitar `strong` grounding.
3. Correr batch ≥20 instancias y medir impacto en tiempos/memoria.
4. Reportar histogramas históricos en `summary.json`.

---

*Documento generado automáticamente el 28/Ene/2026.*
