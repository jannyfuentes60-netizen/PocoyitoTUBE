from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import re
import uuid
import time
import threading

app = Flask(__name__)

DOWNLOAD_FOLDER = 'descargas'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def limpiar_descargas():
    def limpiar():
        while True:
            time.sleep(3600)
            try:
                for archivo in os.listdir(DOWNLOAD_FOLDER):
                    ruta = os.path.join(DOWNLOAD_FOLDER, archivo)
                    if os.path.isfile(ruta) and time.time() - os.path.getmtime(ruta) > 3600:
                        os.remove(ruta)
            except:
                pass
    threading.Thread(target=limpiar, daemon=True).start()

limpiar_descargas()

FORMATOS_AUDIO = {
    'mp3': {'nombre': 'MP3', 'extension': 'mp3', 'codec': 'mp3'},
    'flac': {'nombre': 'FLAC', 'extension': 'flac', 'codec': 'flac'},
    'wav': {'nombre': 'WAV', 'extension': 'wav', 'codec': 'wav'},
    'ogg': {'nombre': 'OGG', 'extension': 'ogg', 'codec': 'vorbis'},
    'm4a': {'nombre': 'M4A', 'extension': 'm4a', 'codec': 'aac'},
    'aac': {'nombre': 'AAC', 'extension': 'aac', 'codec': 'aac'},
    'opus': {'nombre': 'OPUS', 'extension': 'opus', 'codec': 'opus'}
}

EFECTOS = {
    'normal': {'nombre': 'Normal', 'sample_rate': '44100'},
    'radio': {'nombre': 'Radio AM', 'sample_rate': '22050'},
    'telefono': {'nombre': 'Teléfono', 'sample_rate': '16000'},
    'lofi': {'nombre': 'LoFi', 'sample_rate': '32000'}
}

def es_url_valida(url):
    """Verifica si la URL es válida para YouTube"""
    if not url or not isinstance(url, str):
        return False
    patrones = [
        r'(youtube\.com/watch\?v=)',
        r'(youtu\.be/)',
        r'(youtube\.com/shorts/)',
        r'(youtube\.com/embed/)'
    ]
    for patron in patrones:
        if re.search(patron, url):
            return True
    return False

def get_video_info(url):
    if not es_url_valida(url):
        return {'success': False, 'error': 'URL inválida. Asegúrate de usar una URL de YouTube válida.'}
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'success': True,
                'title': info.get('title', 'Sin título'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', 'Desconocido')
            }
    except Exception as e:
        error_msg = str(e)
        if "unable to extract" in error_msg.lower():
            return {'success': False, 'error': 'No se pudo obtener información. Verifica que el video exista.'}
        return {'success': False, 'error': f'Error: {error_msg[:100]}'}

def search_videos(query, max_results=10):
    if not query or len(query.strip()) < 2:
        return {'success': False, 'error': 'Ingresa al menos 2 caracteres para buscar'}
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'playlistend': max_results
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            videos = []
            entries = info.get('entries', [])
            if not entries:
                return {'success': False, 'error': 'No se encontraron videos'}
            
            for entry in entries:
                if entry:
                    video_id = entry.get('id', '')
                    videos.append({
                        'url': entry.get('webpage_url', ''),
                        'title': entry.get('title', 'Sin título'),
                        'duration': entry.get('duration', 0),
                        'thumbnail': f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg" if video_id else '',
                        'uploader': entry.get('uploader', 'Desconocido')
                    })
            return {'success': True, 'videos': videos}
    except Exception as e:
        return {'success': False, 'error': f'Error en búsqueda: {str(e)[:100]}'}

def download_video(url, formato, calidad, efecto):
    if not es_url_valida(url):
        return {'success': False, 'error': 'URL inválida'}
    
    try:
        filename_base = str(uuid.uuid4())
        efecto_info = EFECTOS.get(efecto, EFECTOS['normal'])
        formato_data = FORMATOS_AUDIO.get(formato, FORMATOS_AUDIO['mp3'])
        
        calidad_val = calidad.replace('kbps', '')
        
        ydl_opts = {
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{filename_base}.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': formato_data['codec'],
                'preferredquality': calidad_val,
            }],
            'postprocessor_args': ['-ar', efecto_info['sample_rate']]
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            filename = None
            for file in os.listdir(DOWNLOAD_FOLDER):
                if file.startswith(filename_base):
                    filename = file
                    break
            
            if filename:
                return {
                    'success': True, 
                    'filename': filename, 
                    'title': info.get('title', 'Video')[:50]
                }
            return {'success': False, 'error': 'No se encontró el archivo descargado'}
    except Exception as e:
        error_msg = str(e)
        if "no video formats" in error_msg.lower():
            return {'success': False, 'error': 'Este video no tiene audio disponible para descargar'}
        return {'success': False, 'error': f'Error: {error_msg[:100]}'}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No se recibieron datos'})
    
    query = data.get('query', '').strip()
    if not query:
        return jsonify({'success': False, 'error': 'Ingresa un término de búsqueda'})
    
    return jsonify(search_videos(query))

@app.route('/info', methods=['POST'])
def info():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No se recibieron datos'})
    
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'success': False, 'error': 'Ingresa una URL de YouTube'})
    
    if not es_url_valida(url):
        return jsonify({'success': False, 'error': 'URL inválida. Usa una URL de YouTube como: https://youtube.com/watch?v=...'})
    
    return jsonify(get_video_info(url))

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No se recibieron datos'})
    
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'success': False, 'error': 'No hay URL para descargar'})
    
    if not es_url_valida(url):
        return jsonify({'success': False, 'error': 'URL inválida'})
    
    formato = data.get('formato', 'mp3')
    calidad = data.get('calidad', '192')
    efecto = data.get('efecto', 'normal')
    
    return jsonify(download_video(url, formato, calidad, efecto))

@app.route('/download_file/<filename>')
def download_file(filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'Archivo no encontrado'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=False, host='0.0.0.0', port=port)
