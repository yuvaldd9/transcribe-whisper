import os
import subprocess
import tempfile
import shutil
from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TEMP_FOLDER'] = 'temp_files'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'flac', 'm4a', 'ogg', 'wma', 'aac', 'mp4', 'avi', 'mov', 'mkv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_size_mb(filepath):
    return os.path.getsize(filepath) / (1024 * 1024)

def get_audio_duration(input_file):
    try:
        cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
               '-of', 'csv=p=0', input_file]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0 or not result.stdout.strip():
            return None
        return float(result.stdout.strip())
    except Exception as e:
        print(f"Error getting duration: {e}")
        return None

def split_audio_file(input_file, output_dir, segment_size_mb=5):
    try:
        total_duration = get_audio_duration(input_file)
        if total_duration is None:
            segment_duration = 300  # fallback 5 minutes
        else:
            file_size_mb = get_file_size_mb(input_file)
            segment_duration = (total_duration * segment_size_mb) / file_size_mb

        segment_duration = max(60, min(600, segment_duration))  # between 1 and 10 minutes
        os.makedirs(output_dir, exist_ok=True)

        base_name = os.path.splitext(os.path.basename(input_file))[0]
        base_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        output_pattern = os.path.join(output_dir, f"{base_name}_part_%03d.mp3")

        # Use re-encode to ensure segment files are good for transcription
        split_cmd = [
            'ffmpeg', '-y', '-i', input_file,
            '-f', 'segment',
            '-segment_time', str(int(segment_duration)),
            '-c:a', 'mp3', '-b:a', '128k',
            '-ar', '22050', '-ac', '1',
            output_pattern
        ]

        result = subprocess.run(split_cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            print("Error splitting file:", result.stderr)
            return []

        # Collect all generated segment files
        segments = []
        for i in range(1000):
            segment_path = os.path.join(output_dir, f"{base_name}_part_{i:03d}.mp3")
            if os.path.exists(segment_path):
                segments.append(segment_path)
            else:
                break
        return segments

    except Exception as e:
        print(f"Exception in split_audio_file: {e}")
        return []

def convert_to_mp3_mono_22050(input_file, output_dir):
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    base_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    output_file = os.path.join(output_dir, f"{base_name}_converted.mp3")

    cmd = [
        'ffmpeg', '-y', '-i', input_file,
        '-acodec', 'mp3', '-b:a', '128k',
        '-ar', '22050', '-ac', '1',
        output_file
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Conversion error: {result.stderr}")
        return input_file

    return output_file

def transcribe_audio(file_path):
    try:
        with open(file_path, 'rb') as f:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="he",
                response_format="text"  # plain text response
            )
        return response
    except Exception as e:
        print(f"Error during transcription of {file_path}: {e}")
        return None

def process_audio_file(file_path):
    file_size_mb = get_file_size_mb(file_path)
    print(f"Processing file {file_path} size: {file_size_mb:.2f}MB")

    temp_dir = tempfile.mkdtemp(dir=app.config['TEMP_FOLDER'])
    try:
        ext = os.path.splitext(file_path)[1].lower()
        input_for_transcription = file_path
        if ext in ['.mp4', '.avi', '.mov', '.mkv', '.wma', '.ogg']:
            input_for_transcription = convert_to_mp3_mono_22050(file_path, temp_dir)

        if file_size_mb <= 20:
            transcript = transcribe_audio(input_for_transcription)
            if transcript is None:
                return {"error": "Transcription failed"}
            return transcript

        else:
            segments = split_audio_file(input_for_transcription, temp_dir, segment_size_mb=5)
            if not segments:
                return {"error": "Could not split the audio file"}

            full_transcript = ""
            for seg in segments:
                if os.path.getsize(seg) == 0:
                    continue
                segment_transcript = transcribe_audio(seg)
                if segment_transcript is None:
                    print(f"Warning: failed to transcribe segment {seg}")
                    continue
                full_transcript += segment_transcript + "\n\n"

            if not full_transcript.strip():
                return {"error": "No segments were transcribed"}

            return full_transcript.strip()

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files or request.files['file'].filename == '':
        return jsonify({'error': 'No file selected'}), 400

    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        saved_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(saved_path)

        try:
            transcript = process_audio_file(saved_path)
            if isinstance(transcript, dict) and 'error' in transcript:
                return jsonify({'error': transcript['error']}), 500

            return jsonify({
                'success': True,
                'transcript': transcript,
                'filename': filename
            })
        finally:
            if os.path.exists(saved_path):
                os.remove(saved_path)

    return jsonify({'error': 'Invalid file type'}), 400

if __name__ == '__main__':
    if not os.getenv('OPENAI_API_KEY'):
        print("WARNING: OPENAI_API_KEY not found in environment variables!")
    app.run(host='0.0.0.0', port=5000, debug=True)
