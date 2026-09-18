"""Non-blocking audio engine supporting Linux native audio pipelines."""

import os
import shutil
import subprocess
import time
import wave
import struct
import math
from pathlib import Path
from typing import Optional, Dict

CACHE_AUDIO_DIR = Path.home() / ".cache" / "buddy" / "sounds"


class SoundManager:
    """Manages audio effects with non-blocking playback, rate limiting, and volume."""

    def __init__(self, enabled: bool = True, volume: float = 0.7):
        self.enabled = enabled
        self.volume = max(0.0, min(1.0, volume))
        self.last_played: Dict[str, float] = {}
        self.cooldown = 0.25  # Minimum seconds between repeating same sound effect
        self.player_cmd = self._detect_player()
        self._ensure_synth_cache()

    def _detect_player(self) -> Optional[str]:
        """Find the preferred low-latency audio player on Linux."""
        for cmd in ["pw-play", "paplay", "aplay", "canberra-gtk-play"]:
            if shutil.which(cmd):
                return cmd
        return None

    def _ensure_synth_cache(self) -> None:
        """Synthesize basic wave sounds if custom sound files are absent."""
        try:
            CACHE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
            self._create_tone_if_missing("lightning.wav", freq_start=900, freq_end=150, duration=0.25, noise=True)
            self._create_tone_if_missing("smash.wav", freq_start=180, freq_end=40, duration=0.35, noise=True)
            self._create_tone_if_missing("fire.wav", freq_start=300, freq_end=200, duration=0.3, noise=True)
            self._create_tone_if_missing("bark.wav", freq_start=450, freq_end=220, duration=0.18, noise=False)
            self._create_tone_if_missing("purr.wav", freq_start=80, freq_end=120, duration=0.4, noise=False)
            self._create_tone_if_missing("magic.wav", freq_start=550, freq_end=880, duration=0.3, noise=False)
            self._create_tone_if_missing("jet.wav", freq_start=280, freq_end=340, duration=0.3, noise=True)
            self._create_tone_if_missing("teleport.wav", freq_start=300, freq_end=750, duration=0.22, noise=False)
            self._create_tone_if_missing("grapple.wav", freq_start=600, freq_end=350, duration=0.2, noise=False)
        except Exception as e:
            print(f"[Buddy Audio] Note: Could not create synthesized sound cache: {e}")

    def _create_tone_if_missing(
        self,
        filename: str,
        freq_start: float,
        freq_end: float,
        duration: float,
        noise: bool = False
    ) -> None:
        path = CACHE_AUDIO_DIR / filename
        if path.exists():
            return
        sample_rate = 22050
        n_samples = int(sample_rate * duration)
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            frames = bytearray()
            for i in range(n_samples):
                t = i / sample_rate
                progress = i / n_samples
                freq = freq_start + (freq_end - freq_start) * progress
                envelope = math.sin(math.pi * progress)  # Smooth fade-in & fade-out
                signal = math.sin(2 * math.pi * freq * t)
                if noise:
                    import random
                    signal = 0.7 * signal + 0.3 * (random.random() * 2 - 1)
                val = int(signal * envelope * 12000)
                frames.extend(struct.pack("<h", max(-32767, min(32767, val))))
            w.writeframes(frames)

    def play(self, sound_name: str, custom_path: Optional[str] = None) -> None:
        """Play a sound effect non-blockingly."""
        if not self.enabled or self.volume <= 0.01 or not self.player_cmd:
            return

        now = time.time()
        if sound_name in self.last_played and (now - self.last_played[sound_name]) < self.cooldown:
            return
        self.last_played[sound_name] = now

        sound_file = custom_path
        if not sound_file:
            candidate = CACHE_AUDIO_DIR / f"{sound_name}.wav"
            if candidate.exists():
                sound_file = str(candidate)

        if not sound_file or not os.path.exists(sound_file):
            return

        def _worker():
            try:
                cmd = [self.player_cmd, sound_file] if self.player_cmd != "canberra-gtk-play" else [self.player_cmd, "-f", sound_file]
                proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                proc.wait(timeout=2.0)
            except Exception:
                pass

        import threading
        threading.Thread(target=_worker, daemon=True).start()


audio_manager = SoundManager()
