from software.voice.voice_state import VoiceRuntimeState, VoiceState


def main() -> None:
    state = VoiceRuntimeState()
    assert state.state == VoiceState.LOCKED

    state.set(VoiceState.AUTHENTICATED)
    assert state.authenticated is True

    state.set(VoiceState.LOCKED)
    assert state.authenticated is False

    print("VOICE STATE TEST PASSED")


if __name__ == "__main__":
    main()
