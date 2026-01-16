# OCI Data Upload to Bucket Storage

Aplicación para subir archivos de datos a OCI Object Storage con validación automática de estructura y tipos. 

Cargador Manual de datos hacia OCI Object Storage (Datalake).

## Características

- ✅ Soporte multi-tabla
- ✅ Validación automática de columnas y tipos de datos
- ✅ Verificación post-carga
- ✅ Organización por carpetas (work/<tabla>/)
- ✅ Movimiento automático a carpeta `cargado/`
- ✅ Logging detallado
- ✅ Type hints completos
- ✅ Setup automatizado con entorno virtual

## 🚀 Inicio rápido

```bash
# 1. Clonar/descargar el proyecto
cd oracle-cloud-data-upload-to-bucket

# 2. Ejecutar setup (crea venv, instala dependencias, genera scripts)
python setup.py

# 3. Configurar OCI credentials en ~/.oci/config

# 4. Ajustar conf.json y tables.json con tus valores

# 5. Ejecutar
./run.sh       # Linux/Mac
run.bat        # Windows
```

## Requisitos

- Python 3.7+
- OCI SDK
- Pandas

## Instalación

### Opción 1: Setup automatizado (recomendado)

El script `setup.py` configura automáticamente el entorno virtual e instala todas las dependencias:

```bash
python setup.py
```

Este script:
- ✅ Detecta el comando Python disponible en tu sistema
- ✅ Crea un entorno virtual (`venv/`)
- ✅ Instala todas las dependencias desde `requirements.txt`
- ✅ Genera el script de ejecución apropiado para tu sistema operativo (`run.bat` o `run.sh`)

### Opción 2: Instalación manual

Si prefieres instalar manualmente:

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

## Configuración

### 1. Configurar OCI (`~/.oci/config`)

```ini
[DEFAULT]
user=ocid1.user.oc1..xxxxx
fingerprint=xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx
key_file=~/.oci/oci_api_key.pem
tenancy=ocid1.tenancy.oc1..xxxxx
region=us-ashburn-1
```

### 2. Configurar aplicación (`conf.json`)

```json
{
    "app": {
        "oci_profile": "DEFAULT",
        "oci_region": "us-ashburn-1",
        "oci_namespace": "tu_namespace",
        "oci_use_instance_principals": false
    },
    "work": "C:/WORK-DATA/"
}
```

### 3. Definir tablas (`tables.json`)

```json
[
    {
        "nombre_tabla": "mi_tabla",
        "regex_file": "datos_[0-9]{8}\\.csv\\.gz",
        "sep": ",",
        "encoding": "UTF-8",
        "with_header": true,
        "oci_bucket": "mi-bucket",
        "prefix_path": "ruta/destino",
        "campos": [
            {"name": "columna1", "type": "string", "nullable": true},
            {"name": "columna2", "type": "int", "nullable": false}
        ]
    }
]
```

## Estructura del proyecto

```
oracle-cloud-data-upload-to-bucket/
├── main.py              # Script principal
├── setup.py             # Instalador automático
├── conf.json            # Configuración global OCI
├── tables.json          # Definición de tablas y schemas
├── requirements.txt     # Dependencias Python
├── .gitignore          # Archivos ignorados por Git
├── README.md           # Documentación
├── venv/               # Entorno virtual (generado por setup.py)
├── run.bat/run.sh      # Script de ejecución (generado por setup.py)
└── main.log            # Logs de ejecución
```

### Estructura de directorios de trabajo

```
work/
├── tabla1/
│   ├── archivo2.csv.gz
│   ├── archivo3.csv.gz
│   └── cargado/
│       └── archivo1.csv.gz
└── tabla2/
    ├── archivo1.csv.gz
    └── cargado/
```

## Uso

Después de ejecutar `setup.py`, usa el script generado para tu sistema operativo:

### Windows
```cmd
run.bat 
```

### Linux/Mac
```bash
./run.sh
```

Estos scripts:
- Activan automáticamente el entorno virtual (si no está activado)
- Ejecutan `main.py`

**Nota**: Si prefieres ejecutar manualmente, primero activa el entorno virtual:
```bash
# Activar venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Ejecutar
python main.py
```

## Diagrama de flujo

### Flujo de ejecución

```
                    ┌──────────────────┐
                    │  ./run.sh o      │
                    │  run.bat         │
                    └─────────┬────────┘
                              │
        ┌─────────────────────▼─────────────────────┐
        │         EJECUCIÓN DE main.py              │
        └─────────────────────┬─────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ 1. Conectar OCI  │
                    │    (validar API) │
                    └─────────┬────────┘
                              │
                  ┌───────────▼────────────┐
                  │  Para cada TABLA en    │
                  │  tables.json:          │
                  └───────────┬────────────┘
                              │
            ┌─────────────────▼─────────────────┐
            │                                   │
            ▼                                   ▼
   ┌────────────────┐                 ┌────────────────┐
   │  Tabla 1       │                 │  Tabla N       │
   └────────┬───────┘                 └─────────┬──────┘
            │                                   │
            ▼                                   ▼
   ┌─────────────────────────────────────────────────┐
   │  2. Escanear work/<nombre_tabla>/               │
   │     Buscar archivos con regex                   │
   └─────────────────────┬───────────────────────────┘
                         │
          ┌──────────────▼──────────────┐
          │  Para cada ARCHIVO:         │
          └──────────────┬──────────────┘
                         │
        ┌────────────────▼────────────────┐
        │                                 │
        ▼                                 ▼
┌────────────────┐              ┌────────────────┐
│ archivo1.csv.gz│              │ archivoN.csv.gz│
└────────┬───────┘              └────────┬───────┘
         │                               │
         └───────────────┬───────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ 3. VALIDAR DATA     │
              │  - Leer CSV         │
              │  - Validar columnas │
              │  - Validar tipos    │
              └──────────┬──────────┘
                         │
                    ┌────▼────┐
                    │ ¿Válido?│
                    └────┬────┘
                         │
            ┌────────────┴────────────┐
            │                         │
        ❌ NO                      ✅ SI
            │                         │
            ▼                         ▼
    ┌───────────────┐      ┌───────────────────┐
    │ Mostrar Error │      │ 4. SUBIR A OCI    │
    │ Siguiente     │      │    put_object()   │
    │ archivo       │      └─────────┬─────────┘
    └───────────────┘                │
                              ┌──────▼──────┐
                              │ HTTP 200?   │
                              └──────┬──────┘
                                     │
                        ┌────────────┴──────────────┐
                        │                           │
                    ❌ ERROR                     ✅ OK
                        │                           │
                        ▼                           ▼
                ┌───────────────┐      ┌──────────────────────┐
                │ Mostrar Error │      │ 5. VERIFICAR         │
                │ NO mover      │      │    head_object()     │
                └───────────────┘      └──────────┬───────────┘
                                                  │
                                        ┌─────────▼─────────┐
                                        │ Verificación OK?  │
                                        └─────────┬─────────┘
                                                  │
                                    ┌─────────────┴─────────────┐
                                    │                           │
                                ⚠️ NO                       ✅ SI
                              (advertencia)              (confirmado)
                                    │                           │
                                    └─────────────┬─────────────┘
                                                  │
                                                  ▼
                                    ┌──────────────────────────┐
                                    │ 6. MOVER ARCHIVO         │
                                    │    a cargado/            │
                                    └──────────────┬───────────┘
                                                   │
                                                   ▼
                                         ┌─────────────────┐
                                         │  ✓ Completado   │
                                         └─────────────────┘
```

### Vista de directorios durante el proceso

```
work/
├── tabla1/
│   ├── archivo1.csv.gz  ────► [VALIDAR] ────► [SUBIR] ────► │
│   ├── archivo2.csv.gz  ────► [VALIDAR] ────► [SUBIR] ────► │
│   │                                                        │
│   └── cargado/          ◄──────────────────────────────────┘
│       ├── archivo1.csv.gz  ✓ (subido exitosamente)
│       └── archivo2.csv.gz  ✓ (subido exitosamente)
│
└── tabla2/
    ├── datos.csv.gz     ────► [VALIDAR] ────► [SUBIR] ────► │
    │                                                        │
    └── cargado/         ◄───────────────────────────────────┘
        └── datos.csv.gz  ✓ (subido exitosamente)


                          ↓ (upload)
                          
                    OCI Object Storage
                    ┌──────────────────────────────┐
                    │  Namespace: tdecloud         │
                    ├──────────────────────────────┤
                    │  Bucket: mi-bucket           │
                    │  ├── prefix_path/            │
                    │  │   ├── archivo1.csv.gz     │
                    │  │   ├── archivo2.csv.gz     │
                    │  │   └── datos.csv.gz        │
                    └──────────────────────────────┘
```

## Flujo de procesamiento (detallado)

1. **Conexión**: Valida credenciales OCI
2. **Escaneo**: Busca archivos por regex en cada carpeta de tabla
3. **Validación**: Verifica columnas y tipos de datos
4. **Carga**: Sube archivo a OCI Object Storage (con `put_object`)
5. **Verificación**: Confirma existencia del archivo (con `head_object`)
   - ⚠️ Si falla la verificación pero el upload fue exitoso (HTTP 200), se considera exitoso
   - Puede haber latencia en la propagación de metadata en OCI
6. **Movimiento**: Mueve archivo a carpeta `cargado/`

### Notas sobre verificación

El proceso de verificación (`head_object`) puede fallar debido a:
- **Latencia de propagación**: OCI puede tardar 1-2 segundos en indexar el archivo
- **Permisos limitados**: Usuario tiene permiso de escritura pero no de lectura de metadata
- **Configuración de bucket**: Algunos buckets tienen restricciones de visibilidad

**Importante**: Si el `PUT` devuelve HTTP 200, el archivo **SÍ se subió correctamente**, independientemente del resultado de la verificación. Puedes confirmar manualmente en la consola OCI.

## Tipos de datos soportados

| Tipo JSON | Tipo Pandas | Descripción |
|-----------|-------------|-------------|
| `string`  | `object`    | Texto |
| `int`     | `Int64`     | Entero con nulls |
| `bigint`  | `Int64`     | Entero largo |
| `float`   | `float64`   | Decimal |
| `double`  | `float64`   | Decimal doble precisión |
| `date`    | `object`    | Fecha como string |

## Logs

Los logs se guardan en `main.log` con nivel DEBUG.

## Mejoras v2.0

- ✨ **Setup automatizado** con `setup.py`
- ✨ **Entorno virtual** automático con dependencias
- ✨ **Scripts de ejecución** generados por SO
- ✨ **`.gitignore`** configurado para Python
- ✨ Refactorización completa con type hints
- ✨ Uso de `pathlib.Path` para manejo de rutas
- ✨ f-strings en todo el código
- ✨ Métodos privados claramente identificados
- ✨ Mejor separación de responsabilidades
- ✨ Eliminación de código no usado
- ✨ Constantes extraídas
- ✨ Mejor manejo de errores
- ✨ Logging por tabla
- ✨ Documentación completa en README

## Control de versiones

El proyecto incluye un `.gitignore` configurado para:

### Archivos ignorados automáticamente
- ✅ Entorno virtual (`venv/`)
- ✅ Scripts generados (`run.bat`, `run.sh`)
- ✅ Logs (`*.log`, `main.log`)
- ✅ Archivos Python compilados (`__pycache__/`, `*.pyc`)
- ✅ Archivos de configuración de IDEs (`.vscode/`, `.idea/`)
- ✅ Credenciales OCI (`*.pem`, `*.key`, `.oci/`)
- ✅ Archivos temporales (`*.tmp`, `*.bak`)

### Archivos versionados
- ✅ `main.py` - Código fuente
- ✅ `setup.py` - Instalador
- ✅ `conf.json` - Configuración (sin credenciales)
- ✅ `tables.json` - Definición de tablas
- ✅ `requirements.txt` - Dependencias
- ✅ `README.md` - Documentación

**Nota de seguridad**: Asegúrate de que `conf.json` y `tables.json` no contengan credenciales sensibles. Las credenciales deben estar solo en `~/.oci/config`.

## Troubleshooting

### Error: "No existe oci_bucket configurado"
- Verifica que cada tabla en `tables.json` tenga `oci_bucket` definido.

### Error: "Error intentando autenticar a OCI"
- Verifica que `~/.oci/config` esté correctamente configurado.
- Revisa que tu API key no haya expirado.
- Confirma que el namespace sea correcto.

### Error: "Las columnas no coinciden"
- Verifica que el orden y nombre de columnas en el archivo coincida con `campos` en `tables.json`.
- Revisa el encoding del archivo.

### Advertencia: "NO se pudo verificar su existencia en OCI"

**Causa**: El archivo se subió correctamente (PUT 200), pero `head_object` falló.

**Soluciones**:

1. **Confirmar en consola OCI**: 
   - Ve a tu bucket en la consola web de OCI
   - Busca el archivo en la ruta especificada
   - Si está ahí, ignora la advertencia

2. **Aumentar delay de verificación**:
   ```python
   # En main.py, línea ~223 (método upload_file_object)
   time.sleep(1)  # Cambiar a 2 o 3 segundos
   ```

3. **Verificar permisos**:
   - Tu usuario/policy debe tener:
     - `object-storage-object-write` (para PUT) ✅
     - `object-storage-object-read` (para HEAD) ❌ puede faltar
   
4. **Deshabilitar verificación** (no recomendado):
   - Comenta la sección de verificación en `upload_file_object`

**Nota**: Si el log muestra `"PUT ... HTTP/1.1" 200`, el archivo está en OCI.

## Autor

Edwin R. C. edronald7@gmail.com

## Versión

2.0.0 - 2026-01-15
