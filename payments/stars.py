import requests


def send_stars_invoice(
    bot_token: str,
    chat_id: int,
    user_id: int,
    stars_price: int = 500,
) -> dict:
    """
    Отправляет пользователю счет Telegram Stars
    за 30 дней FLUX AI PRO.
    """

    url = f"https://api.telegram.org/bot{bot_token}/sendInvoice"

    payload = {
        "chat_id": chat_id,
        "title": "FLUX AI PRO — 30 дней",
        "description": (
            "Безлимитный анализ матчей, расширенная статистика, "
            "TOP-3 прогнозов и новые PRO-функции."
        ),
        "payload": f"flux_pro_30_days:{user_id}",
        "currency": "XTR",
        "prices": [
            {
                "label": "FLUX AI PRO — 30 дней",
                "amount": stars_price,
            }
        ],
        "start_parameter": "flux-pro-30-days",
    }

    response = requests.post(url, json=payload, timeout=20)
    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram не создал счет: {result}"
        )

    return result
