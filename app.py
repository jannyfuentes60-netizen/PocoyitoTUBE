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

# Limpiar descargas viejas cada hora
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

# ============================================
# TODOS LOS FORMATOS DISPONIBLES
# ============================================

FORMATOS_AUDIO = {
    'mp3': {
        'nombre': 'MP3',
        'emoji': '🎵',
        'extension': 'mp3',
        'codec': 'mp3',
        'calidades': {
            '320kbps': '320',
            '256kbps': '256',
            '192kbps': '192',
            '128kbps': '128',
            '96kbps': '96'
        }
    },
    'flac': {
        'nombre': 'FLAC (Sin pérdida)',
        'emoji': '🌟',
        'extension': 'flac',
        'codec': 'flac',
        'calidades': {
            'lossless': '0',
            'alta': '5',
            'normal': '8'
        }
    },
    'wav': {
        'nombre': 'WAV (Sin compresión)',
        'emoji': '💿',
        'extension': 'wav',
        'codec': 'wav',
        'calidades': {
            'pcm_16bit': '16',
            'pcm_24bit': '24',
            'pcm_32bit': '32'
        }
    },
    'ogg': {
        'nombre': 'OGG Vorbis',
        'emoji': '🎶',
        'extension': 'ogg',
        'codec': 'vorbis',
        'calidades': {
            '320kbps': '320',
            '256kbps': '256',
            '192kbps': '192',
            '128kbps': '128'
        }
    },
    'm4a': {
        'nombre': 'M4A (AAC)',
        'emoji': '🍎',
        'extension': 'm4a',
        'codec': 'aac',
        'calidades': {
            '320kbps': '320',
            '256kbps': '256',
            '192kbps': '192',
            '128kbps': '128'
        }
    },
    'aac': {
        'nombre': 'AAC',
        'emoji': '🎧',
        'extension': 'aac',
        'codec': 'aac',
        'calidades': {
            '320kbps': '320',
            '256kbps': '256',
            '192kbps': '192',
            '128kbps': '128'
        }
    },
    'opus': {
        'nombre': 'OPUS',
        'emoji': '🚀',
        'extension': 'opus',
        'codec': 'opus',
        'calidades': {
            '256kbps': '256',
            '192kbps': '192',
            '128kbps': '128',
            '96kbps': '96'
        }
    },
    'webm_audio': {
        'nombre': 'WEBM Audio',
        'emoji': '🌐',
        'extension': 'webm',
        'codec': 'opus',
        'calidades': {
            'alta': '192',
            'media': '128',
            'baja': '96'
        }
    }
}

FORMATOS_VIDEO = {
    'mp4': {
        'nombre': 'MP4',
        'emoji': '📹',
        'extension': 'mp4',
        'calidades': {
            '4K (2160p)': '2160',
            '2K (1440p)': '1440',
            '1080p': '1080',
            '720p': '720',
            '480p': '480',
            '360p': '360',
            '240p': '240'
        }
    },
    'webm_video': {
        'nombre': 'WEBM',
        'emoji': '🎬',
        'extension': 'webm',
        'calidades': {
            '4K': '2160',
            '1080p': '1080',
            '720p': '720',
            '480p': '480'
        }
    },
    'mkv': {
        'nombre': 'MKV',
        'emoji': '📦',
        'extension': 'mkv',
        'calidades': {
            '4K': '2160',
            '1080p': '1080',
            '720p': '720'
        }
    },
    'avi': {
        'nombre': 'AVI',
        'emoji': '💾',
        'extension': 'avi',
        'calidades': {
            '1080p': '1080',
            '720p': '720',
            '480p': '480'
        }
    },
    'mov': {
        'nombre': 'MOV',
        'emoji': '🍎',
        'extension': 'mov',
        'calidades': {
            '1080p': '1080',
            '720p': '720'
        }
    },
    '3gp': {
        'nombre': '3GP',
        'emoji': '📱',
        'extension': '3gp',
        'calidades': {
            '360p': '360',
            '240p': '240',
            '144p': '144'
        }
    }
}

# ============================================
# EFECTOS DE "ONDA CAMBIADA"
# (Solo cambia frecuencia de muestreo, sin filtros)
# ============================================

EFECTOS_ONDA = {
    'normal': {
        'nombre': '🔊 Normal',
        'sample_rate': '44100',
        'descripcion': 'Sonido original sin cambios'
    },
    'radio_vieja': {
        'nombre': '📻 Radio Vieja',
        'sample_rate': '22050',
        'descripcion': 'Como radio AM antigua, más cálido'
    },
    'telefono': {
        'nombre': '📞 Teléfono',
        'sample_rate': '16000',
        'descripcion': 'Sonido de llamada telefónica'
    },
    'lofi': {
        'nombre': '🎹 Lofi',
        'sample_rate': '32000',
        'descripcion': 'Más suave, ideal para beats'
    },
    'vaporwave': {
        'nombre': '🌊 Vaporwave',
        'sample_rate': '48000',
        'descripcion': 'Más brillante, efecto espacial'
    },
    'casette': {
        'nombre': '📼 Casette',
        'sample_rate': '24000',
        'descripcion': 'Como cinta de audio antigua'
    },
    'profundo': {
        'nombre': '⬇️ Profundo',
        'sample_rate': '22050',
        'descripcion': 'Graves más pronunciados'
    },
    'brillante': {
        'nombre': '✨ Brillante',
        'sample_rate': '48000',
        'descripcion': 'Agudos más definidos'
    },
    'mono': {
        'nombre': '🎤 Mono (Estéreo a Mono)',
        'sample_rate': '44100',
        'descripcion': 'Convierte a mono, sin filtros'
    }
}

def sanitize_filename(filename):
    """Limpia el nombre del archivo"""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    return filename[:100]

def get_video_info(url):
    """Obtiene información del video"""
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
                'uploader': info.get('uploader', 'Desconocido'),
                'views': info.get('view_count', 0)
            }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def search_videos(query, max_results=15):
    """Busca videos en YouTube"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'playlistend': max_results
    }
    
    try:
        search_query = f"ytsearch{max_results}:{query}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            videos = []
            
            for entry in info.get('entries', []):
                video_id = entry.get('id', '')
                videos.append({
                    'url': entry.get('webpage_url', ''),
                    'title': entry.get('title', 'Sin título'),
                    'duration': entry.get('duration', 0),
                    'thumbnail': f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
                    'uploader': entry.get('uploader', 'Desconocido'),
                    'views': entry.get('view_count', 0)
                })
            
            return {'success': True, 'videos': videos}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def download_video(url, formato_tipo, formato_nombre, calidad, efecto):
    """Descarga el video con el formato, calidad y efecto seleccionados"""
    try:
        filename_base = str(uuid.uuid4())
        efecto_info = EFECTOS_ONDA.get(efecto, EFECTOS_ONDA['normal'])
        sample_rate = efecto_info['sample_rate']
        
        # Determinar si es audio o video
        if formato_tipo == 'audio':
            formato_data = FORMATOS_AUDIO[formato_nombre]
            extension = formato_data['extension']
            codec = formato_data['codec']
            calidad_valor = formato_data['calidades'].get(calidad, list(formato_data['calidades'].values())[0])
            
            ydl_opts = {
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{filename_base}.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': codec,
                    'preferredquality': str(calidad_valor),
                }],
                'postprocessor_args': [
                    '-ar', sample_rate,  # Cambiar frecuencia de muestreo (el "efecto")
                ]
            }
            
            # Para efecto mono, agregar argumento extra
            if efecto == 'mono':
                ydl_opts['postprocessor_args'].extend(['-ac', '1'])
            
            # Para WAV, ajustar profundidad de bits
            if formato_nombre == 'wav':
                if calidad == 'pcm_16bit':
                    ydl_opts['postprocessor_args'].extend(['-acodec', 'pcm_s16le'])
                elif calidad == 'pcm_24bit':
                    ydl_opts['postprocessor_args'].extend(['-acodec', 'pcm_s24le'])
                elif calidad == 'pcm_32bit':
                    ydl_opts['postprocessor_args'].extend(['-acodec', 'pcm_s32le'])
        
        else:  # video
            formato_data = FORMATOS_VIDEO[formato_nombre]
            extension = formato_data['extension']
            altura = formato_data['calidades'].get(calidad, '720')
            
            if altura == '2160':
                format_string = f'bestvideo[height<=2160][ext={extension}]+bestaudio[ext=m4a]/best[height<=2160][ext={extension}]'
            elif altura == '1440':
                format_string = f'bestvideo[height<=1440][ext={extension}]+bestaudio[ext=m4a]/best[height<=1440][ext={extension}]'
            elif altura == '1080':
                format_string = f'bestvideo[height<=1080][ext={extension}]+bestaudio[ext=m4a]/best[height<=1080][ext={extension}]'
            elif altura == '720':
                format_string = f'bestvideo[height<=720][ext={extension}]+bestaudio[ext=m4a]/best[height<=720][ext={extension}]'
            elif altura == '480':
                format_string = f'bestvideo[height<=480][ext={extension}]+bestaudio[ext=m4a]/best[height<=480][ext={extension}]'
            elif altura == '360':
                format_string = f'bestvideo[height<=360][ext={extension}]+bestaudio[ext=m4a]/best[height<=360][ext={extension}]'
            elif altura == '240':
                format_string = f'bestvideo[height<=240][ext={extension}]+bestaudio[ext=m4a]/best[height<=240][ext={extension}]'
            else:
                format_string = f'bestvideo[ext={extension}]+bestaudio[ext=m4a]/best[ext={extension}]'
            
            ydl_opts = {
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{filename_base}.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'format': format_string,
                'merge_output_format': extension,
            }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Buscar el archivo descargado
            filename = None
            for file in os.listdir(DOWNLOAD_FOLDER):
                if file.startswith(filename_base):
                    filename = file
                    break
            
            if not filename:
                for file in os.listdir(DOWNLOAD_FOLDER):
                    if file.endswith(f'.{extension}') and time.time() - os.path.getmtime(os.path.join(DOWNLOAD_FOLDER, file)) < 10:
                        filename = file
                        break
            
            if filename:
                return {
                    'success': True,
                    'filename': filename,
                    'title': info.get('title', 'Video'),
                    'efecto_usado': efecto_info['nombre']
                }
            else:
                return {'success': False, 'error': 'No se encontró el archivo descargado'}
                
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ============================================
# RUTAS DE LA API
# ============================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search():
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify({'success': False, 'error': 'Ingresa algo para buscar'})
    
    result = search_videos(query)
    return jsonify(result)

@app.route('/api/info', methods=['POST'])
def info():
    data = request.json
    url = data.get('url', '')
    
    if not url:
        return jsonify({'success': False, 'error': 'Ingresa una URL'})
    
    result = get_video_info(url)
    return jsonify(result)

@app.route('/api/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url', '')
    formato_tipo = data.get('formato_tipo', 'audio')
    formato_nombre = data.get('formato_nombre', 'mp3')
    calidad = data.get('calidad', '192kbps')
    efecto = data.get('efecto', 'normal')
    
    if not url:
        return jsonify({'success': False, 'error': 'No hay URL'})
    
    result = download_video(url, formato_tipo, formato_nombre, calidad, efecto)
    return jsonify(result)

@app.route('/api/download_file/<filename>')
def download_file(filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'Archivo no encontrado'}), 404

@app.route('/api/formatos')
def get_formatos():
    return jsonify({
        'audio': FORMATOS_AUDIO,
        'video': FORMATOS_VIDEO,
        'efectos': EFECTOS_ONDA
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
