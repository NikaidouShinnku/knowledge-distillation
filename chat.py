
import sys

import agent.distill
from common.show_utils import show_response
from llms import chat, default_model
import argparse
import requests
from bs4 import BeautifulSoup
from consoles import print_markdown

chat_history = []

def fetch_url_content(url):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.get_text()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None


if __name__ == '__main__':
    from common.io import configure_console
    configure_console()
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', nargs='+', action="extend", default=[], type=str, help='add file')
    parser.add_argument('--prompt-file', type=str, help='user prompt', default=None)
    parser.add_argument('--model', nargs='+', action="extend", default=[], help='model name')
    parser.add_argument('--prompt', type=str, help='user prompt',default="")
    parser.add_argument('--history', action='store_true', help='Enter conversation mode')
    parser.add_argument('--stream', action='store_true', help='Run in stream mode')
    parser.add_argument('--no-pretty', action='store_true', help='print in plaintext mode')
    parser.add_argument('--url', type=str, help='URL to fetch content from')

    args = parser.parse_args()

    combined_content = ""

    if args.file:
        for file in args.file:
            with open(file, 'r', encoding='utf-8') as f:
                combined_content += "file-info: " + f.read() + "\n"

    if args.url:
        url_content = fetch_url_content(args.url)
        if url_content:
            combined_content += "web-info: " + url_content + "\n"

    if not args.model:
        args.model = [default_model()]

    if not args.prompt_file and not args.prompt:
        print("error")
        sys.exit(1)

    prompt = ""

    if args.prompt_file:
        with (open(args.prompt_file, 'r', encoding='utf-8') as f):
            prompt += f.read()

    if args.prompt:
        prompt += "\n"
        prompt += args.prompt

    if combined_content:
        prompt = f"""
            {combined_content}

        阅读上面的内容，然后回答用户的问题："{prompt}"
        """

    if not args.history:
        for model in args.model:
            res = chat(prompt=prompt, model=model, stream=args.stream)
            response = show_response(res, title=model, no_pretty=args.no_pretty)

    else:
        chat_history.append(
            {"role": "user", "content": prompt}
        )
        for model in args.model[:1]:
            res = chat(messages=chat_history, model=args.model[0], stream=args.stream)
            response = show_response(res, title=model, no_pretty=args.no_pretty)
            chat_history += [
                {"role": "assistant", "content": response}
            ]
            while True:
                try:
                    q = input("[User]: ")
                except (EOFError, KeyboardInterrupt):
                    break
                if q.strip() in ("/quit", "/exit"):
                    break
                if not q.strip():
                    continue
                chat_history.append(
                    {"role": "user", "content": q}
                )
                res = chat(messages=chat_history, model=args.model[0], stream=args.stream)
                response = show_response(res, title=model, no_pretty=args.no_pretty)
                chat_history += [
                    {"role": "assistant", "content": response}
                ]
                if len(chat_history) > 100:
                    chat_history = chat_history[-100:]
