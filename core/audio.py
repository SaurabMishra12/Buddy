"""Audio engine platform dispatcher for Buddy."""

from platforms import is_macos

if is_macos():
    from platforms.macos.audio import MacOSSoundManager as SoundManager, audio_manager, CACHE_AUDIO_DIR
else:
    from platforms.linux.audio import SoundManager, audio_manager, CACHE_AUDIO_DIR

__all__ = ["SoundManager", "audio_manager", "CACHE_AUDIO_DIR"]
