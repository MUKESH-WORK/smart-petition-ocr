import sys
import os
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT_DIR / ".env"

def get_auth_token():
    token = os.environ.get("NGROK_AUTHTOKEN")
    if token:
        return token.strip()
    
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("NGROK_AUTHTOKEN="):
                    return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return None

def save_auth_token(token):
    lines = []
    found = False
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
    
    new_lines = []
    for line in lines:
        if line.startswith("NGROK_AUTHTOKEN="):
            new_lines.append(f"NGROK_AUTHTOKEN={token}\n")
            found = True
        else:
            new_lines.append(line)
            
    if not found:
        new_lines.append(f"\nNGROK_AUTHTOKEN={token}\n")
        
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

def main():
    print("=" * 79)
    print("  TAMIL NADU e-GRIEVANCE GDP ASSISTANT - NGROK PUBLIC TUNNEL")
    print("=" * 79)
    print()

    token = get_auth_token()
    
    if not token:
        print("[!] No Ngrok Authtoken found.")
        print("    Get your free token from: https://dashboard.ngrok.com/get-started/your-authtoken")
        print()
        user_input = input("Paste your Ngrok Authtoken here (or press Enter to skip): ").strip()
        if user_input:
            token = user_input
            save_auth_token(token)
            print("[✓] Authtoken saved to .env")
        else:
            print("[!] Skipping Ngrok tunnel. Using Local Network.")
            sys.exit(0)

    try:
        from pyngrok import ngrok, conf
        conf.get_default().auth_token = token
        ngrok.set_auth_token(token)
        
        print("[*] Connecting Ngrok tunnel to Frontend on 127.0.0.1:5173...")
        tunnel = ngrok.connect("127.0.0.1:5173", proto="http", bind_tls=True)
        public_url = tunnel.public_url
        if public_url.startswith("http://"):
            public_url = public_url.replace("http://", "https://")
            
        print()
        print("=" * 79)
        print("  ✓ GLOBAL 4G/5G LIVE ACCESS URL (ANY PHONE / INDEPENDENT NETWORK):")
        print(f"    👉 {public_url}")
        print("=" * 79)
        print()
        print("[*] Scan QR code from mobile on ANY cellular network (Airtel, Jio, Vi, BSNL, etc.)")
        print("[*] Keep this window OPEN while testing. Press Ctrl+C to stop.")
        print()

        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[*] Stopping Ngrok tunnel...")
    except Exception as e:
        print(f"\n[!] Ngrok Error: {e}")
        print("    If the token was invalid, update NGROK_AUTHTOKEN in your .env file.")
        sys.exit(1)

if __name__ == "__main__":
    main()
