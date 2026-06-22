# VM provisioning

Each AV engine = one VMware VM with **one** AV product installed plus the
shared `common/agent.py` HTTP service. The host's Celery worker reverts the
VM to a clean snapshot before every scan, so guests can never persistently
pwn the lab.

## Network layout (recommended)

```
  Host (Celery worker, FastAPI, postgres)
        |
        +-- vmnet8 (host-only)  10.10.20.0/24
              |
              +-- AV-Defender      10.10.20.11
              +-- AV-Kaspersky     10.10.20.12
              +-- AV-BitDefender   10.10.20.13
              +-- AV-ESET          10.10.20.14
              +-- AV-Avast         10.10.20.15
              +-- AV-Malwarebytes  10.10.20.16
              +-- AV-Sophos        10.10.20.17
```

VMs have **no internet access** by default. Internet is only enabled briefly
during build to install Windows + the AV product, and again on a schedule
to refresh signatures (rebuild the `clean` snapshot afterwards).

## Per-VM build steps

1. Install Windows 10/11 LTSC, fully patched.
2. Install the AV product. Disable any cloud-upload / "send sample" features.
3. Install Python 3.12 (x64) under `C:\Python312`. Run:
   ```powershell
   pip install fastapi uvicorn python-multipart
   ```
4. Copy `common/agent.py` to `C:\agent\agent.py`.
5. Copy the engine-specific `scan.ps1` to `C:\agent\scan.ps1`.
6. Generate a self-signed cert (PowerShell):
   ```powershell
   New-SelfSignedCertificate -DnsName "av-defender.local" `
     -CertStoreLocation "Cert:\LocalMachine\My" -KeyExportPolicy Exportable
   ```
   Export to `C:\agent\cert.pem` + `key.pem` via `Export-PfxCertificate` + openssl.
7. Set machine env vars:
   ```
   VM_AGENT_TOKEN  = <same shared secret as host .env>
   SCAN_COMMAND    = powershell -ExecutionPolicy Bypass -File C:\agent\scan.ps1 {file}
   TLS_CERT        = C:\agent\cert.pem
   TLS_KEY         = C:\agent\key.pem
   LISTEN_PORT     = 7443
   ```
8. Register the agent as a Windows Service (nssm is easiest):
   ```
   nssm install AVAgent C:\Python312\python.exe C:\agent\agent.py
   nssm set AVAgent Start SERVICE_AUTO_START
   ```
9. Reboot. Confirm `curl -k https://localhost:7443/health` returns `{"status":"ok"}`.
10. **Take a VMware snapshot named `clean`** — this is the state the host reverts to.

## Adding a new AV engine

1. Write `vm-scripts/<engine>/scan.ps1` following the contract:
   - Print `DETECTION_NAME=<exact name>` on stdout when a threat is found.
   - Exit `0` clean, `1` detected, `2` error.
2. Build the VM following the steps above with that engine.
3. Add an entry to `backend/engines.json` and set the matching VMX env var on the worker:
   ```
   ENGINES_VMX_<UPPER_SNAKE_ID>=/srv/vms/<engine>/<engine>.vmx
   ```
4. Restart the Celery worker — new engines are picked up automatically.
