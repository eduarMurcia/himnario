# Hymn Studio

Hymn Studio es una aplicacion de escritorio para sincronizar diapositivas de himnos
con audio y exportar videos MP4.

PowerPoint es el editor. Hymn Studio es el sincronizador y exportador.

## Objetivo

Permitir crear videos de himnos usando PowerPoint como herramienta de diseno y la
aplicacion para sincronizar y exportar.

## Flujo

1. Disenar diapositivas en PowerPoint.
2. Exportarlas como PNG.
3. Cargar las imagenes y el audio.
4. Marcar el cambio de diapositiva con la barra espaciadora.
5. Guardar el proyecto.
6. Exportar un MP4 usando FFmpeg.

## Version 0.1

- Cargar una carpeta de imagenes.
- Cargar un archivo de audio.
- Mostrar vista previa.
- Avanzar diapositivas manualmente.
- Guardar timestamps.
- Guardar y cargar proyectos `.hymn`.
- Exportar MP4 mediante FFmpeg.

La aplicacion evita intencionalmente convertirse en un editor de video.

## Arquitectura

- Python 3.13
- PySide6
- FFmpeg
- JSON para archivos `.hymn`

## Desarrollo

```powershell
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
hymn-studio
```

FFmpeg debe estar disponible en `PATH` para exportar.
