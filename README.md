# getVolunteers Backend API

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.30-orange?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![MySQL](https://img.shields.io/badge/MySQL-5.7%2B-blue?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## 🚀 Project Overview

The `getVolunteers Backend API` is a robust and scalable backend system built with FastAPI, designed to connect volunteers with various needs. It provides a set of RESTful endpoints for managing volunteer profiles and defining different types of volunteer opportunities (needs).

## ✨ Features

- **Volunteer Management:** Create, read, update, and delete volunteer profiles.

- **Need Management:** Create, read, update, and delete volunteer opportunities.

- **Database Integration:** Persistent data storage using MySQL.

- **API Documentation:** Automatic interactive API documentation (Swagger UI / ReDoc).

- **Test Coverage:** Comprehensive unit and integration tests with coverage reporting.

- **Code Quality:** Linting and formatting enforced with Ruff.

- **Database Migrations:** Schema evolution managed with Alembic.

## 🛠️ Technologies Used

- **Backend Framework:** FastAPI

- **Database:** MySQL

- **ORM:** SQLAlchemy

- **Migrations:** Alembic

- **Testing:** Pytest, Pytest-Cov, Pytest-Mock

- **Linting & Formatting:** Ruff

- **Dependency Management:** Pip

- **Environment Variables:** Python-dotenv, Pydantic-settings

- **HTTP Client:** Uvicorn (ASGI server), Starlette (internal)

## ⚙️ Setup & Installation

Follow these steps to set up the development environment on your machine.

### 1. Prerequisites

- **Python 3.12+**: [Download & Install Python](https://www.python.org/downloads/)

- **Git**: [Download & Install Git](https://git-scm.com/downloads)

- **MySQL Database**:
  - **Windows**: Refer to the detailed [MySQL Database Setup on Windows](https://dev.mysql.com/doc/refman/5.7/en/windows-installation.html) and MySQL Workbench.
  - **Linux/macOS**: Install MySQL Server via your package manager (e.g., `sudo apt install mysql-server` on Ubuntu, `brew install mysql@5.7` on macOS).
  - **Database User**: Create a database named `getVolunteers` and a user (e.g., `getvolunteer_user`) with `SELECT`, `INSERT`, `UPDATE`, `DELETE` privileges on it.

### 2. Clone the Repository

```bash
git clone [https://github.com/your-username/get-volunteers-backend.git](https://github.com/your-username/get-volunteers-backend.git)
cd get-volunteers-backend
```

### 3. Create & Activate Virtual Environment

It's highly recommended to use a virtual environment to manage dependencies.

- Windows (Command Prompt / PowerShell):

```bash
python -m venv .venv
.\\.venv\\Scripts\\activate.bat
```

- Linux / macOS (Bash / Zsh):

```bash
python3 -m venv .venv
source ./.venv/bin/activate
```

### 4. Configure Environment Variables

Create a .env file in the project root based on .env.example:

```bash
cp .env.example .env
```

Open .env and fill in your database credentials and a strong secret key:

```bash
# .env
DATABASE_URL="mysql+mysqlconnector://your_username:your_strong_password@localhost:3306/getVolunteers"
SECRET_KEY="your_super_secret_key_here_change_this_in_production"
APP_ENV="development"
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Database Migrations

This project uses Alembic for database migrations. The `alembic/` directory, including its configuration and migration scripts, is version-controlled.

- For Project Maintainers (Initial Setup Only):
  If this is a brand new project and you are setting up migrations for the first time, you need to initialize Alembic:

```bash
alembic init alembic
```

- For All Developers (Applying Migrations):
  To apply all pending database migrations to your local database:

```bash
make migrate-up
```

- For Project Maintainers (Creating New Migrations):
  After making changes to your SQLAlchemy models (`app/db/models.py`), create a new migration script:

```bash
make migrate-new message="Your descriptive message about changes"
```

(Review the generated script in alembic/versions/ before committing.)

## 🚀 Running the Application

To start the FastAPI development server:

```bash
make run
```

The API will be available at `http://127.0.0.1:8000`.
Access the interactive API documentation at `http://127.0.0.1:8000/docs`.

## ✅ Testing

Run unit and integration tests with coverage reporting:

```bash
make coverage
```

This will display a coverage summary in the terminal and generate a detailed HTML report in the `htmlcov/` directory. Open `htmlcov/index.html` in your browser to view it.

## 🧹 Code Quality

This project uses [Ruff](https://beta.ruff.rs/docs/) for linting and formatting.

- Format Code:

```bash
make format
```

- Check for Linting Issues:

```bash
make lint
```

## 🤝 Contributing

We welcome contributions! If you'd like to contribute, please follow these steps:

1. Fork the repository.

2. Create a new branch (git checkout -b feature/your-feature-name).

3. Make your changes and ensure tests pass (make test).

4. Commit your changes (git commit -m "feat: Add new feature").

5. Push to the branch (git push origin feature/your-feature-name).

6. Open a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
