PLUGIN_CONFIG = {
    "name": "exiftool",
    "type": "docker",
    "image": "forensicstack/exiftool:0.1",
    "artifact_types": ["image"],
    "resources": {
        "memory": "512m",
        "cpus": "0.5"
    }
}