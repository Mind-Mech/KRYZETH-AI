# KRYZETH custom wake-word training

The final runtime target is:

    data/voice/wakeword/hey_kryzeth.onnx

The current runtime does **not** require that model. It can use the bundled
openWakeWord ``hey_jarvis_v0.1`` model through ``VOICE_WAKEWORD_MODEL_NAME``.

When the KRYZETH model is trained, set:

    VOICE_WAKEWORD_MODEL_NAME = ""
    VOICE_WAKEWORD_MODEL_PATH = "data/voice/wakeword/hey_kryzeth.onnx"
    WAKE_WORD = "hey kryzeth"

The supplied YAML is only a starting point. Custom openWakeWord training
requires the official training resources and evaluation data; this folder
does not pretend to contain a finished model.
