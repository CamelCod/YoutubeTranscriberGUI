# YouTube Video Transcriber

A Python GUI application that downloads YouTube videos, extracts audio, and transcribes the content using either OpenAI's Whisper or Google's Speech Recognition API.

![GitHub release (latest by date)](https://img.shields.io/github/v/release/YOUR_USERNAME/YoutubeTranscriberGUI)
![GitHub](https://img.shields.io/github/license/YOUR_USERNAME/YoutubeTranscriberGUI)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)

## Features

- Download audio from YouTube videos using yt-dlp
- Split audio intelligently based on silence
- Transcribe using:
  - OpenAI Whisper (multiple model sizes available)
  - Google Web Speech API
- Simple and intuitive GUI interface
- Save transcripts to text files

## 📋 Requirements

- Python 3.8 or higher
- FFmpeg installed and added to your system's PATH
- Python dependencies (see requirements.txt)

## 🔧 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/YoutubeTranscriberGUI.git
   cd YoutubeTranscriberGUI
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install FFmpeg:
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg` (Ubuntu/Debian) or `sudo yum install ffmpeg` (CentOS/RHEL)

4. Install OpenAI Whisper (optional, only if you want to use the Whisper engine):
   ```bash
   pip install openai-whisper
   ```

## 🚀 Usage

Run the application:

```bash
python youtube_transcriber_gui.py
```

1. Enter a YouTube URL in the input field
2. Select your preferred transcription engine:
   - **Whisper**: More accurate, works offline, but requires more resources
   - **Google**: Faster, requires internet connection, less accurate with specialized terms
3. If using Whisper, select a model size (larger = more accurate but slower)
4. Click "Start Transcription"
5. When complete, use "Save Transcript" to save the transcription as a text file

## 📈 Performance Tips

- Use smaller Whisper models for faster processing (tiny or base)
- For longer videos, Google API may be more practical due to speed
- Adjust silence detection parameters for better segmentation
- Ensure your system has adequate RAM for Whisper models (especially "medium" and "large")

## 🔄 Possible Errors and Solutions

- **yt-dlp errors**: Make sure you have the latest version installed (`pip install --upgrade yt-dlp`)
- **Audio splitting issues**: Check that FFmpeg is properly installed and in your PATH
- **Whisper model errors**: Try a smaller model, or ensure your system has enough memory

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube downloading
- [OpenAI Whisper](https://github.com/openai/whisper) for transcription
- [SpeechRecognition](https://github.com/Uberi/speech_recognition) library
- [pydub](https://github.com/jiaaro/pydub) for audio processing