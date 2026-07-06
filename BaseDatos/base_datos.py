"""
Modulo: base_datos.py
Ubicacion: BaseDatos/base_datos.py

Este archivo se encarga de todo lo relacionado con guardar y consultar
informacion en la base de datos del proyecto.

Usamos SQLite: una base de datos que vive en un solo archivo dentro
de esta misma carpeta, sin necesidad de instalar ningun programa
adicional. Python ya trae todo lo necesario para usarla.

Este archivo NO descarga datos de XM ni hace analisis.
Su unica responsabilidad es guardar y leer informacion.
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime, timedelta

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_BASE_DATOS = os.path.join(CARPETA_ACTUAL, "mercado_electrico.db")


def obtener_conexion():
    """
    Abre una conexion hacia el archivo de la base de datos.
    Si el archivo no existe todavia, SQLite lo crea automaticamente.
    """
    conexion = sqlite3.connect(RUTA_BASE_DATOS)
    return conexion


def crear_tablas():
    """
    Crea las tablas del proyecto si todavia no existen.
    Si ya existen, no hace nada (no borra informacion existente).
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    # Tabla del Precio de Bolsa real
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS precio_bolsa (
            fecha TEXT PRIMARY KEY,
            hora_01 REAL, hora_02 REAL, hora_03 REAL, hora_04 REAL,
            hora_05 REAL, hora_06 REAL, hora_07 REAL, hora_08 REAL,
            hora_09 REAL, hora_10 REAL, hora_11 REAL, hora_12 REAL,
            hora_13 REAL, hora_14 REAL, hora_15 REAL, hora_16 REAL,
            hora_17 REAL, hora_18 REAL, hora_19 REAL, hora_20 REAL,
            hora_21 REAL, hora_22 REAL, hora_23 REAL, hora_24 REAL
        )
    """)

    # Tabla del IMAR (Predespacho Ideal)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS imar (
            fecha TEXT PRIMARY KEY,
            hora_01 REAL, hora_02 REAL, hora_03 REAL, hora_04 REAL,
            hora_05 REAL, hora_06 REAL, hora_07 REAL, hora_08 REAL,
            hora_09 REAL, hora_10 REAL, hora_11 REAL, hora_12 REAL,
            hora_13 REAL, hora_14 REAL, hora_15 REAL, hora_16 REAL,
            hora_17 REAL, hora_18 REAL, hora_19 REAL, hora_20 REAL,
            hora_21 REAL, hora_22 REAL, hora_23 REAL, hora_24 REAL
        )
    """)

    # Tabla del Precio Marginal de Escasez (un solo valor por dia,
    # que se mantiene igual durante todo el mes vigente)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS precio_escasez (
            fecha TEXT PRIMARY KEY,
            valor REAL
        )
    """)

    # Tabla de Variables Hidrologicas (Modulo 3): embalses, aportes,
    # capacidad util, y comparacion de aportes con la media historica.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS variables_hidrologicas (
            fecha TEXT PRIMARY KEY,
            embalses_porcentaje REAL,
            embalses_energia REAL,
            aportes_porcentaje REAL,
            aportes_energia REAL,
            aportes_media_historica REAL,
            capacidad_util_energia REAL
        )
    """)

    # Tabla de la Senda de Referencia del Embalse (Resolucion CREG
    # 209 de 2020). Se actualiza aproximadamente cada 6 meses.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS senda_referencia (
            fecha TEXT PRIMARY KEY,
            valor REAL
        )
    """)

    # Tabla del listado de plantas/recursos con su tipo de tecnologia.
    # Se actualiza cada cierto tiempo (no cambia mucho de un dia a otro).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS listado_recursos (
            codigo TEXT PRIMARY KEY,
            nombre TEXT,
            tecnologia TEXT
        )
    """)

    # Tabla de Generacion por Fuente (Modulo 4): total de energia
    # generada por cada tipo de tecnologia, por dia.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generacion_por_fuente (
            fecha TEXT,
            tecnologia TEXT,
            valor_kwh REAL,
            PRIMARY KEY (fecha, tecnologia)
        )
    """)

    # Tabla de Noticias (Modulo 5): titulares y enlaces recopilados,
    # sin interpretacion. Se guarda tambien la fecha en que se hizo
    # la busqueda, para poder limpiar noticias muy viejas si hace falta.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS noticias (
            enlace TEXT PRIMARY KEY,
            titulo TEXT,
            fecha_publicacion TEXT,
            fuente TEXT,
            fecha_busqueda TEXT
        )
    """)

    # Tabla de control de envios: registra si un proceso (ej. el
    # informe diario) ya se ejecuto/envio en una fecha especifica,
    # para no repetirlo varias veces el mismo dia.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS control_envios (
            proceso TEXT,
            fecha TEXT,
            PRIMARY KEY (proceso, fecha)
        )
    """)

    conexion.commit()
    conexion.close()

    print("Tablas verificadas correctamente.")


def _guardar_en_tabla(dataframe, nombre_tabla):
    """
    Funcion interna que guarda un DataFrame en cualquiera de las dos
    tablas (precio_bolsa o imar), ya que ambas tienen la misma
    estructura de columnas (fecha + 24 horas).

    Si un dia ya existe, se actualiza. Si no existe, se agrega.
    Nunca se duplica un mismo dia.
    """
    if len(dataframe) == 0:
        print("No hay datos nuevos para guardar en " + nombre_tabla + ".")
        return

    crear_tablas()

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    filas_guardadas = 0

    for _, fila in dataframe.iterrows():
        cursor.execute("""
            INSERT INTO """ + nombre_tabla + """ (
                fecha,
                hora_01, hora_02, hora_03, hora_04, hora_05, hora_06,
                hora_07, hora_08, hora_09, hora_10, hora_11, hora_12,
                hora_13, hora_14, hora_15, hora_16, hora_17, hora_18,
                hora_19, hora_20, hora_21, hora_22, hora_23, hora_24
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(fecha) DO UPDATE SET
                hora_01=excluded.hora_01, hora_02=excluded.hora_02,
                hora_03=excluded.hora_03, hora_04=excluded.hora_04,
                hora_05=excluded.hora_05, hora_06=excluded.hora_06,
                hora_07=excluded.hora_07, hora_08=excluded.hora_08,
                hora_09=excluded.hora_09, hora_10=excluded.hora_10,
                hora_11=excluded.hora_11, hora_12=excluded.hora_12,
                hora_13=excluded.hora_13, hora_14=excluded.hora_14,
                hora_15=excluded.hora_15, hora_16=excluded.hora_16,
                hora_17=excluded.hora_17, hora_18=excluded.hora_18,
                hora_19=excluded.hora_19, hora_20=excluded.hora_20,
                hora_21=excluded.hora_21, hora_22=excluded.hora_22,
                hora_23=excluded.hora_23, hora_24=excluded.hora_24
        """, (
            fila["Date"],
            float(fila["Hour01"]), float(fila["Hour02"]), float(fila["Hour03"]),
            float(fila["Hour04"]), float(fila["Hour05"]), float(fila["Hour06"]),
            float(fila["Hour07"]), float(fila["Hour08"]), float(fila["Hour09"]),
            float(fila["Hour10"]), float(fila["Hour11"]), float(fila["Hour12"]),
            float(fila["Hour13"]), float(fila["Hour14"]), float(fila["Hour15"]),
            float(fila["Hour16"]), float(fila["Hour17"]), float(fila["Hour18"]),
            float(fila["Hour19"]), float(fila["Hour20"]), float(fila["Hour21"]),
            float(fila["Hour22"]), float(fila["Hour23"]), float(fila["Hour24"])
        ))
        filas_guardadas += 1

    conexion.commit()
    conexion.close()

    print(str(filas_guardadas) + " dia(s) guardado(s) o actualizado(s) en " + nombre_tabla + ".")


def guardar_precio_bolsa(dataframe):
    """
    Guarda un DataFrame con datos de Precio de Bolsa en la base de datos.
    """
    _guardar_en_tabla(dataframe, "precio_bolsa")


def guardar_imar(dataframe):
    """
    Guarda un DataFrame con datos de IMAR en la base de datos.
    """
    _guardar_en_tabla(dataframe, "imar")


def consultar_todo_precio_bolsa():
    """
    Trae todo el historico de Precio de Bolsa guardado en la base de datos.
    """
    conexion = obtener_conexion()
    df = pd.read_sql_query("SELECT * FROM precio_bolsa ORDER BY fecha", conexion)
    conexion.close()
    return df


def consultar_todo_imar():
    """
    Trae todo el historico de IMAR guardado en la base de datos.
    """
    conexion = obtener_conexion()
    df = pd.read_sql_query("SELECT * FROM imar ORDER BY fecha", conexion)
    conexion.close()
    return df


def guardar_precio_escasez(fecha, valor):
    """
    Guarda (o actualiza) el valor del Precio Marginal de Escasez
    para una fecha especifica.
    """
    crear_tablas()

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("""
        INSERT INTO precio_escasez (fecha, valor)
        VALUES (?, ?)
        ON CONFLICT(fecha) DO UPDATE SET valor=excluded.valor
    """, (fecha, valor))

    conexion.commit()
    conexion.close()

    print("Precio de Escasez guardado para la fecha " + fecha + ".")


def consultar_precio_escasez_mas_reciente():
    """
    Trae el valor de Precio de Escasez mas reciente guardado en
    la base de datos (que corresponde al valor vigente del mes actual).

    Retorna:
        Una tupla (fecha, valor), o (None, None) si no hay datos guardados.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("SELECT fecha, valor FROM precio_escasez ORDER BY fecha DESC LIMIT 1")
    resultado = cursor.fetchone()

    conexion.close()

    if resultado is None:
        return None, None

    return resultado[0], resultado[1]


def consultar_todo_precio_escasez():
    """
    Trae todo el historico de Precio de Escasez guardado en la base
    de datos, ordenado por fecha. Sirve para graficar como ha variado
    mes a mes durante el año.

    Retorna:
        Un DataFrame con columnas: fecha, valor.
    """
    conexion = obtener_conexion()
    df = pd.read_sql_query("SELECT * FROM precio_escasez ORDER BY fecha", conexion)
    conexion.close()
    return df


def guardar_variable_hidrologica(fecha, valores_dict):
    """
    Guarda (o actualiza) los valores de las variables hidrologicas
    de un dia especifico.

    Parametros:
        fecha (str): fecha en formato YYYY-MM-DD.
        valores_dict (dict): diccionario con las claves
            embalses_porcentaje, embalses_energia, aportes_porcentaje,
            aportes_energia, aportes_media_historica,
            capacidad_util_energia. Los valores pueden ser None si no
            se pudo obtener el dato para esa fecha.
    """
    crear_tablas()

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("""
        INSERT INTO variables_hidrologicas (
            fecha, embalses_porcentaje, embalses_energia,
            aportes_porcentaje, aportes_energia,
            aportes_media_historica, capacidad_util_energia
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(fecha) DO UPDATE SET
            embalses_porcentaje=excluded.embalses_porcentaje,
            embalses_energia=excluded.embalses_energia,
            aportes_porcentaje=excluded.aportes_porcentaje,
            aportes_energia=excluded.aportes_energia,
            aportes_media_historica=excluded.aportes_media_historica,
            capacidad_util_energia=excluded.capacidad_util_energia
    """, (
        fecha,
        valores_dict.get("embalses_porcentaje"),
        valores_dict.get("embalses_energia"),
        valores_dict.get("aportes_porcentaje"),
        valores_dict.get("aportes_energia"),
        valores_dict.get("aportes_media_historica"),
        valores_dict.get("capacidad_util_energia"),
    ))

    conexion.commit()
    conexion.close()

    print("  Variables hidrologicas guardadas para " + fecha + ".")


def consultar_todo_variables_hidrologicas():
    """
    Trae todo el historico de variables hidrologicas guardado en la
    base de datos, ordenado por fecha.

    Retorna:
        Un DataFrame con todas las columnas de la tabla.
    """
    conexion = obtener_conexion()
    df = pd.read_sql_query("SELECT * FROM variables_hidrologicas ORDER BY fecha", conexion)
    conexion.close()
    return df


def guardar_senda_referencia(tabla_dataframe):
    """
    Guarda (o actualiza) los valores de la Senda de Referencia del
    Embalse, a partir de un DataFrame con columnas "fecha" y "valor".
    """
    if len(tabla_dataframe) == 0:
        print("No hay datos de senda de referencia para guardar.")
        return

    crear_tablas()

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    for _, fila in tabla_dataframe.iterrows():
        cursor.execute("""
            INSERT INTO senda_referencia (fecha, valor)
            VALUES (?, ?)
            ON CONFLICT(fecha) DO UPDATE SET valor=excluded.valor
        """, (fila["fecha"], float(fila["valor"])))

    conexion.commit()
    conexion.close()

    print(str(len(tabla_dataframe)) + " dia(s) de senda de referencia guardado(s).")


def consultar_todo_senda_referencia():
    """
    Trae todo el historico de la Senda de Referencia del Embalse
    guardado en la base de datos.

    Retorna:
        Un DataFrame con columnas: fecha, valor.
    """
    conexion = obtener_conexion()
    df = pd.read_sql_query("SELECT * FROM senda_referencia ORDER BY fecha", conexion)
    conexion.close()
    return df


def guardar_listado_recursos(tabla_dataframe):
    """
    Guarda (reemplazando el contenido anterior) el listado de
    plantas/recursos con su tipo de tecnologia.

    Parametros:
        tabla_dataframe: DataFrame con columnas codigo, nombre, tecnologia.
    """
    crear_tablas()

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("DELETE FROM listado_recursos")

    for _, fila in tabla_dataframe.iterrows():
        cursor.execute("""
            INSERT INTO listado_recursos (codigo, nombre, tecnologia)
            VALUES (?, ?, ?)
        """, (fila["codigo"], fila["nombre"], fila["tecnologia"]))

    conexion.commit()
    conexion.close()


def consultar_listado_recursos():
    """
    Trae el listado completo de plantas/recursos con su tecnologia.

    Retorna:
        Un DataFrame con columnas: codigo, nombre, tecnologia.
    """
    conexion = obtener_conexion()
    df = pd.read_sql_query("SELECT * FROM listado_recursos", conexion)
    conexion.close()
    return df


def guardar_generacion_por_fuente(fecha, totales_por_tecnologia):
    """
    Guarda (o actualiza) los totales de generacion por tecnologia
    de un dia especifico.

    Parametros:
        fecha (str): fecha en formato YYYY-MM-DD.
        totales_por_tecnologia (dict): {tecnologia: valor_kwh}
    """
    crear_tablas()

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    for tecnologia, valor in totales_por_tecnologia.items():
        cursor.execute("""
            INSERT INTO generacion_por_fuente (fecha, tecnologia, valor_kwh)
            VALUES (?, ?, ?)
            ON CONFLICT(fecha, tecnologia) DO UPDATE SET valor_kwh=excluded.valor_kwh
        """, (fecha, tecnologia, valor))

    conexion.commit()
    conexion.close()

    print("Generacion por fuente guardada para " + fecha + ".")


def consultar_generacion_por_fuente_de_un_dia(fecha):
    """
    Trae la generacion por tecnologia de un dia especifico.

    Retorna:
        Un DataFrame con columnas: tecnologia, valor_kwh.
    """
    conexion = obtener_conexion()
    df = pd.read_sql_query(
        "SELECT tecnologia, valor_kwh FROM generacion_por_fuente WHERE fecha = ?",
        conexion, params=(fecha,)
    )
    conexion.close()
    return df


def consultar_todo_generacion_por_fuente():
    """
    Trae todo el historico de generacion por fuente.

    Retorna:
        Un DataFrame con columnas: fecha, tecnologia, valor_kwh.
    """
    conexion = obtener_conexion()
    df = pd.read_sql_query("SELECT * FROM generacion_por_fuente ORDER BY fecha", conexion)
    conexion.close()
    return df


def consultar_fecha_mas_reciente_generacion():
    """
    Retorna la fecha mas reciente que tenga datos de generacion por
    fuente guardados, o None si no hay ninguna.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT MAX(fecha) FROM generacion_por_fuente")
    resultado = cursor.fetchone()
    conexion.close()

    if resultado is None:
        return None
    return resultado[0]


def ya_se_envio_hoy(nombre_proceso):
    """
    Revisa si un proceso especifico (por ejemplo, "diario" o
    "hidrologico") ya se ejecuto/envio el dia de hoy, para evitar
    enviar el mismo informe mas de una vez.

    Parametros:
        nombre_proceso (str): identificador del proceso, ej. "diario".

    Retorna:
        True si ya se envio hoy, False si no.
    """
    crear_tablas()

    hoy = datetime.now().strftime("%Y-%m-%d")

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "SELECT 1 FROM control_envios WHERE proceso = ? AND fecha = ?",
        (nombre_proceso, hoy)
    )
    resultado = cursor.fetchone()
    conexion.close()

    return resultado is not None


def marcar_enviado_hoy(nombre_proceso):
    """
    Registra que un proceso especifico ya se envio el dia de hoy.
    """
    crear_tablas()

    hoy = datetime.now().strftime("%Y-%m-%d")

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        INSERT INTO control_envios (proceso, fecha)
        VALUES (?, ?)
        ON CONFLICT(proceso, fecha) DO NOTHING
    """, (nombre_proceso, hoy))
    conexion.commit()
    conexion.close()

    print("Registrado: '" + nombre_proceso + "' ya se envio hoy (" + hoy + ").")


def dias_desde_ultimo_envio(nombre_proceso):
    """
    Calcula cuantos dias han pasado desde la ultima vez que se envio
    un proceso especifico. Util para procesos periodicos que no son
    diarios (por ejemplo, cada 15 dias).

    Retorna:
        Un numero entero de dias, o None si el proceso nunca se ha
        enviado (lo cual se debe interpretar como "hace falta enviarlo").
    """
    crear_tablas()

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "SELECT MAX(fecha) FROM control_envios WHERE proceso = ?",
        (nombre_proceso,)
    )
    resultado = cursor.fetchone()
    conexion.close()

    if resultado is None or resultado[0] is None:
        return None

    fecha_ultimo_envio = datetime.strptime(resultado[0], "%Y-%m-%d")
    dias_transcurridos = (datetime.now() - fecha_ultimo_envio).days
    return dias_transcurridos


def guardar_noticias(lista_noticias):
    """
    Guarda una lista de noticias en la base de datos. Si una noticia
    (identificada por su enlace) ya existe, no se duplica.

    Parametros:
        lista_noticias: lista de diccionarios con "titulo", "enlace",
                         "fecha", "fuente".
    """
    crear_tablas()

    if len(lista_noticias) == 0:
        print("No hay noticias nuevas para guardar.")
        return

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    fecha_busqueda = datetime.now().strftime("%Y-%m-%d")

    for noticia in lista_noticias:
        cursor.execute("""
            INSERT INTO noticias (enlace, titulo, fecha_publicacion, fuente, fecha_busqueda)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(enlace) DO NOTHING
        """, (noticia["enlace"], noticia["titulo"], noticia["fecha"], noticia["fuente"], fecha_busqueda))

    conexion.commit()
    conexion.close()

    print("Noticias guardadas en la base de datos.")


def consultar_noticias_recientes(dias=7):
    """
    Trae las noticias publicadas en los ultimos N dias.

    Retorna:
        Un DataFrame con columnas: enlace, titulo, fecha_publicacion, fuente.
    """
    crear_tablas()

    fecha_limite = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")

    conexion = obtener_conexion()
    df = pd.read_sql_query(
        "SELECT * FROM noticias WHERE fecha_publicacion >= ? ORDER BY fecha_publicacion DESC",
        conexion, params=(fecha_limite,)
    )
    conexion.close()
    return df


if __name__ == "__main__":
    crear_tablas()

    historico_bolsa = consultar_todo_precio_bolsa()
    historico_imar = consultar_todo_imar()

    print("")
    print("Dias guardados en precio_bolsa: " + str(len(historico_bolsa)))
    print("Dias guardados en imar: " + str(len(historico_imar)))
