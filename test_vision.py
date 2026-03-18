"""
Debug script para testar o Vision Detector.
Roda standalone, mostra o que o modelo ve e responde.

Uso:
    python test_vision.py              # usa config do user_config.json
    python test_vision.py --interval 3 # override intervalo pra 3s
    python test_vision.py --describe   # pede descricao do frame alem de YES/NO
    python test_vision.py --save       # salva cada frame em debug_check_N.jpg
"""

import argparse
import base64
import cv2
import time
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="Vision Detector Debug")
    parser.add_argument("--interval", type=int, default=None, help="Segundos entre checks (default: usa config)")
    parser.add_argument("--describe", action="store_true", help="(deprecated, descricao agora e o metodo padrao)")
    parser.add_argument("--save", action="store_true", help="Salva frames em debug_check_N.jpg")
    parser.add_argument("--model", type=str, default=None, help="Modelo Ollama (default: usa config)")
    parser.add_argument("--checks", type=int, default=20, help="Numero de checks (default: 20)")
    args = parser.parse_args()

    # Load config
    from settings_ui import load_user_config
    from config import CONFIG
    config = load_user_config()
    CONFIG.update(config)

    model = args.model or config.get("ai_vision_model", "moondream")
    interval = args.interval or config.get("ai_vision_interval_seconds", 10)

    print("=" * 50)
    print("Vision Detector - Debug Mode")
    print("=" * 50)
    print(f"  Modelo:    {model}")
    print(f"  Intervalo: {interval}s")
    print(f"  Checks:    {args.checks}")
    print(f"  Describe:  {args.describe}")
    print(f"  Save:      {args.save}")
    print()

    # Init Ollama
    try:
        import ollama
        models = ollama.list()
        model_names = []
        if hasattr(models, 'models'):
            for m in models.models:
                model_names.append(getattr(m, 'model', '') or getattr(m, 'name', ''))
        print(f"  Ollama OK. Modelos: {model_names}")
    except Exception as e:
        print(f"  ERRO Ollama: {e}")
        return

    # Init camera
    cam_index = config.get("camera_index", 0)
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print(f"  ERRO: Camera {cam_index} nao abriu!")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    print(f"  Camera {cam_index} OK")
    print()
    print("-" * 50)
    print("Rodando... Beba agua quando quiser. Ctrl+C pra sair.")
    print("-" * 50)
    print()

    check_num = 0
    try:
        while check_num < args.checks:
            # Flush buffer
            for _ in range(3):
                cap.read()
            ret, frame = cap.read()
            if not ret:
                print("[ERRO] Falha ao capturar frame")
                time.sleep(1)
                continue

            check_num += 1
            timestamp = time.strftime("%H:%M:%S")

            # Save frame
            if args.save:
                fname = f"debug_check_{check_num}.jpg"
                cv2.imwrite(fname, frame)

            # Encode
            _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            img_b64 = base64.b64encode(buf).decode()

            # Drinking detection (describe + keyword match)
            try:
                r = ollama.generate(
                    model=model,
                    prompt="What is the person doing in this image? One sentence.",
                    images=[img_b64],
                    options={"temperature": 0.1, "num_predict": 60}
                )
                answer = r['response'].strip()
                drinking_keywords = ["drinking", "sipping", "gulping", "beverage",
                                     "water bottle", "taking a drink", "hydrating"]
                is_drinking = any(kw in answer.lower() for kw in drinking_keywords)
                marker = " >>> GULP DETECTED! <<<" if is_drinking else ""
                saved = f" [saved: debug_check_{check_num}.jpg]" if args.save else ""
                print(f"[{timestamp}] Check {check_num:3d} | {answer}{marker}{saved}")
            except Exception as e:
                print(f"[{timestamp}] Check {check_num:3d} | ERRO: {e}")

            print()
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nInterrompido pelo usuario.")
    finally:
        cap.release()
        print(f"\nTotal: {check_num} checks realizados.")


if __name__ == "__main__":
    main()
