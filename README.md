# Investment Platform

A Flask-based investment platform that allows users to make deposits, earn interest, and request withdrawals. The platform includes both user and admin interfaces with features for managing investments and generating reports.

## Features

### User Features
- User registration and authentication
- Deposit funds with interest calculation
- Upload payment proof and product ID
- Request withdrawals
- Track deposits and withdrawals
- View investment returns

### Admin Features
- Manage users
- Review and approve/reject deposits
- Review and approve/reject withdrawals
- Set global interest rate
- Generate Excel reports
- Filter transactions by date, status, and user

## Technology Stack

- Backend: Flask (Python)
- Database: MongoDB
- Frontend: HTML, CSS, JavaScript (Vanilla)
- Reports: Pandas, Excel Writer
- Authentication: Flask-Login
- File Uploads: Flask-Uploads

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd investment-platform
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up MongoDB:
- Install MongoDB if not already installed
- Create a new database named `investment_db`

5. Configure environment variables:
- Copy `.env.example` to `.env`
- Update the values in `.env` with your configuration

6. Create required directories:
```bash
mkdir -p static/uploads
```

7. Run the application:
```bash
python app.py
```

## Project Structure

```
investment-platform/
│
├── app.py                  # Main application file
├── requirements.txt        # Project dependencies
├── .env                   # Environment variables
│
├── routes/                # Route handlers
│   ├── admin.py          # Admin routes
│   └── transactions.py    # Deposit/withdrawal routes
│
├── templates/             # HTML templates
│   ├── admin/            # Admin templates
│   │   ├── dashboard.html
│   │   ├── deposits.html
│   │   ├── settings.html
│   │   ├── users.html
│   │   └── withdrawals.html
│   │
│   ├── base.html         # Base template
│   ├── dashboard.html    # User dashboard
│   ├── deposit.html      # Deposit form
│   ├── index.html        # Landing page
│   ├── login.html        # Login form
│   ├── register.html     # Registration form
│   ├── upload_proof.html # Payment proof upload
│   └── withdraw.html     # Withdrawal form
│
├── static/               # Static files
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   └── uploads/         # User uploaded files
│
└── README.md            # Project documentation
```

## Database Collections

### Users Collection
```json
{
    "_id": ObjectId,
    "full_name": "string",
    "email": "string",
    "phone": "string",
    "password": "hashed",
    "is_admin": false,
    "created_at": datetime
}
```

### Deposits Collection
```json
{
    "_id": ObjectId,
    "user_id": ObjectId,
    "amount": float,
    "duration_months": int,
    "interest_rate": float,
    "expected_return": float,
    "product_id": "string",
    "screenshot_url": "string",
    "note": "string",
    "status": "pending/approved/rejected",
    "submitted_at": datetime,
    "approved_at": datetime
}
```

### Withdrawals Collection
```json
{
    "_id": ObjectId,
    "user_id": ObjectId,
    "amount": float,
    "note": "string",
    "status": "pending/approved/rejected",
    "requested_at": datetime,
    "approved_at": datetime
}
```

### Settings Collection
```json
{
    "_id": ObjectId,
    "interest_rate": float,
    "updated_at": datetime
}
```

## Security Considerations

- Passwords are hashed using bcrypt
- File uploads are validated and sanitized
- Admin routes are protected with authentication
- Environment variables are used for sensitive data
- Input validation on both client and server side

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
