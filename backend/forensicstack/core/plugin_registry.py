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

    "eztools": {
        "category": "windows_artifacts",
        # Runs directly on the Windows host — no Docker container.
        # Install EZ Tools once with:  scripts\install-eztools.ps1
        # Override tool directory via env var EZTOOLS_DIR (default C:\EZTools).
        "executor": "native",
        "env_var": "EZTOOL_PLUGIN",
        "timeout": 1800,
        "features": [
            {
                "id": "amcacheparser",
                "label": "Amcache",
                "description": "Analyse le fichier Amcache.hve — programmes exécutés, hashes SHA1, chemins, éditeurs. Clé pour détecter l'exécution de malwares.",
                "accepted_extensions": [".hve"],
            },
            {
                "id": "appcompatcache",
                "label": "AppCompatCache (Shimcache)",
                "description": "Extrait le Shimcache depuis la ruche SYSTEM — liste les exécutables ayant été présents sur le système (avec timestamps).",
                "accepted_extensions": [".dat", "SYSTEM"],
            },
            {
                "id": "evtx",
                "label": "Windows Event Logs",
                "description": "Parse les fichiers .evtx (journaux Windows) en entrées structurées : ID événement, source, utilisateur, message, timestamp.",
                "accepted_extensions": [".evtx"],
            },
            {
                "id": "jumplist",
                "label": "Jump Lists",
                "description": "Analyse les Jump Lists (fichiers récents par application) — révèle les fichiers ouverts par l'utilisateur et les timestamps d'accès.",
                "accepted_extensions": [".automaticDestinations-ms", ".customDestinations-ms"],
            },
            {
                "id": "lnk",
                "label": "LNK (Shortcut) Files",
                "description": "Analyse les fichiers .lnk (raccourcis Windows) — révèle le chemin cible, les timestamps et les métadonnées système de l'hôte source.",
                "accepted_extensions": [".lnk"],
            },
            {
                "id": "mft",
                "label": "MFT (Master File Table)",
                "description": "Parse la $MFT NTFS — liste complète de tous les fichiers/dossiers du volume avec timestamps MACB, taille, attributs et numéros d'inode.",
                "accepted_extensions": ["$MFT", ".mft"],
            },
            {
                "id": "prefetch",
                "label": "Prefetch",
                "description": "Analyse les fichiers Prefetch (.pf) — dernières exécutions (jusqu'à 8), compteur de lancements, DLLs et fichiers accédés au démarrage.",
                "accepted_extensions": [".pf", ".gz"],
            },
            {
                "id": "recyclebin",
                "label": "Recycle Bin",
                "description": "Récupère les entrées de la Corbeille ($I/$R) — fichiers supprimés, taille originale, chemin d'origine et timestamp de suppression.",
                "accepted_extensions": ["*"],
            },
            {
                "id": "registry",
                "label": "Registry (RECmd)",
                "description": "Analyse les ruches de registre Windows avec des centaines de plugins — clés de persistance, MRU, SAM, USB, services, logiciels installés.",
                "accepted_extensions": [".dat", ".reg", "NTUSER.DAT", "SAM", "SYSTEM", "SOFTWARE", "SECURITY"],
            },
            {
                "id": "shellbags",
                "label": "ShellBags",
                "description": "Extrait les ShellBags depuis NTUSER.DAT / UsrClass.dat — dossiers consultés par l'utilisateur, y compris sur supports amovibles ou réseau.",
                "accepted_extensions": ["NTUSER.DAT", "UsrClass.dat", ".dat"],
            },
            {
                "id": "sqlite",
                "label": "SQLite Databases",
                "description": "Requête forensique sur bases SQLite (Chrome history, Firefox places, Edge, WhatsApp, etc.) via des maps prédéfinies.",
                "accepted_extensions": [".db", ".sqlite", ".sqlite3"],
            },
            {
                "id": "srum",
                "label": "SRUM (System Resource Usage)",
                "description": "Parse SRUDB.dat — utilisation réseau, CPU et mémoire par application avec timestamps précis. Idéal pour profiler l'activité réseau d'un malware.",
                "accepted_extensions": [".dat", "SRUDB.dat"],
            },
            {
                "id": "bstrings",
                "label": "BStrings (Strings Forensiques)",
                "description": "Extrait les chaînes Unicode et ASCII d'un fichier binaire avec scoring de pertinence forensique (URLs, IPs, chemins, credentials…).",
                "accepted_extensions": ["*"],
            },
            {
                "id": "hasher",
                "label": "Hasher (Empreintes Fichier)",
                "description": "Calcule MD5, SHA1 et SHA256 d'un fichier pour l'identification et la comparaison avec des bases de hashes connus (VirusTotal, NSRL).",
                "accepted_extensions": ["*"],
            },
            {
                "id": "recentfilecache",
                "label": "RecentFileCache",
                "description": "Parse RecentFileCache.bcf (Windows 7/8) — liste les exécutables récemment lancés, similaire au Shimcache mais pour systèmes 32-bit.",
                "accepted_extensions": [".bcf"],
            },
            {
                "id": "rla",
                "label": "RLA (Transaction Log Replay)",
                "description": "Rejoue les journaux de transactions (.LOG1/.LOG2) pour nettoyer une ruche registre 'dirty' avant analyse RECmd — indispensable sur images live.",
                "accepted_extensions": [".LOG1", ".LOG2", ".dat", "NTUSER.DAT", "SAM", "SYSTEM", "SOFTWARE"],
            },
            {
                "id": "sumemd",
                "label": "SumECmd (User Access Logs)",
                "description": "Parse la base SUM (LogFiles\\SUM) — connexions entrantes RDP/SMB/WinRM avec utilisateurs, adresses IP source et timestamps. Clé pour le mouvement latéral.",
                "accepted_extensions": [".mdb", "SystemIdentity.mdb", "Current.mdb"],
            },
            {
                "id": "wxtcmd",
                "label": "WxTCmd (Windows 10 Timeline)",
                "description": "Parse ActivitiesCache.db — applications utilisées, fichiers ouverts, activité web avec durée de focus. Reconstruit la chronologie d'activité de l'utilisateur.",
                "accepted_extensions": [".db", "ActivitiesCache.db"],
            },
        ],
    },
}
