"""
EchoStream v1.0 - Autonomous Speech & Thought Stream Perception Engine
Part of the IT Solutions Autonomous Enterprise Suite.
"""

__version__ = "1.0.0"
__product__ = "EchoStream"
__tagline__ = "Autonomous Real-Time Audio & Thought Stream Triage Engine"

from echostream.voice_guard import VoiceGuard
from echostream.parser import SemanticStreamParser
from echostream.dispatcher import CorePulseDispatcher
from echostream.watcher import TranscriptWatcher
from echostream.pipeline import (
    AutonomousIngestionPipeline,
    MultiFormatTranscriptNormalizer,
    PipelineRegistry
)

__all__ = [
    "VoiceGuard",
    "SemanticStreamParser",
    "CorePulseDispatcher",
    "TranscriptWatcher",
    "AutonomousIngestionPipeline",
    "MultiFormatTranscriptNormalizer",
    "PipelineRegistry",
]
