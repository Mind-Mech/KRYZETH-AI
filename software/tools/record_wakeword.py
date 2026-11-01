import os
import time
import sounddevice as sd
from scipy.io.wavfile import write

# ----------------------------
# Settings
# ----------------------------

SAMPLE_RATE = 16000
DURATION = 1.5          # seconds
PAUSE = 0.5             # seconds between recordings
TOTAL = 100

OUTPUT_DIR = "wakeword_data/negative"

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 50)
print("KRYZETH Wake Word Recorder")
print("=" * 50)
print()
print(f"Output folder : {OUTPUT_DIR}")
print(f"Recordings    : {TOTAL}")
print(f"Duration      : {DURATION} sec")
print()

input("Press ENTER when you're ready...")

print()

for i in range(1, TOTAL + 1):

    print(f"[{i}/{TOTAL}]")
    print("Say anything EXCEPT KRYZETH")

    time.sleep(1)

    audio = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16"
    )

    sd.wait()

    filename = os.path.join(
        OUTPUT_DIR,
        f"{i:03d}.wav"
    )

    write(filename, SAMPLE_RATE, audio)

    print(f"Saved -> {filename}\n")

    time.sleep(PAUSE)

print("=" * 50)
print("Finished!")
print("=" * 50)