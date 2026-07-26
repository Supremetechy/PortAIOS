from deepgram import DeepgramClient
from deepgram.agent.v1.types import (
    AgentV1Settings, AgentV1SettingsAgent,
    AgentV1SettingsAgentListen, AgentV1SettingsAgentListenProvider_V1,
    AgentV1SettingsAudio, AgentV1SettingsAudioInput,
)
from deepgram.types.think_settings_v1 import ThinkSettingsV1
from deepgram.types.think_settings_v1provider import ThinkSettingsV1Provider_OpenAi
from deepgram.types.speak_settings_v1 import SpeakSettingsV1
from deepgram.types.speak_settings_v1provider import SpeakSettingsV1Provider_Deepgram

client = DeepgramClient()  # type: ignore[call-arg]

with client.agent.v1.connect() as agent:
    settings = AgentV1Settings(
        audio=AgentV1SettingsAudio(
            input=AgentV1SettingsAudioInput(encoding="linear16", sample_rate=24000)
        ),
        agent=AgentV1SettingsAgent(
            listen=AgentV1SettingsAgentListen(
                provider=AgentV1SettingsAgentListenProvider_V1(
                    type="deepgram", model="nova-3"
                )
            ),  # type: ignore[arg-type]
            think=ThinkSettingsV1(
                provider=ThinkSettingsV1Provider_OpenAi(
                    type="open_ai", model="gpt-4o-mini"
                ),
                prompt="You are a helpful AI assistant.",
            ),
            speak=SpeakSettingsV1(
                provider=SpeakSettingsV1Provider_Deepgram(
                    type="deepgram", model="aura-2-asteria-en"
                )
            ),
        ),
    )

    agent.send_settings(settings)
    agent.start_listening()