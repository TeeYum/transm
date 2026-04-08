# Transm (Transmute AI)

**Open-source AI-powered remastering for Loudness War-era metal and rock.**

Transm separates crushed masters into individual stems using state-of-the-art AI models, applies genre-aware DSP processing to restore dynamics and reduce fatigue, and remixes them with proper headroom. Built for audiophiles who want their 2000s metalcore to sound less like it was mastered inside a trash compactor.

## Demo: Before / After

As I Lay Dying — "94 Hours" (10s clip, 0:30–0:40). Processed with the `2000s-metalcore` preset at intensity 0.7.

- [Original clip](docs/samples/aild_94hours_original_clip.wav) (heavily compressed, -12.5 LUFS)
- [Remastered clip](docs/samples/aild_94hours_transm_70_clip.wav) (restored dynamics, -14.0 LUFS, +4.4 dB crest factor)

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Crest Factor | 12.4 dB | 16.8 dB | **+4.4 dB** |
| Peak-to-Loudness Ratio | 8.3 dB | 13.2 dB | **+4.8 dB** |
| True Peak | -4.2 dBTP | -1.0 dBTP | -3.2 dB |
| Clipping | 0.00% | 0.00% | -- |

> Audio clips are short excerpts used for technical demonstration of audio processing. All rights belong to the original artists.

## Status

**Pre-alpha / Research Phase.** See the docs for the full architecture and feasibility assessment.

## Documentation

- [Architecture](docs/architecture.md) — Technical architecture, pipeline design, tech stack, and roadmap
- [Capture Component](docs/capture-component.md) — Lossless stream capture from Spotify, Apple Music, Tidal via system audio loopback
- [Feasibility Assessment](docs/feasibility-assessment.md) — Honest difficulty estimates, model fine-tuning feasibility, and adversarial analysis review
- [Agent Updates](agent-updates.md) — Changelog of all agent-authored changes

## Planned Stack

- **Separation**: `audio-separator` (Demucs, RoFormer, MDX-Net, ensemble)
- **DSP**: `pedalboard` + custom NumPy/SciPy (transient shaping, expansion, de-essing)
- **Analysis**: `pyloudnorm`, `librosa`
- **Mastering** (optional): `matchering`

## Contributing

This project uses a fork-based workflow. All development happens on the [chryst-monode fork](https://github.com/chryst-monode/transm) and is proposed to this repo via pull request. See [CLAUDE.md](CLAUDE.md) for agent-specific instructions.

All commits are co-created by [@TeeYum](https://github.com/TeeYum), [@chryst-monode](https://github.com/chryst-monode), and [Claude](https://claude.ai).

## License

GPL-3.0 (required by Pedalboard and Matchering dependencies)
