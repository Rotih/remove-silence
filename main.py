import os
import sys
from silero import SileroVADProcessor
from ffmpeg import FFmpegProcessor

processors = [
    {"name": "SileroVAD", "processor": SileroVADProcessor()},
    {"name": "FFmpeg", "processor": FFmpegProcessor()},
]


def process(input_file: str):
    print(f"Processing file: {input_file}")
    results = {}

    # create output directory if it doesnt exist
    output_dir = os.path.join(os.path.dirname(input_file), "processed")
    os.makedirs(output_dir, exist_ok=True)

    # get filename without extension
    file_name = os.path.splitext(os.path.basename(input_file))[0]

    # run each processor
    for p in processors:
        name = p["name"]
        processor = p["processor"]

        try:
            print(f"Running {name} processor")
            processor_output = os.path.join(output_dir, f"{file_name}_{name}.wav")
            processor_stats = processor.process_file(input_file, processor_output)
            results[name] = processor_stats
        except Exception as e:
            print(f"Error with {name} processor: {str(e)}")

    # print stats for each processor

    print("\n")

    print("Processing Results:")

    for p in processors:
        name = p["name"]
        stats = results[name]

        input_duration, output_duration, processing_time = (
            stats["input_duration"],
            stats["output_duration"],
            stats["processing_time"],
        )
        reduction = (input_duration - output_duration) / input_duration * 100

        print(f"{name} Approach:")
        print(f"Input Duration: {input_duration:.2f}s")
        print(f"Output Duration: {output_duration:.2f}s")
        print(f"Reduction: {reduction:.1f}%")
        print(f"Processing Time: {processing_time:.2f}s")
        print("\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    args = parser.parse_args()

    try:
        process(args.input_file)
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)
