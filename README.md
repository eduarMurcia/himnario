# Hymn Studio

Hymn Studio es una aplicación de escritorio para sincronizar diapositivas de himnos con audio y exportar videos MP4.

## Objetivo

Permitir crear videos de himnos usando PowerPoint como herramienta de diseño y la aplicación para sincronizar y exportar.

## Flujo
1. Diseñar diapositivas en PowerPoint.
2. Exportarlas como PNG (el soporte directo a PPTX llegará más adelante).
3. Cargar las imágenes y el audio.
4. Marcar el cambio de diapositiva con la barra espaciadora.
5. Guardar el proyecto.
6. Exportar un MP4 usando FFmpeg.

## Roadmap v0.1
- Carga de imágenes.
- Carga de audio.
- Vista previa.
- Sincronización manual.
- Guardado de proyecto JSON.
- Exportación MP4.

## Arquitectura
- Python 3.13
- PySide6
- FFmpeg
- python-vlc o QMediaPlayer
