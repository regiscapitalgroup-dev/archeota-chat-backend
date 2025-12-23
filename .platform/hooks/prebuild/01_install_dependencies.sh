#!/bin/bash
echo "Iniciando instalacion de dependencias graficas..."
sudo dnf install -y pango pango-devel cairo cairo-devel cairo-gobject libffi-devel gdk-pixbuf2 glib2-devel libxml2-devel libxslt-devel libjpeg-turbo-devel zlib-devel urw-base35-fonts google-noto-sans-fonts
echo "Dependencias instaladas."