import os
import re
import json
import shutil
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import oci
import logging as log
import pandas as pd
try:
    from pyfiglet import figlet_format
except ImportError:
    figlet_format = None

__version__ = '2.0.0'
"""
@about: Cargador manual de datos hacia OCI Object Storage mediante SDK
@author: Edwin R. C.
@version: 2.0.0
"""
log.basicConfig(
    filename = __file__[:-3] + '.log', 
    level = log.DEBUG, 
    format = '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)

# Constantes
COMPRESSION_MAP = {'.zip': 'zip', '.gz': 'gzip'}


class InitConfig:
    """Gestor de configuración simplificado"""
    
    @staticmethod
    def get_config(filename: str = 'conf.json') -> Dict:
        """Carga configuración desde JSON"""
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def get_tables(filename: str = 'tables.json') -> List[Dict]:
        """Carga definición de tablas desde JSON"""
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)


class DataValidation:
    """Validador de estructura y tipos de datos"""
    
    def __init__(self, table_conf: Dict, path_data: str):
        self.table_conf = table_conf
        self.path_data = path_data
        self.encoding = table_conf.get('encoding', 'UTF-8')
        self.separador = table_conf.get('sep', ',')
        self.con_cabecera = table_conf.get('with_header', True)

    def get_type_from_name(self, name: str = "string", allow_nulls: bool = True) -> str:
        """Mapea tipo JSON a tipo pandas"""
        type_map = {
            'string': 'object',
            'str': 'object',
            'int': 'Int64' if allow_nulls else 'int64',
            'integer': 'Int64' if allow_nulls else 'int64',
            'bigint': 'Int64' if allow_nulls else 'int64',
            'float': 'float64',
            'double': 'float64',
            'decimal': 'float64',
            'date': 'object',
        }
        return type_map.get(name.lower(), 'object')

    def _get_compression_type(self, filename: str) -> Optional[str]:
        """Detecta tipo de compresión por extensión"""
        for ext, comp_type in COMPRESSION_MAP.items():
            if filename.endswith(ext):
                return comp_type
        return None

    def _read_csv(self) -> Optional[pd.DataFrame]:
        """Lee archivo CSV con validación"""
        if not os.path.exists(self.path_data):
            log.warning(f"Data no existe: {self.path_data}")
            return None
        
        log.info(f"Leyendo datos de muestra: {self.path_data}")
        try:
            compression = self._get_compression_type(self.path_data)
            header = 0 if self.con_cabecera else None
            df = pd.read_csv(
                self.path_data, 
                encoding=self.encoding, 
                sep=self.separador, 
                dtype=str, 
                compression=compression,
                header=header
            )
            return df
        except Exception as ex:
            log.error(f'Error al intentar leer archivo: {ex}')
            return None

    def _validate_columns(self, df: pd.DataFrame, fields: List[Dict]) -> Tuple[bool, str]:
        """Valida columnas del DataFrame contra el schema"""
        expected_cols = [c['name'] for c in fields]
        
        # Normalizar columnas
        df.columns = [str(col).replace(' ', '_').lower() for col in df.columns]
        if len(df.columns) == len(fields):
            df.columns = expected_cols
        
        log.info("Validando existencia de Columnas")
        
        if list(df.columns) != expected_cols:
            log.error(f"Columnas esperadas: {expected_cols}")
            log.error(f"Columnas en data: {list(df.columns)}")
            return False, "Las columnas no coinciden entre la definición (JSON) y la Data."
        
        log.info(f"Columnas válidas: {', '.join(df.columns)}")
        return True, "Columnas válidas"

    def _apply_schema(self, df: pd.DataFrame, schema: Dict) -> pd.DataFrame:
        """Aplica tipos de datos al DataFrame"""
        for col in df.columns:
            try:
                to_type = schema.get(col)
                if to_type and to_type.lower().startswith("int"):
                    df[col] = df[col].apply(
                        lambda x: x if pd.isnull(x) else int(x)
                    ).astype('Int64')
                elif to_type:
                    df[col] = df[col].astype(to_type)
            except Exception as ex:
                log.error(f"Error en la conversion de {col} a tipo {schema.get(col)}, error: {ex}")
                log.error(f"Valores: {','.join(str(v) for v in df.head(10)[col].values)}")
                raise ex
        return df

    def make_validation_data(self) -> Tuple[bool, str]:
        """Valida estructura y tipos del archivo"""
        df = self._read_csv()
        
        if df is None:
            return False, "Error al leer el archivo"
        
        if df.empty:
            log.error("Archivo sin datos, no se reconocen/leen los datos!")
            return False, "Archivo sin datos, no se reconocen/leen los datos!"
        
        log.info(f"Data de {df.shape[0]} filas y {df.shape[1]} columnas")
        
        try:
            fields = self.table_conf.get('campos', [])
            
            # Validar columnas
            valid, msg = self._validate_columns(df, fields)
            if not valid:
                return False, msg
            
            # Construir schema
            schema_dict = {
                c['name']: self.get_type_from_name(c['type'], c.get('nullable', True))
                for c in fields
            }
            
            log.info(f"Validando tipos de datos: {json.dumps(schema_dict)}")
            self._apply_schema(df, schema_dict)
            log.info("Estructura y tipos de datos son válidos!")
            return True, "Datos Validos!"
            
        except Exception as e:
            log.error(f'Error al validar estructura de archivo: {e}')
            return False, f'Error al validar estructura de archivo: {e}'


class OCIIntegration:
    """Integración con OCI Object Storage"""
    
    def __init__(self, conf: Dict):
        self.conf = conf
        app_conf = conf.get('app', {})
        self.oci_config_path = app_conf.get('oci_config_path')
        self.oci_profile = app_conf.get('oci_profile', 'DEFAULT')
        self.oci_region = app_conf.get('oci_region')
        self.oci_namespace = app_conf.get('oci_namespace')
        self.oci_use_instance_principals = app_conf.get('oci_use_instance_principals', False)
        self.client = None

    def _build_client(self) -> None:
        """Construye cliente OCI con autenticación apropiada"""
        if self.oci_use_instance_principals:
            signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
            config = {"region": self.oci_region} if self.oci_region else {}
            self.client = oci.object_storage.ObjectStorageClient(config, signer=signer)
        else:
            if self.oci_config_path:
                config = oci.config.from_file(self.oci_config_path, self.oci_profile)
            else:
                config = oci.config.from_file(profile_name=self.oci_profile)
            if self.oci_region:
                config['region'] = self.oci_region
            self.client = oci.object_storage.ObjectStorageClient(config)

    def check_connection(self) -> bool:
        """Valida conexión a OCI"""
        try:
            if not self.client:
                self._build_client()
            if not self.oci_namespace:
                self.oci_namespace = self.client.get_namespace().data
            log.info(f"Conectado a OCI, namespace: {self.oci_namespace}")
            print(f"Conectado a OCI: namespace {self.oci_namespace}")
            return True
        except Exception as ex:
            log.error(f"Error al intentar autenticar a OCI: {ex}")
            print("Error intentando autenticar a OCI.")
            return False

    def upload_file_object(self, local_fullpath: str, table_conf: Dict) -> Tuple[bool, str]:
        """Sube archivo a OCI Object Storage"""
        oci_bucket = table_conf.get('oci_bucket')
        oci_prefix_path = table_conf.get('prefix_path')
        
        if not oci_bucket:
            msg = "No existe oci_bucket configurado para la tabla."
            log.error(msg)
            return False, msg
        
        try:
            filename = Path(local_fullpath).name
            object_name = f"{oci_prefix_path}/{filename}" if oci_prefix_path else filename
            
            log.info(f"Iniciando carga hacia OCI Object Storage del archivo {filename}, desde {local_fullpath} hacia {object_name}")
            
            with open(local_fullpath, 'rb') as f:
                self.client.put_object(self.oci_namespace, oci_bucket, object_name, f)
            
            msg = f"✓ Archivo Cargado hacia OCI Object Storage: {filename}"
            log.info(msg)

            # Pequeño delay para propagación de metadata en OCI
            time.sleep(1)
            
            # Verificación es informativa, no determina el éxito
            check_status, check_msg = self._check_file_object(oci_bucket, object_name, filename)
            if check_status:
                msg += f"\n✓ Verificación: {check_msg}"
            else:
                msg += f"\n⚠ Advertencia: {check_msg}"
                msg += "\n  El archivo se subió correctamente, pero la verificación falló (puede ser latencia de OCI)."
                log.warning(f"Verificación falló pero upload fue exitoso para {filename}")
            
            # El upload fue exitoso (put_object no lanzó excepción)
            return True, msg
            
        except Exception as ex:
            msg = f"Error al intentar subir archivo al bucket OCI: {ex}"
            log.error(msg)
            return False, msg

    def _check_file_object(self, oci_bucket: str, object_name: str, filename: str) -> Tuple[bool, str]:
        """Verifica existencia del archivo en OCI"""
        try:
            result = self.client.head_object(self.oci_namespace, oci_bucket, object_name)
            
            # Si no hay excepción, el objeto existe (HEAD retornó 200)
            if result is None:
                msg = "El resultado de la verificacion es nulo."
                log.error(msg)
                return False, msg
            
            # Verificar content_length
            try:
                content_length = getattr(result.data, 'content_length', None)
                if content_length is None:
                    # Si no tiene content_length pero HEAD fue exitoso, asumimos que existe
                    msg = f"El archivo {filename} existe en {oci_bucket} (sin metadata de tamaño)"
                    log.info(msg)
                    return True, msg
                elif content_length > 0:
                    msg = f"El archivo {filename} existe en {oci_bucket} ({content_length} bytes)"
                    log.info(msg)
                    return True, msg
                else:
                    msg = f"El archivo {filename} está vacío, el peso del archivo es 0."
                    log.warning(msg)
                    return False, msg
            except AttributeError as ae:
                # Si no podemos acceder a content_length pero HEAD fue exitoso
                msg = f"El archivo {filename} existe en {oci_bucket} (estructura de respuesta inesperada)"
                log.warning(f"AttributeError al leer metadata: {ae}")
                return True, msg
                
        except Exception as ex:
            msg = f"Error al intentar ejecutar la verificacion en OCI: {ex}"
            log.error(msg)
            return False, msg


class App:
    """Aplicación principal de carga de datos"""

    def __init__(self):
        self.load_init_configs()
        
        # Variables de estado para procesamiento
        self.var_ruta_archivo: Optional[str] = None
        self.var_nombre_archivo: Optional[str] = None
        self.var_tabla: Optional[Dict] = None
        
        self.oci_is_valid = False
        self.oci = OCIIntegration(self.conf)
        self.validar_conexion()

    def load_init_configs(self) -> None:
        """Carga configuración y definición de tablas"""
        self.conf = InitConfig.get_config()
        self.tables = InitConfig.get_tables()

    def validar_conexion(self) -> None:
        """Valida conexión a OCI"""
        self.oci_is_valid = self.oci.check_connection()

    def _show_connection_error(self) -> None:
        """Muestra mensaje de error de conexión"""
        print("Se cancela el proceso, no hay conexion con OCI.")
        log.info("Se cancela el proceso, no hay conexion con OCI.")
        print("Debe actualizar su API KEY y configurar nuevamente el archivo ~/.oci/config")
        log.info("Debe actualizar su API KEY y configurar nuevamente el archivo ~/.oci/config")

    def _process_table(self, table: Dict, work_dir: str) -> None:
        """Procesa todos los archivos de una tabla"""
        table_name = table.get('nombre_tabla')
        if not table_name:
            return
        
        table_dir = Path(work_dir) / table_name
        if not table_dir.is_dir():
            log.warning(f"No existe carpeta de tabla: {table_dir}")
            return
        
        data_regex = table.get('regex_file')
        list_files = [
            f for f in os.listdir(table_dir)
            if (table_dir / f).is_file() and re.search(data_regex, f)
        ]
        
        if not list_files:
            log.info(f"No hay archivos para subir en: {table_dir}")
            return
        
        list_files.sort()
        log.info(f"Procesando tabla '{table_name}' con {len(list_files)} archivo(s)")
        print(f"\n{'='*60}")
        print(f"Tabla: {table_name}")
        print(f"{'='*60}")
        
        for filename in list_files:
            self.var_tabla = table
            self.var_ruta_archivo = str(table_dir / filename)
            self.var_nombre_archivo = filename
            print(f"\nProcesando archivo: {self.var_ruta_archivo}")
            log.info(f"Procesando archivo seleccionado para subir: {self.var_ruta_archivo}")
            self._validate_and_upload_data()

    def main(self) -> None:
        """Flujo principal de procesamiento"""
        if not self.oci_is_valid:
            self._show_connection_error()
            return
        
        work_dir = self.conf.get('work')
        for table in self.tables:
            self._process_table(table, work_dir)

    def _move_done_file(self) -> Tuple[bool, str]:
        """Mueve archivo procesado a carpeta cargado/"""
        table_name = self.var_tabla.get('nombre_tabla')
        data_dir = Path(self.conf.get('work')) / table_name
        data_dir_done = data_dir / 'cargado'
        var_ruta_archivo_done = data_dir_done / self.var_nombre_archivo
        
        if self.var_nombre_archivo and Path(self.var_ruta_archivo) != var_ruta_archivo_done:
            try:
                data_dir_done.mkdir(parents=True, exist_ok=True)
                shutil.move(self.var_ruta_archivo, str(var_ruta_archivo_done))
                msg = "Archivo fue Movido a la carpeta cargado/"
                return True, msg
            except Exception as ex:
                msg = f"Error al intentar mover archivo a la carpeta cargado/: {ex}"
                return False, msg
        return False, "No se pudo mover el archivo"

    def _validate_and_upload_data(self) -> None:
        """Valida y sube archivo"""
        if not self.oci_is_valid or not self.var_ruta_archivo:
            print("No estas autenticado con OCI, se cancela el proceso.")
            return
        
        # Validar
        db_is_valid, db_msg_valid = self._call_data_validator()
        if not db_is_valid:
            print(f"Archivo de datos Erroneo, se ha identificado los siguientes errores:")
            print(db_msg_valid)
            print("Verifique/corrija la data y vuelva a intentar nuevamente.")
            return
        
        # Subir
        print("Archivo es Válido, se inicia la carga hacia OCI Object Storage. Espere...")
        up_status, up_msg = self._call_file_uploader()
        if not up_status:
            print("Error en la subida, mas detalles del error:")
            print(up_msg)
            print("Verifique su conexión y permisos al bucket de destino, y vuelva a intentar.")
            return
        
        # Mover
        print(up_msg)
        mv_status, mv_msg = self._move_done_file()
        if mv_status:
            print(mv_msg)
        else:
            print(mv_msg)
            print(f"Debe mover Manualmente el archivo {self.var_ruta_archivo} hacia la sub carpeta cargado/")

    def _call_data_validator(self) -> Tuple[bool, str]:
        """Llama al validador de datos"""
        try:
            data_path = self.var_ruta_archivo.strip()
            data_val = DataValidation(self.var_tabla, data_path)
            return data_val.make_validation_data()
        except Exception as ex:
            msg = f"Error a intentar validar la data: {ex}"
            print(msg)
            return False, msg

    def _call_file_uploader(self) -> Tuple[bool, str]:
        """Llama al uploader de archivos"""
        data_path = self.var_ruta_archivo.strip()
        return self.oci.upload_file_object(data_path, self.var_tabla)


if __name__ == "__main__":
    log.info('=' * 60)
    log.info('Aplicación iniciada')
    
    # Banner ASCII
    print('\n')
    if figlet_format:
        try:
            banner = figlet_format('OCI Datalake', font='big')
            print(banner)
        except:
            print('=' * 60)
            print('OCI DATA TO BUCKET')
            print('=' * 60)
    else:
        print('=' * 60)
        print('OCI DATA TO BUCKET')
        print('=' * 60)
    
    # Descripción
    print(f'v{__version__} - Cargador Manual de Datos a OCI Object Storage')
    print('Validación automática de estructura y tipos de datos')
    print('Soporte multi-tabla con organización por carpetas')
    print('=' * 60)
    print()
    
    app = App()
    app.main()
    
    print("\n")
    print('=' * 60)
    print('Proceso finalizado')
    print('=' * 60)
    input("Presione Enter para salir > ")
