"""Aplicación web: Mortalidad en Colombia 2019.

Visualizaciones interactivas construidas a partir de los
datos de defunciones no fetales del DANE.

"""

import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html
from datos import preparar_datos

# ---------------------------------------------------------------------------
# Colores
# ---------------------------------------------------------------------------
AZUL = "#5B9DDF"
ROSA_OSCURO = "#CB6D67"
LAVANDA = "#9284D6"
COLORES_SEXO = {"Hombre": "#5497D9", "Mujer": "#E88AA8", "Indeterminado": "#CBAA4B"}
COLORES_CIRCULAR = ["#5B9DDF", "#C7B05A", "#AE6AA8", "#7FC88F", "#CB6D67",
                    "#30B1C4", "#E99E5E", "#9284D6", "#9DC276", "#C36886"]
ESCALA_AZUL = ["#BADBFE", "#91C3F6", "#6AA6E4", "#488ACB", "#286CAB"]
TEXTO = "#2E2A3B"
TEXTO_SUAVE = "#6B6680"
FONDO_TARJETA = "#FFFFFF"
LINEA_GUIA = "#EEEAF5"


def formato_miles(numero: int) -> str:
   
    return f"{numero:,}".replace(",", ".")


def aplicar_estilo(figura: go.Figure, alto: int = 420) -> go.Figure:
  
    figura.update_layout(
        height=alto,
        template="plotly_white",
        separators=",.",
        font=dict(family="Segoe UI, Roboto, Helvetica, Arial, sans-serif", size=13, color=TEXTO),
        paper_bgcolor=FONDO_TARJETA,
        plot_bgcolor=FONDO_TARJETA,
        margin=dict(l=10, r=20, t=20, b=10),
        hoverlabel=dict(bgcolor="white", bordercolor=LINEA_GUIA, font_color=TEXTO),
    )
    figura.update_xaxes(gridcolor=LINEA_GUIA, zeroline=False, linecolor=LINEA_GUIA)
    figura.update_yaxes(gridcolor=LINEA_GUIA, zeroline=False, linecolor=LINEA_GUIA)
    return figura


# ---------------------------------------------------------------------------
# Figuras
# ---------------------------------------------------------------------------

def figura_mapa(departamentos):

    figura = px.scatter_map(
        departamentos,
        lat="LATITUD",
        lon="LONGITUD",
        size="MUERTES",
        color="MUERTES",
        color_continuous_scale=ESCALA_AZUL,
        size_max=42,
        hover_name="DEPARTAMENTO",
        custom_data=["MUERTES"],
        zoom=4.6,
        center={"lat": 4.6, "lon": -74.8},
        map_style="carto-positron",
    )
    figura.update_traces(
        marker=dict(opacity=0.85),
        hovertemplate="<b>%{hovertext}</b><br>Muertes: %{customdata[0]:,}<extra></extra>",
    )
    figura.update_layout(coloraxis_colorbar=dict(title="Muertes", thickness=12))
    return aplicar_estilo(figura, alto=620)


def figura_meses(meses):
    """Gráfico de líneas: total de muertes por mes."""
    figura = px.line(meses, x="NOMBRE_MES", y="MUERTES", markers=True)
    figura.update_traces(
        line=dict(color=AZUL, width=2.5),
        marker=dict(size=9, color=AZUL, line=dict(color="white", width=2)),
        hovertemplate="<b>%{x}</b><br>Muertes: %{y:,}<extra></extra>",
    )
    # Etiquetas solo en el mes más alto y el más bajo
    for fila, posicion in [(meses.loc[meses["MUERTES"].idxmax()], "top center"),
                           (meses.loc[meses["MUERTES"].idxmin()], "bottom center")]:
        figura.add_annotation(
            x=fila["NOMBRE_MES"], y=fila["MUERTES"], text=formato_miles(int(fila["MUERTES"])),
            showarrow=False, yshift=16 if posicion == "top center" else -16,
            font=dict(color=TEXTO, size=12),
        )
    figura.update_xaxes(title=None)
    figura.update_yaxes(title="Muertes", tickformat=",d")
    return aplicar_estilo(figura)


def figura_violentas(violentas):
    """Barras: 5 ciudades con más homicidios por arma de fuego (X95)."""
    tabla = violentas.sort_values("HOMICIDIOS")
    figura = px.bar(tabla, x="HOMICIDIOS", y="MUNICIPIO", orientation="h", text="HOMICIDIOS",
                    custom_data=["DEPARTAMENTO"])
    figura.update_traces(
        marker=dict(color=ROSA_OSCURO, cornerradius=4),
        textposition="outside",
        textfont=dict(color=TEXTO),
        hovertemplate="<b>%{y}</b> (%{customdata[0]})<br>Homicidios X95: %{x:,}<extra></extra>",
    )
    # Margen a la derecha para que se lea el número de la barra más larga
    figura.update_xaxes(title="Homicidios (X95)", range=[0, tabla["HOMICIDIOS"].max() * 1.15])
    figura.update_yaxes(title=None)
    return aplicar_estilo(figura, alto=520)


def figura_menor_mortalidad(menor_mortalidad):
    """Gráfico circular: 10 ciudades con menos muertes."""
    tabla = menor_mortalidad.assign(
        ETIQUETA=menor_mortalidad["MUNICIPIO"] + " (" + menor_mortalidad["DEPARTAMENTO"] + ")"
    )
    figura = px.pie(tabla, names="ETIQUETA", values="MUERTES", color_discrete_sequence=COLORES_CIRCULAR)
    figura.update_traces(
        sort=False,
        textinfo="value",
        textfont=dict(color=TEXTO, size=13),
        marker=dict(line=dict(color="white", width=2)),
        hovertemplate="<b>%{label}</b><br>Muertes: %{value}<extra></extra>",
    )
    figura.update_layout(legend=dict(title=None, font=dict(size=12), orientation="h", yanchor="top", y=-0.02))
    return aplicar_estilo(figura, alto=520)


def figura_tabla_causas(causas):
    """Tabla: 10 principales causas de muerte."""
    posiciones = list(range(1, len(causas) + 1))
    filas_color = ["#FFFFFF" if i % 2 else "#F8F6FD" for i in posiciones]
    figura = go.Figure(go.Table(
        columnwidth=[30, 70, 420, 80],
        header=dict(
            values=["<b>#</b>", "<b>Código</b>", "<b>Causa de muerte</b>", "<b>Total de casos</b>"],
            fill_color="#E7E2F7", font=dict(color=TEXTO, size=13), align=["center", "center", "left", "right"],
            height=34,
        ),
        cells=dict(
            values=[posiciones, causas["CODIGO"], causas["NOMBRE"], [formato_miles(int(t)) for t in causas["TOTAL"]]],
            fill_color=[filas_color] * 4, font=dict(color=TEXTO, size=13),
            align=["center", "center", "left", "right"], height=30, line_color=LINEA_GUIA,
        ),
    ))
    return aplicar_estilo(figura, alto=390)


def figura_sexo_departamento(sexo_departamento):
    """Barras apiladas: muertes por sexo en cada departamento."""

    orden = sexo_departamento.groupby("DEPARTAMENTO")["MUERTES"].sum().sort_values(ascending=False).index.tolist()
    figura = px.bar(
        sexo_departamento, x="MUERTES", y="DEPARTAMENTO", color="SEXO", orientation="h",
        color_discrete_map=COLORES_SEXO,
        category_orders={"DEPARTAMENTO": orden, "SEXO": list(COLORES_SEXO)},
    )
    figura.update_traces(
        marker_line=dict(color="white", width=1),
        hovertemplate="<b>%{y}</b><br>%{fullData.name}: %{x:,}<extra></extra>",
    )
    figura.update_layout(
        barmode="stack", bargap=0.25,
        legend=dict(title=None, orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
    )
    figura.update_xaxes(title="Muertes", tickformat=",d")
    figura.update_yaxes(title=None)
    return aplicar_estilo(figura, alto=860)


def figura_grupos_edad(grupos_edad):
    """Histograma: muertes por grupo de edad (GRUPO_EDAD1 agrupado)."""

    categoria_en_lineas = grupos_edad["CATEGORIA"].str.replace(" ", "<br>", n=1, regex=False)
    tabla = grupos_edad.assign(GRUPO=categoria_en_lineas + "<br>(" + grupos_edad["RANGO"] + ")")
    figura = px.histogram(tabla, x="GRUPO", y="MUERTES", histfunc="sum", text_auto=",.0f",
                          category_orders={"GRUPO": tabla["GRUPO"].tolist()})
    figura.update_traces(
        marker=dict(color=LAVANDA, cornerradius=4),
        textposition="outside",
        textfont=dict(color=TEXTO),
        hovertemplate="<b>%{x}</b><br>Muertes: %{y:,}<extra></extra>",
    )
    figura.update_layout(bargap=0.08)
    figura.update_xaxes(title=None, tickangle=0, tickfont=dict(size=11))
    figura.update_yaxes(title="Muertes", tickformat=",d")
    return aplicar_estilo(figura, alto=470)


# ---------------------------------------------------------------------------
# Componentes de la página
# ---------------------------------------------------------------------------

def tarjeta(titulo, descripcion, figura, ancho_completo=False):
    clase = "tarjeta ancho-completo" if ancho_completo else "tarjeta"
    return html.Section(className=clase, children=[
        html.H2(titulo),
        html.P(descripcion, className="descripcion"),
        dcc.Graph(figure=figura, config={"displaylogo": False, "locale": "es"}),
    ])


def indicador(valor, etiqueta):
    return html.Div(className="indicador", children=[
        html.Span(valor, className="indicador-valor"),
        html.Span(etiqueta, className="indicador-etiqueta"),
    ])


def crear_layout(datos):
    departamentos = datos["departamentos"]
    meses = datos["meses"]
    violentas = datos["violentas"]
    mes_mayor = meses.loc[meses["MUERTES"].idxmax()]

    return html.Main(className="contenedor", children=[
        html.Header(className="encabezado", children=[
            html.H1("Mortalidad en Colombia durante el año 2019"),
            html.P("Análisis de las muertes no fetales registradas por el DANE."),
        ]),
       
        html.Div(className="cuadricula", children=[
            tarjeta("Muertes por departamento",
                    "Total de muertes registradas en cada departamento.",
                    figura_mapa(departamentos), ancho_completo=True),

            tarjeta("Muertes por mes",
                    "Total de muertes registradas en cada mes durante 2019.",
                    figura_meses(meses), ancho_completo=True),

            tarjeta("Las 5 ciudades más violentas",
                    "Municipios con más homicidios por arma de fuego.",
                    figura_violentas(violentas)),

            tarjeta("Las 10 ciudades con menor mortalidad",
                    "Municipios con menos muertes registradas en 2019",
                    figura_menor_mortalidad(datos["menor_mortalidad"])),

            tarjeta("Las 10 principales causas de muerte",
                    "Causas con más casos según su código.",
                    figura_tabla_causas(datos["causas"]), ancho_completo=True),

            tarjeta("Muertes por sexo en cada departamento",
                    "Comparación entre hombres y mujeres.",
                    figura_sexo_departamento(datos["sexo_departamento"]), ancho_completo=True),

            tarjeta("Muertes por grupo de edad",
                    "Distribución de las muertes a lo largo del ciclo de vida.",
                    figura_grupos_edad(datos["grupos_edad"]), ancho_completo=True),
        ]),

        html.Footer(className="pie-pagina", children=[
            html.P("Fuente: DANE, Estadísticas Vitales 2019."),
        ]),
    ])


# ---------------------------------------------------------------------------
# Aplicación
# ---------------------------------------------------------------------------
app = Dash(__name__, title="Mortalidad en Colombia 2019")
server = app.server 
app.layout = crear_layout(preparar_datos())

if __name__ == "__main__":
    app.run(debug=False)
