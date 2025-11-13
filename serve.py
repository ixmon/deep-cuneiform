import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, default='unsloth/DeepSeek-OCR', help='Model path: base or models/sumerian-deepseek-ocr')
    args = parser.parse_args()

    # Run vLLM OpenAI server
    subprocess.run([
        'python', '-m', 'vllm.entrypoints.openai.api_server',
        '--model', args.model,
        '--host', 'localhost',
        '--port', '8000',
        '--gpu-memory-utilization', '0.9'
    ])

if __name__ == '__main__':
    main()
