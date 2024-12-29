import sys
from uuid import uuid4
import torch
import torchaudio
from pathlib import Path
import subprocess
import time

from helpers import get_duration


class SileroVADProcessor:
    def __init__(self, pad_duration=0.5, min_speech_duration=0.5):
        self.model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad", model="silero_vad"
        )
        self.get_speech_timestamps = utils[0]
        self.sampling_rate = 16000  # silero supports only 16000hz and 8000hz
        self.pad_duration = pad_duration
        self.min_speech_duration = min_speech_duration
        self.trim_duration = 1.0

    def process_file(self, input_path, output_path):
        """Process audio file, removing silence and normalizing."""
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
            waveform, sr = torchaudio.load(str(input_path))

            # resample to 16000hz
            if sr != self.sampling_rate:
                waveform = torchaudio.transforms.Resample(sr, self.sampling_rate)(
                    waveform
                )

            # convert stereo to mono audio
            waveform = (
                torch.mean(waveform, dim=0, keepdim=True)
                if waveform.shape[0] > 1
                else waveform
            )

            # use 512 samples(32ms) chunks for VAD processing
            raw_timestamps = self.get_speech_timestamps(
                waveform.squeeze(),  # convert to 1d tensor to be compatible with silero
                self.model,
                sampling_rate=self.sampling_rate,
                window_size_samples=512,
            )

            # check for empty timestamps, return 1 second file
            if not raw_timestamps:
                print("No speech detected. Trimming to 1 second.")
                trim_samples = min(
                    int(self.trim_duration * self.sampling_rate), waveform.shape[1]
                )
                trimmed_waveform = waveform[:, :trim_samples]
                processing_time = time.time() - start_time

                torchaudio.save(output_path_str, trimmed_waveform, self.sampling_rate)

                # get input file duration
                input_duration = get_duration(input_path_str)

                # get output file duration
                output_duration = get_duration(output_path_str)

                return {
                    "input_duration": input_duration,
                    "output_duration": output_duration,
                    "num_segments": 0,
                    "processing_time": processing_time,
                }

            # add padding to closer mimic human speech, otherwise the speech is too fast with no gaps
            pad_samples = int(self.pad_duration * self.sampling_rate)
            timestamps = [
                {
                    "start": max(0, segment["start"] - pad_samples),
                    "end": min(len(waveform.squeeze()), segment["end"] + pad_samples),
                }  # add padding before start of timestamp and after end of timestamp unless it's start or end of file
                for segment in raw_timestamps  # iterate through timestamps
                if (segment["end"] - segment["start"]) / self.sampling_rate
                >= self.min_speech_duration  # if speech detected
            ]

            # merge overlapping segments to avoid choppy audio
            merged_timestamps = []
            for segment in sorted(
                timestamps, key=lambda x: x["start"]
            ):  # for iterate trough segments sorted by start time
                if (
                    not merged_timestamps
                    or segment["start"] > merged_timestamps[-1]["end"]
                ):
                    merged_timestamps.append(segment)
                else:
                    merged_timestamps[-1]["end"] = max(
                        merged_timestamps[-1]["end"], segment["end"]
                    )

            processed_wav = torch.cat(
                [  # concatenate speech segments into single tensor
                    waveform.squeeze()[segment["start"] : segment["end"]]
                    for segment in merged_timestamps
                ]
            )

            torchaudio.save(
                temp_path_str, processed_wav.unsqueeze(0), self.sampling_rate
            )  # save file as mono wav

            subprocess.run(
                [  # use loudnorm to normalize again so audio is more consistent, this could be tweaked further
                    "ffmpeg",
                    "-y",
                    "-i",
                    temp_path_str,
                    "-filter:a",
                    "loudnorm=I=-24:TP=-1.5",
                    output_path_str,
                ],
                capture_output=True,
                check=True,
            )

            processing_time = time.time() - start_time

            # get input file duration
            input_duration = get_duration(input_path_str)

            # get output file duration
            output_duration = get_duration(output_path_str)

            # return processng information
            return {
                "input_duration": input_duration,
                "output_duration": output_duration,
                "processing_time": processing_time,
                "num_segments": len(merged_timestamps),
            }

        finally:
            if temp_path.exists():
                temp_path.unlink()
