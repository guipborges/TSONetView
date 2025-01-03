import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, Point
from shapely.validation import make_valid

# === Function Definitions ===

# Função para obter o centro do país selecionado
def get_country_center(selected_country_iso, geojson):
    for feature in geojson["features"]:
        if feature["properties"]["ISO2"] == selected_country_iso:
            geometry = shape(feature["geometry"])
            if geometry.is_valid:
                return geometry.centroid.y, geometry.centroid.x
    return [48, 16]  # Fallback

# Carregar e validar GeoJSON
def load_valid_geojson(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)
        for feature in geojson_data["features"]:
            geometry = shape(feature["geometry"])
            if not geometry.is_valid:
                feature["geometry"] = make_valid(geometry).__geo_interface__
            if "neighbors" not in feature["properties"]:
                feature["properties"]["neighbors"] = []
    return geojson_data

# Função para carregar JSON como pandas DataFrame
def load_json_as_dataframe(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return pd.json_normalize(json.load(f))

# Função para obter vizinhos
#def get_neighbors(selected_country_iso, data):
#    row = data[data["Acronym"] == selected_country_iso]
#    if not row.empty:
#        return row.iloc[0].get("neighbors", [])
#    return []

# Função para obter vizinhos com base no boundaries.json
def get_neighbors(selected_country_iso, electrical_connections):
    neighbors = set()  # Usar um set para evitar duplicações
    for connection in electrical_connections["ConnectivityNode"]:
        from_iso = connection["ConnectivityNode.fromEndIsoCode"]
        to_iso = connection["ConnectivityNode.toEndIsoCode"]
        
        # Adicionar aos vizinhos se o país selecionado for de origem ou destino
        if from_iso == selected_country_iso:
            neighbors.add(to_iso)
        elif to_iso == selected_country_iso:
            neighbors.add(from_iso)
    
    return list(neighbors)  # Retorna a lista de acrônimos de vizinhos


# Função para adicionar linhas de conexão ao mapa
def add_connection_lines_to_map(geojson_data, electrical_connections, map_object, selected_country_iso):
    # Filtrar as conexões com base no país selecionado
    for connection in electrical_connections["ConnectivityNode"]:
        from_name = connection["ConnectivityNode.fromEndName"]
        to_name = connection["ConnectivityNode.toEndName"]
        from_tso = connection["ConnectivityNode.fromEndNameTso"]
        to_tso = connection["ConnectivityNode.toEndNameTso"]
        description = connection["IdentifiedObject.description"]
        from_iso = connection["ConnectivityNode.fromEndIsoCode"]
        to_iso = connection["ConnectivityNode.toEndIsoCode"]

        # Verificar se o país selecionado é o ponto de origem ou destino da conexão
        if from_iso == selected_country_iso or to_iso == selected_country_iso:
            # Coordenadas baseadas nas fronteiras dos países
            from_coords = get_country_center(from_iso, geojson_data)
            to_coords = get_country_center(to_iso, geojson_data)

            # Adicionar a linha no mapa entre as subestações
            folium.PolyLine(
                locations=[from_coords, to_coords],
                color="green",
                weight=4,
                opacity=0.7
            ).add_to(map_object)

            # Adicionar a legenda perto de cada subestação (TSO)
            folium.Marker(
                location=from_coords,
                popup=f"{from_name} ({from_tso})",
                icon=folium.Icon(color='blue')
            ).add_to(map_object)

            folium.Marker(
                location=to_coords,
                popup=f"{to_name} ({to_tso})",
                icon=folium.Icon(color='blue')
            ).add_to(map_object)

            # Adicionar o nome da linha sobre a linha de transmissão
            line_description = from_iso + " - "  + "  " + from_name + " (" + from_tso + ")"  + " - " + to_name + " " + "(" + to_tso + ")" + " - " + to_iso
            midpoint = [(from_coords[0] + to_coords[0]) / 2, (from_coords[1] + to_coords[1]) / 2]
            folium.Marker(
                location=midpoint,
                popup=line_description,
                icon=folium.Icon(color='red')
            ).add_to(map_object)

# Função para sincronizar seletores
def sync_selections():
    if st.session_state["country_select"] != st.session_state["selected_country"]:
        row = data[data["Country"] == st.session_state["country_select"]].iloc[0]
    elif st.session_state["acronym_select"] != st.session_state["selected_acronym"]:
        row = data[data["Acronym"] == st.session_state["acronym_select"]].iloc[0]
    else:
        row = data[data["Company"] == st.session_state["tso_select"]].iloc[0]

    st.session_state["selected_country"] = row["Country"]
    st.session_state["selected_acronym"] = row["Acronym"]
    st.session_state["selected_tso"] = row["Company"]

# === Main Program ===

# Load data
geojson_data = load_valid_geojson("countries.geojson")
data = load_json_as_dataframe("tso_data_cleaned.json")

# Carregar o arquivo electrical_connections.json com codificação UTF-8
with open('boundaries.json', encoding='utf-8') as f:
    electrical_connections = json.load(f)

# Inicializar estados apenas uma vez
if "selected_country" not in st.session_state:
    st.session_state["selected_country"] = data["Country"].iloc[0]
if "selected_acronym" not in st.session_state:
    st.session_state["selected_acronym"] = data["Acronym"].iloc[0]
if "selected_tso" not in st.session_state:
    st.session_state["selected_tso"] = data["Company"].iloc[0]


# UI Selectors
st.title("Interactive TSO Map in Europe")
col1, col2, col3 = st.columns(3)

with col1:
    country_select = st.selectbox(
        "Select Country:",
        data["Country"].unique(),
        index=data["Country"].tolist().index(st.session_state["selected_country"]), 
        key="country_select", on_change=sync_selections
    )
with col2:
    acronym_select = st.selectbox(
        "Select Acronym:",
        data["Acronym"].unique(),
        index=data["Acronym"].tolist().index(st.session_state["selected_acronym"]), 
        key="acronym_select", on_change=sync_selections
    )
with col3:
    tso_select = st.selectbox(
        "Select TSO Name:",
        data["Company"].unique(),
        index=data["Company"].tolist().index(st.session_state["selected_tso"]), 
        key="tso_select", on_change=sync_selections
    )

# Sincronizar seletores apenas quando necessário
#if country_select != st.session_state["selected_country"]:
#    sync_selections()
#elif acronym_select != st.session_state["selected_acronym"]:
#    sync_selections()
#elif tso_select != st.session_state["selected_tso"]:
#    sync_selections()

# Obter informações sincronizadas
country_iso = st.session_state["selected_acronym"]
#neighbors = get_neighbors(country_iso, data)
neighbors = get_neighbors(country_iso, electrical_connections)
center_coords = get_country_center(country_iso, geojson_data)

# Criar mapa
m = folium.Map(location=center_coords, zoom_start=6, tiles="CartoDB positron")
for feature in geojson_data["features"]:
    iso_code = feature["properties"]["ISO2"]
    #color = "red" if iso_code in neighbors else "blue" if iso_code == country_iso else "lightgray"
    color = "blue" if iso_code == country_iso else "lightgray"  # Remover o vermelho
    folium.GeoJson(
        feature,
        style_function=lambda x, color=color: {
            "fillColor": color,
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.7 if color != "lightgray" else 0.4,
        },
        tooltip=feature["properties"]["ISO2"]
    ).add_to(m)

# Adicionar as conexões no mapa
add_connection_lines_to_map(geojson_data, electrical_connections, m, country_iso)

# Mostrar mapa
st_folium(m, width=700, height=500)

# Exibir informações
st.write(f"**Country:** {st.session_state['selected_country']}")
st.write(f"**Acronym:** {st.session_state['selected_acronym']}")
st.write(f"**TSO Name:** {st.session_state['selected_tso']}")
st.write("**Neighboring Countries' Acronyms:**")
st.write(", ".join(neighbors) if neighbors else "No neighbors found")

# Combine neighboring acronyms with country names and TSO names
neighboring_info = []
for acronym in neighbors:
    row = data[data["Acronym"] == acronym]
    if not row.empty:
        country_name = row.iloc[0]["Country"]
        tso_name = row.iloc[0]["Company"]
        neighboring_info.append(f"{acronym} - {country_name} ({tso_name})")

# Display neighboring countries with details.
if neighboring_info:
    for info in neighboring_info:
        st.write(f"- {info}")
else:
    st.write("No neighboring countries found.")