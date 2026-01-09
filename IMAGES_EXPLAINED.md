# 🐳 Explicación del Sistema de Imágenes Docker/Singularity

## ❓ ¿Por cada instancia/patch genero una imagen nueva?

**SÍ**, cada instancia tiene su **propia imagen Docker** porque:
- Cada instancia es un **commit específico** del repositorio
- El código base es diferente para cada versión
- Los tests son específicos a ese commit

## 🏗️ Cómo funciona el sistema

### 1. Nomenclatura de Imágenes Docker

Para una instancia como `astropy__astropy-12907`:

```
Formato: swebench/sweb.eval.x86_64.{org}_1776_{repo}-{version}:latest

Ejemplo:
astropy__astropy-12907 → swebench/sweb.eval.x86_64.astropy_1776_astropy-12907:latest
astropy__astropy-13033 → swebench/sweb.eval.x86_64.astropy_1776_astropy-13033:latest
django__django-11234  → swebench/sweb.eval.x86_64.django_1776_django-11234:latest
```

**Cada versión = Imagen diferente** ❌ NO se reutilizan entre instancias

### 2. Patrones de búsqueda (config/swebench_config.yaml)

El sistema busca imágenes en orden de prioridad:

```yaml
image_patterns:
  - "swebench/sweb.eval.x86_64.{org}_1776_{repo}-{version}:latest"  # Oficial SWE-bench
  - "ghcr.io/swe-bench/sweb.eval.x86_64.{org}_1776_{repo}-{version}:latest"  # GitHub Registry
  - "aorwall/swe-bench-{repo}:{instance_id}"  # Alternativa
  - "swebench/{repo}:{instance_id}"  # Fallback
```

### 3. Proceso de construcción (primera vez)

```
1. Verificar caché → ❌ No existe
2. Resolver imagen Docker → swebench/sweb.eval.x86_64.astropy_1776_astropy-12907:latest
3. Descargar imagen Docker desde Docker Hub (varios GB)
4. Convertir a Singularity .sif
5. Guardar en caché → /fs/nexus-scratch/ihbas/.containers/singularity/swebench_cache/astropy/astropy__astropy-12907.sif
6. Usar la imagen
```

**Tiempo: ~5-15 minutos** (dependiendo del tamaño de la imagen)

### 4. Proceso con caché (segunda vez en adelante)

```
1. Verificar caché → ✅ Existe!
2. Usar imagen cacheada → /fs/nexus-scratch/.../astropy__astropy-12907.sif
3. Ejecutar tests inmediatamente
```

**Tiempo: ~segundos** (solo lectura del disco)

## 📊 Estructura del Caché

```
/fs/nexus-scratch/ihbas/.containers/singularity/swebench_cache/
├── astropy/
│   ├── astropy__astropy-12907.sif  (2.1 GB)
│   ├── astropy__astropy-13033.sif  (2.1 GB)
│   └── astropy__astropy-13236.sif  (2.1 GB)
├── scikit-learn/
│   ├── scikit-learn__scikit-learn-13241.sif  (3.2 GB)
│   └── scikit-learn__scikit-learn-13779.sif  (3.2 GB)
├── django/
│   └── django__django-11234.sif  (1.8 GB)
└── matplotlib/
    └── matplotlib__matplotlib-23913.sif  (2.5 GB)
```

**Cada archivo .sif es una imagen completa** con:
- Sistema operativo base
- Python + dependencias
- Código del repositorio en el commit específico
- Tests originales de SWE-bench

## 🔄 ¿Las imágenes se reutilizan?

### ❌ NO se reutilizan entre INSTANCIAS diferentes

```
astropy__astropy-12907 → imagen 12907 (commit A)
astropy__astropy-13033 → imagen 13033 (commit B)
                         ↑
                         Diferentes commits = Diferentes imágenes
```

### ✅ SÍ se reutilizan para LA MISMA instancia

```
Primera ejecución de astropy__astropy-12907:
  → Descarga + Construye .sif (10 min)

Segunda ejecución de astropy__astropy-12907:
  → Usa caché (instantáneo)

Tercera ejecución de astropy__astropy-12907:
  → Usa caché (instantáneo)
```

## 💾 Gestión del Caché

### Configuración (config/swebench_config.yaml)

```yaml
singularity:
  cache_dir: "/fs/nexus-scratch/ihbas/.containers/singularity/swebench_cache"
  max_cache_size_gb: 100  # Límite de 100 GB
  cleanup_after_days: 30  # Limpia imágenes > 30 días
  organize_by_repo: true  # Organiza por repositorio
```

### Ver estadísticas del caché

```python
from swebench_singularity import CacheManager

cache = CacheManager()
print(cache.get_cache_report())
```

Ejemplo de salida:
```
Singularity Cache Report
========================

Location: /fs/nexus-scratch/ihbas/.containers/singularity/swebench_cache
Total Entries: 52
Total Size: 87.3 GB

By Repository:
  astropy: 15 entries, 31.5 GB
  scikit-learn: 20 entries, 40.0 GB
  django: 10 entries, 10.2 GB
  matplotlib: 7 entries, 5.6 GB

Oldest Entry: astropy__astropy-12907 (12.3 days)
Largest Entry: scikit-learn__scikit-learn-13241 (3.2 GB)
```

### Limpiar caché manualmente

```bash
# Ver estadísticas
python scripts/swebench_cache_manager.py stats

# Limpiar imágenes viejas (>30 días)
python scripts/swebench_cache_manager.py cleanup --days 30

# Limpiar por tamaño (mantener <100GB)
python scripts/swebench_cache_manager.py cleanup --size 100

# Eliminar instancia específica
python scripts/swebench_cache_manager.py remove astropy__astropy-12907

# Limpiar TODO (¡cuidado!)
python scripts/swebench_cache_manager.py clear
```

## 📈 Optimizaciones del Sistema

### 1. **Caché local** (línea 617-627 en singularity_builder.py)
```python
if not force_rebuild:
    cached_path = self.cache.get(instance_id, repo_name)
    if cached_path:
        logger.info(f"Using cached image for {instance_id}: {cached_path}")
        return BuildResult(from_cache=True)  # ⚡ Instantáneo
```

### 2. **Pre-construcción de contenedores** (scripts/slurm/slurm_batch_build_containers.sh)
```bash
# Construir todas las imágenes de antemano
sbatch scripts/slurm/slurm_batch_build_containers.sh
```

Esto permite:
- Construir en paralelo (5 simultáneos)
- Evitar esperas durante ejecución
- Ejecutar tests inmediatamente

### 3. **Reintentos automáticos** (línea 658-667)
```python
max_retries = 3  # Reintenta 3 veces si falla
retry_delay = 5  # Con backoff exponencial (5s, 10s, 15s)
```

## 🎯 Estrategias de Uso

### Para pruebas rápidas (1-5 instancias)
```bash
# No pre-construir, dejar que se construyan bajo demanda
bash submit_quick_test.sh
```
**Ventaja:** Simple, no requiere planificación
**Desventaja:** Primera ejecución lenta (~10 min por imagen)

### Para batch grandes (50-200 instancias)
```bash
# 1. Pre-construir todas las imágenes
echo "astropy__astropy-12907" > instances.txt
echo "astropy__astropy-13033" >> instances.txt
# ... más instancias ...
sbatch scripts/slurm/slurm_batch_build_containers.sh

# 2. Esperar que termine la construcción

# 3. Ejecutar tests (ahora instantáneo)
python scripts/submit_integrated_batch.py --instance-file instances.txt
```
**Ventaja:** Tests ejecutan inmediatamente
**Desventaja:** Requiere planificación, más espacio en disco

## 🔍 Debugging: ¿Por qué se descarga una imagen?

Si ves que se descarga una imagen inesperadamente:

1. **Verificar caché:**
```bash
ls -lh /fs/nexus-scratch/ihbas/.containers/singularity/swebench_cache/astropy/
```

2. **Verificar configuración:**
```bash
grep cache_dir config/swebench_config.yaml
```

3. **Verificar logs:**
```bash
grep "Using cached\|Cache miss" logs/quick_test_*.out
```

4. **Force rebuild activado:**
```python
# En el código, verifica si force_rebuild=True
builder.build_instance(instance_id, force_rebuild=False)  # ✅ Usa caché
builder.build_instance(instance_id, force_rebuild=True)   # ❌ Descarga siempre
```

## 📊 Costos de Espacio en Disco

### Por imagen:
- **Pequeña** (flask, requests): ~800 MB - 1.5 GB
- **Media** (astropy, pytest): ~2-3 GB
- **Grande** (django, scikit-learn): ~3-5 GB

### Ejemplo para 100 instancias:
```
Astropy (15 instancias):    15 × 2.1 GB = 31.5 GB
Scikit-learn (20):          20 × 3.2 GB = 64.0 GB
Django (30):                30 × 1.8 GB = 54.0 GB
Matplotlib (10):            10 × 2.5 GB = 25.0 GB
Otros (25):                 25 × 2.0 GB = 50.0 GB
                            ──────────────────────
Total:                      ~224.5 GB
```

**Recomendación:** Monitorea el espacio en disco regularmente con:
```bash
bash check_job_status.sh  # Incluye info de disco
du -sh /fs/nexus-scratch/ihbas/.containers/singularity/swebench_cache/
```

## 🚀 Resumen

| Pregunta | Respuesta |
|----------|-----------|
| ¿Una imagen por instancia? | ✅ Sí, cada instancia tiene su propia imagen |
| ¿Se reutilizan entre instancias? | ❌ No, cada commit es diferente |
| ¿Se cachean localmente? | ✅ Sí, en `/fs/nexus-scratch/.../swebench_cache/` |
| ¿Cuánto espacio ocupan? | 📊 2-3 GB por imagen (promedio) |
| ¿Cuánto tarda la primera vez? | ⏱️ 5-15 minutos (descarga + conversión) |
| ¿Y la segunda vez? | ⚡ Instantáneo (desde caché) |
| ¿Se pueden pre-construir? | ✅ Sí, con `slurm_batch_build_containers.sh` |
| ¿Se limpian automáticamente? | ✅ Sí, según config (>30 días o >100GB) |

---

**Conclusión:** El sistema es inteligente y eficiente:
1. Primera ejecución: lenta (construye)
2. Subsecuentes: rápidas (caché)
3. Pre-construye para batch grandes
4. Limpia automáticamente para ahorrar espacio
