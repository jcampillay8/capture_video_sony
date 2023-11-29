# PARTE 1
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from flask import Flask, request
import os
import cv2
import base64
import io
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

server = Flask(__name__)
app = dash.Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container(
    [
        dbc.Row([
            dbc.Col(html.H1("Editor Videos Familia", style={"text-align": "center", "margin-top": "20px", "margin-bottom": "20px"}), width=6),
        ]),
        dbc.Input(id="input-ruta", placeholder="Introduce la ruta del video", type="text"),
        html.Div(id="file-name"),
        dbc.Row([
            dbc.Col(html.Div(dbc.Button("Extraer imágenes", id="extract-button", color="primary"), style={"margin-top": "20px", "margin-bottom": "20px"}), width=3),
            dbc.Col(html.Div(dbc.Button("Mostrar imágenes", id="display-button", color="primary"), style={"margin-top": "20px", "margin-bottom": "20px"}), width=3),
        ]),

        dbc.Row(id="image-row"),
        #dbc.Pagination(id="pagination", max_value=20, active_page=1,first_last=True, previous_next=True,size="L",fully_expanded=False),

        html.Div("Select a page", id="pagination-contents"),
        dbc.Row([
            dbc.Col(html.Div(dbc.Pagination(id="pagination", className="wrap", max_value=1, active_page=1, first_last=True, previous_next=True, size="L", fully_expanded=True),),style={"maxWidth": "1200px", "overflow": "scroll","margin-bottom": "20px"},),
        ],),


        dbc.Form(
            [
                dbc.Row(
                    [
                        dbc.Label("Nombre Video", className="mr-2"),
                        dbc.Input(id="nombre-video", placeholder="Introduce el nombre del video", type="text"),
                    ],
                    className="mr-3",
                ),
                dbc.Row(
                    [
                        dbc.Label("Inicio Video", className="mr-2"),
                        dbc.Input(id="inicio-video", placeholder="Introduce el inicio del video (hh:MM:ss)", type="text"),
                    ],
                    className="mr-3",
                ),
                dbc.Row(
                    [
                        dbc.Label("Fin Video", className="mr-2"),
                        dbc.Input(id="fin-video", placeholder="Introduce el fin del video (hh:MM:ss)", type="text"),
                    ],
                    className="mr-3",
                ),
                dbc.Row(
                    [
                        dbc.Label("Asignar Ruta Video Nuevo", className="mr-2"),
                        dbc.Input(id="ruta-video-nuevo", placeholder="Introduce la ruta del video nuevo", type="text"),
                    ],
                    className="mr-3",
                ),
                dbc.Row([
                    dbc.Col(html.Div(dbc.Button("Crear", id="crear-button", color="primary"), style={"margin-top": "20px", "margin-bottom": "20px"}), width=6),
                ]),
            ],
        ),
        html.Div(id="video-creado"),
    ]
)

# PARTE 2
@app.callback(Output("file-name", "children"), [Input("input-ruta", "value")])
def update_output(value):
    if value is None:
        return "No se ha introducido ninguna ruta."
    else:
        filename = os.path.basename(value)
        return f"El nombre del video cargado es: {filename}"

@app.callback(Output("image-row", "children"), Output("pagination", "max_value"), [Input("extract-button", "n_clicks"), Input("pagination", "active_page")], [State("input-ruta", "value")])
def extract_images(n, page, value):
    if n is None:
        return [], 1
    else:
        cap = cv2.VideoCapture(value)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_name = os.path.splitext(os.path.basename(value))[0]
        os.makedirs(f'Capturas_Imagenes/{video_name}', exist_ok=True)
        for i in range(0, frame_count, int(20 * fps)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if ret:
                _, buffer = cv2.imencode('.jpg', frame)
                # Save the image to the file system
                with open(f'Capturas_Imagenes/{video_name}/{int(i // fps):06d}.jpg', 'wb') as f:
                    f.write(buffer)
        cap.release()
        return "Imagenes guardas exitosamente en Capturas_Imagenes/" + video_name, len(os.listdir(f'Capturas_Imagenes/{video_name}')) // 3 + (len(os.listdir(f'Capturas_Imagenes/{video_name}')) % 3 > 0)

@app.callback(Output("image-row", "children",allow_duplicate=True), [Input("display-button", "n_clicks"), Input("pagination", "active_page")], [State("input-ruta", "value")],prevent_initial_call=True)
def display_images(n, page, value):
    if n is None:
        return []
    else:
        video_name = os.path.splitext(os.path.basename(value))[0]
        image_folder = f'Capturas_Imagenes/{video_name}'
        image_files = sorted(os.listdir(image_folder))
        start = (page - 1) * 3
        end = start + 3
        images = []
        for image_file in image_files[start:end]:
            with open(f'{image_folder}/{image_file}', 'rb') as f:
                encoded_image = base64.b64encode(f.read()).decode('utf-8')
                images.append((encoded_image, int(os.path.splitext(image_file)[0])))
        image_divs = [dbc.Col([html.Img(src=f"data:image/jpeg;base64,{image[0]}", height="200px"), html.P(f"Tiempo: {image[1] // 3600:02d}:{image[1] % 3600 // 60:02d}:{image[1] % 60:02d}")]) for image in images]
        return image_divs

@app.callback(Output("video-creado", "children"), [Input("crear-button", "n_clicks")], [State("input-ruta", "value"), State("nombre-video", "value"), State("inicio-video", "value"), State("fin-video", "value"), State("ruta-video-nuevo", "value")])
def create_video(n, ruta, nombre, inicio, fin, ruta_nuevo):
    if nombre is None:
        nombre = "video_default"
    nombre = nombre + ".mp4"
    if n is None:
        return ""
    else:
        if inicio is None:
            inicio = "00:00:00"
        if fin is None:
            cap = cv2.VideoCapture(ruta)
            total_seconds = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS))
            cap.release()
            fin = f"{total_seconds // 3600:02d}:{total_seconds % 3600 // 60:02d}:{total_seconds % 60:02d}"
        inicio_seconds = int(inicio.split(":")[0]) * 3600 + int(inicio.split(":")[1]) * 60 + int(inicio.split(":")[2])
        fin_seconds = int(fin.split(":")[0]) * 3600 + int(fin.split(":")[1]) * 60 + int(fin.split(":")[2])
        ffmpeg_extract_subclip(ruta, inicio_seconds, fin_seconds, targetname=os.path.join(ruta_nuevo, nombre))
        return f"Video creado: {os.path.join(ruta_nuevo, nombre)}"

if __name__ == "__main__":
    app.run_server(debug=True)
