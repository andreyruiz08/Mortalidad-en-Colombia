"""Carga y preparación de los datos de mortalidad en Colombia (2019).

Lee los tres archivos de Excel de la carpeta data/ y construye las tablas
resumidas que usa cada visualización de la aplicación.
"""

from pathlib import Path

import pandas as pd

CARPETA_DATOS = Path(__file__).parent / "data"
ARCHIVO_MORTALIDAD = CARPETA_DATOS / "Datosmortalidad.xlsx"
ARCHIVO_MORTALIDAD_CSV = CARPETA_DATOS / "mortalidad_2019.csv"
ARCHIVO_DIVIPOLA = CARPETA_DATOS / "divisionpoliticoadministrativa.xlsx"
ARCHIVO_CAUSAS = CARPETA_DATOS / "Codigoscausamuerte.xlsx"

COLUMNAS_MORTALIDAD = ["COD_DANE", "COD_DEPARTAMENTO", "MES", "SEXO", "GRUPO_EDAD1", "COD_MUERTE"]
TIPOS_MORTALIDAD = {"COD_DANE": str, "COD_DEPARTAMENTO": str, "COD_MUERTE": str}

MESES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

SEXOS = {1: "Hombre", 2: "Mujer", 3: "Indeterminado"}

# Agrupación de GRUPO_EDAD1 según la tabla de referencia del DANE:
# (categoría, código inicial, código final, rango de edad)
GRUPOS_EDAD = [
    ("Mortalidad neonatal", 0, 4, "Menor de 1 mes"),
    ("Mortalidad infantil", 5, 6, "1 a 11 meses"),
    ("Primera infancia", 7, 8, "1 a 4 años"),
    ("Niñez", 9, 10, "5 a 14 años"),
    ("Adolescencia", 11, 11, "15 a 19 años"),
    ("Juventud", 12, 13, "20 a 29 años"),
    ("Adultez temprana", 14, 16, "30 a 44 años"),
    ("Adultez intermedia", 17, 19, "45 a 59 años"),
    ("Vejez", 20, 24, "60 a 84 años"),
    ("Longevidad / Centenarios", 25, 28, "85 a 100+ años"),
    ("Edad desconocida", 29, 29, "Sin información"),
]

# Homicidios con arma de fuego: CIE-10 X95 "Agresión con disparo de otras
# armas de fuego, y las no especificadas" (incluye X950 a X959)
CODIGO_HOMICIDIO_ARMA_FUEGO = "X95"

PALABRAS_MINUSCULA = {"De", "Del", "La", "Las", "Los", "Y", "El"}
NOMBRES_CORTOS = {
    "ARCHIPIÉLAGO DE SAN ANDRÉS, PROVIDENCIA Y SANTA CATALINA": "San Andrés y Providencia",
}


def nombre_legible(nombre: str) -> str:
    """Convierte 'SAN JOSÉ DE CÚCUTA' en 'San José de Cúcuta'."""
    nombre = nombre.strip()
    if nombre in NOMBRES_CORTOS:
        return NOMBRES_CORTOS[nombre]
    palabras = nombre.title().split(" ")
    return " ".join(
        p.lower() if i > 0 and p in PALABRAS_MINUSCULA else p
        for i, p in enumerate(palabras)
    )


# ---------------------------------------------------------------------------
# Lectura de los archivos de Excel
# ---------------------------------------------------------------------------

def convertir_mortalidad_a_csv() -> None:
    """Guarda en CSV solo las columnas que usa la aplicación.

    Leer el Excel completo (19 MB, 244.355 filas) necesita más memoria de la
    que ofrece el plan gratuito de Render (512 MB). El CSV liviano se genera
    una sola vez a partir del Excel original y queda guardado en data/.
    """
    mortalidad = pd.read_excel(
        ARCHIVO_MORTALIDAD,
        sheet_name="No_Fetales_2019",
        usecols=COLUMNAS_MORTALIDAD,
        dtype=TIPOS_MORTALIDAD,
        engine="calamine",
    )
    mortalidad.to_csv(ARCHIVO_MORTALIDAD_CSV, index=False)


def cargar_mortalidad() -> pd.DataFrame:
    """Registros de defunciones no fetales de 2019 (una fila por muerte)."""
    if not ARCHIVO_MORTALIDAD_CSV.exists():
        convertir_mortalidad_a_csv()
    return pd.read_csv(ARCHIVO_MORTALIDAD_CSV, dtype=TIPOS_MORTALIDAD)


def cargar_municipios() -> pd.DataFrame:
    """División político-administrativa (DIVIPOLA): nombres, tipo y coordenadas."""
    municipios = pd.read_excel(
        ARCHIVO_DIVIPOLA,
        sheet_name="Hoja3",
        header=None,
        skiprows=2,
        names=["COD_DEPARTAMENTO", "DEPARTAMENTO", "COD_DANE", "MUNICIPIO", "TIPO", "LONGITUD", "LATITUD"],
        dtype=str,
        engine="calamine",
    )
    municipios["DEPARTAMENTO"] = municipios["DEPARTAMENTO"].map(nombre_legible)
    municipios["MUNICIPIO"] = municipios["MUNICIPIO"].map(nombre_legible)
    # Las coordenadas vienen con coma decimal ("-75,581775")
    for columna in ["LONGITUD", "LATITUD"]:
        municipios[columna] = pd.to_numeric(municipios[columna].str.replace(",", "."))
    return municipios


def cargar_causas() -> pd.DataFrame:
    """Catálogo CIE-10 con códigos de 3 y 4 caracteres y su descripción."""
    causas = pd.read_excel(ARCHIVO_CAUSAS, sheet_name="Final", header=8, usecols="C:F", dtype=str, engine="calamine")
    causas.columns = ["COD_3", "NOMBRE_3", "COD_4", "NOMBRE_4"]
    causas = causas.dropna(subset=["COD_3"])
    for columna in causas.columns:
        causas[columna] = causas[columna].str.strip()
    # Los nombres de 3 caracteres vienen en "Tipo Título"; se dejan como frase
    causas["NOMBRE_3"] = causas["NOMBRE_3"].str.capitalize()

    # En los datos hay códigos de 4 caracteres (I219) y de 3 caracteres (F03),
    # así que se arma un diccionario único código -> nombre con ambos niveles.
    nombres_3 = causas.drop_duplicates("COD_3").set_index("COD_3")["NOMBRE_3"]
    nombres_4 = causas.set_index("COD_4")["NOMBRE_4"]
    return pd.concat([nombres_3, nombres_4]).rename("NOMBRE").rename_axis("CODIGO").reset_index()


# ---------------------------------------------------------------------------
# Tablas para cada visualización
# ---------------------------------------------------------------------------

def muertes_por_departamento(mortalidad, municipios):
    """Total de muertes por departamento con el centro geográfico para el mapa."""
    centros = municipios.groupby(["COD_DEPARTAMENTO", "DEPARTAMENTO"], as_index=False)[["LATITUD", "LONGITUD"]].mean()
    totales = mortalidad.groupby("COD_DEPARTAMENTO").size().rename("MUERTES").reset_index()
    return centros.merge(totales, on="COD_DEPARTAMENTO").sort_values("MUERTES", ascending=False)


def muertes_por_mes(mortalidad):
    """Total de muertes en cada mes de 2019."""
    tabla = mortalidad.groupby("MES").size().rename("MUERTES").reset_index()
    tabla["NOMBRE_MES"] = tabla["MES"].map(MESES)
    return tabla


def ciudades_mas_violentas(mortalidad, municipios, cantidad=5):
    """Municipios con más homicidios por arma de fuego (código X95)."""
    homicidios = mortalidad[mortalidad["COD_MUERTE"].str.startswith(CODIGO_HOMICIDIO_ARMA_FUEGO)]
    tabla = homicidios.groupby("COD_DANE").size().rename("HOMICIDIOS").reset_index()
    tabla = tabla.merge(municipios[["COD_DANE", "MUNICIPIO", "DEPARTAMENTO"]], on="COD_DANE")
    return tabla.nlargest(cantidad, "HOMICIDIOS")


def ciudades_menor_mortalidad(mortalidad, municipios, cantidad=10):
    """Municipios con menos muertes registradas.

    Se excluyen las áreas no municipalizadas porque no son ciudades. Los
    empates se ordenan alfabéticamente por nombre del municipio.
    """
    ciudades = municipios[municipios["TIPO"] != "Área no municipalizada"]
    tabla = mortalidad.groupby("COD_DANE").size().rename("MUERTES").reset_index()
    tabla = tabla.merge(ciudades[["COD_DANE", "MUNICIPIO", "DEPARTAMENTO"]], on="COD_DANE")
    return tabla.sort_values(["MUERTES", "MUNICIPIO"]).head(cantidad)


def principales_causas(mortalidad, causas, cantidad=10):
    """Las causas de muerte más frecuentes con su código CIE-10 y nombre."""
    tabla = mortalidad.groupby("COD_MUERTE").size().rename("TOTAL").reset_index()
    tabla = tabla.nlargest(cantidad, "TOTAL")
    tabla = tabla.merge(causas, left_on="COD_MUERTE", right_on="CODIGO", how="left")
    return tabla[["CODIGO", "NOMBRE", "TOTAL"]]


def muertes_por_sexo_y_departamento(mortalidad, municipios):
    """Muertes por sexo en cada departamento (formato largo para barras apiladas)."""
    departamentos = municipios[["COD_DEPARTAMENTO", "DEPARTAMENTO"]].drop_duplicates()
    tabla = mortalidad.groupby(["COD_DEPARTAMENTO", "SEXO"]).size().rename("MUERTES").reset_index()
    tabla["SEXO"] = tabla["SEXO"].map(SEXOS)
    return tabla.merge(departamentos, on="COD_DEPARTAMENTO")


def muertes_por_grupo_edad(mortalidad):
    """Muertes agrupadas en las categorías del ciclo de vida de GRUPO_EDAD1."""
    filas = []
    for categoria, inicio, fin, rango in GRUPOS_EDAD:
        total = mortalidad["GRUPO_EDAD1"].between(inicio, fin).sum()
        filas.append({"CATEGORIA": categoria, "RANGO": rango, "MUERTES": int(total)})
    return pd.DataFrame(filas)


def preparar_datos() -> dict:
    """Lee los archivos y devuelve todas las tablas que necesita la aplicación."""
    mortalidad = cargar_mortalidad()
    municipios = cargar_municipios()
    causas = cargar_causas()
    return {
        "total_muertes": len(mortalidad),
        "departamentos": muertes_por_departamento(mortalidad, municipios),
        "meses": muertes_por_mes(mortalidad),
        "violentas": ciudades_mas_violentas(mortalidad, municipios),
        "menor_mortalidad": ciudades_menor_mortalidad(mortalidad, municipios),
        "causas": principales_causas(mortalidad, causas),
        "sexo_departamento": muertes_por_sexo_y_departamento(mortalidad, municipios),
        "grupos_edad": muertes_por_grupo_edad(mortalidad),
    }
