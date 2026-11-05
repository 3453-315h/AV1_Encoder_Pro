import os
import sys
import unittest
import tempfile
import subprocess
from unittest.mock import patch, MagicMock

# Ensure mock imports for Tk/PIL so av1_encoder_ctk can be tested headlessly
if 'customtkinter' not in sys.modules:
    class MockModule:
        class CTk:
            def __init__(self, *args, **kwargs):
                pass
        @staticmethod
        def set_appearance_mode(*args, **kw): pass
        @staticmethod
        def set_default_color_theme(*args, **kw): pass
        def __getattr__(self, name):
            return lambda *args, **kw: None

    sys.modules['customtkinter'] = MockModule()
    sys.modules['tkinter'] = MockModule()
    sys.modules['PIL'] = MockModule()
    sys.modules['PIL.Image'] = MockModule()

import encode_cli
import av1_encoder_ctk


class TestCLIEncoder(unittest.TestCase):
    def test_cli_rav1e_flags(self):
        """librav1e must use -qp and -speed, NOT -crf and -cpu-used."""
        cmd = encode_cli.build_command(
            input_path="input.mp4",
            output_path="output.mp4",
            quality=50,
            preset=6,
            encoder="librav1e",
            audio_codec="none"
        )
        self.assertIn("-qp", cmd)
        self.assertIn("-speed", cmd)
        self.assertNotIn("-crf", cmd)
        self.assertNotIn("-cpu-used", cmd)

    def test_cli_libaom_cq_mode_has_bv0(self):
        """libaom-av1 constant quality mode must pass -b:v 0."""
        cmd = encode_cli.build_command(
            input_path="input.mp4",
            output_path="output.mp4",
            quality=50,
            preset=4,
            encoder="libaom-av1",
            audio_codec="none"
        )
        self.assertIn("-crf", cmd)
        self.assertIn("-b:v", cmd)
        idx = cmd.index("-b:v")
        self.assertEqual(cmd[idx + 1], "0")

    def test_cli_preset_clamping(self):
        """Preset values exceeding encoder capability must be clamped."""
        # libaom max is 8
        cmd_aom = encode_cli.build_command(
            input_path="input.mp4",
            output_path="output.mp4",
            quality=50,
            preset=12,
            encoder="libaom-av1",
            audio_codec="none"
        )
        idx_cpu = cmd_aom.index("-cpu-used")
        self.assertEqual(cmd_aom[idx_cpu + 1], "8")

        # rav1e max is 10
        cmd_rav = encode_cli.build_command(
            input_path="input.mp4",
            output_path="output.mp4",
            quality=50,
            preset=13,
            encoder="librav1e",
            audio_codec="none"
        )
        idx_speed = cmd_rav.index("-speed")
        self.assertEqual(cmd_rav[idx_speed + 1], "10")

    def test_webm_audio_copy_incompatible(self):
        """Copying incompatible audio (like AAC) into WebM must convert to Opus."""
        with patch("encode_cli.probe_audio_codec", return_value="aac"):
            cmd = encode_cli.build_command(
                input_path="input.mp4",
                output_path="output.webm",
                quality=50,
                preset=6,
                encoder="libsvtav1",
                audio_codec="copy"
            )
            self.assertFalse(
                "-c:a" in cmd and cmd[cmd.index("-c:a") + 1] == "copy",
                "AAC must not be directly copied into WebM"
            )
            self.assertIn("libopus", cmd)

    def test_webm_audio_copy_compatible(self):
        """Copying compatible audio (Opus) into WebM must pass -c:a copy."""
        with patch("encode_cli.probe_audio_codec", return_value="opus"):
            cmd = encode_cli.build_command(
                input_path="input.mkv",
                output_path="output.webm",
                quality=50,
                preset=6,
                encoder="libsvtav1",
                audio_codec="copy"
            )
            self.assertIn("-c:a", cmd)
            self.assertEqual(cmd[cmd.index("-c:a") + 1], "copy")

    def test_mp4_audio_copy_aac(self):
        """Copying AAC into MP4 is container-compatible and passes -c:a copy."""
        with patch("encode_cli.probe_audio_codec", return_value="aac"):
            cmd = encode_cli.build_command(
                input_path="input.mov",
                output_path="output.mp4",
                quality=50,
                preset=6,
                encoder="libsvtav1",
                audio_codec="copy"
            )
            self.assertIn("-c:a", cmd)
            self.assertEqual(cmd[cmd.index("-c:a") + 1], "copy")

    def test_video_only_input_forces_an(self):
        """Input with no audio stream automatically passes -an."""
        with patch("encode_cli.probe_audio_codec", return_value=None):
            cmd = encode_cli.build_command(
                input_path="input.mp4",
                output_path="output.webm",
                quality=50,
                preset=6,
                encoder="libsvtav1",
                audio_codec="copy"
            )
            self.assertIn("-an", cmd)
            self.assertNotIn("-c:a", cmd)

    def test_output_overwrite_guard(self):
        """Existing output must not be overwritten when overwrite=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "out.webm")
            with open(out_file, "w") as f:
                f.write("original content")

            res = encode_cli.encode_video(
                input_path="dummy.mp4",
                output_path=out_file,
                overwrite=False
            )
            self.assertFalse(res)
            with open(out_file, "r") as f:
                self.assertEqual(f.read(), "original content")

    def test_failure_cleans_temporary_file(self):
        """When encode fails, partial/temporary output must be cleaned up."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inp_file = os.path.join(tmpdir, "in.mp4")
            out_file = os.path.join(tmpdir, "out.webm")
            with open(inp_file, "w") as f:
                f.write("not a real video")

            res = encode_cli.encode_video(
                input_path=inp_file,
                output_path=out_file,
                overwrite=True
            )
            self.assertFalse(res)
            self.assertFalse(os.path.exists(out_file))
            files = os.listdir(tmpdir)
            self.assertEqual(files, ["in.mp4"])


class TestGUIEncoder(unittest.TestCase):
    def setUp(self):
        # Create a mock instance with required attributes
        self.app = MagicMock()
        self.app.ffmpeg_path = "ffmpeg"
        self.app.ffprobe_path = "ffprobe"
        self.app.log = MagicMock()
        self.app.active_processes = []
        self.app._cancel_requested = False
        self.app._schedule_cancelled = False
        self.app._batch_running = False
        self.app._scheduled_thread = None

    def test_gui_compile_rav1e_flags(self):
        """GUI compile_encode_commands must produce -qp and -speed for rav1e."""
        self.app.grain_var.get.return_value = 0
        self.app.audio_var.get.return_value = "No Audio"
        self.app.audio_bitrate_var.get.return_value = "128k"
        self.app.tune_var.get.return_value = "VQ (Visual Quality)"
        self.app.resolution_var.get.return_value = "Original"
        self.app.encoder_var.get.return_value = "librav1e"
        self.app.thread_var.get.return_value = 0
        self.app._probe_audio_info = MagicMock(return_value=None)

        steps = av1_encoder_ctk.AV1EncoderPro.compile_encode_commands(
            self.app, "input.mp4", "output.mp4", crf=32, preset="12"
        )
        cmd = steps[0][1]
        self.assertIn("-qp", cmd)
        self.assertIn("-speed", cmd)
        self.assertNotIn("-crf", cmd)
        self.assertNotIn("-cpu-used", cmd)
        # Check clamping to 10
        idx_speed = cmd.index("-speed")
        self.assertEqual(cmd[idx_speed + 1], "10")

    def test_gui_compile_libaom_cq_mode(self):
        """GUI compile_encode_commands for libaom must include -b:v 0 and clamp preset."""
        self.app.grain_var.get.return_value = 0
        self.app.audio_var.get.return_value = "No Audio"
        self.app.audio_bitrate_var.get.return_value = "128k"
        self.app.tune_var.get.return_value = "VQ (Visual Quality)"
        self.app.resolution_var.get.return_value = "Original"
        self.app.encoder_var.get.return_value = "libaom-av1"
        self.app.thread_var.get.return_value = 0
        self.app._probe_audio_info = MagicMock(return_value=None)

        steps = av1_encoder_ctk.AV1EncoderPro.compile_encode_commands(
            self.app, "input.mp4", "output.mp4", crf=32, preset="10"
        )
        cmd = steps[0][1]
        self.assertIn("-crf", cmd)
        self.assertIn("-b:v", cmd)
        idx_bv = cmd.index("-b:v")
        self.assertEqual(cmd[idx_bv + 1], "0")
        # Check clamping to 8
        idx_cpu = cmd.index("-cpu-used")
        self.assertEqual(cmd[idx_cpu + 1], "8")

    def test_gui_batch_cancel_stops_subsequent_files(self):
        """Cancelling a batch during file 1 must ensure file 2 never starts."""
        files = ["video1.mp4", "video2.mp4"]
        settings = {'crf': 30, 'preset': '6', 'custom_folder': '', 'ext': '.webm'}

        # Mock compile_encode_commands and subprocess
        step_call_count = 0
        def fake_compile(inp, out, crf, preset):
            nonlocal step_call_count
            step_call_count += 1
            # User clicks cancel during file 1
            self.app._cancel_requested = True
            return [("ENCODE", ["echo", "encoding", inp])]

        self.app.compile_encode_commands = fake_compile
        av1_encoder_ctk.AV1EncoderPro.run_batch(self.app, files, settings)

        # compile_encode_commands should have run only once (for file 1), never for file 2
        self.assertEqual(step_call_count, 1)

    def test_gui_batch_skips_av1_files(self):
        """Batch processing must skip files ending in _AV1."""
        files = ["movie.mp4", "movie_AV1.webm", "clip_av1.mp4"]
        settings = {'crf': 30, 'preset': '6', 'custom_folder': '', 'ext': '.webm'}

        encoded_files = []
        def fake_compile(inp, out, crf, preset):
            encoded_files.append(inp)
            return [("ENCODE", ["echo", inp])]

        self.app.compile_encode_commands = fake_compile
        av1_encoder_ctk.AV1EncoderPro.run_batch(self.app, files, settings)

        self.assertEqual(encoded_files, ["movie.mp4"])


class TestEndToEndEncoding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a small 1-second test clip with AAC audio
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.fixture_path = os.path.join(cls.tmpdir.name, "fixture.mp4")
        gen_cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=160x120:rate=10",
            "-f", "lavfi", "-i", "sine=duration=1:frequency=440",
            "-c:v", "libx264", "-c:a", "aac",
            cls.fixture_path
        ]
        res = subprocess.run(gen_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode != 0:
            raise unittest.SkipTest("ffmpeg not available or failed to generate test fixture")

    @classmethod
    def tearDownClass(cls):
        cls.tmpdir.cleanup()

    def test_e2e_svtav1_encode(self):
        """Smoke encode 1s fixture with libsvtav1."""
        out_path = os.path.join(self.tmpdir.name, "out_svt.webm")
        success = encode_cli.encode_video(
            self.fixture_path, out_path,
            quality=50, preset=8, encoder="libsvtav1",
            audio_codec="copy", overwrite=True
        )
        self.assertTrue(success)
        self.assertTrue(os.path.exists(out_path))

    def test_e2e_libaom_encode(self):
        """Smoke encode 1s fixture with libaom-av1."""
        out_path = os.path.join(self.tmpdir.name, "out_aom.webm")
        success = encode_cli.encode_video(
            self.fixture_path, out_path,
            quality=50, preset=8, encoder="libaom-av1",
            audio_codec="libopus", overwrite=True
        )
        self.assertTrue(success)
        self.assertTrue(os.path.exists(out_path))

    def test_e2e_rav1e_encode(self):
        """Smoke encode 1s fixture with librav1e."""
        out_path = os.path.join(self.tmpdir.name, "out_rav1e.mp4")
        success = encode_cli.encode_video(
            self.fixture_path, out_path,
            quality=50, preset=10, encoder="librav1e",
            audio_codec="none", overwrite=True
        )
        self.assertTrue(success)
        self.assertTrue(os.path.exists(out_path))


if __name__ == "__main__":
    unittest.main()
