# Claim Extraction Module

Este módulo implementa la extracción y validación de claims comportamentales desde GitHub issues y sus patches correspondientes.

## 🎯 ¿Qué es el Grounding Check?

El **grounding check** verifica que un claim extraído del issue realmente se refiere a código que fue modificado en el gold patch. Esto previene generar tests para claims irrelevantes o sobre funcionalidad no tocada por el fix.

### Problema que resuelve

```
Issue: "Table.read() crashes with lowercase QDP commands"

Claims extraídos del issue:
✅ C1: "_parse_qdp_commands must handle lowercase"
❌ C2: "Table.read must not crash"
❌ C3: "validate_input should check commands"

Gold Patch solo modifica: _parse_qdp_commands

Resultado:
- Solo C1 está "grounded" (el patch realmente modifica ese símbolo)
- C2 y C3 NO están grounded (mencionados en el issue pero no en el patch)
```

## 📦 Componentes Implementados

### 1. `grounding.py`

Implementa el grounding check completo:

- **`extract_symbols_from_diff(patch: str)`** - Extrae funciones y clases modificadas del patch
- **`is_claim_grounded(claim: dict, patch: str)`** - Verifica si un claim está grounded
- **`calculate_grounding_strength(claim: dict, patch: str)`** - Calcula strong/weak/none
- **`filter_grounded_claims(claims: List[dict], patch: str)`** - Filtra lista de claims
- **`normalize_symbol(symbol: str)`** - Normaliza símbolos (maneja `Class.method`)

### 2. Tipos de Grounding

| Tipo | Condición | Uso |
|------|-----------|-----|
| **Strong** | Todos los target_symbols están en el patch | Alta confianza |
| **Weak** | Al menos un target_symbol está en el patch | Confianza media |
| **None** | Ningún target_symbol está en el patch | Descartar claim |

### 3. Extracción de Símbolos

El extractor busca símbolos en:

1. **Hunk headers** (más confiable): `@@ ... @@ def function_name`
2. **Definiciones modificadas**: `-def old_func()` o `+def new_func()`
3. **Definiciones de clases**: `-class OldClass:` o `+class NewClass:`
4. **Métodos en contexto**: Para cuando solo el body cambió

## 🚀 Uso

### Ejemplo Básico

```python
from claim_extraction.grounding import (
    extract_symbols_from_diff,
    is_claim_grounded,
    filter_grounded_claims
)

# 1. Extraer símbolos del patch
patch = """
diff --git a/auth.py b/auth.py
@@ -10,5 +10,5 @@ def authenticate(username, password):
-    return True
+    return validate_password(password)
"""

symbols = extract_symbols_from_diff(patch)
print(symbols)  # {'authenticate'}

# 2. Verificar un claim
claim = {
    'claim_id': 'C1',
    'target_symbols': ['authenticate']
}

is_grounded = is_claim_grounded(claim, patch)
print(is_grounded)  # True

# 3. Filtrar múltiples claims
claims = [
    {'claim_id': 'C1', 'target_symbols': ['authenticate']},
    {'claim_id': 'C2', 'target_symbols': ['login']},
    {'claim_id': 'C3', 'target_symbols': ['logout']}
]

grounded, ungrounded = filter_grounded_claims(claims, patch)
print(len(grounded))  # 1 (solo C1)
```

### Análisis Detallado

```python
from claim_extraction.grounding import calculate_grounding_strength

claim = {
    'target_symbols': ['authenticate', 'validate_password']
}

result = calculate_grounding_strength(claim, patch)
print(result.strength)          # 'weak' (solo authenticate matchea)
print(result.matched_symbols)   # {'authenticate'}
print(result.unmatched_symbols) # {'validate_password'}
print(result.to_dict())         # JSON serializable
```

### Demo Completo

```bash
python demo_grounding.py
```

Ejecuta 5 ejemplos que demuestran:
1. Claim grounded (astropy ejemplo real)
2. Claim NO grounded (mismo issue)
3. Filtrado de múltiples claims
4. Extracción de símbolos complejos
5. Weak vs Strong grounding

## 📊 Métricas

### Grounding Rate

```python
grounded, ungrounded = filter_grounded_claims(all_claims, patch)
grounding_rate = len(grounded) / len(all_claims)
```

**Target**: ≥ 60% grounding rate en experimentos

Si grounding rate < 50% → El prompt de extracción puede estar generando claims demasiado amplios

## 🧪 Testing

```bash
# Ejecutar tests (cuando pytest esté configurado)
pytest tests/test_grounding.py -v

# Ejecutar demo interactivo
python demo_grounding.py
```

Los tests cubren:
- Extracción de símbolos de diversos tipos de patches
- Normalización de símbolos dotados (`Class.method`)
- Grounding fuerte vs débil
- Filtrado de claims
- Escenarios reales de SWE-bench

## 🔄 Integración con Pipeline

### En Claim Extraction

```python
def extract_claims_with_grounding(instance_id, problem_statement, patch):
    # 1. Extraer claims con LLM
    raw_claims = llm_extract_claims(problem_statement)

    # 2. Filtrar por grounding
    grounded_claims, ungrounded = filter_grounded_claims(
        raw_claims,
        patch,
        min_strength='weak'  # o 'strong' para más restrictivo
    )

    # 3. Guardar solo grounded claims
    save_claims(instance_id, grounded_claims)

    # 4. Log ungrounded para análisis
    log_ungrounded_claims(instance_id, ungrounded)

    return grounded_claims
```

### En Validación de Claims

```python
def validate_claim_quality(claim, patch, instance):
    """Valida la calidad de un claim antes de generar test."""

    # Check 1: Grounding
    grounding = calculate_grounding_strength(claim, patch)
    if not grounding.is_grounded:
        return False, "Not grounded in patch"

    # Check 2: Confidence
    if claim['confidence'] != 'high':
        return False, "Confidence not high"

    # Check 3: Has GWT structure
    if not all(claim.get(k) for k in ['given', 'when', 'then']):
        return False, "Missing GWT structure"

    return True, "Valid claim"
```

## 📁 Estructura de Archivos

```
claim_extraction/
├── __init__.py           # Exports públicos
├── grounding.py          # Grounding check implementation
├── schema.py            # [FUTURO] JSON schema y dataclasses
├── extraction.py        # [FUTURO] LLM claim extraction
└── test_generation.py   # [FUTURO] Claim → pytest test

tests/
└── test_grounding.py    # Tests unitarios

demo_grounding.py         # Demo interactivo
```

## 🎓 Conceptos Clave

### ¿Por qué es necesario el grounding?

Los issues de GitHub frecuentemente mencionan:
- **Síntomas**: "La aplicación crashea cuando..."
- **Contexto**: "Probé con Table.read() y..."
- **Especulaciones**: "Tal vez el problema está en validate_input()"

**Pero el patch puede tocar solo una función específica** que es la verdadera raíz del problema.

Sin grounding → Generamos tests para código que no fue modificado → Tests pasan/fallan en ambos C_bug y C_gold → No validan nada.

Con grounding → Solo generamos tests para código modificado → Tests fallan en C_bug, pasan en C_gold → Validan el fix correctamente.

### Strong vs Weak Grounding

**Strong grounding** (todos los símbolos matchean):
- Claim muy específico sobre el código modificado
- Alta confianza en que el test será relevante
- Usar cuando quieres máxima precisión

**Weak grounding** (al menos un símbolo matchea):
- Claim puede referenciar código relacionado
- Aún útil pero puede ser menos preciso
- Usar para maximizar cobertura

**Recomendación**: Comenzar con weak grounding, analizar resultados, ajustar si necesario.

## 📈 Próximos Pasos

1. ✅ Grounding check implementado
2. ⬜ Schema de claims (JSON schema + dataclasses)
3. ⬜ Extracción automática con LLM
4. ⬜ Test generation pipeline
5. ⬜ Integración con Streamlit app

## 🔗 Referencias

- Documentación principal: `/docs/project_documentation_2026-01-21.md`
- Sección de grounding: Sección 3.3 del documento
- Scoring de issues: `/swe_bench_analysis/score_issues.py`
