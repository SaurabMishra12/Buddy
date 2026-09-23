"""Native macOS audio backend using AppKit NSSound for low-latency, zero-fork playback."""

import os
import queue
import time
import wave
import struct
import math
import random
import threading
from pathlib import Path
from typing import Optional, Dict

import AppKit
from platforms.base import PlatformAudio

CACHE_AUDIO_DIR = Path.home() / "Library" / "Caches" / "Buddy" / "sounds"


class AudioPriority(int):
    UI = 100
    ULTIMATE = 90
    INTERACTION = 80
    ABILITY = 60
    AMBIENT = 20


class DummyAudio(PlatformAudio):
    """Null audio implementation for mute mode, headless tests, and preview canvases."""
    def __init__(self):
        self.enabled = False
        self.volume = 0.0

    def play(self, sound_name: str, custom_path: Optional[str] = None, priority: int = 0) -> None:
        pass

    def set_volume(self, volume: float) -> None:
        pass


class MacOSSoundManager(PlatformAudio):
    """Manages audio effects using native AppKit NSSound with priority channels, category volume, and rate limiting."""

    def __init__(self, enabled: bool = True, volume: float = 0.7):
        self.enabled = enabled
        self.volume = max(0.0, min(1.0, volume))
        self.sfx_volume: float = 1.0
        self.ability_volume: float = 1.0
        self.ambient_volume: float = 0.6
        self.low_power_mode: bool = False
        self.last_played: Dict[str, float] = {}
        self.cooldown = 0.20  # Minimum seconds between repeating same sound effect
        self._sound_cache: Dict[str, AppKit.NSSound] = {}
        self._cache_limit = 48
        self._audio_queue: queue.Queue = queue.Queue(maxsize=16)
        self._current_priority: int = 0
        self._priority_expiry: float = 0.0
        self._init_worker_thread()
        # Ensure synthesized cache in background so engine startup is instant
        threading.Thread(target=self._ensure_synth_cache, daemon=True).start()

    def set_volume(self, volume: float) -> None:
        self.volume = max(0.0, min(1.0, float(volume)))

    def set_sfx_volume(self, val: float) -> None:
        self.sfx_volume = max(0.0, min(1.0, float(val)))

    def set_ability_volume(self, val: float) -> None:
        self.ability_volume = max(0.0, min(1.0, float(val)))

    def set_low_power_mode(self, active: bool) -> None:
        self.low_power_mode = bool(active)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def _init_worker_thread(self) -> None:
        """Starts background audio worker thread for non-blocking operations."""
        def _audio_loop():
            while True:
                item = self._audio_queue.get()
                if item is None:
                    break
                try:
                    name, path, vol = item
                    self._play_direct(name, path, vol)
                except Exception:
                    pass
                finally:
                    self._audio_queue.task_done()

        t = threading.Thread(target=_audio_loop, daemon=True)
        t.start()

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
            self._create_tone_if_missing("thwip.wav", freq_start=1400, freq_end=320, duration=0.15, noise=True)
            self._create_tone_if_missing("web.wav", freq_start=850, freq_end=220, duration=0.18, noise=False)
            self._create_tone_if_missing("laser.wav", freq_start=1200, freq_end=600, duration=0.20, noise=False)
            self._create_tone_if_missing("roar.wav", freq_start=120, freq_end=60, duration=0.45, noise=True)
            self._create_tone_if_missing("swoosh.wav", freq_start=400, freq_end=100, duration=0.22, noise=True)
            self._create_tone_if_missing("charge.wav", freq_start=200, freq_end=650, duration=0.4, noise=False)
            self._create_tone_if_missing("slash.wav", freq_start=600, freq_end=120, duration=0.2, noise=True)
            self._create_tone_if_missing("shunpo.wav", freq_start=700, freq_end=300, duration=0.15, noise=True)
            self._create_tone_if_missing("bankai.wav", freq_start=140, freq_end=480, duration=0.6, noise=True)
            self._create_tone_if_missing("chire.wav", freq_start=800, freq_end=1200, duration=0.35, noise=False)
            self._create_tone_if_missing("cero.wav", freq_start=250, freq_end=80, duration=0.5, noise=True)
            self._create_tone_if_missing("ice.wav", freq_start=1100, freq_end=400, duration=0.25, noise=False)
        except Exception as e:
            print(f"[Buddy Audio macOS] Note: Could not create synthesized sound cache: {e}")

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
                envelope = math.sin(math.pi * progress)
                signal = math.sin(2 * math.pi * freq * t)
                if noise:
                    signal = 0.7 * signal + 0.3 * (random.random() * 2 - 1)
                val = int(signal * envelope * 12000)
                frames.extend(struct.pack("<h", max(-32767, min(32767, val))))
            w.writeframes(frames)

    def play(self, sound_name: str, custom_path: Optional[str] = None, priority: int = AudioPriority.ABILITY) -> None:
        """Play a sound effect non-blockingly via AppKit NSSound queued to background worker."""
        if not self.enabled or self.volume <= 0.01:
            return

        now = time.time()
        # Suppress lower priority if higher priority is still playing
        if now < self._priority_expiry and priority < self._current_priority:
            return

        if sound_name in self.last_played and (now - self.last_played[sound_name]) < self.cooldown:
            return
        self.last_played[sound_name] = now

        self._current_priority = priority
        self._priority_expiry = now + 0.35

        try:
            self._audio_queue.put_nowait((sound_name, custom_path, self.volume))
        except queue.Full:
            pass

    def _play_direct(self, sound_name: str, custom_path: Optional[str] = None, vol: Optional[float] = None) -> None:
        play_volume = vol if vol is not None else self.volume
        if not self.enabled or play_volume <= 0.01:
            return

        sound_file = custom_path
        if not sound_file:
            candidate = CACHE_AUDIO_DIR / f"{sound_name}.wav"
            if candidate.exists():
                sound_file = str(candidate)

        if not sound_file or not os.path.exists(sound_file):
            return

        try:
            # Check sound cache
            sound = self._sound_cache.get(sound_file)
            if not sound:
                sound = AppKit.NSSound.alloc().initWithContentsOfFile_byReference_(sound_file, True)
                if sound:
                    if len(self._sound_cache) >= self._cache_limit:
                        self._sound_cache.pop(next(iter(self._sound_cache)))
                    self._sound_cache[sound_file] = sound

            if sound:
                sound.setVolume_(play_volume)
                if sound.isPlaying():
                    sound.stop()
                sound.play()
        except Exception:
            # Fallback to afplay command if NSSound throws
            try:
                import subprocess
                subprocess.Popen(
                    ["afplay", "-v", str(play_volume), sound_file],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except Exception:
                pass


SoundManager = MacOSSoundManager
audio_manager = MacOSSoundManager()
dummy_audio = DummyAudio()

