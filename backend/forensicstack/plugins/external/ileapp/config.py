from enum import Enum

class PluginType(Enum):
    INTERNAL = "internal"
    DOCKER = "docker"

PLUGIN_CONFIG = {
    "name": "ileapp",
    "type": PluginType.DOCKER,
    "image": "forensicstack/ileapp:0.1",
    "artifact_types": ["ios_backup"],
    "resources": {
        "memory": "3g",
        "cpus": "1"
    }
}