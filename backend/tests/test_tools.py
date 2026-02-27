"""
Tool-level tests — test forensic tools directly, without the API layer.

YARA:      runs via yara-python (Python library, always available)
Volatility: checks the vol.exe / vol binary is callable
Plaso:      checks log2timeline is callable
ChromaDB:   unit-tests the ChromaService wrapper with a mock client
"""
import json
import os
import subprocess
import sys
import pytest
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


# ═══════════════════════════════════════════════════════════
# YARA (yara-python)
# ═══════════════════════════════════════════════════════════

class TestYara:
    """YARA scanning via the yara-python library."""

    @pytest.fixture(scope="class")
    def rules(self):
        try:
            import yara
        except ImportError:
            pytest.skip("yara-python not installed")
        rules_file = DATA_DIR / "test_rules.yar"
        return yara.compile(str(rules_file))

    # Standard EICAR test string (scanned from memory to avoid AV quarantine on disk)
    EICAR_BYTES = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

    def test_eicar_match(self, rules):
        """EICAR test string in memory should trigger the EICAR_Test_File rule."""
        matches = rules.match(data=self.EICAR_BYTES)
        rule_names = [m.rule for m in matches]
        assert "EICAR_Test_File" in rule_names, (
            f"Expected EICAR_Test_File in {rule_names}"
        )

    def test_pe_header_match(self, rules):
        """Fake PE binary in memory should trigger the PE_Header_Test rule."""
        pe_bytes = (DATA_DIR / "test_binary.bin").read_bytes()
        matches = rules.match(data=pe_bytes)
        rule_names = [m.rule for m in matches]
        assert "PE_Header_Test" in rule_names, (
            f"Expected PE_Header_Test in {rule_names}"
        )

    def test_no_match_on_log(self, rules):
        """Plain log file should NOT trigger any rule."""
        log_bytes = (DATA_DIR / "test.log").read_bytes()
        matches = rules.match(data=log_bytes)
        assert len(matches) == 0, f"Unexpected match on log file: {matches}"

    def test_scan_bytes_directly(self):
        """YARA can scan raw bytes (no file needed)."""
        import yara
        rule = yara.compile(source='rule TestRule { strings: $s = "FORENSICSTACK" condition: $s }')
        matches = rule.match(data=b"Hello FORENSICSTACK world")
        assert len(matches) == 1
        assert matches[0].rule == "TestRule"

    def test_compile_invalid_rule_raises(self):
        """Invalid YARA syntax raises a compile error."""
        import yara
        with pytest.raises(yara.SyntaxError):
            yara.compile(source="rule Bad { condition: this_is_not_valid }")


# ═══════════════════════════════════════════════════════════
# VOLATILITY3
# ═══════════════════════════════════════════════════════════

class TestVolatility:
    """Check that Volatility3 (vol / vol.exe) is accessible."""

    @pytest.fixture(scope="class")
    def vol_cmd(self):
        for cmd in ("vol", "vol.exe", "vol3", "python -m volatility3"):
            try:
                result = subprocess.run(
                    cmd.split() + ["--help"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode in (0, 1, 2):   # vol returns 2 on --help sometimes
                    return cmd.split()
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        pytest.skip("Volatility3 (vol / vol.exe) not found in PATH")

    def test_volatility_accessible(self, vol_cmd):
        result = subprocess.run(
            vol_cmd + ["--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        combined = result.stdout + result.stderr
        assert any(kw in combined.lower() for kw in ("volatility", "framework", "usage")), (
            f"Unexpected vol output: {combined[:200]}"
        )

    def test_volatility_lists_plugins(self, vol_cmd):
        """Running vol.exe with no plugin prints a usage/selection message."""
        result = subprocess.run(
            vol_cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        combined = result.stdout + result.stderr
        # vol.exe without a plugin arg prints a selection/usage message
        assert any(kw in combined.lower() for kw in (
            "windows", "linux", "plugin", "select", "usage", "framework", "help"
        )), f"Unexpected vol output: {combined[:300]}"


# ═══════════════════════════════════════════════════════════
# PLASO
# ═══════════════════════════════════════════════════════════

class TestPlaso:
    """Check that log2timeline (Plaso) is accessible."""

    @pytest.fixture(scope="class")
    def log2timeline_cmd(self):
        for cmd in ("log2timeline.py", "log2timeline", "log2timeline.exe"):
            try:
                result = subprocess.run(
                    [cmd, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode in (0, 1):
                    return cmd
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        pytest.skip("log2timeline (Plaso) not found in PATH")

    def test_log2timeline_accessible(self, log2timeline_cmd):
        result = subprocess.run(
            [log2timeline_cmd, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        combined = result.stdout + result.stderr
        assert "plaso" in combined.lower() or "log2timeline" in combined.lower(), (
            f"Unexpected log2timeline output: {combined[:200]}"
        )


# ═══════════════════════════════════════════════════════════
# CHROMA SERVICE (unit test — no Docker required)
# ═══════════════════════════════════════════════════════════

class TestChromaService:
    """Unit-test ChromaService logic with a mocked chromadb client."""

    def _make_service(self):
        """Return a ChromaService with a fully mocked HTTP client."""
        from unittest.mock import MagicMock, patch
        from forensicstack.core.chroma_service import ChromaService
        from forensicstack.core.models.finding_models import Finding

        mock_collection = MagicMock()
        mock_collection.count.return_value = 2
        mock_collection.query.return_value = {
            "ids": [["art1_volatility_0", "art1_exiftool_1"]],
            "metadatas": [[
                {
                    "tool": "volatility",
                    "artifact_type": "windows.pslist",
                    "source": "memory",
                    "timestamp": "",
                    "confidence": "0.7",
                    "artifact_id": "1",
                    "case_id": "1",
                    "data_json": json.dumps({"PID": 4, "ImageFileName": "System"}),
                },
                {
                    "tool": "exiftool",
                    "artifact_type": "file_metadata",
                    "source": "/data/image.jpg",
                    "timestamp": "2024:01:01 00:00:00",
                    "confidence": "0.4",
                    "artifact_id": "1",
                    "case_id": "1",
                    "data_json": json.dumps({"Make": "Canon"}),
                },
            ]],
            "distances": [[0.05, 0.30]],
        }

        svc = ChromaService.__new__(ChromaService)
        svc._client = MagicMock()
        svc._collection = mock_collection
        return svc, mock_collection

    def test_add_findings(self):
        from forensicstack.core.chroma_service import ChromaService
        from forensicstack.core.models.finding_models import Finding

        svc, collection = self._make_service()
        findings = [
            Finding(
                tool="volatility",
                artifact_type="windows.pslist",
                source="memory",
                timestamp=None,
                data={"PID": 4, "ImageFileName": "System"},
                confidence=0.7,
            ),
            Finding(
                tool="volatility",
                artifact_type="windows.pslist",
                source="memory",
                timestamp=None,
                data={"PID": 1234, "ImageFileName": "svchost.exe"},
                confidence=0.7,
            ),
        ]
        svc.add_findings(findings, artifact_id=1, case_id=1)
        collection.upsert.assert_called_once()

    def test_search_returns_hits(self):
        svc, _ = self._make_service()
        hits = svc.search("suspicious process", n_results=5)
        assert len(hits) == 2
        # Sorted by score descending
        assert hits[0]["score"] >= hits[1]["score"]
        assert hits[0]["tool"] == "volatility"
        assert hits[0]["data"]["PID"] == 4

    def test_search_with_case_filter(self):
        svc, collection = self._make_service()
        svc.search("malware", n_results=5, case_id=1)
        call_kwargs = collection.query.call_args[1]
        assert call_kwargs["where"] == {"case_id": 1}

    def test_search_with_tool_filter(self):
        svc, collection = self._make_service()
        svc.search("metadata", n_results=5, tool="exiftool")
        call_kwargs = collection.query.call_args[1]
        assert call_kwargs["where"] == {"tool": "exiftool"}

    def test_search_with_combined_filter(self):
        svc, collection = self._make_service()
        svc.search("process", n_results=5, case_id=2, tool="volatility")
        call_kwargs = collection.query.call_args[1]
        assert call_kwargs["where"] == {"$and": [{"case_id": 2}, {"tool": "volatility"}]}

    def test_delete_by_artifact(self):
        svc, collection = self._make_service()
        svc.delete_by_artifact(artifact_id=42)
        collection.delete.assert_called_once_with(where={"artifact_id": 42})

    def test_get_stats(self):
        svc, _ = self._make_service()
        stats = svc.get_stats()
        assert stats["collection"] == "findings"
        assert stats["total_findings"] == 2


# ═══════════════════════════════════════════════════════════
# NORMALIZERS (unit tests — pure Python, no I/O needed)
# ═══════════════════════════════════════════════════════════

class TestNormalizers:
    """Test that each normalizer parses its expected output format."""

    def _write_tmp(self, tmp_path, filename, content):
        p = tmp_path / filename
        p.write_text(json.dumps(content), encoding="utf-8")
        return tmp_path

    def test_exiftool_normalizer(self, tmp_path):
        from forensicstack.core.normalizers.exiftool_normalizer import ExiftoolNormalizer
        data = [{"SourceFile": "/data/img.jpg", "Make": "Canon", "DateTimeOriginal": "2024:01:01"}]
        out_dir = self._write_tmp(tmp_path, "job123_raw.json", data)
        findings = ExiftoolNormalizer().normalize(str(out_dir))
        assert len(findings) == 1
        assert findings[0].tool == "exiftool"
        assert findings[0].artifact_type == "file_metadata"
        assert findings[0].data["Make"] == "Canon"

    def test_volatility_normalizer(self, tmp_path):
        from forensicstack.core.normalizers.volatility_normalizer import VolatilityNormalizer
        data = {"rows": [{"PID": 4, "ImageFileName": "System"}]}
        out_dir = self._write_tmp(tmp_path, "windows_pslist.json", data)
        findings = VolatilityNormalizer().normalize(str(out_dir))
        assert len(findings) == 1
        assert findings[0].tool == "volatility"
        assert findings[0].data["PID"] == 4
