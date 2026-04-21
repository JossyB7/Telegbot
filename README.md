# Telegram PSD Layer Bot

This bot receives an image on Telegram, removes its background, fits it onto a predefined PSD layer, and returns the composite.

## Quick Start

1. Clone the repo and add a valid PSD template in `psd_templates/template.psd`.
2. Update the `.env` file or copy `.env.example` and fill in your real details.
3. Install dependencies:
    ```
    pip install -r requirements.txt
    ```
4. Run:
    ```
    python bot.py
    ```
5. Or build/run via Docker:
    ```
    docker build -t telegram_psd_bot .
    docker run --env-file .env telegram_psd_bot
    ```

## Usage

1. Start bot in Telegram.
2. Send a photo.
3. Bot returns the composited image.

## Environment Variables

See `.env.example`.

## Notes

- The PSD template must have a layer named `USER_PHOTO` for correct placement.
- All processing is ephemeral; user images are deleted after processing.
