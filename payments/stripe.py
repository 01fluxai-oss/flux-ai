import os
import stripe

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

PRICE_ID = os.environ["STRIPE_PRICE_ID"]


def create_checkout_session(user_id):
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[
            {
                "price": PRICE_ID,
                "quantity": 1,
            }
        ],
        success_url="https://t.me/FluxAiSportsBot",
        cancel_url="https://t.me/FluxAiSportsBot",
        metadata={
            "telegram_id": str(user_id)
        }
    )

    return session.url
