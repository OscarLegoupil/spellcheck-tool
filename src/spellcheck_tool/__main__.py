import argparse
import json
import socket
import threading
import webbrowser
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Finnish and English document proofreading")
    sub = parser.add_subparsers(dest="command")
    serve = sub.add_parser("serve", help="Open the local application")
    serve.add_argument("--port", type=int, default=0)
    serve.add_argument("--no-browser", action="store_true")
    check = sub.add_parser("check", help="Review a document without the browser interface")
    check.add_argument("input", type=Path)
    check.add_argument("--language", choices=["fi", "en", "mixed"], default="mixed")
    check.add_argument("--english", choices=["en-GB", "en-US"], default="en-GB")
    check.add_argument("--output", type=Path)
    check.add_argument("--profile", type=Path)
    sub.add_parser("doctor", help="Test the installed proofreading engines")
    args = parser.parse_args()
    from .engines import Engines

    if args.command == "doctor":
        from .models import Options, Segment

        engines = Engines()
        failed = False
        for lang, text in [
            ("en", "This is an test with a speling mistake."),
            ("fi", "Tämä on kirjotusvirhe."),
        ]:
            try:
                findings = engines.check(
                    Segment("test", text, "test", lang), Options(language=lang)
                )
                assert any(f.suggestions for f in findings), "No corrections returned"
                print(f"{lang}: OK ({len(findings)} findings)")
            except Exception as exc:
                print(f"{lang}: FAILED - {exc}")
                failed = True
        engines.close()
        raise SystemExit(1 if failed else 0)
    if args.command == "check":
        from .models import Options
        from .pipeline import export, load_document, review

        config = json.loads(args.profile.read_text("utf-8")) if args.profile else {}
        config.update(language=args.language, english=args.english)
        options = Options(**config)
        output = args.output or args.input.with_name(
            args.input.stem + "_reviewed" + args.input.suffix
        )
        if output.resolve() == args.input.resolve():
            parser.error("The output must be a separate file.")
        engines = Engines()
        try:
            document = load_document(args.input.name, args.input.read_bytes())
            report, findings = review(document, options, engines)
            choices = [{"id": f.id, "correction": f.suggestions[0]} for f in findings if f.selected]
            output.write_bytes(export(document, findings, choices))
            output.with_suffix(output.suffix + ".json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), "utf-8"
            )
            print(
                f"Saved {output}: {len(choices)} annotations; {len(report['warnings'])} coverage notices."
            )
        finally:
            engines.close()
        return
    import uvicorn

    from .app import create_app

    app = create_app()
    port = getattr(args, "port", 0)
    if not port:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
    url = f"http://127.0.0.1:{port}/#{app.state.access_token}"
    print(
        f"\nSpellcheck Tool\nOpen: {url}\nKeep this window open. Press Ctrl+C to stop.\n",
        flush=True,
    )
    if not getattr(args, "no_browser", False):
        timer = threading.Timer(1.2, lambda: webbrowser.open(url))
        timer.daemon = True
        timer.start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
