# Verification Harness for AI-Generated Patches
## Documento de Arquitectura y Progreso del Proyecto (Actualización 28/Ene/2026)

**Autor:** Ignacio Hernández  
**Tipo:** Trabajo Fin de Máster / Research Project  
**Universidad:** University of Maryland  
**Fecha:** 28 de enero de 2026

---

## 1. Resumen Ejecutivo

- **Estado general:** las tres capas del harness (ejecución reproducible, SQI, verificación semántica) están integradas.
- **Novedad clave:** el módulo `claim_extraction` pasó de extracción manual a un flujo **totalmente automatizado** con grounding auditable.
- **Resultado tangible:** corrida `claims_6199435` (27/Ene) generó **7 claims finales grounded** en 5 issues (Astropy, Requests, pylint).

---

## 2. Arquitectura del Sistema

Mismo diagrama base (Dataset Loader → Orquestador → SQI / Singularity / Claim Pipeline), con dos añadidos:
1. **Code Context Builder** ahora exporta `touched_files_text` por archivo modificado.
2. **Claim Pipeline** utiliza prompt reforzado para apuntar a símbolos específicos.

---

## 3. Avances del Módulo Claim Extraction

### 3.1 Nuevas Capacidades

| Mejora | Descripción | Archivos |
|--------|-------------|----------|
| Touched files | `prepare_instances.py` lee cada archivo del patch y adjunta texto truncado. | `claim_extraction/prepare_instances.py` |
| Runner aware | CLI pasa `touched_files_text` a `process_instance`. | `claim_extraction/cli.py` |
| Prompt específico | Instrucciones para usar helpers modificados y prohibir APIs superficiales. | `claim_extraction/prompts/claim_prompt_v2_1.jinja` |
| Slurm robusto | `start_vllm_claim_extractor.sbatch` fija `ROOT_DIR`, rutas absolutas y logs en carpeta dedicada. | `claim_extraction/scripts_slurm/start_vllm_claim_extractor.sbatch` |

### 3.2 Métricas del Primer Batch Automático

Fuente: `claim_extraction/claims_out/summary.json` (27/Ene 20:28 UTC-5)

| Métrica | Valor |
|---------|-------|
| Instancias elegibles | 5/5 (100%) |
| Claims finales | 7 (todos grounded) |
| Grounding | 7 weak_file, 0 strong |
| Avg score | 4.9 |
| Specificity rate | 0.5 |
| Evidence verified | 100% |

Logs: `claim_extraction/scripts_slurm/logs/claims_6199435.err`.

### 3.3 Impacto

- Astropy (`astropy__astropy-7746`) ahora produce claim grounded en `_array_converter`/`_return_list_of_arrays`.
- Requests (`psf__requests-2148`) captura error de socket → `requests.exceptions.ConnectionError`.
- Pylint issues generan 5 claims adicionales con grounding en helpers internos.

---

## 4. Estado de Otros Módulos

| Módulo | Estado | Comentarios |
|--------|--------|-------------|
| Dataset Loader | ✅ Estable | Soporta filtros por repo/ID + caching de repos. |
| SQI | ✅ Implementado | Métricas estáticas listas para combinarse con claims. |
| Singularity Runner | ✅ | Contenedores reproducibles, falta integrar nuevos tests. |
| Mutation Harness | ⚠️ | Definido pero pendiente de integración con claims generados automáticamente. |

---

## 5. Integración del Pipeline Completo

1. Selección de issues (`claim_extraction/ids.txt`).
2. `prepare_instances.py` genera `claim_extraction/instances.json` con contexto + archivos.
3. `sbatch claim_extraction/scripts_slurm/start_vllm_claim_extractor.sbatch`.
4. Salida: `claim_extraction/claims_out/*.json` + `summary.json` con métricas y errores.
5. Próximo paso: alimentar estos claims a generador de tests + validación diferencial (C_bug/C_gold/C_mut).

---

## 6. Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Specificity baja (50%) | Claims menos accionables | Ajustar prompt y agregar heurísticas en post-proceso. |
| Sólo weak_file grounding | Dificulta defensa académica | Agregar parsing de definiciones para `strong`. |
| Coste de cargar archivos grandes | Tiempo/memoria en prepare | Truncado 60k chars + métricas para medir overhead. |
| Discrepancia símbolo (Requests) | Claim no coincide 100% con patch | Revisión manual + reglas para detectar drift. |

---

## 7. Próximos Hitos (Q1 2026)

1. **Specificity upgrade:** nueva plantilla Given/When con ejemplos concretos.
2. **Grounding fuerte:** mapear definiciones en diff/AST para `diff_definition` evidence.
3. **Batch ≥20 issues:** medir tiempo/pico memoria tras tocar archivos.
4. **Validación diferencial:** ejecutar tests generados con C_bug/C_gold/C_mut y reportar FAR reduction.
5. **Documentación viva:** reportes diarios en `docs/Claim_extractor_YYYY-MM-DD.md` + actualización del documento general.

---

## 8. Referencias

- Documentación previa: `docs/Claim_extractor_2026-01-26.md`.
- Reporte específico: `docs/Claim_extractor_2026-01-28.md`.
- Logs de Slurm: `claim_extraction/scripts_slurm/logs/`.

---

*Documento autoactualizado el 28/Ene/2026.*
