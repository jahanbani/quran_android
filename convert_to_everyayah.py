#!/usr/bin/env python3
"""
Convert full Quran surah files to EveryAyah format (verse-by-verse)

This script:
1. Downloads the 48kbps EveryAyah Parhizgar files as reference for timing
2. Measures the duration of each ayah from the reference files
3. Splits your high-quality 128kbps surah files using those timings
4. Outputs properly named files (001001.mp3, 001002.mp3, etc.)

Requirements:
- Python 3.7+
- ffmpeg (portable version will be downloaded if not found)
- Your surah files named as: 001.mp3, 002.mp3, ... 114.mp3
"""

import os
import subprocess
import urllib.request
import json
from pathlib import Path

# Quran structure: number of ayahs per surah
AYAH_COUNTS = [
    7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99,
    128, 111, 110, 98, 135, 112, 78, 118, 64, 77, 227, 93, 88, 69, 60,
    34, 30, 73, 54, 45, 83, 182, 88, 75, 85, 54, 53, 89, 59, 37, 35, 38,
    29, 18, 45, 60, 49, 62, 55, 78, 96, 29, 22, 24, 13, 14, 11, 11, 18,
    12, 12, 30, 52, 52, 44, 28, 28, 20, 56, 40, 31, 50, 40, 46, 42, 29,
    19, 36, 25, 22, 17, 19, 26, 30, 20, 15, 21, 11, 8, 8, 19, 5, 8, 8,
    11, 11, 8, 3, 9, 5, 4, 7, 3, 6, 3, 5, 4, 5, 6
]

class EveryAyahConverter:
    def __init__(self, input_dir, output_dir):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.reference_dir = Path("everyayah_reference_48kbps")
        self.output_dir.mkdir(exist_ok=True)
        self.reference_dir.mkdir(exist_ok=True)

    def get_audio_duration(self, file_path):
        """Get duration of an audio file in seconds using ffprobe"""
        try:
            result = subprocess.run([
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'json',
                str(file_path)
            ], capture_output=True, text=True, check=True)

            data = json.loads(result.stdout)
            return float(data['format']['duration'])
        except Exception as e:
            print(f"Error getting duration for {file_path}: {e}")
            return None

    def download_reference_ayah(self, surah, ayah):
        """Download a single ayah from EveryAyah as timing reference"""
        filename = f"{surah:03d}{ayah:03d}.mp3"
        url = f"https://everyayah.com/data/Parhizgar_48kbps/{filename}"
        output_path = self.reference_dir / filename

        if output_path.exists():
            return output_path

        try:
            print(f"  Downloading reference: {filename}")
            urllib.request.urlretrieve(url, output_path)
            return output_path
        except Exception as e:
            print(f"  Error downloading {filename}: {e}")
            return None

    def get_ayah_timings_from_reference(self, surah):
        """Get timings for all ayahs in a surah from reference files"""
        ayah_count = AYAH_COUNTS[surah - 1]
        timings = []
        cumulative_time = 0

        print(f"\nGetting timing reference for Surah {surah} ({ayah_count} ayahs)...")

        for ayah in range(1, ayah_count + 1):
            ref_file = self.download_reference_ayah(surah, ayah)
            if ref_file:
                duration = self.get_audio_duration(ref_file)
                if duration:
                    timings.append({
                        'ayah': ayah,
                        'start': cumulative_time,
                        'duration': duration,
                        'end': cumulative_time + duration
                    })
                    cumulative_time += duration

        return timings

    def split_surah(self, surah):
        """Split a surah file into individual ayah files"""
        # Input file should be named 001.mp3, 002.mp3, etc.
        input_file = self.input_dir / f"{surah:03d}.mp3"

        if not input_file.exists():
            print(f"\n⚠️  Surah {surah} file not found: {input_file}")
            return False

        print(f"\n{'='*60}")
        print(f"Processing Surah {surah}: {input_file.name}")
        print(f"{'='*60}")

        # Get timing reference from 48kbps files
        timings = self.get_ayah_timings_from_reference(surah)

        if not timings:
            print(f"  ❌ Could not get timing reference for Surah {surah}")
            return False

        # Split the high-quality file using the timings
        print(f"\nSplitting {input_file.name} into {len(timings)} ayahs...")

        for timing in timings:
            ayah = timing['ayah']
            output_file = self.output_dir / f"{surah:03d}{ayah:03d}.mp3"

            # Use ffmpeg to extract the segment
            # -i: input file
            # -ss: start time
            # -t: duration
            # -c copy: copy codec (faster, no re-encoding)
            # If copy doesn't work due to keyframes, use -c:a libmp3lame -b:a 128k

            try:
                subprocess.run([
                    'ffmpeg', '-y',  # overwrite
                    '-i', str(input_file),
                    '-ss', str(timing['start']),
                    '-t', str(timing['duration']),
                    '-c', 'copy',  # Try copy first (faster)
                    str(output_file)
                ], capture_output=True, check=True)

                print(f"  ✅ Created: {output_file.name} ({timing['duration']:.2f}s)")

            except subprocess.CalledProcessError:
                # If copy fails, re-encode
                try:
                    subprocess.run([
                        'ffmpeg', '-y',
                        '-i', str(input_file),
                        '-ss', str(timing['start']),
                        '-t', str(timing['duration']),
                        '-c:a', 'libmp3lame',
                        '-b:a', '128k',
                        str(output_file)
                    ], capture_output=True, check=True)

                    print(f"  ✅ Created: {output_file.name} ({timing['duration']:.2f}s) [re-encoded]")

                except Exception as e:
                    print(f"  ❌ Failed to create {output_file.name}: {e}")

        return True

    def convert_all(self, start_surah=1, end_surah=114):
        """Convert all surahs from start_surah to end_surah"""
        print("\n" + "="*60)
        print("EveryAyah Format Converter")
        print("Converting high-quality Quran audio to verse-by-verse format")
        print("="*60)

        for surah in range(start_surah, end_surah + 1):
            self.split_surah(surah)

        print("\n" + "="*60)
        print("✅ Conversion Complete!")
        print(f"Output directory: {self.output_dir.absolute()}")
        print("="*60)


def check_ffmpeg():
    """Check if ffmpeg is available"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except:
        return False


def main():
    print("\nQuran Audio Converter - EveryAyah Format")
    print("-" * 60)

    # Check for ffmpeg
    if not check_ffmpeg():
        print("❌ ffmpeg not found!")
        print("\nPlease install ffmpeg:")
        print("1. Download from: https://www.gyan.dev/ffmpeg/builds/")
        print("2. Extract and add bin folder to PATH")
        print("3. Or place ffmpeg.exe in the same folder as this script")
        return

    print("✅ ffmpeg found")

    # Get input/output directories
    input_dir = input("\nEnter folder containing your surah files (001.mp3, 002.mp3, ...): ").strip()
    if not input_dir:
        input_dir = "input_surahs"

    output_dir = input("Enter output folder for EveryAyah files [Parhizgar_128kbps]: ").strip()
    if not output_dir:
        output_dir = "Parhizgar_128kbps"

    # Ask which surahs to convert
    print("\nWhich surahs do you want to convert?")
    print("1. All surahs (1-114)")
    print("2. Specific range")
    print("3. Single surah")

    choice = input("Choice [1]: ").strip() or "1"

    start_surah = 1
    end_surah = 114

    if choice == "2":
        start_surah = int(input("Start surah [1]: ") or "1")
        end_surah = int(input("End surah [114]: ") or "114")
    elif choice == "3":
        surah = int(input("Surah number: "))
        start_surah = end_surah = surah

    # Create converter and run
    converter = EveryAyahConverter(input_dir, output_dir)
    converter.convert_all(start_surah, end_surah)


if __name__ == "__main__":
    main()
