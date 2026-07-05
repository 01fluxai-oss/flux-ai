import os
import stripe

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

STRIPE_PRICE_ID = os.environ["STRIPE_PRICE_ID"]
PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://flux-ai-8p34.onrender.com")


def create_checkout_session(user_id):
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[
            {
                "price": STRIPE_PRICE_ID,
                "quantity": 1,
            }
        ],
        success_url=f"{PUBLIC_URL}/payment-success",
        cancel_url=f"{PUBLIC_URL}/payment-cancel",
        metadata={
            "telegram_id": str(user_id)
        },
        subscription_data={
            "metadata": {
                "telegram_id": str(user_id)
            }
        },
    )

    return session.url
