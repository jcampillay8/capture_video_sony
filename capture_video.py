# PARTE 1
import dash
from dash import dcc, html
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from flask import Flask, request
import os
import cv2
import base64
import io
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
import re
import webview
from multiprocessing import Process, freeze_support


server = Flask(__name__)

app = dash.Dash(
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP]
)

app.layout = dbc.Container(
    [
        dbc.Row([
            dbc.Col(html.H1("Editor Videos Familia", style={"text-align": "center", "margin-top": "20px", "margin-bottom": "20px"}), width=6),
        ]),
        dbc.Input(id="input-ruta", placeholder="Introduce la ruta del video", type="text"),
        html.Div(html.B(id="file-name")),
        dbc.Row([
            dbc.Col(html.Div(dbc.Button("Extraer imágenes", id="extract-button", color="primary"), style={"margin-top": "20px", "margin-bottom": "20px"}), width=3),
            dbc.Col(html.Div(dbc.Button("Mostrar imágenes", id="display-button", color="primary"), style={"margin-top": "20px", "margin-bottom": "20px"}), width=3),
        ]),

        html.Div(id='progress-bar', children=[], style={'width': '0%', 'height': '24px', 'background-color': '#007BFF', 'color': 'white', 'textAlign': 'center'}),
        dcc.Interval(id='interval', interval=2200, n_intervals=0), 
        dbc.Row(id="image-row", style={'margin-top': '20px'}),

        html.Div(html.B("Select a page"), id="pagination-contents"),
        dbc.Row([
            dbc.Col(html.Div(dbc.Pagination(id="pagination", className="wrap", max_value=1, active_page=1, first_last=True, previous_next=True, size="L", fully_expanded=True),),style={"maxWidth": "1200px", "overflow": "scroll","margin-bottom": "20px"},),
        ],),

        html.Div(id="video-creado",style={'margin-top': '20px','margin-bottom': '20px'}),

        dbc.Form(
            [
                dbc.Row(
                    [
                        dbc.Label(html.B("Nombre Video"), className="mr-2"),
                        dbc.Input(id="nombre-video", placeholder="Introduce el nombre del video", type="text"),
                    ],
                    className="mr-3",
                ),
                dbc.Row(
                    [
                        dbc.Label(html.B("Inicio Video"), className="mr-2"),
                        dbc.Input(id="inicio-video", placeholder="Introduce el inicio del video (hh:MM:ss)", type="text"),
                    ],
                    className="mr-3",
                ),
                dbc.Row(
                    [
                        dbc.Label(html.B("Fin Video"), className="mr-2"),
                        dbc.Input(id="fin-video", placeholder="Introduce el fin del video (hh:MM:ss)", type="text"),
                    ],
                    className="mr-3",
                ),
                dbc.Row(
                    [
                        dbc.Label(html.B("Asignar Ruta Video Nuevo"), className="mr-2"),
                        dbc.Input(id="ruta-video-nuevo", placeholder="Introduce la ruta del video nuevo", type="text"),
                    ],
                    className="mr-3",
                ),
                dbc.Row([
                    dbc.Col(html.Div(dbc.Button("Crear", id="crear-button", color="primary"), style={"margin-top": "20px", "margin-bottom": "20px"}), width=6),
                ]),
            ],
        ),
    ]
)

# PARTE 2
@app.callback(
    [Output('progress-bar', 'style'), Output('progress-bar', 'children')],
    [Input('interval', 'n_intervals'), Input('extract-button', 'n_clicks')],
    [State('input-ruta', 'value')]
)
def update_progress(n, clicks, value):
    if clicks is None:
        return {'width': '0%', 'height': '24px', 'background-color': '#007BFF', 'color': 'white', 'textAlign': 'center'}, "0%"
    else:
        cap = cv2.VideoCapture(value)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        total_time = frame_count // (20 * fps)
        progress = round(min(n * 20 / total_time * 100, 100), 1)  # update progress every 20 seconds
        return {'width': f'{progress}%', 'height': '24px', 'background-color': '#007BFF', 'color': 'white', 'textAlign': 'center'}, f"{progress}%"
    

@app.callback(Output("file-name", "children"), [Input("input-ruta", "value")])
def update_output(value):
    if value is None:
        return "No se ha introducido ninguna ruta."
    else:
        filename = os.path.basename(value)
        return f"El nombre del video cargado es: {filename}"

@app.callback(Output("image-row", "children"), 
            Output("pagination", "max_value"), 
            [Input("extract-button", "n_clicks"), 
            #Input("pagination", "active_page")
            ], 
            [State("input-ruta", "value")])
#def extract_images(n, page, value):
def extract_images(n, value):
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

@app.callback(Output("image-row", "children",allow_duplicate=True), 
            [Input("display-button", "n_clicks"), 
            Input("pagination", "active_page")], 
            [State("input-ruta", "value")],
            prevent_initial_call=True)
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

# PART 3
@app.callback(Output("video-creado", "children"), [Input("crear-button", "n_clicks")], [State("input-ruta", "value"), State("nombre-video", "value"), State("inicio-video", "value"), State("fin-video", "value"), State("ruta-video-nuevo", "value")])
def create_video(n, ruta, nombre, inicio, fin, ruta_nuevo):
    if n is None:
        return ""
    else:
        cap = cv2.VideoCapture(ruta)
        total_seconds = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS))
        cap.release()

        if inicio is None:
            inicio = "00:00:00"
        if fin is None:
            fin = f"{total_seconds // 3600:02d}:{total_seconds % 3600 // 60:02d}:{total_seconds % 60:02d}"
        
        # Verificar formato de tiempo
        time_format = re.compile("^([0-1][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$")
        if not time_format.match(inicio):
            return dbc.Alert(
                [
                    html.I(className="bi bi-x-octagon-fill me-2"),
                    "El inicio del video no cumple con el formato 'hh:MM:ss'",
                ],
                color="danger",
                className="d-flex align-items-center",
            )
        if not time_format.match(fin):
            return dbc.Alert(
                [
                    html.I(className="bi bi-x-octagon-fill me-2"),
                    "El fin del video no cumple con el formato 'hh:MM:ss'",
                ],
                color="danger",
                className="d-flex align-items-center",
            )
        
        inicio_seconds = int(inicio.split(":")[0]) * 3600 + int(inicio.split(":")[1]) * 60 + int(inicio.split(":")[2])
        fin_seconds = int(fin.split(":")[0]) * 3600 + int(fin.split(":")[1]) * 60 + int(fin.split(":")[2])
        
        # Verificar que el fin del video no sea anterior al inicio
        if fin_seconds <= inicio_seconds:
            return dbc.Alert(
                [
                    html.I(className="bi bi-x-octagon-fill me-2"),
                    "El fin del video no puede ser anterior al inicio del video",
                ],
                color="danger",
                className="d-flex align-items-center",
            )
        
        # Verificar que el fin del video no sea mayor a la duración del video original
        if fin_seconds > total_seconds:
            return dbc.Alert(
                [
                    html.I(className="bi bi-x-octagon-fill me-2"),
                    "El fin del video no puede ser mayor a la duración del video original",
                ],
                color="danger",
                className="d-flex align-items-center",
            )
        
        if nombre is None:
            nombre = "video_default"
        nombre = nombre + ".mp4"
        
        ffmpeg_extract_subclip(ruta, inicio_seconds, fin_seconds, targetname=os.path.join(ruta_nuevo, nombre))
        return dbc.Alert(
            [
                html.I(className="bi bi-check-circle-fill me-2"),
                f"Video creado: {os.path.join(ruta_nuevo, nombre)}",
            ],
            color="success",
            className="d-flex align-items-center",
        )

def start_dash():
    app.run_server(debug=False)

if __name__ == "__main__":
    freeze_support()
    # Inicia la aplicación Dash en un proceso separado
    p = Process(target=start_dash)
    p.start()

    # Crea y muestra la ventana de la aplicación web
    window = webview.create_window('Handycam Video Familia!', 'http://localhost:8050')
    webview.start()

    # Termina el proceso de la aplicación Dash cuando se cierra la ventana de la aplicación web
    p.terminate()

