# CampusEats

CampusEats connects campus food vendors that have leftover food with students who want it, reducing food waste and hunger on campus.

---

## How to Run Locally

### 1. Clone the Repository
```bash
git clone git@github.com:Riconashty/campuseats.git
cd campuseats
```

### 2. Create and Activate Virtual Environment
```bash
python3 -m venv .venv
```
- **macOS / Linux:** `source .venv/bin/activate`
- **Windows:** `.venv\Scripts\activate`

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install -e .
```

### 4. Create Environment Configuration
```bash
cp .env.example .env
```

### 5. Run the Application
```bash
python run.py
```
Open `http://localhost:5000` in your browser.

### 6. Run Tests
```bash
python -m unittest discover tests
```
