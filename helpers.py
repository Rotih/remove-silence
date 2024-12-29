import subprocess
import os


def does_file_exist(file_path: str) -> bool:
    """Check if a file exists"""

    return os.path.exists(file_path)


def get_duration(file_path: str) -> float:
    """Get the duration of a file in seconds"""

    try:
        return float(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",  # use ffprobe to read duration of processed file
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    file_path,
                ]
            )
            .decode()
            .strip()
        )
    except Exception as e:
        print(f"Error getting duration for file {file_path}: {str(e)}")
        raise
