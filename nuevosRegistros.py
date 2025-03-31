import os
from notion_client import Client
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env
load_dotenv()

# 1. Inicializar el cliente de Notion
notion_api = os.environ.get("NOTION_API_KEY")
if not notion_api:
    print("Error: No se encontró la variable de entorno 'NOTION_API_KEY'. Asegúrate de haber configurado el archivo .env")
    exit()

notion = Client(auth=notion_api)

# 2. Definir los IDs de tus bases de datos (¡ahora los lee del .env!)
DATABASE_ID_PROYECTOS = os.environ.get("DATABASE_ID_PROYECTOS")
DATABASE_ID_PARTIDAS = os.environ.get("DATABASE_ID_PARTIDAS")

# --- (El resto del código de la función crear_proyecto queda igual) ---
def crear_proyecto(nombre_proyecto):
    """
    Crea una nueva página de proyecto en la base de datos de Proyectos.
    """
    try:
        response = notion.pages.create(
            parent={"database_id": DATABASE_ID_PROYECTOS},
            properties={
                "ID del proyecto": {"title": [{"text": {"content": nombre_proyecto}}]},
                # ... (puedes añadir más propiedades aquí si tu base de datos de Proyectos tiene más campos)
            }
        )
        return response['id']
    except Exception as e:
        print(f"Error al crear el proyecto '{nombre_proyecto}': {e}")
        return None

def crear_partidas(num_partidas, proyecto_id):
    """
    Crea múltiples páginas de partida en la base de datos de Partidas y las relaciona con el proyecto.
    El nombre de cada partida ahora incluye el nombre del proyecto y un contador.
    """
    partidas_ids = []

    # 1. Obtener el nombre del proyecto a partir del proyecto_id
    try:
        proyecto_page = notion.pages.retrieve(proyecto_id) # Recupera la página del proyecto usando su ID
        proyecto_nombre = proyecto_page['properties']['ID del proyecto']['title'][0]['plain_text'] # Asume que "ID del proyecto" es la propiedad 'Title'
    except Exception as e:
        print(f"Error al obtener el nombre del proyecto con ID '{proyecto_id}': {e}")
        return partidas_ids # Devuelve una lista vacía de partidas_ids si no se puede obtener el nombre del proyecto

    for i in range(num_partidas):
        # 2. Construir el nombre de la partida con el formato deseado
        partida_conteo = f"{i:02d}.00" # Formatea el contador a "00.00", "01.00", "02.00", etc.
        nombre_partida = f"{proyecto_nombre}-{partida_conteo}" # Combina nombre del proyecto y contador

        try:
            response = notion.pages.create(
                parent={"database_id": DATABASE_ID_PARTIDAS},
                properties={
                    "ID de partida": {"title": [{"text": {"content": nombre_partida}}]}, # Usa el nuevo nombre de partida
                    "Proyectos": {
                        "relation": [
                            {"id": proyecto_id}
                        ]
                    },
                    # ... (puedes añadir más propiedades aquí si tu base de datos de Partidas tiene más campos)
                }
            )
            partidas_ids.append(response['id'])
            print(f"Partida '{nombre_partida}' creada con ID: {response['id']}")
        except Exception as e:
            print(f"Error al crear la partida '{nombre_partida}': {e}")
    return partidas_ids

if __name__ == "__main__":
    nombre_proyecto_usuario = input("Introduce el nombre del proyecto: ")
    num_partidas_usuario = int(input("Introduce el número de partidas para el proyecto: "))

    proyecto_page_id = crear_proyecto(nombre_proyecto_usuario)
    if proyecto_page_id:
        print(f"Proyecto '{nombre_proyecto_usuario}' creado con ID: {proyecto_page_id}")
        partidas_ids = crear_partidas(num_partidas_usuario, proyecto_page_id)
        if partidas_ids:
            print(f"Se crearon {len(partidas_ids)} partidas para el proyecto '{nombre_proyecto_usuario}'.")
            print("¡Proceso completado con éxito!")
        else:
            print("Hubo errores al crear las partidas.")
    else:
        print("Hubo errores al crear el proyecto.")
