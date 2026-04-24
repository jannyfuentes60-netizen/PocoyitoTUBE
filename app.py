from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import re
import uuid
import time
import threading

app = Flask(__name__)

# Configuración
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

def get_video_info(url):
    ydl_opts = {'quiet': True, 'no_warnings': True}
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
        return {'success': False, 'error': str(e)}

def search_videos(query, max_results=10):
    ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            videos = []
            for entry in info.get('entries', []):
                videos.append({
                    'url': entry.get('webpage_url', ''),
                    'title': entry.get('title', 'Sin título'),
                    'duration': entry.get('duration', 0),
                    'thumbnail': f"https://img.youtube.com/vi/{entry.get('id', '')}/mqdefault.jpg",
                    'uploader': entry.get('uploader', 'Desconocido')
                })
            return {'success': True, 'videos': videos}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def download_video(url, formato, calidad, efecto):
    try:
        filename_base = str(uuid.uuid4())
        efecto_info = EFECTOS.get(efecto, EFECTOS['normal'])
        
        formato_data = FORMATOS_AUDIO[formato]
        ydl_opts = {
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{filename_base}.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': formato_data['codec'],
                'preferredquality': calidad.replace('kbps', ''),
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
                return {'success': True, 'filename': filename, 'title': info.get('title', 'Video')}
            return {'success': False, 'error': 'No se encontró el archivo'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({'success': False, 'error': 'No query provided'})
    return jsonify(search_videos(data['query']))

@app.route('/info', methods=['POST'])
def info():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'success': False, 'error': 'No url provided'})
    return jsonify(get_video_info(data['url']))

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'success': False, 'error': 'No url provided'})
    
    result = download_video(
        data['url'],
        data.get('formato', 'mp3'),
        data.get('calidad', '192'),
        data.get('efecto', 'normal')
    )
    return jsonify(result)

@app.route('/download_file/<filename>')
def download_file(filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=10000)
