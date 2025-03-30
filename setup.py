from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="youtube-transcriber-gui",
    version="1.0.0",
    author="YOUR_NAME",
    author_email="YOUR_EMAIL",
    description="A YouTube video transcription GUI application using Whisper and Google Speech APIs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/YOUR_USERNAME/YoutubeTranscriberGUI",
    py_modules=["youtube_transcriber_gui"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "youtube-transcriber=youtube_transcriber_gui:main",
        ],
    },
)