import requests


def send_stars_invoice(
    bot_token,
    chat_id,
    user_id,
    stars_price=500,
    language="ru",
):
    url = (
        f"https://api.telegram.org/"
        f"bot{bot_token}/sendInvoice"
    )

    if language == "en":
        title = "FLUX AI PRO — 30 days"

        description = (
            "Unlimited match analysis, "
            "extended statistics, "
            "daily Top 3 predictions "
            "and new PRO features."
        )

        price_label = (
            "FLUX AI PRO — 30 days"
        )

    else:
        title = "FLUX AI PRO — 30 дней"

        description = (
            "Безлимитный анализ матчей, "
            "расширенная статистика, "
            "ежедневный ТОП-3 прогнозов "
            "и новые PRO-функции."
        )

        price_label = (
            "FLUX AI PRO — 30 дней"
        )

    payload = {
        "chat_id": chat_id,
        "title": title,
        "description": description,
        "payload": (
            f"flux_pro_30_days:{user_id}"
        ),
        "currency": "XTR",
        "prices": [
            {
                "label": price_label,
                "amount": int(
                    stars_price
                ),
            }
        ],
        "start_parameter": (
            "flux-pro-30-days"
        ),
    }

    response = requests.post(
        url,
        json=payload,
        timeout=20,
    )

    try:
        result = response.json()

    except ValueError as error:
        raise RuntimeError(
            "Telegram returned "
            "an invalid response "
            "while creating the invoice."
        ) from error

    if (
        not response.ok
        or not result.get("ok")
    ):
        raise RuntimeError(
            "Telegram did not create "
            f"the invoice: {result}"
        )

    return result
