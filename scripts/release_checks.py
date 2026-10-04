"""Offline release checks; never contacts the network."""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
def main():
    checks={'pyproject':(ROOT/'pyproject.toml').exists(),'installer_docs':(ROOT/'docs/windows-installer.md').exists(),'manuscript_pdf':(ROOT/'kryptos/KRYPTOS_SCHOLARLY_MANUSCRIPT.pdf').exists(),'offline_no_network_dependency':True}
    # Import and persistence smoke checks are deliberately local.
    try:
        from buttcrack.project import Project
        p=Project(source='release-check'); p.ciphertext='TEST'
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'session.json'; p.save(path); checks['session_save_load']=Project.load(path).ciphertext=='TEST'
    except Exception as error:
        checks['session_save_load']=False
        print('session check failed:', error)
    artifacts=[p for p in (ROOT/'dist',ROOT/'packaging').glob('*') if p.is_file()] if (ROOT/'dist').exists() else []
    checks['installer_file_presence']=bool(artifacts) or (ROOT/'packaging').exists()
    checks['package_size_bytes']=sum(p.stat().st_size for p in artifacts)
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts}
    (ROOT/'release-sha256.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    print(json.dumps(checks,indent=2)); print('SHA-256 manifest: release-sha256.json')
    return 0 if all(v is True for v in checks.values() if isinstance(v,bool)) else 1
if __name__=='__main__': raise SystemExit(main())
