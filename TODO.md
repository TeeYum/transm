# TODO

## Tuning Rationale

### Why `0.7` Seems Better Than `0.35`

- The current `2000s-metalcore` preset still declares `intensity = 0.35` as the default, but the public demo in `README.md` uses `0.7`.
- This likely sounds better because the current intensity system scales only gain-like fields, not the full behavior of the processing chains.
- In `src/transm/preset_loader.py`, only selected gain/boost parameters are multiplied by intensity. Thresholds, ratios, Q values, frequencies, and most detector behavior remain fixed.
- In practice, `0.35` makes many audible moves too small for a dense metalcore mix:
  - Drum transient attack becomes `+1.575 dB` instead of `+3.15 dB` at `0.7`.
  - Drum cymbal taming becomes only `-1.05 dB` instead of `-2.1 dB`.
  - Bass harmonic boost becomes only `+0.7 dB` instead of `+1.4 dB`.
  - Guitar mid boost becomes only `+0.7 dB` instead of `+1.4 dB`.
  - Vocal tuck becomes only `-0.525 dB` instead of `-1.05 dB`.
- Those sub-1 dB moves are often too polite once separation artifacts, cymbal wash, and dense guitars are in play.
- Meanwhile, expansion, de-essing, and compression behavior are mostly fixed, so low intensity does not produce a proportionally gentle version of the whole preset. It mostly produces weak EQ/transient moves on top of fixed dynamics logic.

### Concrete Evidence From Current Demo

- The current demo clip `docs/samples/aild_94hours_transm_70_clip.wav` shows meaningful metric shifts relative to the original:
  - LUFS: about `-12.6` to `-14.3`
  - PLR: about `8.2 dB` to `13.2 dB`
  - Crest factor: about `11.8 dB` to `16.2 dB`
  - True peak: about `-4.45 dBTP` to `-1.03 dBTP`
- That suggests `0.7` is not just louder or brighter; it is creating a materially stronger dynamic/tone correction than the nominal default.

## Tuning Recommendations

### 1. Raise The Effective Default

- Consider changing the metalcore preset default from `0.35` to `0.6` or `0.65`.
- If listening tests continue to prefer `0.7`, make `0.7` the default for `2000s-metalcore`.
- Keep a lower-intensity option available as an explicit conservative mode, not the default.

### 2. Change Intensity Scaling

- The current scaling is linear: `scaled_value = base_value * intensity`.
- That makes low settings too weak.
- Try a non-linear scaling rule instead, for example:
  - `scaled_value = base_value * sqrt(intensity)`
  - or `scaled_value = base_value * (0.25 + 0.75 * intensity)`
- Goal: low settings should still sound like a meaningful preset, not like a barely-on version.

### 3. Scale More Than Gain Fields

- Right now the most audible behavior is often controlled by values that do not change with intensity.
- Candidates to tie to intensity:
  - Drum expander threshold and ratio.
  - Vocal expander threshold and ratio.
  - Bass compressor threshold.
  - De-esser threshold and ratio.
  - Guitar stereo width target.
- Without this, intensity mostly behaves like "EQ amount" rather than "preset strength."

### 4. Retune Base Preset Values Upward Slightly

- The current metalcore base values are still fairly conservative.
- Likely candidates for stronger defaults:
  - Drums transient attack: from `4.5 dB` toward `5.5-6.0 dB`.
  - Drum cymbal cut: slightly more than `-3 dB` for harsh sources.
  - Vocals level tuck: from `-1.5 dB` toward `-2.0` or `-2.5 dB`.
  - Guitar mid boost: more than `+2 dB` may be needed for scooped-era tones.
  - Stereo width target: `1.3` may be worth testing instead of `1.2`.

### 5. Split Intensity Into Macro Knobs

- A single global intensity knob is too blunt.
- Consider replacing or supplementing it with:
  - `dynamics`
  - `cymbal_tame`
  - `bass_recovery`
  - `vocal_tuck`
  - `guitar_body`
- This will likely make tuning faster and user results more predictable.

### 6. Add Source- And Stem-Aware Auto-Tuning

- If stem QA is poor, cap intensity automatically.
- If spectral tilt is already bright, increase cymbal taming and reduce presence boosts.
- If PLR is already decent, reduce expansion/transient emphasis.
- If the vocal stem is contaminated, reduce vocal presence and level moves.

### 7. Sweep Intensity Systematically

- Run listening and metric sweeps across:
  - `0.2`
  - `0.35`
  - `0.5`
  - `0.65`
  - `0.7`
  - `0.8`
- Score each on:
  - punch
  - cymbal fatigue
  - guitar body
  - bass clarity
  - artifact level
  - full-song listenability
- Expectation: preference likely rises sharply around `0.5-0.6`, which would explain why `0.7` feels like the first setting that is truly doing enough.

---

## Quality Improvement Roadmap

> The next quality gains should come from improving separation quality first,
> then adding model-based stem restoration, then eventually training a
> metalcore-specific restoration model. Do NOT jump straight to generative
> "remastering" unless the QA harness proves the current DSP pipeline is the
> bottleneck.

### Priority 1: Better Separation

Transm's biggest quality bottleneck is likely still stem separation. If the drum, guitar, and cymbal stems are contaminated, every downstream DSP move amplifies artifacts.

**Next steps:**
- Add audio-separator backend selection beyond just demucs and one RoFormer checkpoint.
- Benchmark Demucs vs BS-RoFormer vs Mel-Band RoFormer vs MDX/MDXC on the QA fixture set.
- Add ensemble mode: combine multiple separators and pick/merge the best stem estimates.
- Add a "separation confidence" score before DSP intensity is chosen.
- Use conservative DSP automatically when stem bleed/artifacts are high.

**Relevant model families:**
- **HTDemucs / Demucs v4**: good baseline.
- **BS-RoFormer / BandSplit-RoFormer**: likely better for modern source separation.
- **Mel-Band RoFormer**: promising for better per-band handling.
- **MDX23 / MDXC**: useful as ensemble members.
- **SCNet / ZFTurbo MSS training repo models**: worth benchmarking if available through audio-separator or separately.

**Why this matters:** The 2026 Music Source Restoration Challenge systems that performed well leaned heavily on RoFormer/BSRNN/MDX-style separation and ensembling. The winning and second-place systems used sequential/ensemble separation plus restoration, not just simple DSP.

**Sources:**
- MSR Challenge results: https://msrchallenge.com/
- MSR overview paper: https://papers.cool/arxiv/2601.04343
- CUPAudioGroup system: https://papers.cool/arxiv/2603.16926
- CP-JKU system: https://papers.cool/arxiv/2603.04032

### Priority 2: Add Model-Based Stem Restoration

After separation, Transm currently uses mostly DSP. The next model-based upgrade would be to run a restoration model per stem, especially on bass/guitars/vocals.

**Candidate directions:**
- **BSRNN/BS-RoFormer restoration models**: align with the MSR Challenge second-place approach — separation first, targeted reconstruction second.
- **HiFi++ GAN-style waveform restorers**: CP-JKU used HiFi++ GAN experts after BandSplit-RoFormer separation.
- **U-Former / Music Source Restoration baselines**: research direction for undoing production degradations like EQ, compression, distortion, reverb, and lossy codecs.
- **Instrument-specific restorers**: separate models or configs for drums, bass, guitars, vocals rather than one general model.

**Caveat:** Drums/percussion are hard. The MSR overview reports percussion restoration averaged only ~0.29 dB improvement across teams, while bass averaged much higher. Start with bass/guitar/vocal restoration before promising snare transient reconstruction.

### Priority 3: Super-Resolution / Lossy Repair As Optional Toggles

These are useful only for bad sources, not as a default "make everything better" stage.

**Options:**
- **AudioSR**: diffusion-based audio super-resolution to 48 kHz / 24 kHz bandwidth. Use only when the input is bandwidth-limited or visibly low-pass damaged. It can hallucinate high frequencies, which may make cymbals worse.
  - Paper/project: https://audioldm.github.io/audiosr/
  - GitHub: https://github.com/haoheliu/versatile_audio_super_resolution

- **Apollo**: GAN/band-sequence audio restoration aimed at lossy-to-higher-quality music repair. Interesting for MP3/AAC-damaged sources, but should remain experimental until validated against metalcore fixtures.
  - Paper: https://huggingface.co/papers/2409.08514
  - GitHub: https://github.com/JusperLee/Apollo

### Priority 4: Train A Metalcore-Specific Restoration Model

This is the "real product moat," but it is NOT the next immediate step.

**Practical training setup:**
1. Collect clean/open multitrack stems where licensing permits.
2. Build degradation pipelines that mimic early-2000s metalcore mastering:
   - brickwall limiting
   - clipping
   - high-frequency cymbal harshness
   - low-mid mud
   - codec artifacts
   - over-compression
3. Train on paired clean/degraded stems.
4. Start with one target, probably bass or guitars, not full-mix mastering.
5. Evaluate with Transm QA: blind listening, PLR/LUFS, artifact scores, and stem-specific metrics.

**Model directions:**
- Fine-tune BandSplit-RoFormer / Mel-Band RoFormer for metalcore separation.
- Train BSRNN-style stem restoration for bass/guitar/vocals.
- Explore HiFi++ GAN-style waveform restoration for post-separation cleanup.
- Track SonicMaster-style all-in-one restoration/mastering research, but treat it as research-grade unless code/weights are production-ready.
  - SonicMaster: https://huggingface.co/papers/2508.03448

---

## Recommended Roadmap

1. **Now**: Preset tuning and fixture-based listening evaluation (highest ROI).
2. **Next**: Build separator benchmarking inside QA.
3. **Then**: Add separator ensemble mode and confidence-based DSP intensity.
4. **Then**: Add optional AudioSR/Apollo-style source repair toggles for lossy/bandwidth-limited inputs only.
5. **Later**: Prototype stem restoration on bass and guitars using MSR-inspired models.
6. **Eventually**: Fine-tune/train a metalcore-specific separator/restorer.

> **The pragmatic thesis**: Transm gets better fastest by becoming separation-aware
> and artifact-aware, not by adding a black-box generative remastering model too early.

---

## Project State Assessment

- Transm is past the architecture-only stage and is now a real prototype with:
  - working CLI
  - measurable before/after analysis
  - tests for most DSP components
  - a coherent preset-driven processing model
- The project is strongest where it is pragmatic:
  - per-stem DSP
  - conservative limiter behavior
  - honest QA posture
  - explicit separation dependency handling
- The main weakness is not code structure; it is tuning maturity:
  - only one public demo clip
  - one preset with an underpowered default intensity
  - limited evidence across multiple albums/subgenres
  - current intensity abstraction is too simple for the behavior it is meant to control
- The next highest-ROI work is preset tuning and fixture-based listening evaluation, not more product surface area.
