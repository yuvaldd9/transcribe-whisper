import os
import subprocess
import tempfile
import shutil
import logging
from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename
from openai import OpenAI
from dotenv import load_dotenv
import concurrent.futures
from typing import List, Tuple, Optional

load_dotenv()

# ---------- Logging ----------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("transcriber")

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TEMP_FOLDER'] = 'temp_files'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'flac', 'm4a', 'ogg', 'wma', 'aac', 'mp4', 'avi', 'mov', 'mkv'}

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_size_mb(filepath: str) -> float:
    try:
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        logger.info("File size for %s: %.2f MB", filepath, size_mb)
        return size_mb
    except Exception as e:
        logger.exception("Failed to get file size for %s: %s", filepath, e)
        raise

def get_audio_duration(input_file: str) -> Optional[float]:
    try:
        cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
               '-of', 'csv=p=0', input_file]
        logger.info("Running ffprobe for duration: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            logger.warning("ffprobe returned non-zero: %s", result.stderr.strip())
            return None
        out = result.stdout.strip()
        if not out:
            logger.warning("ffprobe returned empty stdout for duration")
            return None
        duration = float(out)
        logger.info("Duration for %s: %.2f seconds", input_file, duration)
        return duration
    except Exception as e:
        logger.exception("Error getting duration for %s: %s", input_file, e)
        return None

def split_audio_file(input_file: str, output_dir: str, segment_size_mb: int = 5) -> List[str]:
    try:
        logger.info("Splitting file '%s' into segments (target %d MB each) in %s",
                    input_file, segment_size_mb, output_dir)

        total_duration = get_audio_duration(input_file)
        if total_duration is None:
            # fallback to 5 minutes segments if unable to detect duration
            segment_duration = 300
            logger.info("Could not get total duration, using fallback segment duration %ds", segment_duration)
        else:
            file_size_mb = get_file_size_mb(input_file)
            # compute approximate segment duration so each segment ~ segment_size_mb
            segment_duration = (total_duration * segment_size_mb) / max(file_size_mb, 0.001)
            logger.info("Computed segment_duration: %.2f sec (total_duration=%.2f, file_size_mb=%.2f)",
                        segment_duration, total_duration, file_size_mb)

        # clamp to reasonable bounds
        segment_duration = int(max(60, min(600, segment_duration)))  # between 1 and 10 minutes
        logger.info("Final segment duration (clamped): %d seconds", segment_duration)

        os.makedirs(output_dir, exist_ok=True)

        base_name = os.path.splitext(os.path.basename(input_file))[0]
        base_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        output_pattern = os.path.join(output_dir, f"{base_name}_part_%03d.mp3")

        split_cmd = [
            'ffmpeg', '-y', '-i', input_file,
            '-f', 'segment',
            '-segment_time', str(int(segment_duration)),
            '-c:a', 'mp3', '-b:a', '128k',
            '-ar', '22050', '-ac', '1',
            output_pattern
        ]

        logger.info("Running ffmpeg split command: %s", " ".join(split_cmd))
        result = subprocess.run(split_cmd, capture_output=True, text=True, timeout=900)
        if result.returncode != 0:
            logger.error("Error splitting file: ffmpeg returned %d", result.returncode)
            logger.error("ffmpeg stderr: %s", result.stderr)
            return []

        # Collect all generated segment files and sort them to maintain order
        segments = []
        i = 0
        while True:
            segment_path = os.path.join(output_dir, f"{base_name}_part_{i:03d}.mp3")
            if os.path.exists(segment_path):
                segments.append(segment_path)
                i += 1
            else:
                break

        logger.info("Split produced %d segments", len(segments))
        if len(segments) == 0:
            logger.warning("No segments found after splitting")
        else:
            for idx, s in enumerate(segments):
                try:
                    size_mb = get_file_size_mb(s)
                except Exception:
                    size_mb = -1
                logger.info(" Segment %03d: %s (%.2f MB)", idx, s, size_mb)

        return segments

    except Exception as e:
        logger.exception("Exception in split_audio_file: %s", e)
        return []

def convert_to_mp3_mono_22050(input_file: str, output_dir: str) -> str:
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    base_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    output_file = os.path.join(output_dir, f"{base_name}_converted.mp3")

    cmd = [
        'ffmpeg', '-y', '-i', input_file,
        '-acodec', 'mp3', '-b:a', '128k',
        '-ar', '22050', '-ac', '1',
        output_file
    ]

    logger.info("Converting %s -> %s", input_file, output_file)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("Conversion error for %s: %s", input_file, result.stderr)
        # return original as fallback
        return input_file

    logger.info("Conversion successful: %s", output_file)
    return output_file

def transcribe_audio(file_path: str) -> Optional[str]:
    """
    Transcribe a single file path and return text or None on failure.
    """
    try:
        logger.info("Transcribing file: %s", file_path)
        with open(file_path, 'rb') as f:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="he",
                response_format="text"
            )
        # response is plain text string according to response_format
        if isinstance(response, str):
            logger.info("Transcription completed for %s (length=%d chars)", file_path, len(response))
            return response
        # If SDK returns object, try to coerce
        logger.info("Transcription completed for %s (type=%s)", file_path, type(response))
        return str(response)
    except Exception as e:
        logger.exception("Error during transcription of %s: %s", file_path, e)
        return None

def transcribe_segment_worker(args: Tuple[int, str]) -> Tuple[int, Optional[str]]:
    """
    Worker wrapper that returns (index, transcript_or_none).
    """
    index, path = args
    logger.info("Worker started for segment %d: %s", index, path)
    transcript = transcribe_audio(path)
    if transcript is None:
        logger.warning("Worker: transcription failed for segment %d (%s)", index, path)
    else:
        logger.info("Worker: transcription succeeded for segment %d (chars=%d)", index, len(transcript))
    return index, transcript

def process_audio_file(file_path: str):
    file_size_mb = get_file_size_mb(file_path)
    logger.info("Processing file %s size: %.2fMB", file_path, file_size_mb)

    temp_dir = tempfile.mkdtemp(dir=app.config['TEMP_FOLDER'])
    logger.info("Created temporary dir: %s", temp_dir)
    try:
        ext = os.path.splitext(file_path)[1].lower()
        input_for_transcription = file_path
        if ext in ['.mp4', '.avi', '.mov', '.mkv', '.wma', '.ogg']:
            logger.info("Input is a container/video type; converting to mp3 mono 22050")
            input_for_transcription = convert_to_mp3_mono_22050(file_path, temp_dir)
            logger.info("Conversion result: %s", input_for_transcription)

        # small files: transcribe directly
        if file_size_mb <= 20:
            logger.info("File <= 20MB, transcribing directly")
            transcript = transcribe_audio(input_for_transcription)
            if transcript is None:
                logger.error("Transcription failed for %s", input_for_transcription)
                return {"error": "Transcription failed"}
            return transcript

        # large files: split and transcribe segments in parallel
        else:
            logger.info("File > 20MB, splitting to segments for parallel transcription")
            segments = split_audio_file(input_for_transcription, temp_dir, segment_size_mb=5)
            if not segments:
                logger.error("No segments returned from split")
                return {"error": "Could not split the audio file"}

            # Make sure segments are sorted by filename (should already be named _part_000 etc.)
            segments_sorted = sorted(segments)
            logger.info("Transcribing %d segments in parallel", len(segments_sorted))

            # prepare worker args with index so we preserve order after parallel execution
            worker_args = [(idx, seg) for idx, seg in enumerate(segments_sorted)]

            # Determine number of workers: limit to a reasonable number
            cpu_count = os.cpu_count() or 2
            max_workers = min(len(worker_args), max(2, cpu_count * 2, 4))
            logger.info("Using max_workers=%d (cpu_count=%s, segments=%d)", max_workers, cpu_count, len(worker_args))

            results = [None] * len(worker_args)  # placeholder for ordered results

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Map futures
                future_to_index = {executor.submit(transcribe_segment_worker, arg): arg[0] for arg in worker_args}
                for future in concurrent.futures.as_completed(future_to_index):
                    idx = future_to_index[future]
                    try:
                        index, transcript = future.result()
                        results[index] = transcript
                        if transcript is None:
                            logger.warning("Segment %d produced no transcript", index)
                        else:
                            logger.info("Segment %d transcript length: %d chars", index, len(transcript))
                    except Exception as e:
                        logger.exception("Exception while transcribing segment %d: %s", idx, e)
                        results[idx] = None

            # Validate order: results list indices match segment order
            full_transcript_parts = []
            failed_segments = []
            for i, seg_trans in enumerate(results):
                seg_path = segments_sorted[i]
                if seg_trans:
                    # add header for traceability (optional)
                    full_transcript_parts.append(seg_trans.strip())
                else:
                    failed_segments.append((i, seg_path))
                    logger.warning("Segment %d (%s) failed to transcribe", i, seg_path)

            if len(failed_segments) == len(results):
                logger.error("All segments failed to transcribe")
                return {"error": "No segments were transcribed"}

            if failed_segments:
                logger.info("Some segments failed (%d). They are skipped in final assembly.", len(failed_segments))

            full_transcript = "\n\n".join(full_transcript_parts).strip()
            logger.info("Assembled full transcript (chars=%d)", len(full_transcript) if full_transcript else 0)
            return full_transcript

    finally:
        logger.info("Cleaning up temporary directory: %s", temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files or request.files['file'].filename == '':
        logger.info("Upload endpoint called without a file")
        return jsonify({'error': 'No file selected'}), 400

    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        saved_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        logger.info("Saving uploaded file to %s", saved_path)
        file.save(saved_path)

        try:
            transcript = process_audio_file(saved_path)
            if isinstance(transcript, dict) and 'error' in transcript:
                logger.error("Processing returned error: %s", transcript['error'])
                return jsonify({'error': transcript['error']}), 500

            logger.info("Returning transcript for %s", filename)
            return jsonify({
                'success': True,
                'transcript': transcript,
                'filename': filename
            })
        finally:
            # always remove uploaded file to avoid disk growth
            if os.path.exists(saved_path):
                try:
                    os.remove(saved_path)
                    logger.info("Removed uploaded file %s", saved_path)
                except Exception:
                    logger.exception("Failed to remove uploaded file %s", saved_path)

    logger.info("Invalid file type uploaded: %s", request.files['file'].filename if 'file' in request.files else 'N/A')
    return jsonify({'error': 'Invalid file type'}), 400

if __name__ == '__main__':
    if not os.getenv('OPENAI_API_KEY'):
        logger.warning("OPENAI_API_KEY not found in environment variables!")
    app.run(host='0.0.0.0', port=5000, debug=True)
