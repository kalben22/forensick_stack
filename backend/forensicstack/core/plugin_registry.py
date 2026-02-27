PLUGIN_REGISTRY = {
    "ileapp": {
        "image": "forensicstack/ileapp:0.1",
        "category": "mobile_ios",
        "default_type": "fs",
        "env_var": "ILEAPP_TYPE",
        "memory": "4g",
        "cpus": "2",
        "timeout": 3600
    },

    "aleapp": {
        "image": "forensicstack/aleapp:0.1",
        "category": "mobile_android",
        "default_type": "fs",
        "env_var": "ALEAPP_TYPE",
        "memory": "4g",
        "cpus": "2",
        "timeout": 3600
    },

    "volatility": {
        "image": "forensicstack/volatility:0.1",
        "category": "memory",
        "memory": "6g",
        "cpus": "2",
        "timeout": 7200
    },

    "exiftool": {
        "image":"forensicstack/exiftool:0.1",
        "category":"metadata",
        "memory":"512m",
        "cpus":"0.5",
        "timeout":300,
        "env_var":"EXIF_MODE",      
        "default_type":"file"
    },
}