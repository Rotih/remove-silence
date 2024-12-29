# Silence Removal Python Program

A Python utility that processes audio files using two methods: Silero VAD (Voice Activity Detection) and FFmpeg. Both approaches remove silence and normalize audio output.

## Prerequisites (Other versions may be compatible, these are just what I used)

- Python 3.12.2
- FFmpeg version 2024-04-10-git-0e4dfa4709-full_build-www.gyan.dev
- Required Python packages (see requirements.txt):
  - torch==2.5.1
  - torchaudio==2.5.1

## Installation

1. Install Python 3.12.2
2. Install FFmpeg and ensure it's in your system PATH
3. Install required packages:

```bash
pip install -r requirements.txt
```

## Usage

Run the script with an input audio file:

```bash
python main.py path/to/audio/file.wav
```

The script will:

1. Create a 'processed' subdirectory where the input file is located. I've included a media folder with an example test file.
2. Process the file using both methods:
   - Silero VAD: `{filename}_silero.wav`
   - FFmpeg: `{filename}_ffmpeg.wav`
3. Display processing statistics

## Processing Methods

### Silero VAD

- ML model based voice detection
- Adds 0.5s padding around speech segments
- Minimum speech duration: 0.5s
- Handles silence by trimming to 1 second
- Uses PyTorch backend

### FFmpeg

- Signal-based silence detection
- Silence threshold: -40dB
- Minimum silence duration: 1.0s
- Two-pass normalization
- Generates 1-second silent file for silent inputs

## Output Statistics

For each method, displays:

- Original duration (seconds)
- Processed duration (seconds)
- Reduction percentage
- Processing time
- Number of detected segments

## Error Handling

The script handles:

- Missing input files
- Processing errors
- Silent audio files
- Windows/Unix path differences
- Temporary file cleanup
