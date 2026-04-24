# Usa una imagen oficial de Python con soporte completo
FROM python:3.11-slim

# Instala FFmpeg (necesario para conversión de audio y efectos de sample rate)
# También instala herramientas útiles
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos de dependencias primero (mejor caché)
COPY requirements.txt .

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de la aplicación
COPY app.py .
COPY templates/ ./templates/

# Crea la carpeta de descargas
RUN mkdir -p descargas

# Expone el puerto que usará Render
EXPOSE 10000

# Variables de entorno para producción
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Comando para ejecutar la app con Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
