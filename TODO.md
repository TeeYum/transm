# Transm — Quality Improvement Roadmap

> The next quality gains should come from improving separation quality first,
> then adding model-based stem restoration, then eventually training a
> metalcore-specific restoration model. Do NOT jump straight to generative
> "remastering" unless the QA harness proves the current DSP pipeline is the
> bottleneck.

## Priority 1: Better Separation

Transm's biggest quality bottleneck is likely still stem separation. If the drum, guitar, and cymbal stems are contaminated, every downstream DSP move amplifies artifacts.

### Next steps

- Add audio-separator backend selection beyond just demucs and one RoFormer checkpoint.
- Benchmark Demucs vs BS-RoFormer vs Mel-Band RoFormer vs MDX/MDXC on the QA fixture set.
- Add ensemble mode: combine multiple separators and pick/merge the best stem estimates.
- Add a "separation confidence" score before DSP intensity is chosen.
- Use conservative DSP automatically when stem bleed/artifacts are high.

### Relevant model families

- **HTDemucs / Demucs v4**: good baseline.
- **BS-RoFormer / BandSplit-RoFormer**: likely better for modern source separation.
- **Mel-Band RoFormer**: promising for better per-band handling.
- **MDX23 / MDXC**: useful as ensemble members.
- **SCNet / ZFTurbo MSS training repo models**: worth benchmarking if available through audio-separator or separately.

### Why this matters

The 2026 Music Source Restoration Challenge systems that performed well leaned heavily on RoFormer/BSRNN/MDX-style separation and ensembling. The winning and second-place systems used sequential/ensemble separation plus restoration, not just simple DSP.

### Sources

- MSR Challenge results: https://msrchallenge.com/
- MSR overview paper: https://papers.cool/arxiv/2601.04343
- CUPAudioGroup system: https://papers.cool/arxiv/2603.16926
- CP-JKU system: https://papers.cool/arxiv/2603.04032

---

## Priority 2: Add Model-Based Stem Restoration

After separation, Transm currently uses mostly DSP. The next model-based upgrade would be to run a restoration model per stem, especially on bass/guitars/vocals.

### Candidate directions

- **BSRNN/BS-RoFormer restoration models**: align with the MSR Challenge second-place approach — separation first, targeted reconstruction second.
- **HiFi++ GAN-style waveform restorers**: CP-JKU used HiFi++ GAN experts after BandSplit-RoFormer separation.
- **U-Former / Music Source Restoration baselines**: research direction for undoing production degradations like EQ, compression, distortion, reverb, and lossy codecs.
- **Instrument-specific restorers**: separate models or configs for drums, bass, guitars, vocals rather than one general model.

### Caveat

Drums/percussion are hard. The MSR overview reports percussion restoration averaged only ~0.29 dB improvement across teams, while bass averaged much higher. Start with bass/guitar/vocal restoration before promising snare transient reconstruction.

---

## Priority 3: Super-Resolution / Lossy Repair As Optional Toggles

These are useful only for bad sources, not as a default "make everything better" stage.

### Options

- **AudioSR**: diffusion-based audio super-resolution to 48 kHz / 24 kHz bandwidth. Use only when the input is bandwidth-limited or visibly low-pass damaged. It can hallucinate high frequencies, which may make cymbals worse.
  - Paper/project: https://audioldm.github.io/audiosr/
  - GitHub: https://github.com/haoheliu/versatile_audio_super_resolution

- **Apollo**: GAN/band-sequence audio restoration aimed at lossy-to-higher-quality music repair. Interesting for MP3/AAC-damaged sources, but should remain experimental until validated against metalcore fixtures.
  - Paper: https://huggingface.co/papers/2409.08514
  - GitHub: https://github.com/JusperLee/Apollo

---

## Priority 4: Train A Metalcore-Specific Restoration Model

This is the "real product moat," but it is NOT the next immediate step.

### Practical training setup

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

### Model directions

- Fine-tune BandSplit-RoFormer / Mel-Band RoFormer for metalcore separation.
- Train BSRNN-style stem restoration for bass/guitar/vocals.
- Explore HiFi++ GAN-style waveform restoration for post-separation cleanup.
- Track SonicMaster-style all-in-one restoration/mastering research, but treat it as research-grade unless code/weights are production-ready.
  - SonicMaster: https://huggingface.co/papers/2508.03448

---

## Recommended Roadmap

1. **Now**: Build separator benchmarking inside QA.
2. **Next**: Add separator ensemble mode and confidence-based DSP intensity.
3. **Then**: Add optional AudioSR/Apollo-style source repair toggles for lossy/bandwidth-limited inputs only.
4. **Then**: Prototype stem restoration on bass and guitars using MSR-inspired models.
5. **Later**: Fine-tune/train a metalcore-specific separator/restorer.

> **The pragmatic thesis**: Transm gets better fastest by becoming separation-aware
> and artifact-aware, not by adding a black-box generative remastering model too early.
