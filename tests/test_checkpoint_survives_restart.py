# tests/test_checkpoint_survives_restart.py
import subprocess, sys, uuid, os


def test_interrupt_survives_process_restart():
    case_id = f"stress-{uuid.uuid4().hex[:8]}"
    env = {**os.environ, "RECON_FAKE_INVESTIGATOR": "1"}

    first = subprocess.run([sys.executable, "tests/_stress/run_until_interrupt.py", case_id],
                            capture_output=True, text=True, timeout=60, env=env)

    assert first.returncode == 0, first.stderr
    assert "PAUSED_OK" in first.stdout

    second = subprocess.run([sys.executable, "tests/_stress/resume_and_check.py", case_id],
                             capture_output=True, text=True, timeout=60, env=env)
    assert second.returncode == 0, second.stderr
    assert "PAYLOAD_INTACT_OK" in second.stdout
    assert "RESUME_OK" in second.stdout