# YouTube Video Transcriber GUI

A simple desktop application built with Python and Tkinter to download audio from YouTube videos and generate text transcriptions using OpenAI's Whisper or Google's Speech Recognition API.

![Screenshot (Add a screenshot of the running GUI here!)](img/screenshot.png)
*(Optional: Create an 'img' folder and place your screenshot there)*

## Features

*   **Download YouTube Audio:** Directly fetches audio streams from provided YouTube URLs using `yt-dlp`.
*   **Multiple Transcription Engines:**
    *   **OpenAI Whisper:** Utilizes various Whisper models (tiny, base, small, medium, large) for high-accuracy, local transcription.
    *   **Google Web Speech API:** Offers a faster, cloud-based alternative (requires internet, less accurate, rate-limited).
*   **Intelligent Audio Splitting:** Automatically splits audio based on silence using `pydub` to handle long videos efficiently.
*   **User-Friendly Interface:** Simple GUI built with Tkinter for easy operation.
*   **Progress Logging:** Displays status messages, download progress (via `yt-dlp`), and transcription steps.
*   **Save Transcript:** Allows saving the generated transcription to a text file.

## Prerequisites

Before you begin, ensure you have the following installed:

1.  **Python:** Version 3.7 or higher is recommended.
    *   Download from [python.org](https://www.python.org/)
    *   Make sure Python and Pip are added to your system's PATH during installation.

2.  **FFmpeg:** **Absolutely essential** for audio processing (used by `pydub`).
    *   Download from the official website: [ffmpeg.org](https://ffmpeg.org/download.html)
    *   **Crucially:** You **must** add the directory containing the `ffmpeg` executable (e.g., the `bin` folder within the downloaded files) to your system's **PATH environment variable**.
    *   **Verify Installation:** Open a *new* terminal or command prompt window *after* modifying the PATH and type:
        ```bash
        ffmpeg -version
        ```
        If this command runs successfully and shows the version info, you're good to go. If not, the application will likely fail during audio splitting.

3.  **(Optional but Recommended) Git:** Needed to clone the repository easily.
    *   Download from [git-scm.com](https://git-scm.com/)

## Installation

Follow these steps to set up the project locally:

1.  **Clone the Repository:**
    Open your terminal or Git Bash and run:
    ```bash
    git clone https://github.com/CamelCod/YoutubeTranscriberGUI.git
    cd YoutubeTranscriberGUI
    ```
    *(Ensure `YoutubeTranscriberGUI` matches the actual name of your repository on GitHub)*

2.  **Create and Activate a Virtual Environment:** (Highly Recommended)
    This isolates project dependencies.
    ```bash
    # On Windows
    python -m venv .venv
    .\.venv\Scripts\activate

    # On macOS / Linux
    python -m venv .venv
    source .venv/bin/activate
    ```
    Your terminal prompt should now indicate the active environment (e.g., `(.venv)`).

3.  **Install Dependencies:**
    Install all required Python libraries using the provided `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: This step downloads `openai-whisper`, `yt-dlp`, `pydub`, `SpeechRecognition`, and their dependencies, including `torch` (PyTorch). The PyTorch/Whisper installation can take some time and requires significant disk space.*

## Running the Application

1.  **Activate Virtual Environment:** If it's not already active, navigate to the project directory in your terminal and activate the virtual environment (see Step 2 in Installation).

2.  **Run the GUI Script:**
    Execute the main Python script:
    ```bash
    python youtube_transcriber_gui.py
    ```

    The application window should appear.

## Usage Guide

1.  **Enter URL:** Paste the complete URL of the YouTube video you want to transcribe into the "YouTube URL" field.
2.  **Select Engine:**
    *   `whisper`: Choose this for higher accuracy. It runs locally on your machine.
    *   `google`: Choose this for potentially faster results on short segments (requires internet connection, may be less accurate, and can be rate-limited by Google).
3.  **Select Whisper Model (if applicable):** If you chose the `whisper` engine, select the desired model size from the dropdown.
    *   `tiny`, `base`: Faster, less accurate, lower resource usage.
    *   `small`, `medium`: Good balance of speed and accuracy.
    *   `large`: Slowest, most accurate, requires significant RAM/VRAM.
    *   *(The first time you use a specific Whisper model, it will be downloaded automatically, which may take a while.)*
4.  **Start Transcription:** Click the "Start Transcription" button.
5.  **Monitor Progress:** Watch the "Output Log & Transcript" area for status updates on downloading, splitting, and transcribing chunks. `yt-dlp` download progress might also appear here or in the terminal you launched the app from.
6.  **View & Save Transcript:** Once the process is complete, if successful, the final combined transcript will replace the log messages in the output area. The "Save Transcript" button will become active. Click it to save the transcript to a `.txt` file.

## Troubleshooting

*   **"ffmpeg not found" / Audio Splitting Fails:** This almost always means FFmpeg wasn't installed correctly OR its directory wasn't added properly to the system PATH. Double-check the PATH variable and try restarting your terminal or computer. Verify with `ffmpeg -version`.
*   **"yt-dlp: command not found" / Download Fails:** Ensure `yt-dlp` installed correctly (`pip show yt-dlp`). Try upgrading it (`pip install --upgrade yt-dlp`). Make sure your virtual environment is active.
*   **Download Errors (e.g., 403 Forbidden, 404 Not Found):** Check the error messages from `yt-dlp` in the log. The video might be private, deleted, age-restricted, region-locked, or require login. Sometimes YouTube changes things; updating `yt-dlp` might help.
*   **Whisper Errors / Slow Performance:**
    *   Ensure `openai-whisper` and `torch` installed without errors. Reinstall if needed (`pip install --force-reinstall openai-whisper torch`).
    *   Transcription, especially with larger models (`medium`, `large`), is CPU-intensive and requires significant RAM. Consider using a smaller model if performance is too slow.
    *   For much faster Whisper performance, use an NVIDIA GPU with CUDA installed correctly. You may need to install a specific PyTorch build with CUDA support (see [pytorch.org](https://pytorch.org/get-started/locally/)).
*   **Google API Errors:** Errors like `RequestError` often mean network issues or that you've hit Google's free API usage limits. `UnknownValueError` means the API couldn't understand the audio segment.
*   **GUI Freezes:** While unlikely with the current threading, if the GUI becomes unresponsive, check the terminal window where you launched `python youtube_transcriber_gui.py`. Critical errors might be printed there.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.