# Verification Harness for AI-Generated Patches
## Documento de Arquitectura y Progreso del Proyecto

**Autor:** Igancio Hernández 
**Tipo:** Trabajo Fin de Máster / Research Project  
**Universidad:** University of Maryland
**Fecha:** Enero 2026

---

## 1. Resumen Ejecutivo

### 1.1 Problema

Los agentes de IA que generan parches de código (SWE-agent, Agentless, etc.) se evalúan principalmente ejecutando los tests existentes del repositorio. Esto produce **false acceptances**: parches que pasan los tests pero no cumplen la intención real del issue.

**Ejemplo:**
- Issue: "La función `parse()` debe ser case-insensitive"
- Parche generado: Añade `.lower()` solo en un branch, no en todos
- Tests existentes: Solo testean el caso uppercase → PASS
- Realidad: El parche está incompleto → **False Acceptance**

### 1.2 Solución Propuesta

Un **verification harness** que extiende la evaluación de SWE-bench con capas adicionales:

1. **Ejecución reproducible** en contenedores Singularity
2. **Análisis estático** agregado en un Static Quality Index (SQI)
3. **Verificación semántica** basada en "claims" extraídos del issue original

### 1.3 Contribución Principal

> *"Diseñamos un harness de verificación para parches generados por IA que agrega evidencia estática y dinámica, e introducimos un componente de generación de tests basado en claims comportamentales extraídos del issue, reduciendo false acceptances comparado con la ejecución de tests baseline."*

### 1.4 Avances Recientes 🚀

**Fecha: 21 Enero 2026**

#### ✅ Clasificación Completa de SWE-bench Lite

- **300 issues** analizados y clasificados por dificultad
- Sistema de scoring automático basado en:
  - Tamaño del patch (líneas modificadas)
  - Complejidad del issue (explicit behavior keywords)
  - Testabilidad (return/exception vs visual/performance)
  - Tier del repositorio (pytest/pylint=easy, matplotlib=hard)

**Resultados destacados:**
- **pylint-dev/pylint**: 96/100 promedio, 6/6 Tier 1 🎯
- **pytest-dev/pytest**: 86/100 promedio, 16/17 Tier 1 🎯
- **astropy/astropy**: 82.5/100 promedio, 5/6 Tier 1
- **django/django**: 66/100 promedio, 56/114 Tier 1

Top issue identificado: `astropy__astropy-7746` (score: 100)

#### ✅ Módulo de Grounding Check Implementado

**Problema resuelto:** Prevenir generación de tests para claims sobre código no modificado.

**Implementación completa:**
- `claim_extraction/grounding.py` (300+ líneas)
- 28 test cases unitarios
- Demo interactivo con 5 ejemplos reales
- Documentación completa en README.md

**API principal:**
```python
# Extraer símbolos modificados en el patch
symbols = extract_symbols_from_diff(patch)

# Verificar si claim está grounded
is_grounded = is_claim_grounded(claim, patch)

# Análisis detallado (strong/weak/none)
result = calculate_grounding_strength(claim, patch)

# Filtrar lista de claims
grounded, ungrounded = filter_grounded_claims(claims, patch)
```

**Validación:**
- ✅ Extrae correctamente símbolos de patches reales
- ✅ Maneja símbolos dotados (`Class.method`)
- ✅ Distingue strong/weak/none grounding
- ✅ Demo funcional con ejemplos de astropy y django

**Próximo paso:** Usar grounding check en extracción manual de claims para primeros 5 issues.

---

## 2. Arquitectura del Sistema

### 2.1 Diagrama General

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              VERIFICATION HARNESS                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   Dataset    │    │   Streamlit  │    │    Claim     │                   │
│  │   Loader     │───▶│     App      │◀───│   Storage    │                   │
│  │  (HF API)    │    │ (Orquestador)│    │   (JSON)     │                   │
│  └──────────────┘    └──────┬───────┘    └──────────────┘                   │
│                             │                                                │
│         ┌───────────────────┼───────────────────┐                           │
│         ▼                   ▼                   ▼                           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   Static     │    │  Singularity │    │    Claim     │                   │
│  │  Analysis    │    │   Runner     │    │   Pipeline   │                   │
│  │  (SQI)       │    │  (Tests)     │    │  (LLM-based) │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
│         │                   │                   │                           │
│         ▼                   ▼                   ▼                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      VERIFICATION RESULTS                            │   │
│  │  • Static Quality Index (SQI)                                       │   │
│  │  • SWE-bench Test Results (PASS/FAIL)                               │   │
│  │  • Claim-Test Results (PASS/FAIL)                                   │   │
│  │  • Mutation Kill Rate (MKR)                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Componentes Implementados

#### 2.2.1 DatasetLoader

```python
# Carga instancias desde HuggingFace y normaliza
{
  "repo": "django/django",
  "base_commit": "a1b2c3d...",
  "patch": "diff --git...",
  "problem_statement": "Issue description...",
  "metadata": {
    "instance_id": "django__django-10914",
    "FAIL_TO_PASS": "[\"test_file_upload_permissions\"]",
    "PASS_TO_PASS": "[\"test_other...\"]",
    "test_patch": "diff --git a/tests/..."
  }
}
```

**Funcionalidades:**
- Carga SWE-bench Lite, Verified, o Full
- Filtros por repositorio, límites para experimentos pequeños
- Normalización de campos para el pipeline

#### 2.2.2 Singularity Runner (Execution Layer)

**Flujo de ejecución:**
```
1. Checkout del repo en base_commit
2. Montar /workspace con código
3. Configurar PYTHONPATH y dependencias
4. Aplicar patch (opcional)
5. Ejecutar tests (pytest / Django runtests.py)
6. Capturar resultados y logs
```

**Por qué Singularity:** Restricción del cluster UMD (equivalente funcional a Docker).

#### 2.2.3 Static Analysis Layer (SQI)

**Herramientas integradas:**

| Herramienta | Propósito | Métricas |
|-------------|-----------|----------|
| Flake8 | Style/PEP8 | Violations count |
| MyPy | Type checking | Type errors |
| Bandit | Security | Vulnerability score |
| Radon | Complexity | Cyclomatic complexity |
| Pylint | Code quality | Pylint score |

**Static Quality Index (SQI):**
```python
SQI = weighted_aggregate(
    flake8_score,
    mypy_score,
    bandit_score,
    radon_score,
    pylint_score
)
# Clasificación: A (>80), B (60-80), C (40-60), D (<40)
```

**Uso:** Rechazar parches con SQI bajo aunque pasen tests (early filtering).

#### 2.2.4 Streamlit App

**Funcionalidades:**
- Selección de instancia de SWE-bench
- Visualización de issue + patch
- Ejecución de análisis estático
- Ejecución de tests en Singularity
- Visualización de logs y resultados
- Historial de ejecuciones

---

## 3. Contribución Nueva: Claims + Claim-Tests

### 3.1 ¿Qué es un Claim?

Un **claim** es una afirmación testable sobre el comportamiento esperado del código, extraída del issue original.

**Estructura Given-When-Then:**

```json
{
  "claim_id": "C1",
  "claim_type": "exception",
  "claim_text": "Table.read must not raise ValueError for lowercase QDP commands",
  "given": "A QDP file with lowercase command 'read serr 1 2'",
  "when": "Table.read(file, format='ascii.qdp') is called",
  "then": "No ValueError is raised, table is returned successfully",
  "confidence": "high",
  "target_symbols": ["_parse_qdp_commands", "Table.read"],
  "evidence": {
    "spans": [
      "ascii.qdp assumes that commands in a QDP file are upper case",
      "QDP itself is not case sensitive"
    ]
  }
}
```

### 3.2 Tipos de Claims

| Tipo | Descripción | Test Pattern |
|------|-------------|--------------|
| `return` | La función debe retornar un valor específico | `assert func() == expected` |
| `exception` | La función debe/no debe lanzar excepción | `pytest.raises()` o ausencia |
| `invariant` | Una propiedad debe mantenerse | Múltiples assertions |
| `state_change` | El estado debe cambiar de forma específica | Before/after comparison |

### 3.3 Grounding: Conexión Claim ↔ Patch

**Problema:** El issue puede mencionar síntomas, contexto irrelevante, o funciones que el usuario *cree* que están rotas pero que el patch no modifica.

**Solución:** Verificar que los `target_symbols` del claim aparecen en el diff del gold patch.

```
┌─────────────────┐         ┌─────────────────┐
│ problem_statement│         │   gold patch    │
│    (issue)      │         │    (diff)       │
└────────┬────────┘         └────────┬────────┘
         │                           │
         ▼                           ▼
   Extraer claims           Extraer símbolos
         │                    modificados
         │                           │
         └───────────┬───────────────┘
                     ▼
              ┌──────────────┐
              │   Grounding  │
              │    Check     │
              └──────┬───────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
   ✅ Grounded              ❌ Not Grounded
   (generar test)           (descartar/bajar
                             confianza)
```

**Implementación:**

```python
def extract_symbols_from_diff(patch: str) -> set[str]:
    """Extrae funciones/clases modificadas en el patch"""
    symbols = set()
    
    # Definiciones de funciones
    for match in re.finditer(r'[-+]\s*def\s+(\w+)\s*\(', patch):
        symbols.add(match.group(1))
    
    # Definiciones de clases
    for match in re.finditer(r'[-+]\s*class\s+(\w+)', patch):
        symbols.add(match.group(1))
    
    return symbols

def is_claim_grounded(claim: dict, patch: str) -> bool:
    """Verifica si el claim toca código modificado"""
    patch_symbols = extract_symbols_from_diff(patch)
    claim_symbols = set(claim['target_symbols'])
    return len(patch_symbols & claim_symbols) > 0
```

**Ejemplo:**

```
Issue: "Table.read() crashes with lowercase QDP commands"

Gold Patch:
- def _parse_qdp_commands(line):
-     if line.startswith('READ'):
+ def _parse_qdp_commands(line):
+     if line.upper().startswith('READ'):

Patch symbols: {_parse_qdp_commands}

Claim C1: target_symbols = [Table.read]        → ❌ Not grounded
Claim C2: target_symbols = [_parse_qdp_commands] → ✅ Grounded
```

#### 3.3.1 Implementación del Grounding Check ✅

**Estado:** Completado (21 Enero 2026)
**Ubicación:** `claim_extraction/grounding.py`

El grounding check está completamente implementado y validado. API principal:

```python
from claim_extraction.grounding import (
    extract_symbols_from_diff,
    is_claim_grounded,
    calculate_grounding_strength,
    filter_grounded_claims
)

# Uso básico
patch = """
diff --git a/auth.py b/auth.py
@@ -10,5 +10,5 @@ def authenticate(user, pwd):
-    return True
+    return validate(user, pwd)
"""

# 1. Extraer símbolos del patch
symbols = extract_symbols_from_diff(patch)
# → {'authenticate', 'validate'}

# 2. Verificar un claim
claim = {
    'claim_id': 'C1',
    'target_symbols': ['authenticate']
}
is_grounded = is_claim_grounded(claim, patch)
# → True

# 3. Análisis detallado
result = calculate_grounding_strength(claim, patch)
# → GroundingResult(
#     is_grounded=True,
#     strength='strong',
#     matched_symbols={'authenticate'},
#     unmatched_symbols=set()
# )

# 4. Filtrado batch
grounded, ungrounded = filter_grounded_claims(all_claims, patch)
```

**Características clave:**
- ✅ Extrae símbolos de hunk headers (más confiable)
- ✅ Maneja símbolos dotados (`Class.method`)
- ✅ Calcula strong/weak/none grounding
- ✅ Incluye metadata en claims filtrados
- ✅ 28 test cases cubriendo escenarios reales

**Demo ejecutable:**
```bash
python demo_grounding.py
# Ejecuta 5 ejemplos con datos reales de SWE-bench
```

### 3.4 Modelo de Confianza para Claims

La confianza de un claim se determina por 4 factores:

```python
confidence(claim) = f(
    requirement_specificity,  # ¿El issue es explícito?
    diff_grounding,           # ¿Los símbolos están en el patch?
    observability,            # ¿El comportamiento es testable?
    llm_agreement             # (opcional) ¿El LLM está seguro?
)
```

#### Factor A: Requirement Specificity (texto del issue)

| Nivel | Indicadores | Ejemplo |
|-------|-------------|---------|
| Explicit | "must", "should return", "raises TypeError" | "should return empty list for empty input" |
| Implied | "returns", "expected", código de ejemplo | "the output looks wrong: [example]" |
| Vague | "doesn't work", "improve", "refactor" | "handle this better" |

#### Factor B: Diff Grounding (más fuerte)

| Nivel | Condición |
|-------|-----------|
| Strong | `target_symbols ⊂ patch_symbols` (todos los símbolos en diff) |
| Weak | `target_symbols ∩ patch_symbols ≠ ∅` (al menos uno) |
| None | `target_symbols ∩ patch_symbols = ∅` (ninguno) |

#### Factor C: Observability (testabilidad)

| Nivel | Comportamiento |
|-------|----------------|
| High | Return values, exceptions, API output |
| Medium | State changes via public API |
| Low | Internal state, performance, visual output |

#### Matriz de Confianza Final

| Specificity | Grounding | Observability | → Confidence |
|-------------|-----------|---------------|--------------|
| Explicit | Strong | High | **HIGH** |
| Explicit | Weak | High | **HIGH** |
| Implied | Strong | High | **MEDIUM** |
| Implied | Weak | Medium | **MEDIUM** |
| Vague | Any | Any | **LOW** |
| Any | None | Any | **LOW** |

**Regla:** Solo generamos tests para claims con confianza HIGH.

---

## 4. Validación Metodológica

### 4.1 El Problema de Ground Truth

No existe un dataset estándar de "claims correctos". Solución: **validación por ejecución diferencial**.

### 4.2 Tres Configuraciones de Código

| Config | Estado del Repo | Descripción |
|--------|-----------------|-------------|
| C_bug | base_commit | Código buggy (antes del fix) |
| C_gold | base_commit + gold_patch | Código correcto (después del fix) |
| C_mut | gold + mutantes | Gold con mutaciones en líneas tocadas |

### 4.3 Criterios de Validez de un Claim-Test

Un claim-test es **válido** si y solo si:

```
1. FAIL en C_bug    (detecta el bug original)
2. PASS en C_gold   (el fix lo resuelve)  
3. MKR > 0 en C_mut (detecta regresiones)
```

**Intuición:**
- Si no falla en C_bug → no está testeando el bug
- Si no pasa en C_gold → el test está mal escrito o el claim es incorrecto
- Si no mata mutantes → el test es demasiado débil

### 4.4 Diagrama de Validación

```
                    ┌─────────────┐
                    │  Claim-Test │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
    ┌─────────┐       ┌─────────┐       ┌─────────┐
    │  C_bug  │       │  C_gold │       │  C_mut  │
    │  (run)  │       │  (run)  │       │  (run)  │
    └────┬────┘       └────┬────┘       └────┬────┘
         │                 │                 │
         ▼                 ▼                 ▼
      FAIL?             PASS?            KILLS?
         │                 │                 │
         └────────┬────────┴────────┬───────┘
                  ▼                 ▼
            All conditions    Any condition
                met?              fails?
                  │                 │
                  ▼                 ▼
            ✅ VALID           ❌ INVALID
              CLAIM              CLAIM
```

---

## 5. Métricas del Sistema

### 5.1 Métricas de Claims

| Métrica | Fórmula | Objetivo |
|---------|---------|----------|
| Extraction Rate | claims_extraídos / issues_procesados | Cobertura |
| Grounding Rate | claims_grounded / claims_extraídos | Relevancia |
| **CVR** (Claim Validity Rate) | claims_válidos / claims_grounded | Calidad |

### 5.2 Métricas de Tests

| Métrica | Fórmula | Objetivo |
|---------|---------|----------|
| Test Generation Rate | tests_compilables / claims | Factibilidad |
| **MKR** (Mutation Kill Rate) | mutantes_muertos / mutantes_totales | Robustez |

### 5.3 Métricas de Verificación (objetivo final)

| Métrica | Fórmula | Objetivo |
|---------|---------|----------|
| **FAR** (False Acceptance Rate) | false_accepts / total_patches | Reducir |
| Rejection Accuracy | true_rejects / (true_rejects + false_rejects) | Maximizar |

### 5.4 Comparación Experimental

```
Baseline (SWE-bench only):
  Patch → Run SWE-bench tests → PASS/FAIL

Our Method (SWE-bench + Claims):
  Patch → Run SWE-bench tests → Run Claim-tests → PASS/FAIL

Hypothesis: FAR_ours < FAR_baseline
```

---

## 6. Pipeline de Ejecución

### 6.1 Flujo Completo

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PIPELINE DE VERIFICACIÓN                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. INPUT                                                                │
│     ├── instance_id (e.g., "django__django-10914")                      │
│     ├── candidate_patch (parche a verificar)                            │
│     └── [gold_patch] (solo para validación)                             │
│                                                                          │
│  2. STATIC ANALYSIS                                                      │
│     ├── Ejecutar flake8, mypy, bandit, radon, pylint                    │
│     ├── Calcular SQI                                                     │
│     └── Si SQI < threshold → REJECT (early exit)                        │
│                                                                          │
│  3. SWE-BENCH TESTS                                                      │
│     ├── Aplicar patch en Singularity                                    │
│     ├── Ejecutar tests oficiales                                        │
│     └── Si tests FAIL → REJECT                                          │
│                                                                          │
│  4. CLAIM EXTRACTION (si no existe en cache)                            │
│     ├── LLM: problem_statement + gold_patch → claims                    │
│     ├── Filtrar por grounding                                           │
│     ├── Filtrar por confidence = HIGH                                   │
│     └── Guardar en claims/<instance_id>.json                            │
│                                                                          │
│  5. CLAIM-TEST GENERATION (si no existe en cache)                       │
│     ├── Para cada claim: LLM → pytest test                              │
│     ├── Validar sintaxis (compile check)                                │
│     ├── Test-fixer: corregir imports si necesario                       │
│     └── Guardar en claim-tests/<instance_id>/                           │
│                                                                          │
│  6. CLAIM-TEST EXECUTION                                                 │
│     ├── Sync claim-tests al repo                                        │
│     ├── Ejecutar en Singularity con el patch candidato                  │
│     └── Si algún claim-test FAIL → REJECT                               │
│                                                                          │
│  7. OUTPUT                                                               │
│     ├── verification_result: ACCEPT / REJECT                            │
│     ├── sqi_score: float                                                │
│     ├── swebench_tests: {passed: N, failed: M}                          │
│     ├── claim_tests: {passed: N, failed: M, details: [...]}             │
│     └── rejection_reasons: [...]                                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Validación de Claims (fase de desarrollo)

Durante el desarrollo, validamos claims usando el gold patch:

```python
def validate_claims_for_instance(instance_id):
    instance = load_instance(instance_id)
    claims = load_or_extract_claims(instance)
    
    results = []
    for claim in claims:
        test_code = generate_test(claim, instance)
        
        # Ejecutar en las 3 configuraciones
        bug_result = run_test(test_code, config='bug')
        gold_result = run_test(test_code, config='gold')
        mut_results = run_mutation_tests(test_code, instance)
        
        is_valid = (
            not bug_result.passed and 
            gold_result.passed and 
            mut_results.kill_rate > 0
        )
        
        results.append({
            'claim_id': claim['claim_id'],
            'is_valid': is_valid,
            'bug_fails': not bug_result.passed,
            'gold_passes': gold_result.passed,
            'mkr': mut_results.kill_rate
        })
    
    return results
```

---

## 7. Clasificación de Issues de SWE-bench Lite

### 7.1 Distribución por Repositorio

| Repo | Issues | Dificultad Claims | Recomendación |
|------|--------|-------------------|---------------|
| django/django | ~90 | ⭐⭐ Media | Filtrar por módulo |
| sympy/sympy | ~50 | ⭐⭐⭐ Alta | Evitar inicialmente |
| scikit-learn | ~30 | ⭐⭐⭐ Alta | Evitar |
| matplotlib | ~25 | ⭐⭐⭐⭐ Alta | Evitar |
| astropy | ~20 | ⭐⭐ Media | Buenos candidatos |
| sphinx | ~20 | ⭐⭐⭐ Alta | Evitar |
| pytest | ~15 | ⭐ Baja | **Ideales** |
| pylint | ~15 | ⭐ Baja | **Ideales** |
| xarray | ~15 | ⭐⭐ Media | Buenos |
| requests | ~10 | ⭐ Baja | **Ideales** |
| flask | ~10 | ⭐ Baja | **Ideales** |

### 7.2 Tiers para Experimentación

**Tier 1 (Empezar aquí):** pytest, pylint, requests, flask
- Requisitos explícitos en issues
- Comportamiento observable (return/exception)
- Patches pequeños

**Tier 2 (Expandir después):** django (subconjunto), astropy, xarray
- Requisitos semi-explícitos
- Necesita filtrado cuidadoso

**Tier 3 (Evitar inicialmente):** matplotlib, sklearn, sympy, sphinx
- Output visual o numérico difícil de testear
- Requisitos implícitos

### 7.3 Script de Scoring

Ver `score_issues.py` para clasificar automáticamente issues por dificultad.

```bash
python score_issues.py --tier 1 --output easy_issues.json
python score_issues.py --top 50 --min-score 60 --output experiment_set.json
```

---

## 8. Prompts del Sistema

### 8.1 Prompt de Extracción de Claims

```
You are a software verification expert. Extract testable behavioral 
claims from a GitHub issue and its fix.

## Issue
{problem_statement}

## Gold Patch (for grounding only)
{patch}

## Task
Extract behavioral claims that:
1. Are explicitly stated or strongly implied in the issue
2. Can be verified by a unit test
3. Target symbols that appear in the patch

## Output Format
Return JSON array with: claim_id, claim_type, claim_text, given, 
when, then, confidence, target_symbols, evidence

## Rules
- Only extract claims grounded in the issue text (no invention)
- Every claim must reference at least one symbol from the patch
- Prefer "return" and "exception" claims (more testable)
```

### 8.2 Prompt de Generación de Tests

```
You are a test engineer. Generate a pytest test for the following 
behavioral claim.

## Claim
{claim_json}

## Target Module
Repository: {repo}
File modified: {target_file}

## Requirements
- Test must be self-contained
- Use standard pytest assertions
- Handle claim_type appropriately:
  - "return": assert func() == expected
  - "exception": pytest.raises()
  - "invariant": multiple assertions
  - "state_change": before/after comparison

## Output
```python
def test_claim_{claim_id}():
    # Given: {given}
    # When: {when}
    # Then: {then}
    ...
```
```

---

## 9. Estado Actual del Proyecto

### 9.1 Completado ✅

| Componente | Estado | Notas |
|------------|--------|-------|
| DatasetLoader | ✅ | HF API, filtros, normalización |
| Singularity Runner | ✅ | Reproducibilidad verificada |
| Static Analysis (SQI) | ✅ | 5 herramientas integradas |
| Streamlit App | ✅ | Orquestación básica |
| Diseño de Claims | ✅ | Schema JSON definido |
| Clasificación Issues | ✅ | Scoring automático (300 issues) |
| **Grounding Check** | ✅ | **Módulo completo con tests y demo** |
| Documentación | ✅ | Este documento |

### 9.2 En Progreso 🔄

| Componente | Estado | Próximos pasos |
|------------|--------|----------------|
| Claim Extraction | 🔄 | Extracción manual de 5-10 issues |
| Test Generation | 🔄 | Implementar generación básica |
| Test Fixer | 🔄 | Manejo de imports |
| Validación Manual | 🔄 | Validar claims en C_bug/C_gold |

### 9.3 Pendiente 📋

| Componente | Prioridad | Dependencias |
|------------|-----------|--------------|
| Validación C_bug/C_gold/C_mut | Alta | Claim extraction |
| Mutation Testing Integration | Alta | Test generation |
| Métricas Dashboard | Media | Validación |
| Ablation Studies | Media | Pipeline completo |
| Paper/Thesis Writing | Baja | Experimentos |

### 9.4 Módulo Grounding Check - Detalles de Implementación ✅

**Fecha de implementación:** 21 Enero 2026

El módulo `claim_extraction/grounding.py` implementa el grounding check completo:

#### Funciones Principales

```python
# 1. Extracción de símbolos del patch
symbols = extract_symbols_from_diff(patch)
# Extrae funciones, clases y métodos modificados
# Estrategias: hunk headers, definiciones, context lines

# 2. Verificación de grounding
is_grounded = is_claim_grounded(claim, patch, require_strong=False)
# Verifica si los target_symbols del claim están en el patch

# 3. Cálculo de fuerza de grounding
result = calculate_grounding_strength(claim, patch)
# Retorna: GroundingResult con strength='strong'|'weak'|'none'

# 4. Filtrado de claims
grounded, ungrounded = filter_grounded_claims(claims, patch, min_strength='weak')
# Filtra lista completa de claims por grounding
```

#### Características Implementadas

- **Symbol Extraction**: Parsea git diffs usando regex patterns para:
  - Hunk headers (`@@ ... @@ def function_name`)
  - Function/class definitions (`-def old()` / `+def new()`)
  - Context lines con definiciones

- **Symbol Normalization**: Maneja símbolos dotados como `Table.read` → `{Table, read, Table.read}`

- **Grounding Types**:
  - **Strong**: Todos los `target_symbols` están en el patch
  - **Weak**: Al menos un `target_symbol` está en el patch
  - **None**: Ningún símbolo matchea

- **Metadata**: Los claims grounded incluyen información de grounding:
  ```json
  {
    "grounding": {
      "is_grounded": true,
      "strength": "strong",
      "matched_symbols": ["_parse_qdp_commands"],
      "unmatched_symbols": [],
      "match_ratio": 1.0
    }
  }
  ```

#### Tests y Validación

- **Tests unitarios**: `tests/test_grounding.py` (28 test cases)
  - Extracción de símbolos (funciones, clases, métodos)
  - Normalización de símbolos dotados
  - Grounding simple y complejo
  - Weak vs strong grounding
  - Filtrado de claims
  - Escenarios de integración con ejemplos reales

- **Demo interactivo**: `demo_grounding.py`
  - 5 ejemplos completos con datos reales de SWE-bench
  - Ejemplo grounded (astropy__astropy-7746)
  - Ejemplo NOT grounded (mismo issue)
  - Filtrado múltiple (Django scenario)
  - Extracción de símbolos complejos
  - Comparación weak vs strong

#### Resultados del Demo

Ejecutando `python demo_grounding.py`:

```
EJEMPLO 1: astropy__astropy-7746
  Claim: "_parse_qdp_commands must handle lowercase"
  Patch symbols: {_parse_qdp_commands, _line_type}
  ✅ GROUNDED (strength: STRONG, match ratio: 100%)

EJEMPLO 2: Mismo issue
  Claim: "Table.read must not raise ValueError"
  Patch symbols: {_parse_qdp_commands}
  ❌ NOT GROUNDED (Table.read no está en el patch)

EJEMPLO 3: Django filtering
  3 claims → 1 grounded (33%), 2 not grounded (67%)
```

#### Integración con Pipeline

El grounding check se integrará en dos puntos:

1. **Post-extracción** (filtro):
   ```python
   raw_claims = llm_extract_claims(problem_statement)
   grounded, _ = filter_grounded_claims(raw_claims, patch)
   save_claims(instance_id, grounded)  # Solo guardar grounded
   ```

2. **Pre-validación** (verificación de calidad):
   ```python
   def validate_claim_quality(claim, patch):
       grounding = calculate_grounding_strength(claim, patch)
       return grounding.is_grounded and grounding.strength != 'none'
   ```

#### Archivos Creados

```
claim_extraction/
├── __init__.py          # Exports del módulo
├── grounding.py         # Implementación completa (300 líneas)
└── README.md            # Documentación del módulo

tests/
└── test_grounding.py    # 28 test cases (400 líneas)

demo_grounding.py         # Demo interactivo (350 líneas)
```

#### Métricas Objetivo

- **Grounding Rate**: ≥ 60% de claims extraídos deben estar grounded
- Si < 50% → Revisar prompt de extracción (puede estar generando claims muy amplios)
- Si > 80% → Excelente, el prompt está bien calibrado

---

## 10. Plan de Trabajo (Actualizado)

### Fase 1: Validación del Pipeline (Semanas 1-2)

**✅ Completado:**
1. ✅ Ejecutado `score_issues.py` - 300 issues clasificados
2. ✅ Implementado módulo de grounding check completo
3. ✅ Tests y demo funcionando correctamente

**🔄 En progreso:**
4. Seleccionar 5 issues perfectos (score=100, Tier 1)
5. Extracción manual de claims para validación del concepto
6. Ejecutar grounding check en claims extraídos
7. Medir grounding rate inicial

**📋 Siguiente:**
8. Generar tests para claims grounded (manual/Claude)
9. Validar en C_bug/C_gold
10. Calcular CVR (Claim Validity Rate)
11. Decisión: ¿CVR ≥ 70%? → Si no, iterar en diseño de claims

### Fase 2: Automatización (Semanas 2-3)

1. Configurar Qwen2.5-32B o Llama-70B en cluster
2. Implementar pipeline de extracción automática
3. Implementar generación de tests
4. Implementar test-fixer para imports
5. Validar CVR en 20-30 issues

### Fase 3: Evaluación (Semanas 4-5)

1. Integrar mutation testing (mutmut)
2. Ejecutar validación completa en 50 issues
3. Calcular métricas: CVR, MKR, FAR
4. Comparar baseline vs our method
5. Ablation: sin claims / claims simples / claims complejos

### Fase 4: Escritura (Semanas 6-8)

1. Análisis de resultados
2. Redacción de tesis/paper
3. Visualizaciones y tablas
4. Revisión con advisor

---

## 11. Infraestructura

### 11.1 Hardware (UMD Nexus Cluster)

- GPU: RTX A6000 (48GB VRAM)
- Suficiente para: Qwen2.5-72B-AWQ, Llama-70B-GPTQ

### 11.2 Entornos Python

```
verifier_harness/     # Streamlit + runner + analysis
├── requirements.txt  # streamlit, singularity bindings, pytest

verifier_llm/         # Claim extraction + test generation
├── requirements.txt  # transformers, vllm, torch
```

### 11.3 Estructura de Directorios

```
/fs/nexus-scratch/ihbas/verifier_harness/
├── app/                    # Streamlit app
├── runners/                # Singularity execution
├── analyzers/              # Static analysis
├── claim_extraction/       # ✨ NEW: Claim extraction module
│   ├── __init__.py
│   ├── grounding.py        # Grounding check implementation
│   ├── schema.py           # [FUTURO] Claim schemas
│   ├── extraction.py       # [FUTURO] LLM extraction
│   ├── test_generation.py  # [FUTURO] Test generation
│   └── README.md
├── swe_bench_analysis/     # Issue classification
│   ├── score_issues.py     # Scoring script
│   └── scored_issues.json  # 300 issues scored
├── claims/                 # Extracted claims JSON
│   └── <instance_id>.json
├── claim-tests/            # Generated tests
│   └── <instance_id>/
│       ├── test_claim_C1.py
│       └── test_claim_C2.py
├── tests/                  # Unit tests
│   └── test_grounding.py   # Grounding tests
├── results/                # Execution results
├── logs/                   # Execution logs
└── demo_grounding.py       # ✨ NEW: Interactive demo
```

---

## 12. Referencias

### Papers
- SWE-bench: Jimenez et al., ICLR 2024
- SWE-agent: Yang et al., 2024
- Agentless: Xia et al., 2024
- UTBoost: Yu et al., 2024

### Recursos
- SWE-bench: https://swebench.com
- Dataset: https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite
- Repositorio SWE-bench: https://github.com/SWE-bench/SWE-bench

---

## Apéndice A: JSON Schema Completo para Claims

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["instance_id", "claims"],
  "properties": {
    "instance_id": {"type": "string"},
    "extraction_model": {"type": "string"},
    "extraction_timestamp": {"type": "string", "format": "date-time"},
    "claims": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["claim_id", "claim_type", "claim_text", "confidence", "target_symbols"],
        "properties": {
          "claim_id": {"type": "string", "pattern": "^C[0-9]+$"},
          "claim_type": {"enum": ["return", "exception", "invariant", "state_change"]},
          "claim_text": {"type": "string", "minLength": 10},
          "given": {"type": "string"},
          "when": {"type": "string"},
          "then": {"type": "string"},
          "confidence": {"enum": ["high", "medium", "low"]},
          "confidence_factors": {
            "type": "object",
            "properties": {
              "requirement_specificity": {"enum": ["explicit", "implied", "vague"]},
              "diff_grounded": {"type": "boolean"},
              "observability": {"enum": ["high", "medium", "low"]}
            }
          },
          "target_symbols": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1
          },
          "evidence": {
            "type": "object",
            "properties": {
              "spans": {"type": "array", "items": {"type": "string"}},
              "line_numbers": {"type": "array", "items": {"type": "integer"}}
            }
          }
        }
      }
    }
  }
}
```

---

*Documento generado: Enero 2026*
*Última actualización: 21 Enero 2026 - Implementación completa del módulo de grounding check*
