# SHAHPURA ONLINE HUB — Production Web Starter

This is a real server-backed shopping website starter, not a browser-only demo.

## Includes
- Customer registration/login
- Product catalog and categories
- Search
- Cart with server-side session
- Checkout with address
- Cash on Delivery
- Orders and order history
- SQLite database
- Admin product creation
- Admin order status management
- Stock deduction when an order is placed

## Run
1. Install Python 3.11+
2. `pip install -r requirements.txt`
3. `python app.py`
4. Open `http://127.0.0.1:5000`

## Production before launch
- Set a strong SECRET_KEY environment variable.
- Move from SQLite to PostgreSQL for a public multi-user deployment.
- Add HTTPS.
- Add a real payment gateway using YOUR merchant account/API keys.
- Add shipping/delivery integration if required.
- Add image upload/storage.
- Add proper CSRF protection, rate limiting, password reset, email/SMS verification and backups.
- Create a real admin account instead of using a development bootstrap.

The website can later share the same backend API/database with an Android app.
