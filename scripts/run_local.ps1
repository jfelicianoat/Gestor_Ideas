# Script de arranque local para desarrollo en Windows
# Uso: powershell -File scripts\run_local.ps1

$ErrorActionPreference = "Stop"

# Verificar que existe el entorno virtual
if (-Not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "[INFO] Creando entorno virtual..." -ForegroundColor Yellow
    python -m venv .venv
}

# Activar entorno virtual
. .venv\Scripts\Activate.ps1

# Instalar dependencias en modo editable
Write-Host "[INFO] Instalando dependencias..." -ForegroundColor Yellow
pip install -e ".[dev]" --quiet

# Ejecutar la aplicación
Write-Host "[INFO] Arrancando Gestor de Ideas..." -ForegroundColor Green
python -m adaptador.main
