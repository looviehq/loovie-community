"""LoovieVideoSettings contract: size/frame outputs and the silent-render rule."""

from __future__ import annotations

from comfyui_loovie.nodes.loovie_video_settings import LoovieVideoSettings


def _process(*, with_audio: bool, audio_frames: int = 50):
    return LoovieVideoSettings().process(
        width=960,
        height=544,
        num_frames=49,
        fps=24,
        audio_frames=audio_frames,
        audio_fps=25,
        with_audio=with_audio,
        seed=42,
    )


def test_audio_frames_are_emitted_even_when_audio_is_disabled() -> None:
    out = _process(with_audio=False)
    # LTX 2.5 concatenates the video and audio latents before sampling, so a
    # zero-length audio latent fails the sampler. The gate drops the track
    # after decode instead.
    assert out[4] == 50
    assert out[6] is False


def test_audio_enabled_keeps_the_same_budget() -> None:
    out = _process(with_audio=True)
    assert out[4] == 50
    assert out[6] is True


def test_seed_is_resolved_when_random() -> None:
    out = _process(with_audio=True)
    assert out[7] == 42
