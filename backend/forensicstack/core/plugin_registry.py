PLUGIN_REGISTRY = {
    "ileapp": {
        "image": "forensicstack/ileapp:0.1",
        "category": "mobile_ios",
        "default_type": "fs",
        "env_var": "ILEAPP_TYPE",
        "memory": "4g",
        "cpus": "2",
        "timeout": 3600,
        "features": [
            {
                "id": "fs",
                "label": "Full iOS Extraction",
                "description": "Extraction complète des artefacts iOS : messages, contacts, appels, géolocalisation, applications installées, historique Safari.",
                "accepted_extensions": [".tar", ".zip", ".tar.gz"],
            },
        ],
    },

    "aleapp": {
        "image": "forensicstack/aleapp:0.1",
        "category": "mobile_android",
        "default_type": "fs",
        "env_var": "ALEAPP_TYPE",
        "memory": "4g",
        "cpus": "2",
        "timeout": 3600,
        "features": [
            {
                "id": "fs",
                "label": "Full Android Extraction",
                "description": "Extraction complète des artefacts Android : SMS, appels, applications, comptes Google, historique Chrome, fichiers multimédia.",
                "accepted_extensions": [".tar", ".zip", ".ab"],
            },
        ],
    },

    "volatility": {
        "image": "forensicstack/volatility:0.1",
        "category": "memory",
        "env_var": "VOLATILITY_PLUGIN",
        "memory": "6g",
        "cpus": "2",
        "timeout": 7200,
        # Volatility 3 downloads symbol tables (ISF) on first run → needs network
        # and must write its cache to ~/.cache/volatility3 → disable read-only.
        # plugin_volumes: named Docker volume persists symbol cache between runs
        # so symbols are only downloaded once, not on every job.
        "network": "bridge",
        "readonly": False,
        "plugin_volumes": ["forensicstack_vol3_symbols:/root/.cache/volatility3"],
        "features": [
            {
                "id": "windows.pslist",
                "label": "Process List",
                "description": "Liste tous les processus actifs au moment de la capture mémoire (PID, PPID, nom, heure de démarrage).",
                "accepted_extensions": [".raw", ".dmp", ".vmem", ".mem", ".lime"],
            },
            {
                "id": "windows.cmdline",
                "label": "Command Lines",
                "description": "Affiche les arguments de ligne de commande complets pour chaque processus en cours d'exécution.",
                "accepted_extensions": [".raw", ".dmp", ".vmem", ".mem", ".lime"],
            },
            {
                "id": "windows.netscan",
                "label": "Network Scan",
                "description": "Scan des connexions réseau actives et des sockets en écoute (TCP/UDP, adresses IP, ports).",
                "accepted_extensions": [".raw", ".dmp", ".vmem", ".mem", ".lime"],
            },
            {
                "id": "windows.dlllist",
                "label": "DLL List",
                "description": "Liste toutes les DLLs chargées par chaque processus, avec leur chemin et adresse de base.",
                "accepted_extensions": [".raw", ".dmp", ".vmem", ".mem", ".lime"],
            },
            {
                "id": "windows.malfind",
                "label": "Malfind",
                "description": "Détecte les régions mémoire suspectes susceptibles de contenir du code injecté ou du shellcode.",
                "accepted_extensions": [".raw", ".dmp", ".vmem", ".mem", ".lime"],
            },
        ],
    },

    "exiftool": {
        "image": "forensicstack/exiftool:0.1",
        "category": "metadata",
        "memory": "512m",
        "cpus": "0.5",
        "timeout": 300,
        "env_var": "EXIF_MODE",
        "default_type": "file",
        "features": [
            {
                "id": "all",
                "label": "All Metadata",
                "description": "Extrait toutes les métadonnées disponibles : EXIF, XMP, IPTC, GPS, informations caméra, timestamps, données embarquées.",
                "accepted_extensions": ["*"],
            },
        ],
    },
}
