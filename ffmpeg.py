from pathlib import Path
import subprocess
import time
from typing import Dict
from uuid import uuid4

from helpers import get_duration


class FFmpegProcessor:
    def __init__(self, silence_thresh=-40, min_silence_duration=1.0):
        self.silence_thresh = silence_thresh
        self.min_silence_duration = min_silence_duration

    # helper function to parse string output from silencedetect, just generated this with gpt and verified that it works
    def _parse_silence_timestamps(self, stderr_output):
        """Parses the output string"""
        silence_spans = []
        silence_start = None

        for line in stderr_output.split("\n"):
            try:
                if "silence_start" in line:
                    silence_start = float(
                        line.split("silence_start:")[1].split("|")[0].strip()
                    )
                elif "silence_end" in line and silence_start is not None:
                    silence_end = float(
                        line.split("silence_end:")[1].split("|")[0].strip()
                    )
                    silence_spans.append((silence_start, silence_end))
                    silence_start = None
            except (ValueError, IndexError):
                continue

        return silence_spans

    def _generate_segments(self, silence_spans, duration):
        segments = []
        last_end = 0

        for start, end in silence_spans:
            # checks if theres a gap between end of the last silence and start of current silence
            if start > last_end:
                # when we find a gap between silence that means its a nonsilent segment, and we can append the between filter
                # between filter for ffmpeg will keep these timestamps
                segments.append(f"between(t,{last_end},{start})")
            last_end = end

        if last_end < duration:
            segments.append(f"between(t,{last_end},{duration})")

        return segments

    def process_file(self, input_path: str, output_path: str) -> Dict:
        """Process audio using FFmpeg with simplified normalization and silence removal."""
        start_time = time.time()

        # prepare all file paths
        input_path = Path(input_path).resolve()
        input_path_str = str(input_path)
        output_path = Path(output_path).resolve()
        output_path_str = str(output_path)
        temp_path = output_path.parent / f"{uuid4()}.wav"
        temp_path_str = str(temp_path)

        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        try:
            # convert to mono and normalize
            # online solutions recommended a double pass
            normalize_filter = (
                "aresample=16000,"
                "pan=mono|c0=c0,"
                "speechnorm=p=0.7:e=1.5:c=2:t=0.1:r=0.001:f=0.001,"  # first pass: normalization and noise reduction
                "speechnorm=p=0.95:e=1.2:c=1.5:t=0.15:r=0.001:f=0.001:m=0.4"  # second pass: boost volume
            )

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    input_path_str,
                    "-af",
                    normalize_filter,
                    temp_path_str,
                ],
                capture_output=True,
                check=True,
            )

            # naively detect silence with just decibel and silence duration parameters
            silence_filter = f"silencedetect=noise={self.silence_thresh}dB:d={self.min_silence_duration}:mono=1"

            result = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    temp_path_str,
                    "-af",
                    silence_filter,
                    "-f",
                    "null",
                    "-",
                ],
                capture_output=True,
                text=True,
            )

            # parse the output string
            silence_spans = self._parse_silence_timestamps(result.stderr)

            # if no silence detected, return original file with only normalization filter
            if not silence_spans:
                print("no silence detected, returning normalized file without trims")
                import shutil

                shutil.copy2(temp_path_str, output_path_str)
                segments = []
            # handle silence span removal
            else:
                print(f"found silences at {silence_spans}")
                duration = get_duration(temp_path_str)
                segments = self._generate_segments(silence_spans, duration)

                print(f"Created segments: {segments}")

                filter_to_apply = None

                # if no segments (entire file is silence), return file trimmed to 1 second
                if not segments:
                    # trim filter
                    filter_to_apply = "atrim=0:1,asetpts=PTS-STARTPTS"
                else:
                    # select using segments
                    filter_to_apply = f"aselect='{'+'.join(segments)}',asetpts=N/SR/TB"

                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        temp_path_str,
                        "-af",
                        filter_to_apply,
                        output_path_str,
                    ],
                    capture_output=True,
                    check=True,
                )

                processing_time = time.time() - start_time

            # verify output file exists before checking duration
            if not output_path.exists():
                raise FileNotFoundError(f"Output file not found: {output_path}")

            # get original file duration
            input_duration = get_duration(input_path_str)

            # get processed file duration
            output_duration = get_duration(output_path_str)

            return {
                "input_duration": input_duration,
                "output_duration": output_duration,
                "processing_time": processing_time,
                "num_segments": len(segments) if "segments" in locals() else 0,
                "silence_spans": silence_spans,
            }
        except subprocess.CalledProcessError as e:
            print(
                f"Error during FFmpeg processing: {e.stderr.decode() if e.stderr else str(e)}"
            )
            raise
        finally:
            if temp_path.exists():
                temp_path.unlink()
