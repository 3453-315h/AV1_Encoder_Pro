#!/bin/sh

# Default to CLI mode if MODE is not set
MODE=${MODE:-cli}

if [ "$MODE" = "web" ]; then
    echo "Starting Web UI..."
    exec python web_ui.py
elif [ "$MODE" = "gui" ]; then
    echo "Starting Desktop GUI..."
    exec python av1_encoder_ctk.py
else
    # CLI mode - pass all arguments to the CLI script
    # If no arguments provided, show help
    if [ $# -eq 0 ]; then
        exec python encode_cli.py --help
    else
        exec python encode_cli.py "$@"
    fi
fi
