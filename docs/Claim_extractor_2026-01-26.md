# Verification Harness for AI-Generated Patches
## Documento de Arquitectura v2.1 (Final)

**Autor:** [Tu nombre]  
**Tipo:** Trabajo Fin de Máster  
**Universidad:** University of Maryland  
**Fecha:** Enero 2026

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
10. [Implementación](#10-implementación)

---

## 1. Resumen Ejecutivo

### 1.1 Problema

Los agentes de IA que generan parches de código se evalúan ejecutando tests existentes. Esto produce **false acceptances**: parches que pasan tests pero no cumplen la intención del issue.

### 1.2 Solución

Un **verification harness** con tres capas:

1. **Ejecución reproducible** en contenedores Singularity
2. **Análisis estático** (SQI - Static Quality Index)
3. **Verificación semántica** basada en claims con grounding auditable

### 1.3 Contribución Principal

> *"Diseñamos un harness de verificación que extrae claims comportamentales desde el issue y código buggy, los valida mediante grounding multinivel AUDITABLE contra el patch, y los filtra con scoring compuesto basado en evidencia verificada, reduciendo false acceptances comparado con tests baseline."*

### 1.4 Posicionamiento

**El sistema es un "Filtro de Seguridad", NO un "Oráculo Absoluto".**

| El sistema... | Significa que... |
|---------------|------------------|
| ❌ No es oráculo | No garantiza corrección absoluta |
| ✅ Es filtro | Identifica parches sospechosos para revisión |
| ✅ Es auditable | Cada decisión tiene evidencia verificable |
| ✅ Es reproducible | Criterios concretos y deterministas |

---

## 2. Arquitectura del Sistema

### 2.1 Diagrama General

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     VERIFICATION HARNESS v2.1 (FINAL)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ CAPA 0: ELIGIBILITY FILTER                                            │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐│  │
│  │  │ Criterios concretos:                                             ││  │
│  │  │ • Excepción concreta (ValueError, KeyError, etc.) → +2          ││  │
│  │  │ • Stacktrace presente → +2                                       ││  │
│  │  │ • Keyword comportamental (returns, raises, fails) → +1          ││  │
│  │  │ • Referencias a código (`func`, func()) → +1                    ││  │
│  │  │ UMBRAL: score ≥ 2 → ELIGIBLE                                    ││  │
│  │  └──────────────────────────────────────────────────────────────────┘│  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                         │                                    │
│                                         ▼                                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ CAPA 1: EXTRACCIÓN DE CLAIMS                                          │  │
│  │  Issue + Code Context → LLM → JSON Parser (4 fallbacks) → Raw Claims │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                         │                                    │
│                                         ▼                                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ CAPA 2: GROUNDING MULTINIVEL (AUDITABLE)                              │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐│  │
│  │  │ STRONG (solo definiciones):                                      ││  │
│  │  │  • defined_functions en diff → +3                               ││  │
│  │  │  • defined_classes en diff → +3                                 ││  │
│  │  │  • assigned_attrs (CONST=, self.attr=) en diff → +3            ││  │
│  │  │  ❌ NO llamadas (upper(), split(), etc.)                        ││  │
│  │  ├──────────────────────────────────────────────────────────────────┤│  │
│  │  │ WEAK_FILE: símbolo en archivo tocado → +1                       ││  │
│  │  ├──────────────────────────────────────────────────────────────────┤│  │
│  │  │ WEAK_REF: símbolo importado en contexto → +1                    ││  │
│  │  ├──────────────────────────────────────────────────────────────────┤│  │
│  │  │ EVIDENCIA AUDITABLE por cada match:                             ││  │
│  │  │  {type, symbol, path, line, snippet}                            ││  │
│  │  └──────────────────────────────────────────────────────────────────┘│  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                         │                                    │
│                                         ▼                                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ CAPA 3: VERIFICACIÓN DE EVIDENCIA (EXPANDIDA)                         │  │
│  │  • Evidence span en issue → +2                                       │  │
│  │  • Evidence en docstring/comment → +1                                │  │
│  │  • Match stacktrace (archivo+función) → +1                          │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                         │                                    │
│                                         ▼                                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ CAPA 4: SCORING COMPUESTO                                             │  │
│  │  score = grounding + evidence + observable + confidence              │  │
│  │  UMBRAL: score ≥ 2 → CLAIM ACEPTADO                                  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  OUTPUT: Claims auditables listos para generación de tests                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Claims y Grounding Auditable

### 3.1 Estructura de Claim con Evidencia

```json
{
  "claim_id": "C1",
  "claim_type": "exception",
  "claim_text": "_parse_qdp_commands must not raise ValueError for lowercase input",
  "given": "A command string 'read serr 1 2' in lowercase",
  "when": "_parse_qdp_commands(line) is called",
  "then": "Parses successfully without ValueError",
  "target_symbols": ["_parse_qdp_commands"],
  "confidence": "high",
  
  "evidence": {
    "spans": ["QDP commands are not case sensitive"]
  },
  
  "grounding": {
    "status": "strong",
    "level": 1,
    "matched_symbols": ["_parse_qdp_commands"],
    "rule": "symbol_in_diff_definition",
    "evidence": [
      {
        "type": "diff_definition",
        "symbol": "_parse_qdp_commands",
        "path": "astropy/io/ascii/qdp.py",
        "line": 68,
        "snippet": "def _parse_qdp_commands(line):"
      }
    ]
  },
  
  "evidence_verification": {
    "score": 2,
    "verified": true,
    "matches": [
      {
        "source": "issue",
        "type": "direct",
        "span": "QDP commands are not case sensitive"
      }
    ]
  },
  
  "specificity": {
    "is_specific": true,
    "has_symbols": true,
    "has_observable": true,
    "issues": []
  },
  
  "computed_score": 6,
  "score_factors": [
    "+3: strong_grounding (defined symbol in diff)",
    "+2: evidence_verified (issue)",
    "+1: has_observable"
  ]
}
```

### 3.2 Reglas de Grounding (ESTRICTAS)

#### STRONG Grounding (+3)

**Se concede SOLO si el símbolo aparece en:**

| Fuente | Patrón | Ejemplo |
|--------|--------|---------|
| Función definida | `[-+]\s*def\s+(\w+)\s*\(` | `+def _parse_qdp_commands(line):` |
| Clase definida | `[-+]\s*class\s+(\w+)\s*[:\(]` | `+class QDPReader:` |
| Atributo/constante | `[-+]\s*([A-Z_]+|self\.\w+)\s*=` | `+FILE_PERMISSIONS = 0o644` |

**❌ NO se concede strong por:**
- Llamadas a funciones: `upper()`, `split()`, `parse()`
- Métodos builtin: `len()`, `str()`, `append()`
- Llamadas namespaced: `line.upper()`, `self.parse()`

#### WEAK_FILE Grounding (+1)

El símbolo aparece en el contenido de un archivo tocado por el patch, pero no en el diff mismo.

```json
{
  "type": "file_reference",
  "symbol": "Table",
  "path": "astropy/io/ascii/qdp.py",
  "line": 15,
  "snippet": "from astropy.table import Table"
}
```

#### WEAK_REF Grounding (+1)

El símbolo es importado o referenciado en el contexto.

```json
{
  "type": "import_reference",
  "symbol": "QDPReader",
  "path": "code_context",
  "line": 0,
  "snippet": "from .qdp import QDPReader"
}
```

### 3.3 Normalización de Símbolos

Para matching flexible pero correcto:

| Input | Variantes Normalizadas |
|-------|------------------------|
| `Class.method` | `Class.method`, `Class`, `method` |
| `self.attr` | `self.attr`, `attr` |
| `FooBar` | `FooBar`, `foo_bar` |
| `foo_bar` | `foo_bar`, `FooBar` |

---

## 4. Eligibility Filter

### 4.1 Criterios Concretos (Reproducibles)

Un issue es **ELIGIBLE** si y solo si `eligibility_score ≥ 2` (suma de señales):

| Criterio | Detección | Score |
|----------|-----------|-------|
| Excepción concreta | `ValueError`, `TypeError`, `KeyError`, etc. en texto | +2 |
| Stacktrace | `File "...", line N` o `Traceback` | +2 |
| Keyword comportamental | `should return`, `raises`, `fails to`, `incorrectly` | +1 |
| Referencias código | Backticks `` `func` `` o `func()` | +1 |
| Ejemplos código | ` ``` ` o `>>>` | +1 |

**UMBRAL:** `eligibility_score ≥ 2` (suma de señales)

### 4.2 Ejemplos

**✅ ELIGIBLE:**
```
"Table.read() raises ValueError when QDP file has lowercase commands"
→ Score: 4 (exception + behavior keyword + code ref)
```

**✅ ELIGIBLE:**
```
"Traceback...
  File 'django/forms/fields.py', line 45, in clean
    raise ValidationError(...)"
→ Score: 4 (stacktrace + exception)
```

**❌ INELIGIBLE:**
```
"This doesn't work, seems broken"
→ Score: 0 (vague, no specific info)
```

**❌ INELIGIBLE:**
```
"There's a bug in the parser"
→ Score: 0 (vague, no exception/behavior/code)
```

### 4.3 Métrica

```
Eligibility Rate = issues_eligible / total_issues
```

---

## 5. Pipeline de Extracción

### 5.1 Flujo Completo

```
                    ┌──────────────────┐
                    │   SWE-bench      │
                    │   Instance       │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Eligibility      │
                    │ Filter           │
                    └────────┬─────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    ▼                 ▼
              ELIGIBLE          INELIGIBLE
                    │                 │
                    ▼                 ▼
              Continue           Skip + Log
                    │
                    ▼
         ┌─────────────────────┐
         │ CodeContextBuilder  │
         │ • Patch files ±50L  │
         │ • Stacktrace files  │
         │ • Docstrings        │
         │ • Symbol search     │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │ LLM (Qwen2.5-Coder) │
         │ + Improved Prompt   │
         │ + Negative Examples │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │ JSON Parser         │
         │ 4 fallback levels   │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │ Raw Claims          │
         └──────────┬──────────┘
                    │
         ┌──────────┴──────────┐
         │                     │
         ▼                     ▼
    ┌─────────┐          ┌───────────┐
    │ Patch   │          │ Code      │
    │ Symbols │          │ Context   │
    │ (strict)│          │           │
    └────┬────┘          └─────┬─────┘
         │                     │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │ Grounding Check     │
         │ (with evidence)     │
         └──────────┬──────────┘
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
    GROUNDED              UNGROUNDED
         │                     │
         ▼                     ▼
    Continue               Discard
         │
         ▼
    ┌─────────────────────┐
    │ Evidence Verify     │
    │ (issue+doc+stack)   │
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │ Compute Score       │
    │ + Specificity       │
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │ Filter: score ≥ 2   │
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │ Final Claims        │
    │ (auditable)         │
    └─────────────────────┘
```

---

## 6. Sistema de Scoring

### 6.1 Fórmula Compuesta

```
score = grounding_score + evidence_score + observable_score + confidence_score
```

### 6.2 Componentes

| Componente | Condición | Puntos |
|------------|-----------|--------|
| **Grounding** | strong (defined symbol) | +3 |
| | weak_file o weak_ref | +1 |
| | none | +0 |
| **Evidence** | span directo en issue | +2 |
| | span parcial (fuzzy match, umbral configurable) | +1 |
| | en docstring/comment | +1 |
| | match stacktrace | +1 |
| | (máximo +3) | |
| **Observable** | tiene keyword observable | +1 |
| | no tiene observable | -1 |
| **Confidence** | high | +1 |
| | medium | +0 |
| | low | -1 |


#### Lista base de *observable keywords* (determinista)

Se usa un conjunto fijo de términos para marcar *observables* (return/exception/state). Lista base (ampliable):

- **Return/value**: `return`, `returns`, `result`, `value`, `output`, `equals`, `==`
- **Exception**: `raise`, `raises`, `exception`, `error`, `not raise`, `not throw`
- **State change**: `set`, `sets`, `update`, `updates`, `create`, `creates`, `delete`, `deletes`, `write`, `writes`

> Nota: esta lista es un parámetro del harness y se reporta en `metadata` para reproducibilidad.

### 6.3 Umbral

**score ≥ 2** → Claim aceptado

### 6.4 Ejemplos de Score

**Claim A: score = 6 ✅**
```
+3: strong_grounding (defined symbol in diff)
+2: evidence_verified (direct match in issue)
+1: has_observable
+0: medium_confidence
= 6
```

**Claim B: score = 2 ✅ (borderline)**
```
+1: weak_file
+1: evidence in docstring
+1: has_observable
-1: low_confidence
= 2
```

**Claim C: score = 0 ❌**
```
+0: no_grounding
+0: evidence_not_verified
-1: no_observable
+1: high_confidence
= 0
```

### 6.5 Claim Specificity

Un claim es **específico** si:

| Criterio | Check |
|----------|-------|
| Tiene símbolos | `len(target_symbols) > 0` |
| Tiene observable | Keyword en `then` |
| No es vago | Sin "properly", "correctly", etc. |
| Given concreto | `len(given) > 10` |
| When concreto | `len(when) > 10` |

**Métrica:** `specificity_rate = specific_claims / total_claims`

---

## 7. Validación Metodológica

### 7.1 Tres Configuraciones

| Config | Estado | Descripción |
|--------|--------|-------------|
| C_bug | base_commit | Código con bug |
| C_gold | base_commit + gold_patch | Código correcto |
| C_mut | gold + mutantes | Gold con mutaciones |

### 7.2 Criterios de Validez

Un claim-test es **válido** si y solo si:

```
1. FAIL en C_bug    → detecta el bug original
2. PASS en C_gold   → el fix lo resuelve
3. MKR > 0 en C_mut → detecta regresiones (no overfitted)
```

### 7.3 Por Qué Esta Validación Funciona

La validación diferencial es nuestra **defensa principal** contra el sesgo de self-confirmation:

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEFENSA CONTRA SESGO                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  CLAIM (generado por LLM)                                       │
│        │                                                         │
│        │  ¿Podría ser inventado/incorrecto?                     │
│        │                                                         │
│        ▼                                                         │
│  ┌─────────────┐                                                │
│  │ GROUNDING   │ → "¿Toca código que realmente cambió?"         │
│  │ AUDITABLE   │    (con evidencia: path, line, snippet)        │
│  └──────┬──────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────┐                                                │
│  │ EVIDENCE    │ → "¿Está soportado por el issue real?"         │
│  │ VERIFIED    │    (no solo LLM dice que sí)                   │
│  └──────┬──────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────┐                                                │
│  │ SCORING     │ → "¿Tiene suficiente calidad?"                 │
│  │ COMPUESTO   │    (múltiples factores, no solo uno)           │
│  └──────┬──────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────┐                                                │
│  │ VALIDACIÓN  │ → "¿Funciona en la práctica?"                  │
│  │ DIFERENCIAL │    FAIL(C_bug) ∧ PASS(C_gold) ∧ MKR>0         │
│  └─────────────┘                                                │
│                                                                  │
│  Solo si pasa TODAS las capas → Claim considerado válido        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Críticas y Defensas

### 8.1 Crítica A: GIGO (Garbage In, Garbage Out)

**Problema:** Issues vagos producen claims inventados.

**Defensa implementada:**

| Capa | Mecanismo |
|------|-----------|
| Eligibility Filter | Criterios concretos con score ≥ 2 |
| Prompt | Checklist + ejemplos negativos |
| Fallback | Si vago → return `[]` |
| Métrica | Reportamos `eligibility_rate` |

**En la tesis:** *"Reconocemos que no todos los issues son procesables. Reportamos eligibility rate de X% y solo evaluamos sobre issues elegibles."*

### 8.2 Crítica B: Abismo JSON → Código

**Problema:** Tests generados fallan por imports, fixtures.

**Defensa:**

| Capa | Mecanismo |
|------|-----------|
| Métricas separadas | Compilation, Execution, Validity |
| Test fixer | Auto-reparar imports comunes |
| Scope | Solo unit tests, sin DB/network |

**En la tesis:** *"Separamos métricas por etapa para identificar dónde falla el pipeline. La compilation rate de Y% indica que Z% de claims son inherentemente no-testeables en este framework."*

### 8.3 Crítica C: Grounding por Ruido

**Problema:** "Tu strong grounding se activa por `upper()` y otras llamadas."

**Defensa implementada:**

```
STRONG grounding SOLO por:
  • defined_functions en diff
  • defined_classes en diff
  • assigned_attrs en diff

❌ NO por llamadas (upper, split, len, etc.)
```

**En la tesis:** *"Strong grounding se restringe a símbolos DEFINIDOS en el diff, no llamadas. Esto elimina falsos positivos por builtins y métodos comunes. Ver Sección 3.2 para reglas exactas."*

### 8.4 Crítica D: Self-Confirmation Bias

**Problema:** LLM inventa claim → weak grounding lo acepta → falso positivo.

**Defensa (multicapa, NO solo "cambiar modelo"):**

```
┌────────────────────────────────────────────────────────────────┐
│ DEFENSA MULTICAPA CONTRA SELF-CONFIRMATION                      │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 1. GROUNDING AUDITABLE                                         │
│    - Cada match tiene evidencia verificable                    │
│    - Path, line, snippet concretos                             │
│    - No es "el LLM dice que sí"                                │
│                                                                 │
│ 2. EVIDENCE VERIFICATION EXTERNA                               │
│    - Verificamos spans contra issue ORIGINAL                   │
│    - No contra lo que el LLM generó                            │
│    - String matching, no LLM judgment                          │
│                                                                 │
│ 3. SCORING COMPUESTO                                           │
│    - Múltiples factores independientes                         │
│    - No basta con que LLM diga "high confidence"               │
│    - Grounding + Evidence + Observable requeridos              │
│                                                                 │
│ 4. VALIDACIÓN DIFERENCIAL (C_bug/C_gold/C_mut)                 │
│    - Prueba empírica de que el claim detecta el bug            │
│    - El test DEBE fallar en buggy, pasar en gold               │
│    - No basta con "el claim suena correcto"                    │
│                                                                 │
│ 5. (OPCIONAL) MODELOS DIFERENTES                               │
│    - Claims: Qwen-72B                                          │
│    - Tests: Llama-70B                                          │
│    - Ablation para medir impacto                               │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**En la tesis:** *"La defensa contra self-confirmation NO depende únicamente de usar modelos diferentes. Implementamos verificación multicapa: grounding auditable con evidencia concreta (path, line, snippet), verificación de evidence spans contra el issue original mediante string matching, scoring compuesto que requiere múltiples factores, y validación diferencial empírica. Ver Sección 7 para el framework completo."*

### 8.5 Crítica E: ¿Y si el Grounding Weak es Ruido?

**Defensa:**

1. **Métricas separadas:** Reportamos strong vs weak por separado
2. **Grounding Precision Sampled:** Muestreo manual de 30 claims weak para estimar falsos positivos
3. **Ablation:** Comparar resultados usando solo strong vs strong+weak

**En la tesis:** *"Para validar la precisión del grounding weak, realizamos muestreo manual de N=30 claims, encontrando una precision de X%. Ver Apéndice B para metodología de evaluación."*

---

## 9. Métricas

### 9.1 Métricas de Eligibility

| Métrica | Fórmula | Propósito |
|---------|---------|-----------|
| Eligibility Rate | `eligible / total` | Cobertura del método |

### 9.2 Métricas de Extracción

| Métrica | Fórmula | Propósito |
|---------|---------|-----------|
| Extraction Rate | `raw_claims / eligible_issues` | Productividad |
| Parse Success | `parsed / extractions` | Robustez del parser |
| Grounding Rate | `grounded / extracted` | Relevancia |

### 9.3 Métricas de Calidad de Claims

| Métrica | Fórmula | Propósito |
|---------|---------|-----------|
| **Specificity Rate** | `specific_claims / total_claims` | Calidad de formulación |
| **Evidence Verified Rate** | `verified / total_claims` | Soporte en issue |
| Strong Grounding % | `strong / grounded` | Conexión directa |
| Avg Claim Score | `Σscore / claims` | Calidad general |

### 9.4 Métricas de Validación (Nuevas)

| Métrica | Fórmula | Propósito |
|---------|---------|-----------|
| **Grounding Precision (Sampled)** | Manual eval 30 claims | Validar weak grounding |
| CVR (Claim Validity Rate) | `valid_tests / executed_tests` | Efectividad |
| MKR (Mutation Kill Rate) | `killed / mutants` | Robustez |

**Metodología (Grounding Precision Sampled):** muestreo estratificado por `weak_file`/`weak_ref` (N=30), anotación con guideline fija; opcionalmente 2 anotadores y acuerdo (Cohen’s κ).

### 9.5 Métrica Final

**Definición operacional:** un *false acceptance* ocurre cuando un parche **pasa los tests baseline** pero **falla** al menos un claim-test considerado válido por nuestro criterio diferencial (`FAIL(C_bug) ∧ PASS(C_gold) ∧ MKR>0`).



| Métrica | Fórmula | Objetivo |
|---------|---------|----------|
| **FAR Reduction** | `1 - FAR_ours / FAR_baseline` | Maximizar |

---

## 10. Implementación

### 10.1 Estructura

```
claim_extraction_v2.1/
├── claim_extractor.py      # Pipeline principal
├── prepare_instances.py    # Preparación de datos
├── requirements.txt        # Dependencias
└── PROJECT_DOCUMENTATION.md
```

### 10.2 Uso

```bash
# 1. Preparar instancias
python prepare_instances.py \
    --output instances.json \
    --tier 1 --limit 20

# 2. Extraer claims (con todas las mejoras v2.1)
python claim_extractor.py \
    --input instances.json \
    --output claims/ \
    --min-score 2

# 3. Ver métricas
cat claims/summary.json | jq '
  .eligibility,
  .totals,
  .by_grounding,
  .quality_metrics
'
```

### 10.3 Output Ejemplo

```json
{
  "eligibility": {
    "total_instances": 20,
    "eligible": 18,
    "ineligible": 2,
    "eligibility_rate": 0.90
  },
  "totals": {
    "total_raw_claims": 42,
    "total_grounded_claims": 36,
    "total_final_claims": 31,
    "grounding_rate": 0.857
  },
  "by_grounding": {
    "strong": 22,
    "weak_file": 7,
    "weak_ref": 2
  },
  "quality_metrics": {
    "avg_specificity_rate": 0.84,
    "avg_evidence_verified_rate": 0.71,
    "avg_claim_score": 4.2
  }
}
```

---

## Apéndice A: Checklist para Defensa de Tesis

### Preguntas Anticipadas y Respuestas

| Pregunta del Tribunal | Respuesta Preparada |
|----------------------|---------------------|
| "¿No es esto GIGO?" | "Filtramos con eligibility criteria concretos. Reportamos eligibility rate." |
| "¿Cómo saben que el grounding es correcto?" | "Cada grounding tiene evidencia auditable: path, line, snippet. Además, muestreo manual de 30 claims." |
| "¿Y el weak grounding?" | "Reportamos strong vs weak por separado. Ablation muestra impacto de cada nivel." |
| "¿No es self-confirmation?" | "Defensa multicapa: grounding auditable + evidence verification externa + validación diferencial. No depende de cambiar modelo." |
| "¿Por qué no es un oráculo?" | "Es un filtro de alta recall. Identifica sospechosos para revisión, no garantiza corrección." |
| "¿Funciona en la práctica?" | "Validación diferencial: FAIL(C_bug), PASS(C_gold), MKR>0. Reducimos FAR en X%." |

---

## Apéndice B: Schema JSON Completo


> **Convención de niveles:** `level` codifica el tipo de grounding para trazabilidad:  
> `0 = none`, `1 = strong`, `2 = weak_file`, `3 = weak_ref`.


```json
{
  "instance_id": "string",
  "eligible": true,
  "eligibility": {
    "score": 4,
    "reasons": ["mentions_exception:ValueError", "has_stacktrace"]
  },
  "claims": [
    {
      "claim_id": "C1",
      "claim_type": "exception|return|invariant|state_change",
      "claim_text": "string",
      "given": "string",
      "when": "string", 
      "then": "string",
      "target_symbols": ["string"],
      "confidence": "high|medium|low",
      "evidence": {
        "spans": ["string"]
      },
      "grounding": {
        "status": "strong|weak_file|weak_ref|none",
        "level": 0,  # 0:none, 1:strong, 2:weak_file, 3:weak_ref

        "matched_symbols": ["string"],
        "rule": "string",
        "evidence": [
          {
            "type": "diff_definition|file_reference|import_reference",
            "symbol": "string",
            "path": "string",
            "line": 123,
            "snippet": "string"
          }
        ]
      },
      "evidence_verification": {
        "score": 2,
        "verified": true,
        "matches": [
          {
            "source": "issue|docstring_comment|stacktrace",
            "type": "direct|partial|function_match",
            "span": "string"
          }
        ]
      },
      "specificity": {
        "is_specific": true,
        "has_symbols": true,
        "has_observable": true,
        "issues": []
      },
      "computed_score": 6,
      "score_factors": ["string"]
    }
  ],
  "stats": {
    "eligible": true,
    "raw_claims": 3,
    "grounded_claims": 2,
    "final_claims": 2,
    "grounding_rate": 0.67,
    "specificity_rate": 1.0,
    "evidence_verified_rate": 0.5,
    "avg_score": 5.0
  }
}
```

---

*Documento v2.1 Final - Enero 2026*
