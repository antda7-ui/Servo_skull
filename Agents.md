Overview

Building an AI-powered servo skull in the style of Warhammer 40k — a small autonomous machine spirit that speaks in character and, eventually, will be mounted in a 3D-printed physical shell with a camera and a mechadendrite robotic arm capable of identifying and picking up objects.

This is a personal hobby/portfolio project, built incrementally in phases. Current phase: Phase 1 — bare-bones voice chatbot only. No camera, no arm, no LEDs, no physical shell yet.

Hardware & environment constraints
Compute: tethered to an existing desktop over cable — no onboard/embedded compute board (explicitly ruled out buying a Jetson).
Desktop specs: AMD FX-8350 CPU, 8GB RAM, AMD Radeon R9 380 GPU.
No CUDA / no usable GPU acceleration. The R9 380 is unsupported by current ROCm — everything must run CPU-only. Do not suggest CUDA-only libraries or assume GPU acceleration is available.
OS: Linux Mint 22.
Input for this phase: USB mic (repurposed from an old USB camera/mic).
Power: tethered/wired, not battery powered.
Cost constraint

No recurring/paid cloud AI API costs. Everything in the audio pipeline must run locally and be free to use indefinitely. Do not suggest paid APIs (OpenAI, Anthropic API, ElevenLabs, etc.) as the primary path — local, open-source, self-hosted tools only for the core pipeline.

Architecture (Phase 1)

Push-to-talk (currently: press Enter to start/stop, not a physical button yet) → record mic audio → local speech-to-text → local LLM (in-character response) → local text-to-speech → audio effects for a gritty mechanical voice → playback.

Tools in use:

STT: whisper.cpp, running fully local/CPU
LLM: Ollama, running Llama 3.2 3B Instruct locally
TTS: Piper, using the en_GB-alan-medium voice as the base
Audio grit effects: sox (bitcrush/overdrive/ring-mod style processing layered on top of Piper's clean output)
Recording/playback: arecord / aplay
Persona rules (critical — apply to all LLM-facing prompt work)

The servo skull is a machine spirit bonded in service to the user (its "Tech-Marine"). Character requirements:

Formal, deferential, but economical — not verbose (1-4 sentences per response in almost all cases).
Treats routine tasks (search, questions, calculations) as small rites of service to the Omnissiah, without being flowery about it.
Must never repeat stock phrases, catchphrases, or canned flavor text across turns. Every response should be freshly generated in-character, not pulled from a fixed phrase list. This is a hard requirement — do not suggest implementations that rely on a canned phrase bank.
No stage directions or action text (no "whirs").
Planned build order
Phase 1 (current): chat-only voice loop — push-to-talk, STT, local LLM with persona, TTS, grit effects, playback. No vision, no movement.
Phase 2: add a camera + object detection (identify objects only, no arm interaction yet).
Phase 3: static robotic arm control — command arm to fixed/known poses, no vision feedback yet.
Phase 4: closed-loop pick-and-place — combine vision + arm for a constrained task (known object, fixed lighting/surface).
Phase 5: generalize object handling and tie arm/vision actions into the LLM as tool calls (e.g. "pick up the wrench" becomes an agent action), plus web search as a tool for general queries.
Later / not yet started: physical shell design/3D printing, LEDs, any onboard movement — mechanical design is being handled separately by the project owner (a mechanical engineer) and isn't a software task yet.
Dev tooling
Editor: VS Code with GitHub Copilot (free tier).
Repo: Servo_skull on GitHub, cloned locally.
Python virtual environment used for all pip installs (system Python is externally managed on Mint — do not suggest pip install without a venv or --break-system-packages).

Implementation plan

The immediate goal is a reliable Phase 1 command-line voice loop. Keep each external tool behind a small Python adapter so that individual stages can be tested without recording or speaking, and keep the first implementation simple enough to diagnose on the older CPU.

1. Establish the project skeleton and local runtime
	- Confirm the repository's current files and create a Python package, test package, configuration file, and documentation for local setup.
	- Create and document the required virtual environment workflow.
	- Add a configuration layer for executable paths, model paths, audio device, sample rate, channels, recording limits, Ollama model name, Piper voice, and effect settings. Do not hard-code machine-specific paths in the application.
	- Add a startup diagnostics command that checks Python dependencies, `whisper.cpp`, Ollama, Piper, SoX, `arecord`, and `aplay`, and reports actionable failures without making network or paid-service calls.

2. Validate the audio device and recording boundary
	- Enumerate or configure the USB microphone and verify that `arecord` can capture a short WAV file in the format expected by STT.
	- Implement push-to-talk using Enter to begin and end capture, with Ctrl-C and recording-duration limits handled cleanly.
	- Add a playback check using `aplay` and retain an optional debug mode that keeps intermediate WAV files.
	- Test silence, an empty recording, and an unavailable device so the loop can return to an idle state instead of crashing.

3. Implement the local speech-to-text adapter
	- Wrap the selected `whisper.cpp` executable and model with `subprocess` using argument lists, explicit timeouts, and captured stderr.
	- Normalize the transcription result into plain text and treat empty or failed transcription as a recoverable turn failure.
	- Add a fixture-based test using a known WAV or mocked process result so tests do not require the microphone or a Whisper model.

4. Implement the persona-constrained LLM adapter
	- Wrap the local Ollama interface and make the model configurable, defaulting to Llama 3.2 3B Instruct.
	- Define a system prompt that enforces the servo skull's formal, deferential, economical voice, 1-4 sentence default length, fresh wording, and no stage directions.
	- Send only the necessary conversation context, enforce a response timeout, and normalize unexpected model output before TTS.
	- Add prompt-contract tests for sentence-length guidance, forbidden stage directions, and the absence of canned phrase logic. Use a mocked Ollama response in unit tests.

5. Implement Piper speech synthesis and audio effects
	- Wrap Piper with a configurable voice and output format, writing temporary files safely and reporting synthesis errors.
	- Build the SoX effect chain as configuration rather than shell text, then tune it against several Piper samples for intelligibility and mechanical grit.
	- Add a clean-output mode and an effects-enabled mode so TTS can be tested independently from audio processing.

6. Compose the end-to-end voice loop
	- Connect push-to-talk, recording, STT, LLM, TTS, effects, and playback in that order with clear per-stage status output.
	- Keep failures isolated to the current turn; make it possible to retry without restarting the application.
	- Add graceful shutdown, temporary-file cleanup, logging, and a debug option for preserving artifacts.
	- Ensure no API key, cloud endpoint, CUDA dependency, or recurring service is introduced anywhere in the core path.

7. Test and tune on the target machine
	- Add unit tests for configuration, command construction, response cleanup, failure handling, and persona rules.
	- Add an opt-in hardware/integration test command for microphone capture, local model calls, synthesis, effects, and playback; keep it separate from the default test suite.
	- Measure latency and CPU/memory use for short and long turns, then choose practical recording and timeout defaults for the FX-8350 and 8GB RAM system.
	- Test noisy input, silence, long speech, Ollama being unavailable, and missing model files.

8. Define the Phase 1 completion gate and next handoff
	- Document the exact install, diagnostics, run, debug, and test commands.
	- Mark Phase 1 complete only when repeated push-to-talk turns work locally, failures recover cleanly, output remains intelligible after effects, and the persona rules are consistently met.
	- Record the chosen interfaces and measurements needed to begin Phase 2 object identification without coupling vision code into the Phase 1 loop.

Project decisions

- Whisper.cpp has been cloned and built, but no model has been selected or installed yet. Start by evaluating `base.en` as the initial CPU-oriented model; keep the model path configurable so `small.en` or another model can be tested later if accuracy is insufficient.
- Use Ollama's local HTTP API, with the model name configurable and defaulting to `llama3.2:3b-instruct`.
- Use a conventional Python CLI entry point with `pytest` for the default automated test suite.
- Preserve conversation history between turns in memory, bounded by a configurable turn count or context budget. If the local model becomes slow or exceeds available memory, reduce the retained history or use a rolling summary as a free, local workaround.
- Do not retain recorded audio or transcripts by default. Debug mode may preserve temporary artifacts only when explicitly enabled.
- Use the ALSA default microphone for now; keep the device setting configurable for later troubleshooting.
- Tune SoX effects first for speech intelligibility and low latency. A harsher mechanical character can be added after the clean voice path is reliable.

Current status

- The repository was cloned to `/home/anthony/whisper.cpp` and is on a clean `master` worktree.
- The `base.en` model is installed at `/home/anthony/whisper.cpp/models/ggml-base.en.bin` and is approximately 141 MB.
- CMake is installed and whisper.cpp has been built successfully from `/home/anthony/whisper.cpp`.
- The CLI is available at `/home/anthony/whisper.cpp/build/bin/whisper-cli` and is using CPU-only execution as expected.
- A smoke test using `samples/jfk.wav` completed successfully: the 11-second sample was transcribed correctly in approximately 3.97 seconds with four CPU threads.
- The smoke test used approximately 285 MB peak resident memory and 374% CPU utilization, providing an initial performance baseline for the target machine.
- A Python virtual environment was created at `/home/anthony/Documents/Servo_skull/.venv` with the package installed in editable mode and pytest available.
- The initial Python package, configuration layer, pytest skeleton, and Whisper subprocess adapter are implemented and covered by six passing tests.
- The adapter smoke test successfully transcribed `samples/jfk.wav` through Python in approximately 4.41 seconds with approximately 284 MB peak resident memory.
- `arecord`, `aplay`, and SoX are installed. ALSA exposes the default route through PipeWire and the onboard ALC892 capture devices; the USB microphone still needs a short recording check.
- The ALSA audio adapter and diagnostic command are implemented, covered by four additional tests, and exposed as `servo-skull-audio-check`.
- The real 3-second ALSA diagnostic passed: it captured a 96,044-byte 16 kHz mono WAV through the default device and played it successfully.
- The Enter-key push-to-talk recorder is implemented as `servo-skull-record`, with graceful SIGINT stopping, Ctrl-C cancellation, maximum-duration enforcement, and empty-recording rejection.
- Push-to-talk behavior is covered by six additional tests, including timeout enforcement and stale-output rejection. A non-interactive start/stop smoke test reached the expected empty-recording guard when no speech was supplied.
- A code review found and fixed potential `arecord` pipe deadlocks, ineffective timeout enforcement while waiting for Enter, hardcoded user paths, incomplete audio environment configuration, and weak WAV frame validation.
- The full test suite passes with 16 tests. The Python Whisper adapter and real ALSA diagnostic still pass after the review fixes.
- The Ollama HTTP adapter is implemented with a configurable endpoint/model, bounded in-memory history, typed connection/response errors, persona prompting, and spoken-output normalization.
- Ollama is installed at version `0.32.14`, its local HTTP daemon is reachable, and the installed model `llama3.2:3b` produced a successful live in-character response through the adapter.
- The configured default remains `llama3.2:3b-instruct` per the project decision, but that exact tag is not currently installed; use `SERVO_SKULL_OLLAMA_MODEL=llama3.2:3b` or install the selected tag for live use.
- The full test suite passes with 22 tests, including six Ollama adapter and persona-contract tests.
- Piper is available at `/home/anthony/servo-skull-venv/bin/piper`, the `en_GB-alan-medium` voice is installed at `/home/anthony/en_GB-alan-medium.onnx`, and SoX is installed.
- The Piper speech synthesis and SoX effects adapters are implemented with configurable executable, voice, timeout, and structured effect settings.
- Clean-output and effects-enabled paths are independently testable. A live synthesis check produced a 180,268-byte clean WAV and a 181,238-byte processed WAV.
- The full test suite passes with 28 tests, including six Piper/SoX adapter tests.
- The retryable end-to-end voice loop is implemented in `servo_skull/loop.py` with explicit stage status, per-turn temporary cleanup, debug artifact retention, clean-voice mode, and failure isolation in the CLI.
- The `servo-skull` command is available with `--debug`, `--clean-voice`, and `--debug-directory` options.
- The full test suite passes with 31 tests, including three voice-loop composition tests.
- The opt-in `servo-skull-integration-check` command is implemented for the real local pipeline, with sample-WAV mode, interactive `--record` mode, optional playback, and optional debug artifact retention.
- A sample-based integration run passed through Whisper, Ollama, Piper, SoX, and `aplay` using `SERVO_SKULL_OLLAMA_MODEL=llama3.2:3b`.
- The first interactive recording attempt exposed a PipeWire/ALSA behavior: `arecord` exits with status 1 and `Aborted by signal Interrupt...` on a normal Enter stop. The recorder now accepts that status only when a valid WAV with audio frames exists, while preserving real failure reporting.
- The direct default-device capture check passes, and the full test suite passes with 32 tests.
- A real interactive microphone integration run passed end to end: the captured phrase was transcribed as "Servo School, do you hear me?", Ollama returned an in-character response, Piper and SoX generated the response audio, and playback succeeded.
- The integration check now reports per-stage latency. A sample baseline measured Whisper at 4.23 seconds, Ollama at 2.34 seconds, Piper plus SoX at 3.73 seconds, and 10.30 seconds total before playback.

Immediate next step

1. Create the Python package, virtual-environment setup, configuration layer, and pytest skeleton described in step 1 above.
2. Implement and unit-test the Whisper adapter using the verified CLI invocation and configurable model path.
3. Add a local recording/playback diagnostic using the ALSA default device before wiring in Ollama.

The first six setup and adapter steps are complete and reviewed. The sample and real microphone integration checks are complete. Resume with target-machine tuning: repeat the timing check across short and long turns, then evaluate Whisper thread/model settings, Ollama response limits, and Piper/SoX latency while preserving intelligibility.

Remaining question

- After the first `base.en` transcription benchmark, is its accuracy acceptable, or should we trade additional CPU latency for `small.en`?