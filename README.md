# AV Fashion - Intentionally Vulnerable Flask App (TryHackMe Room)

AV Fashion is a small fashion store website with 3–4+ intentionally designed vulnerabilities mapped to OWASP Top 10. Use it to practice exploitation in a safe environment. Flags are revealed when you successfully exploit the vulnerabilities.

Important: This is for educational purposes only. Do not deploy to the internet.

## Quick Start

1. Python 3.10+
2. Install dependencies:
```bash
python -m venv venv
venv\Scripts\activate  # on Windows PowerShell
pip install -r requirements.txt
```
3. Run the app:
```bash
python app.py
```
4. Browse to `http://127.0.0.1:5000`

The app auto-creates `database.db` and seeds users/products. Placeholder images are generated under `static/images/` as `image1.jpg` … `image9.jpg`.

## App Overview (What to expect)
- Home page shows 9 new dresses, each with image, small description, and a "Check stock" badge. A line on the page reminds users: for buy please sign in.
- Navbar: Login, Signup, Upload, Profile (after login), and a Search box.
- Auth, Search, Comments, Profile, File view, and Upload routes are deliberately unsafe.

## Vulnerabilities and Flags

- SQL Injection (Login) — OWASP Top 10: A03:2021-Injection
  - Route: `/login`
  - Vulnerable SQL: `SELECT id, username FROM users WHERE username = '<user>' AND password = '<pass>'`
  - Example credential payloads:
    - Username: `' OR 1=1 --`
    - Password: anything
  - On a successful auth bypass, visit `http://127.0.0.1:5000/flag/sqli` for the flag.
  - Flag: `THM{sqli_login_bypass_success}`

- SQL Injection (Search) — OWASP Top 10: A03:2021-Injection
  - Route: `/search?q=<payload>`
  - Vulnerable SQL: `... WHERE name LIKE '%<q>%' OR description LIKE '%<q>%'`
  - Example payload ideas:
    - `%25' OR 1=1 --` (URL encoded `%` = `%25`)
    - `' UNION SELECT ...` (exploration)
  - Use to enumerate data and confirm injection is possible.

- Stored XSS (Comments) — OWASP Top 10: A03:2021-Injection
  - Route: `/product/<id>`
  - Post a comment that includes a `<script>` tag; it is stored and rendered unsanitized using `|safe`.
  - Minimal payload ideas:
    - `<script>alert('xss')</script>`
    - `<script>fetch('/flag/xss').then(r=>r.text()).then(t=>document.body.insertAdjacentHTML('afterbegin','<div class="alert">'+t+'</div>'))</script>`
  - Flag endpoint: `http://127.0.0.1:5000/flag/xss`
  - Flag: `THM{stored_xss_comment_pop_executed}`

- IDOR (Profile) — OWASP Top 10: A01:2021-Broken Access Control
  - Route: `/profile/<user_id>`
  - There is no authorization check; change the `user_id` in the URL to view other users.
  - Example: log in as any user, then navigate to `/profile/3` to view the admin profile.
  - Flag endpoint: `http://127.0.0.1:5000/flag/idor`
  - Flag: `THM{insecure_direct_object_reference_profile}`

- Path Traversal (File View) — OWASP Top 10: A05:2021-Security Misconfiguration
  - Route: `/view?path=<relative_or_traversal>`
  - Reads files by joining the input path to the app base directory without proper validation.
  - Examples:
    - `/view?path=app.py`
    - `/view?path=../database.db`
    - Windows-style: `/view?path=..\\database.db`
  - Flag endpoint: `http://127.0.0.1:5000/flag/path`
  - Flag: `THM{directory_traversal_exposed_sensitive_file}`

- Unsafe File Upload — OWASP Top 10: A05:2021-Security Misconfiguration
  - Route: `/upload` (requires login)
  - No file-type checking; filenames are not sanitized; files served at `/uploads/<filename>`.
  - Try uploading arbitrary files, e.g., `.html`, `.js`, or `.php` (note: served as static). Then access them under `/uploads/`.
  - Flag endpoint: `http://127.0.0.1:5000/flag/upload`
  - Flag: `THM{arbitrary_file_upload_and_execute}`

## Suggested Exploitation Path (Walkthrough)

1. Recon
   - Visit `/` to see products and hints. Try the Search box with normal queries.
2. SQLi Login Bypass
   - Go to `/login`. Use username `' OR 1=1 --` and any password to bypass login.
   - Confirm you are logged in; profile and logout appear in navbar.
   - Visit `/flag/sqli` to capture the SQLi flag.
3. IDOR
   - Browse your profile, then change the URL to `/profile/3`. Capture `/flag/idor`.
4. Stored XSS
   - Go to a product like `/product/1`. Submit a comment with a `<script>` payload that fetches and displays the XSS flag:
     ```html
     <script>fetch('/flag/xss').then(r=>r.text()).then(t=>document.body.insertAdjacentHTML('afterbegin','<div class="alert">'+t+'</div>'))</script>
     ```
   - Reload the product page to execute the stored payload and display the flag.
5. Path Traversal
   - Access `/view?path=app.py` and `/view?path=../database.db` to read files. Capture `/flag/path`.
6. Unsafe Upload
   - Log in and visit `/upload`. Upload a `.html` or `.js` file and access it under `/uploads/yourfile`. Capture `/flag/upload`.

## Content and Styling Details (as requested)
- Site name: AV Fashion
- Dark blue background across pages.
- Home page shows 9 images named `image1.jpg` ... `image9.jpg`.
- Each product card has a small description, stock value (like 40, 20...), and a line reminding that to buy, please sign in.

## Mapping to OWASP Top 10 (Summary)
- **A01: Broken Access Control**: IDOR (`/profile/<id>`) — no authorization check.
- **A03: Injection**: SQLi in Login and Search; Stored XSS in Comments.
- **A05: Security Misconfiguration**: Path Traversal (`/view`); Unsafe File Upload (`/upload`).

## Diagrams / Screenshots (placeholders)
- Architecture: Browser ⇄ Flask ⇄ SQLite; Static images served from `static/images/`.
- Add your own screenshots of: Home page, SQLi exploit, XSS comment, IDOR profile change, Traversal output, and Uploaded file access.

## Reflection (Prompts)
- Design choices to intentionally include flaws while keeping UX realistic.
- Challenges balancing discoverability vs. subtlety of vulnerabilities.
- Learning outcomes around input handling, access control, and safe file processing.

## Resetting the Environment
- Stop the server and delete `database.db` to reset data, then rerun `python app.py`.

## Disclaimer
This project is intentionally insecure. Use only in isolated, local environments.

