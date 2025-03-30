import os
import sys
import argparse
import tempfile
import shutil
import subprocess  # Added for yt-dlp
from pydub import AudioSegment
from pydub.silence import split_on_silence
import speech_recognition as sr
try:
    import whisper # Use OpenAI Whisper
    whisper_available = True
except ImportError:
    print("Warning: OpenAI Whisper library not found. Whisper engine will not be available.")
    print("Install it with: pip install openai-whisper")
    whisper_available = False


# --- Configuration ---
DEFAULT_CHUNK_LENGTH_MS = 60 * 1000 # Default chunk length limit (used if silence splitting creates overly long chunks)
DEFAULT_SILENCE_THRESH = -40        # Default silence threshold in dBFS for splitting (lower is stricter)
DEFAULT_MIN_SILENCE_LEN = 500       # Default minimum silence length in ms
DEFAULT_WHISPER_MODEL = "base"      # Default whisper model ("tiny", "base", "small", "medium", "large")
DEFAULT_ENGINE = "whisper" if whisper_available else "google" # Default to whisper if available

# --- Helper Functions ---

def download_audio(youtube_url, temp_dir):
    """Downloads audio from YouTube URL using yt-dlp and saves as WAV."""
    try:
        print(f"Downloading audio for: {youtube_url} using yt-dlp")

        # Define output template for yt-dlp within the temp directory
        # Use a fixed name stem we can predict
        output_base = os.path.join(temp_dir, 'downloaded_audio')
        output_template = f'{output_base}.%(ext)s'
        wav_path = f'{output_base}.wav' # Expected final path after conversion

        command = [
            'yt-dlp',
            '--no-check-certificate', # Add this to potentially bypass SSL issues
            '-x',                      # Extract audio
            '--audio-format', 'wav',   # Convert to WAV
            '-o', output_template,     # Output file template
            '--no-playlist',           # Ensure only single video is downloaded
            '--progress',              # Show progress
            '--verbose',               # More detailed output for debugging
            youtube_url
        ]

        # Execute yt-dlp command
        print(f"Running command: {' '.join(command)}")
        # Using check=True will raise CalledProcessError if yt-dlp fails
        process = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')

        print("yt-dlp stdout:")
        print(process.stdout if process.stdout else "(No stdout)")
        print("\nyt-dlp stderr:") # Stderr might contain progress or warnings
        print(process.stderr if process.stderr else "(No stderr)")

        # Check if the expected WAV file exists (yt-dlp handles the conversion)
        if os.path.exists(wav_path):
            print(f"Download and conversion successful: {wav_path}")
            return wav_path
        else:
            # Check if *any* WAV file was created if naming is odd (unlikely with explicit format)
             possible_files = [f for f in os.listdir(temp_dir) if f.startswith('downloaded_audio') and f.endswith('.wav')]
             if possible_files:
                    actual_path = os.path.join(temp_dir, possible_files[0])
                    print(f"Warning: Downloaded file found as {actual_path}, using it.")
                    # Optionally rename it if you need a consistent name, though not strictly required
                    # os.rename(actual_path, wav_path)
                    return actual_path
             else:
                print(f"Error: Expected WAV file '{wav_path}' not found after yt-dlp execution. Check yt-dlp output above.")
                print("Files in temp directory:", os.listdir(temp_dir))
                return None

    except FileNotFoundError:
        print("\nError: 'yt-dlp' command not found.")
        print("Please ensure yt-dlp is installed (pip install yt-dlp) and in your system's PATH.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"\nError: yt-dlp failed with return code {e.returncode}.")
        print("yt-dlp stdout (error):")
        print(e.stdout if e.stdout else "(No stdout)")
        print("\nyt-dlp stderr (error):")
        print(e.stderr if e.stderr else "(No stderr)")
        print("\nCheck the error message from yt-dlp. It might indicate the video is unavailable, private, region-locked, or requires authentication.")
        return None
    except Exception as e:
        print(f"\nAn unexpected error occurred during download/conversion: {e}")
        return None


def split_audio_intelligently(audio_path, temp_dir, min_silence_len=DEFAULT_MIN_SILENCE_LEN, silence_thresh=DEFAULT_SILENCE_THRESH, chunk_length_limit_ms=DEFAULT_CHUNK_LENGTH_MS * 2):
    """Splits audio based on silence, trying to keep chunks under a size limit."""
    if not os.path.exists(audio_path):
        print(f"Error: Audio file not found for splitting: {audio_path}")
        return []
    try:
        print(f"Loading audio file for splitting: {audio_path}")
        audio = AudioSegment.from_wav(audio_path)
        print(f"Audio loaded ({len(audio)/1000:.1f} seconds). Splitting based on silence...")

        chunks = split_on_silence(
            audio,
            min_silence_len=min_silence_len,    # Minimum length of silence (ms)
            silence_thresh=silence_thresh,      # Consider silence anything quieter than this dBFS
            keep_silence=300                    # Keep a bit of silence at the start/end (ms)
        )

        if not chunks:
             print("No silence detected for splitting, or audio too short. Processing as a single chunk.")
             chunks = [audio] # Process the whole audio if no silence found


        processed_chunks_paths = []
        total_chunks = 0

        for i, chunk in enumerate(chunks):
            # If a chunk is too long (e.g., long monologue without silence), split it by time
            if len(chunk) > chunk_length_limit_ms:
                num_sub_chunks = (len(chunk) + chunk_length_limit_ms - 1) // chunk_length_limit_ms
                sub_chunk_len = len(chunk) / num_sub_chunks # Use float division for better distribution
                print(f"Chunk {i} is too long ({len(chunk)/1000:.1f}s > {chunk_length_limit_ms/1000:.1f}s), splitting into {num_sub_chunks} sub-chunks...")
                for j in range(num_sub_chunks):
                    start_ms = int(j * sub_chunk_len)
                    end_ms = int(min((j + 1) * sub_chunk_len, len(chunk)))
                    if start_ms >= end_ms: continue # Avoid creating zero-length chunks

                    sub_chunk = chunk[start_ms:end_ms]
                    chunk_filename = os.path.join(temp_dir, f"chunk_{total_chunks}.wav")
                    print(f"   Exporting sub-chunk: {chunk_filename} ({start_ms/1000:.1f}s - {end_ms/1000:.1f}s)")
                    try:
                       sub_chunk.export(chunk_filename, format="wav")
                       processed_chunks_paths.append(chunk_filename)
                       total_chunks += 1
                    except Exception as export_err:
                       print(f"   Error exporting sub-chunk {chunk_filename}: {export_err}")

            else:
                if len(chunk) < 100: # Skip very short segments (likely noise)
                     print(f"Skipping very short chunk {i} ({len(chunk)}ms)")
                     continue
                chunk_filename = os.path.join(temp_dir, f"chunk_{total_chunks}.wav")
                print(f"Exporting chunk: {chunk_filename} ({len(chunk)/1000:.1f}s)")
                try:
                    chunk.export(chunk_filename, format="wav")
                    processed_chunks_paths.append(chunk_filename)
                    total_chunks += 1
                except Exception as export_err:
                    print(f"   Error exporting chunk {chunk_filename}: {export_err}")

        print(f"Audio split into {len(processed_chunks_paths)} chunks.")
        return processed_chunks_paths
    except Exception as e:
        print(f"Error splitting audio: {e}")
        return []


def transcribe_chunk_whisper(chunk_path, model_size="base", model_cache_dir=None):
    """Transcribes a single audio chunk using Whisper."""
    global whisper # Ensure whisper module is accessible
    if not whisper_available:
        print("  Whisper library not available. Cannot transcribe.")
        return ""

    print(f"  Transcribing {os.path.basename(chunk_path)} using Whisper ({model_size})...")
    try:
        # Load model once if not loaded, specifying cache directory if desired
        # This is a simplification; for high performance, load model once outside the loop
        model = whisper.load_model(model_size, download_root=model_cache_dir)
        # Detect language or specify if known: result = model.transcribe(chunk_path, language='en', fp16=False)
        result = model.transcribe(chunk_path, fp16=False) # Use fp16=False for CPU usage compatibility, consider True if using GPU
        return result['text'].strip()
    except Exception as e:
        print(f"  Error transcribing chunk {os.path.basename(chunk_path)} with Whisper: {e}")
        return "" # Return empty string on error


def transcribe_chunk_google(chunk_path, recognizer):
    """Transcribes a single audio chunk using Google Web Speech API."""
    print(f"  Transcribing {os.path.basename(chunk_path)} using Google Web Speech API...")
    with sr.AudioFile(chunk_path) as source:
        try:
            # Adjust for ambient noise once per recognizer instance can sometimes help
            # recognizer.adjust_for_ambient_noise(source)
            audio_listened = recognizer.record(source)
            # Try recognizing the speech
            text = recognizer.recognize_google(audio_listened)
            return text.strip()
        except sr.WaitTimeoutError:
             print(f"  Timeout waiting for speech in chunk {os.path.basename(chunk_path)} with Google.")
             return ""
        except sr.UnknownValueError:
            print(f"  Google Speech Recognition could not understand audio in {os.path.basename(chunk_path)}.")
            return "" # Return empty string if audio is unintelligible
        except sr.RequestError as e:
            print(f"  Could not request results from Google SR service for {os.path.basename(chunk_path)}; {e}")
            print("  Check network connection or potential API rate limits.")
            return "" # Return empty string on request error
        except Exception as e:
            print(f"  Unexpected error transcribing chunk {os.path.basename(chunk_path)} with Google: {e}")
            return ""

# --- Main Function ---

def main(args):
    """Main execution flow."""
    youtube_url = args.url
    output_file = args.output
    engine = args.engine.lower()
    whisper_model_size = args.whisper_model
    silence_thresh = args.silence_thresh
    min_silence_len = args.min_silence_len
    temp_dir = None # Initialize temp_dir

    # Validate engine choice
    if engine == "whisper" and not whisper_available:
        print("Error: Whisper engine selected, but the 'openai-whisper' library is not installed.")
        print("Please install it ('pip install openai-whisper') or choose the 'google' engine.")
        sys.exit(1)
    elif engine not in ["whisper", "google"]:
         print(f"Error: Unknown engine '{engine}'. Choose 'whisper' or 'google'.")
         sys.exit(1)


    try:
        # Create a temporary directory for processing
        temp_dir = tempfile.mkdtemp(prefix="youtube_transcriber_")
        print(f"Created temporary directory: {temp_dir}")

        # 1. Download Audio using yt-dlp
        audio_file_path = download_audio(youtube_url, temp_dir)
        if not audio_file_path:
            print("Failed to download audio. Exiting.")
            return # Error handled in download function

        # 2. Split Audio into Chunks (intelligently)
        # Optional: Increase chunk limit for potentially faster Whisper processing if memory allows
        chunk_paths = split_audio_intelligently(
            audio_file_path,
            temp_dir,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh
            # chunk_length_limit_ms = DEFAULT_CHUNK_LENGTH_MS * 3 # Example: Allow longer chunks
        )
        if not chunk_paths:
            print("No audio chunks were generated or an error occurred during splitting. Cannot proceed.")
            return

        # 3. Transcribe Chunks
        full_transcript = []
        num_chunks = len(chunk_paths)
        recognizer = sr.Recognizer() # Initialize Recognizer (used only for Google engine)

        print(f"\nStarting transcription of {num_chunks} chunks using '{engine}' engine...")

        for i, chunk_path in enumerate(chunk_paths):
            print(f"\nProcessing chunk {i + 1}/{num_chunks}...")
            text = ""
            try:
                if engine == "whisper":
                    # Optional: Specify where whisper downloads models: model_cache = os.path.join(os.path.expanduser("~"), ".cache", "whisper_models")
                    text = transcribe_chunk_whisper(chunk_path, model_size=whisper_model_size) # , model_cache_dir=model_cache
                elif engine == "google":
                    # Caution: Google API has rate limits and might fail on many consecutive requests
                    text = transcribe_chunk_google(chunk_path, recognizer)

                if text:
                    print(f"  Transcription (Chunk {i + 1}): {text}")
                    full_transcript.append(text)
                else:
                    print(f"  Chunk {i + 1} resulted in empty or failed transcription.")

            except Exception as transcribe_err:
                 print(f"  Critical error during transcription of chunk {i + 1}: {transcribe_err}")
                 # Decide if you want to stop or continue
                 # continue

        # 4. Save Full Transcript
        final_text = " ".join(full_transcript).strip()
        if final_text:
            print(f"\nTranscription complete. Saving to: {output_file}")
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(final_text)
                print("Transcript saved successfully.")
            except Exception as e:
                print(f"Error saving transcript file '{output_file}': {e}")
        else:
            print("\nTranscription did not produce any text output.")

    finally:
        # 5. Cleanup: Remove temporary directory and its contents
        if temp_dir and os.path.exists(temp_dir):
             print(f"Cleaning up temporary directory: {temp_dir}")
             try:
                 shutil.rmtree(temp_dir)
                 print("Cleanup complete.")
             except Exception as e:
                 print(f"Warning: Could not remove temporary directory {temp_dir}. Error: {e}")
                 print("You may need to delete it manually.")

if __name__ == "__main__":
    # Define available whisper models if whisper is installed
    whisper_models = ["tiny", "base", "small", "medium", "large"] if whisper_available else ["N/A"]
    default_model = DEFAULT_WHISPER_MODEL if whisper_available and DEFAULT_WHISPER_MODEL in whisper_models else whisper_models[0]

    parser = argparse.ArgumentParser(
        description="Transcribe a long YouTube video using yt-dlp for download and speech recognition.",
        formatter_class=argparse.RawTextHelpFormatter # Keep formatting in help message
        )
    parser.add_argument("url", help="The URL of the YouTube video.")
    parser.add_argument("-o", "--output", default="transcript.txt",
                        help="Output file path for the transcription (default: transcript.txt).")
    parser.add_argument("-e", "--engine", default=DEFAULT_ENGINE, choices=["whisper", "google"],
                        help=f"Speech recognition engine (default: {DEFAULT_ENGINE}).\n"
                             f" 'whisper': More accurate, runs locally (requires openai-whisper).\n"
                             f" 'google': Uses free Web Speech API (less accurate, requires internet, rate limited).")
    parser.add_argument("-m", "--whisper-model", default=default_model, choices=whisper_models,
                        help=f"Whisper model size (default: {default_model}). Ignored if engine is not 'whisper'.\n"
                             f" Models range from 'tiny' (fastest, least accurate) to 'large' (slowest, most accurate).\n"
                             f" Larger models require more RAM/VRAM.")
    parser.add_argument("-st", "--silence-thresh", type=int, default=DEFAULT_SILENCE_THRESH,
                        help=f"Silence threshold in dBFS for splitting audio (lower is stricter, default: {DEFAULT_SILENCE_THRESH}).")
    parser.add_argument("-msl", "--min-silence-len", type=int, default=DEFAULT_MIN_SILENCE_LEN,
                        help=f"Minimum silence length in ms required to split audio (default: {DEFAULT_MIN_SILENCE_LEN}).")

    # Check basic dependencies early (ffmpeg check requires running it)
    try:
        import yt_dlp
        import pydub
        import speech_recognition
        if DEFAULT_ENGINE == 'whisper' and not whisper_available:
             pass # We handle this later if user explicitly selects whisper
    except ImportError as err:
        print(f"\nError: Missing required Python library: '{err.name}'")
        print("Please install prerequisites using pip inside your activated virtual environment:")
        print("pip install yt-dlp pydub SpeechRecognition openai-whisper")
        sys.exit(1)

    # Simple check if yt-dlp exists in PATH (might not be exhaustive)
    try:
        subprocess.run(['yt-dlp', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (subprocess.CalledProcessError, FileNotFoundError):
         print("\nWarning: Could not execute 'yt-dlp'.")
         print("Make sure yt-dlp is installed ('pip install yt-dlp') and accessible in your system's PATH.")
         # Optionally exit here, or let the download function handle the error later
         # sys.exit(1)

    args = parser.parse_args()

    # Final check before running main logic
    if args.engine == "whisper" and not whisper_available:
         print("\nError: Cannot use '--engine whisper' because the 'openai-whisper' library is not installed or failed to import.")
         print("Install it with 'pip install openai-whisper' or select '--engine google'.")
         sys.exit(1)


    main(args)