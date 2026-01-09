# 🚀 Quick Start Guide - Batch Jobs

Este proyecto tiene varios scripts `.sh` y puede ser confuso. Esta guía te muestra **exactamente** qué usar y cuándo.

## ⚡ Para ejecutar UNA instancia rápida (RECOMENDADO)

Tienes 2 opciones igualmente válidas:

### Opción A: Script automático (más inteligente)

```bash
bash submit_quick_test.sh
```

**Qué hace:**
- Usa el sistema inteligente de batch submission
- Maneja automáticamente la configuración de SLURM
- Ejecuta: `astropy__astropy-12907` (instancia que ya sabemos que funciona)
- Tiempo: ~30 minutos
- Recursos: 4 CPUs, 8GB RAM

### Opción B: SLURM directo (más simple)

```bash
sbatch quick_slurm_test.sh
```

**Qué hace:**
- Envía el job directamente a SLURM
- Menos overhead, más directo
- Misma instancia: `astropy__astropy-12907`
- Tiempo: ~30 minutos
- Recursos: 4 CPUs, 8GB RAM

## 📊 Monitorear el job

### Ver status de jobs
```bash
bash check_job_status.sh
```

O manualmente:
```bash
squeue -u $USER                    # Ver jobs activos
sacct -u $USER                     # Ver historial de jobs
```

### Ver logs en tiempo real
```bash
bash scripts/monitor_job.sh
```

O manualmente:
```bash
tail -f logs/quick_test_*.out      # Para Opción B
tail -f logs/slurm_integrated_*.out # Para Opción A
```

## 📁 Ver resultados

```bash
# Ver el archivo de resultado
ls -lh results/astropy__astropy-12907.json

# Ver el contenido formateado
cat results/astropy__astropy-12907.json | python -m json.tool | less
```

## 🎯 Siguiente paso: Batch de múltiples instancias

Una vez que confirmes que funciona, ejecuta un batch más grande:

```bash
python scripts/submit_integrated_batch.py \
  --limit 10 \
  --repos astropy scikit-learn \
  --enable-static \
  --enable-fuzzing \
  --enable-rules \
  --cpus 4 \
  --mem 8 \
  --time 60 \
  --max-parallel 5
```

## ❌ Cancelar un job

```bash
# Encontrar el JOB_ID
squeue -u $USER

# Cancelar
scancel <JOB_ID>
```

## 📚 Scripts disponibles (Referencia)

| Script | Uso | Propósito |
|--------|-----|-----------|
| `submit_quick_test.sh` | Primera vez / Prueba rápida | Ejecuta 1 instancia de prueba |
| `quick_slurm_test.sh` | Primera vez / Prueba rápida | Ejecuta 1 instancia (SLURM directo) |
| `check_job_status.sh` | Monitoreo | Ver status de jobs y resultados |
| `scripts/monitor_job.sh` | Monitoreo | Ver logs en tiempo real |
| `scripts/setup_fuzzing.sh` | Setup inicial (1 vez) | Configura el entorno |
| `scripts/submit_integrated_batch.py` | Producción | Batch de múltiples instancias |
| `scripts/slurm/slurm_integrated_pipeline.sh` | Producción | Pipeline principal SLURM |

## 💡 Troubleshooting

**"Permission denied"**
```bash
chmod +x submit_quick_test.sh quick_slurm_test.sh check_job_status.sh
```

**"Command not found: sbatch"**
- No estás en un nodo con SLURM, necesitas estar en el cluster

**"Conda environment not found"**
```bash
bash scripts/setup_fuzzing.sh  # Ejecuta el setup inicial
```

**Job queda en estado PENDING**
```bash
squeue -u $USER  # Verifica el estado
# Puede estar esperando recursos disponibles en el cluster
```

## ✅ Flujo de trabajo típico

1. **Primera vez:**
   ```bash
   bash scripts/setup_fuzzing.sh  # Setup inicial (1 vez)
   ```

2. **Probar que funciona:**
   ```bash
   bash submit_quick_test.sh  # O: sbatch quick_slurm_test.sh
   ```

3. **Monitorear:**
   ```bash
   bash check_job_status.sh
   bash scripts/monitor_job.sh
   ```

4. **Ver resultados:**
   ```bash
   cat results/astropy__astropy-12907.json | python -m json.tool
   ```

5. **Escalar a batch:**
   ```bash
   python scripts/submit_integrated_batch.py --limit 20 --repos astropy
   ```
