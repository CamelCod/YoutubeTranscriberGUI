import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import queue # Optional, can use .after instead
import os
import sys
import tempfile
import shutil
import subprocess
from pydub import AudioSegment
from pydub.silence import split_on_silence
import speech_recognition as sr

# Attempt to import whisper and check availability
try:
    import whisper
    whisper_available = True
    whisper_models = ["tiny", "base", "small", "medium", "large"]
except ImportError:
    whisper_available = False
    whisper_models = ["N/A - Please install openai-whisper"]
    print("WARNING: openai-whisper not found. Whisper engine unavailable.")
    print("Install using: pip install openai-whisper")


# --- Core Transcription Logic (Adapted from previous script) ---
# --- Configuration ---
DEFAULT_CHUNK_LENGTH_MS = 60 * 1000
DEFAULT_SILENCE_THRESH = -40
DEFAULT_MIN_SILENCE_LEN = 500
DEFAULT_WHISPER_MODEL = "base" if whisper_available else "N/A"

def log_message(message, output_widget):
    """Safely update the Tkinter text widget from any thread."""
    output_widget.after(0, lambda: _update_output(message, output_widget))

def _update_output(message, output_widget):
     """Internal function to append message and scroll."""
     output_widget.configure(state='normal')
     output_widget.insert(tk.END, message + "\n")
     output_widget.configure(state='disabled')
     output_widget.see(tk.END) # Scroll to the end


def download_audio(youtube_url, temp_dir, status_callback):
    """Downloads audio using yt-dlp and saves as WAV."""
    wav_path = None # Define wav_path initially
    try:
        status_callback(f"Starting download for: {youtube_url} using yt-dlp...")

        output_base = os.path.join(temp_dir, 'downloaded_audio')
        output_template = f'{output_base}.%(ext)s'
        wav_path = f'{output_base}.wav'

        command = [
            'yt-dlp',
            '--no-check-certificate',
            '-x', '--audio-format', 'wav',
            '-o', output_template,
            '--no-playlist',
            '--progress',
            '--verbose', # Verbose output can help debug download issues
            youtube_url
        ]

        status_callback(f"Running command: {' '.join(command)}")
        process = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')

        status_callback("yt-dlp stdout:\n" + (process.stdout or "(No stdout)"))
        if process.stderr:
             status_callback("yt-dlp stderr:\n" + process.stderr) # Log warnings/progress

        if os.path.exists(wav_path):
            status_callback(f"Download and conversion successful: {wav_path}")
            return wav_path
        else:
             possible_files = [f for f in os.listdir(temp_dir) if f.startswith('downloaded_audio') and f.endswith('.wav')]
             if possible_files:
                    actual_path = os.path.join(temp_dir, possible_files[0])
                    status_callback(f"Warning: Downloaded file found as {actual_path}, using it.")
                    return actual_path
             else:
                status_callback(f"Error: Expected WAV file '{wav_path}' not found after yt-dlp execution.")
                status_callback(f"Files in temp dir: {os.listdir(temp_dir)}")
                return None

    except FileNotFoundError:
        status_callback("\nERROR: 'yt-dlp' command not found.")
        status_callback("Ensure yt-dlp is installed (pip install yt-dlp) and in your system's PATH.")
        return None
    except subprocess.CalledProcessError as e:
        status_callback(f"\nERROR: yt-dlp failed with return code {e.returncode}.")
        status_callback("yt-dlp stderr (error):\n" + (e.stderr or "(No stderr)"))
        status_callback("Check if the video is available, not private/region-locked, etc.")
        return None
    except Exception as e:
        status_callback(f"\nERROR during download/conversion: {e}")
        return None


def split_audio_intelligently(audio_path, temp_dir, status_callback, min_silence_len=DEFAULT_MIN_SILENCE_LEN, silence_thresh=DEFAULT_SILENCE_THRESH, chunk_length_limit_ms=DEFAULT_CHUNK_LENGTH_MS * 2):
    """Splits audio based on silence."""
    if not audio_path or not os.path.exists(audio_path):
        status_callback(f"Error: Audio file not found for splitting: {audio_path}")
        return []
    try:
        status_callback(f"Loading audio file for splitting: {audio_path}")
        audio = AudioSegment.from_wav(audio_path)
        status_callback(f"Audio loaded ({len(audio)/1000:.1f} seconds). Splitting based on silence...")

        chunks = split_on_silence(
            audio, min_silence_len=min_silence_len,
            silence_thresh=silence_thresh, keep_silence=300
        )

        if not chunks:
             status_callback("No silence detected, processing as a single chunk.")
             chunks = [audio]

        processed_chunks_paths = []
        total_chunks = 0

        for i, chunk in enumerate(chunks):
            if len(chunk) > chunk_length_limit_ms:
                 # Split long chunks by time
                 num_sub_chunks = (len(chunk) + chunk_length_limit_ms - 1) // chunk_length_limit_ms
                 sub_chunk_len = len(chunk) / num_sub_chunks
                 status_callback(f"Chunk {i} too long ({len(chunk)/1000:.1f}s), splitting into {num_sub_chunks} sub-chunks...")
                 for j in range(num_sub_chunks):
                    start_ms = int(j * sub_chunk_len)
                    end_ms = int(min((j + 1) * sub_chunk_len, len(chunk)))
                    if start_ms >= end_ms: continue

                    sub_chunk = chunk[start_ms:end_ms]
                    chunk_filename = os.path.join(temp_dir, f"chunk_{total_chunks}.wav")
                    status_callback(f"   Exporting sub-chunk: {os.path.basename(chunk_filename)} ({len(sub_chunk)/1000:.1f}s)")
                    try:
                       sub_chunk.export(chunk_filename, format="wav")
                       processed_chunks_paths.append(chunk_filename)
                       total_chunks += 1
                    except Exception as export_err:
                       status_callback(f"   ERROR exporting sub-chunk {chunk_filename}: {export_err}")

            else:
                 if len(chunk) < 100: continue # Skip tiny chunks
                 chunk_filename = os.path.join(temp_dir, f"chunk_{total_chunks}.wav")
                 status_callback(f"Exporting chunk: {os.path.basename(chunk_filename)} ({len(chunk)/1000:.1f}s)")
                 try:
                     chunk.export(chunk_filename, format="wav")
                     processed_chunks_paths.append(chunk_filename)
                     total_chunks += 1
                 except Exception as export_err:
                     status_callback(f"   ERROR exporting chunk {chunk_filename}: {export_err}")


        status_callback(f"Audio split into {len(processed_chunks_paths)} chunks.")
        return processed_chunks_paths

    except Exception as e:
        status_callback(f"ERROR during audio splitting: {e}")
        return []


def transcribe_chunk_whisper(chunk_path, model_size, status_callback, model_cache_dir=None):
    """Transcribes a single audio chunk using Whisper."""
    global whisper # Access the imported module
    if not whisper_available:
        status_callback("ERROR: Whisper library not available.")
        return ""
    status_callback(f"  Transcribing {os.path.basename(chunk_path)} (Whisper model: {model_size})...")
    try:
        model = whisper.load_model(model_size, download_root=model_cache_dir)
        result = model.transcribe(chunk_path, fp16=False) # Use fp16=False for CPU compatibility
        transcription = result['text'].strip()
        status_callback(f"  Segment Result: {transcription if transcription else '--silence--'}")
        return transcription
    except Exception as e:
        status_callback(f"  ERROR transcribing chunk {os.path.basename(chunk_path)} with Whisper: {e}")
        return ""

def transcribe_chunk_google(chunk_path, recognizer, status_callback):
    """Transcribes a single audio chunk using Google Web Speech API."""
    status_callback(f"  Transcribing {os.path.basename(chunk_path)} (Google API)...")
    with sr.AudioFile(chunk_path) as source:
        try:
            audio_listened = recognizer.record(source)
            text = recognizer.recognize_google(audio_listened)
            transcription = text.strip()
            status_callback(f"  Segment Result: {transcription if transcription else '--silence--'}")
            return transcription
        except sr.UnknownValueError:
            status_callback(f"  Google API could not understand audio: {os.path.basename(chunk_path)}")
            return ""
        except sr.RequestError as e:
            status_callback(f"  Google API request failed for {os.path.basename(chunk_path)}; {e}")
            return ""
        except Exception as e:
            status_callback(f"  ERROR transcribing {os.path.basename(chunk_path)} with Google: {e}")
            return ""

# --- Transcription Process Function (to run in thread) ---

def run_transcription_process(url, engine, model_size, output_widget):
    """The main process: download, split, transcribe."""
    temp_dir = None
    transcript_parts = []
    success = False

    # Define the callback using the log_message function
    status_callback = lambda msg: log_message(msg, output_widget)

    try:
        if not url:
            status_callback("ERROR: YouTube URL cannot be empty.")
            return False

        # Create Temp Directory
        temp_dir = tempfile.mkdtemp(prefix="youtube_gui_")
        status_callback(f"Created temporary directory: {temp_dir}")

        # 1. Download
        status_callback("\n--- Downloading Audio ---")
        audio_file_path = download_audio(url, temp_dir, status_callback)
        if not audio_file_path:
            status_callback("ERROR: Audio download failed. See messages above.")
            return False # Stop the process

        # 2. Split
        status_callback("\n--- Splitting Audio ---")
        # These could be GUI options later
        silence_thresh = DEFAULT_SILENCE_THRESH
        min_silence_len = DEFAULT_MIN_SILENCE_LEN
        chunk_paths = split_audio_intelligently(
            audio_file_path, temp_dir, status_callback,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh
        )
        if not chunk_paths:
            status_callback("ERROR: Audio splitting failed or produced no chunks.")
            return False

        # 3. Transcribe
        status_callback(f"\n--- Transcribing Chunks ({engine}) ---")
        num_chunks = len(chunk_paths)
        recognizer = sr.Recognizer() if engine == "google" else None

        for i, chunk_path in enumerate(chunk_paths):
            status_callback(f"\nProcessing chunk {i + 1}/{num_chunks}...")
            text = ""
            if engine == "whisper":
                if not whisper_available:
                     status_callback("ERROR: Whisper selected but not installed.")
                     continue # Skip chunk or return False? Maybe better to error out earlier
                text = transcribe_chunk_whisper(chunk_path, model_size, status_callback)
            elif engine == "google":
                text = transcribe_chunk_google(chunk_path, recognizer, status_callback)

            if text:
                transcript_parts.append(text)
            else:
                # status_callback(f"  Chunk {i + 1} resulted in empty transcription.")
                pass # Avoid cluttering log with empty results

        # 4. Combine Transcript
        final_transcript = " ".join(transcript_parts).strip()
        status_callback("\n--- Transcription Complete ---")
        if final_transcript:
            # Clear the log and add final transcript *only* if successful
            output_widget.after(0, lambda: output_widget.configure(state='normal'))
            output_widget.after(0, lambda: output_widget.delete('1.0', tk.END))
            output_widget.after(0, lambda: output_widget.insert(tk.END, final_transcript))
            output_widget.after(0, lambda: output_widget.configure(state='disabled'))
            output_widget.after(0, lambda: output_widget.see('1.0')) # Scroll to top
            status_callback("\nFinal transcript displayed above.")
            success = True
        else:
            status_callback("WARNING: Transcription finished but produced no text.")
            success = False # Consider this unsuccessful if no text

        return success

    except Exception as e:
        status_callback(f"\n--- CRITICAL ERROR ---")
        status_callback(f"An unexpected error occurred: {e}")
        import traceback
        status_callback(traceback.format_exc()) # Log detailed error
        return False
    finally:
        # Cleanup
        if temp_dir and os.path.exists(temp_dir):
            status_callback(f"Cleaning up temporary directory: {temp_dir}")
            try:
                shutil.rmtree(temp_dir)
                status_callback("Cleanup complete.")
            except Exception as e:
                status_callback(f"Warning: Could not remove temp directory {temp_dir}: {e}")


# --- GUI Class ---

class TranscriptionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Video Transcriber")
        # self.root.geometry("700x600") # Optional: set initial size

        # Style
        self.style = ttk.Style(self.root)
        self.style.theme_use('clam') # Use a slightly more modern theme ('clam', 'alt', 'default', 'classic')

        # Frame for inputs
        input_frame = ttk.Frame(root, padding="10")
        input_frame.pack(fill=tk.X)

        # URL Input
        ttk.Label(input_frame, text="YouTube URL:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.url_entry = ttk.Entry(input_frame, width=60)
        self.url_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        input_frame.columnconfigure(1, weight=1) # Make entry expand

        # Engine Selection
        ttk.Label(input_frame, text="Engine:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.engine_var = tk.StringVar()
        engines = ["whisper", "google"] if whisper_available else ["google"]
        self.engine_combo = ttk.Combobox(input_frame, textvariable=self.engine_var, values=engines, state="readonly")
        if engines:
             self.engine_combo.set(engines[0])
        self.engine_combo.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        self.engine_combo.bind("<<ComboboxSelected>>", self.update_model_options) # Update models when engine changes

        # Whisper Model Selection
        self.model_label = ttk.Label(input_frame, text="Whisper Model:")
        self.model_label.grid(row=1, column=2, padx=(20, 5), pady=5, sticky=tk.W) # Add padding left
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(input_frame, textvariable=self.model_var, values=whisper_models, state="readonly", width=15)
        if whisper_available and DEFAULT_WHISPER_MODEL in whisper_models:
            self.model_combo.set(DEFAULT_WHISPER_MODEL)
        elif whisper_models:
            self.model_combo.set(whisper_models[0]) # Set first available if default not there
        self.model_combo.grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)


        # Start Button
        self.start_button = ttk.Button(input_frame, text="Start Transcription", command=self.start_transcription_thread)
        self.start_button.grid(row=2, column=0, columnspan=4, padx=5, pady=10)

        # Output Area
        output_frame = ttk.Frame(root, padding=(10, 0, 10, 10))
        output_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(output_frame, text="Output Log & Transcript:").pack(anchor=tk.W, pady=(0,5))
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, state='disabled', height=15)
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # Save Button
        self.save_button = ttk.Button(output_frame, text="Save Transcript", command=self.save_transcript, state='disabled')
        self.save_button.pack(pady=5)

        # Initial State Update
        self.update_model_options() # Set initial visibility/state of model combo


    def update_model_options(self, event=None):
        """Enable/disable Whisper model selection based on engine."""
        if self.engine_var.get() == "whisper" and whisper_available:
            self.model_label.grid() # Show label
            self.model_combo.grid() # Show combobox
            self.model_combo.config(state='readonly')
        else:
            self.model_label.grid_remove() # Hide label
            self.model_combo.grid_remove() # Hide combobox
            # Optionally set model var to empty or N/A
            # self.model_var.set("N/A")


    def start_transcription_thread(self):
        """Starts the transcription process in a separate thread."""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL.")
            return

        engine = self.engine_var.get()
        model_size = self.model_var.get()

        if engine == "whisper" and not whisper_available:
            messagebox.showerror("Error", "Whisper engine selected, but 'openai-whisper' is not installed.")
            return
        if engine == "whisper" and model_size == "N/A":
             messagebox.showerror("Error", "Please select a valid Whisper model.")
             return


        # Disable button, clear output, enable saving later
        self.start_button.config(state='disabled')
        self.save_button.config(state='disabled') # Disable save until successful run
        self.output_text.config(state='normal')
        self.output_text.delete('1.0', tk.END)
        self.output_text.config(state='disabled')
        log_message("Starting transcription process...", self.output_text) # Initial log

        # Run the main logic in a thread
        self.transcription_thread = threading.Thread(
            target=self.run_transcription_wrapper,
            args=(url, engine, model_size),
            daemon=True # Allows exiting app even if thread is running (might be abrupt)
        )
        self.transcription_thread.start()

    def run_transcription_wrapper(self, url, engine, model_size):
        """Wrapper to run the core logic and handle GUI updates on completion."""
        success = False
        try:
             success = run_transcription_process(url, engine, model_size, self.output_text)
        finally:
             # Schedule GUI updates back in the main thread using 'after'
             self.root.after(0, lambda: self.on_transcription_complete(success))


    def on_transcription_complete(self, success):
        """Called from the main thread after transcription finishes."""
        self.start_button.config(state='normal') # Re-enable button
        if success:
            self.save_button.config(state='normal') # Enable save ONLY if successful
            messagebox.showinfo("Success", "Transcription finished successfully!")
        else:
             self.save_button.config(state='disabled') # Ensure save is disabled on failure
             messagebox.showerror("Error", "Transcription failed. Check the log for details.")


    def save_transcript(self):
        """Saves the content of the output text area to a file."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not file_path:
            return # User cancelled

        try:
            # We only save the final transcript, not the whole log
            # Get text - Assumes final text replaced log on success
            self.output_text.config(state='normal') # Must enable to get text
            transcript = self.output_text.get("1.0", tk.END).strip()
            self.output_text.config(state='disabled')

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(transcript)
            messagebox.showinfo("Saved", f"Transcript saved successfully to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save transcript: {e}")


# --- Main Execution ---
if __name__ == "__main__":
    # --- Dependency Checks (Basic) ---
    # Check for ffmpeg (simple check, might not be robust)
    ffmpeg_found = False
    try:
        # Check return code only, suppress output
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ffmpeg_found = True
    except (subprocess.CalledProcessError, FileNotFoundError):
         pass # Will show warning below

     # Check for yt-dlp
    yt_dlp_found = False
    try:
        subprocess.run(['yt-dlp', '--version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        yt_dlp_found = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Start GUI
    root = tk.Tk()
    app = TranscriptionApp(root)

    # Show warnings if dependencies missing
    if not ffmpeg_found:
        messagebox.showwarning("Dependency Warning",
                               "ffmpeg not found in PATH.\n\n"
                               "Audio splitting/conversion will likely fail.\n\n"
                               "Please download from ffmpeg.org and add it to your system's PATH.")
    if not yt_dlp_found:
        messagebox.showwarning("Dependency Warning",
                              "'yt-dlp' command not found.\n\n"
                              "Downloading will likely fail.\n\n"
                              "Please install with 'pip install yt-dlp' and ensure it's in your PATH.")

    root.mainloop()