# app/agents/subscription_agent.py - Advanced Subscription Agent for C.A.T.S. v2.0
# Production-ready agent with semantic web navigation, multi-language form detection,
# dynamic field mapping, and security question handling.
# Uses the subscription profile from app.config.subscription_config.

import os
import sys
import json
import logging
import time
import random
import re
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urljoin, urlparse

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

# HTML parsing and form handling
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
    logging.warning("BeautifulSoup not installed; HTML parsing will be limited.")

# Language detection
try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed(0)  # for consistent results
except ImportError:
    detect = None
    logging.warning("langdetect not installed; language detection will be disabled.")

# Optional: Selenium for JavaScript-heavy pages
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logging.warning("Selenium not installed; fallback to requests-based navigation.")

# Import subscription configuration
from app.config.subscription_config import get_subscription_profile, get_subscription_field

# ------------------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------------
DEFAULT_REGISTER_URL = os.environ.get("SUBSCRIPTION_REGISTER_URL", "https://example.com/register")
DEFAULT_LOGIN_URL = os.environ.get("SUBSCRIPTION_LOGIN_URL", "https://example.com/login")
DEFAULT_TRIAL_URL = os.environ.get("SUBSCRIPTION_TRIAL_URL", "https://example.com/trial")
DEFAULT_USER_AGENT = "C.A.T.S.-v2.0-SubscriptionAgent/1.0"
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 1.0

# ------------------------------------------------------------------------------
# Multilingual Semantic Dictionaries
# ------------------------------------------------------------------------------
# Mapping of language codes to dictionaries of field labels (canonical -> list of possible labels)
LANGUAGE_DICTIONARIES = {
    "en": {
        "name": ["name", "full name", "your name", "first and last name"],
        "first_name": ["first name", "given name", "first"],
        "last_name": ["last name", "surname", "family name", "last"],
        "email": ["email", "e-mail", "email address", "e-mail address"],
        "password": ["password", "pwd", "pass", "create password", "confirm password"],
        "confirm_password": ["confirm password", "re-enter password", "password confirmation"],
        "zipcode": ["zip", "zip code", "postal code", "postcode"],
        "address_line1": ["address", "street address", "address line 1", "addr line1"],
        "address_line2": ["address line 2", "apt", "suite", "unit", "address line 2"],
        "city": ["city", "town"],
        "state": ["state", "province", "region", "county"],
        "country": ["country", "nation"],
        "card_number": ["card number", "credit card", "credit card number", "cc number"],
        "card_expiry_month": ["expiration month", "expiry month", "month", "expiration month"],
        "card_expiry_year": ["expiration year", "expiry year", "year", "expiration year"],
        "card_cvv": ["cvv", "cvc", "security code", "verification code"],
        "security_question": ["security question", "secret question", "security question"],
        "security_answer": ["security answer", "answer", "your answer"],
    },
    "es": {
        "name": ["nombre", "nombre completo", "nombre y apellidos"],
        "first_name": ["nombre", "primer nombre", "nombre de pila"],
        "last_name": ["apellido", "apellidos", "primer apellido"],
        "email": ["correo", "email", "correo electrónico"],
        "password": ["contraseña", "clave", "contraseña", "confirmar contraseña"],
        "confirm_password": ["confirmar contraseña", "repetir contraseña"],
        "zipcode": ["código postal", "código postal", "zip"],
        "address_line1": ["dirección", "calle", "dirección línea 1"],
        "address_line2": ["dirección línea 2", "apt", "suite", "piso"],
        "city": ["ciudad", "población"],
        "state": ["estado", "provincia", "región"],
        "country": ["país"],
        "card_number": ["número de tarjeta", "tarjeta de crédito", "número de tarjeta de crédito"],
        "card_expiry_month": ["mes de vencimiento", "mes expiración", "mes"],
        "card_expiry_year": ["año de vencimiento", "año expiración", "año"],
        "card_cvv": ["cvv", "código de seguridad", "código de verificación"],
        "security_question": ["pregunta de seguridad", "pregunta secreta"],
        "security_answer": ["respuesta de seguridad", "respuesta", "tu respuesta"],
    },
    "fr": {
        "name": ["nom", "nom complet", "prénom et nom"],
        "first_name": ["prénom", "prénom", "nom de famille"],
        "last_name": ["nom de famille", "patronyme"],
        "email": ["e-mail", "email", "adresse email"],
        "password": ["mot de passe", "mdp", "mot de passe", "confirmer le mot de passe"],
        "confirm_password": ["confirmer le mot de passe", "vérifier le mot de passe"],
        "zipcode": ["code postal", "cp", "zip"],
        "address_line1": ["adresse", "rue", "ligne d'adresse 1"],
        "address_line2": ["ligne d'adresse 2", "apt", "appartement", "suite"],
        "city": ["ville", "commune"],
        "state": ["état", "région", "province"],
        "country": ["pays"],
        "card_number": ["numéro de carte", "carte de crédit", "numéro de carte de crédit"],
        "card_expiry_month": ["mois d'expiration", "mois", "mois d'échéance"],
        "card_expiry_year": ["année d'expiration", "année", "année d'échéance"],
        "card_cvv": ["cvv", "code de sécurité", "code de vérification"],
        "security_question": ["question de sécurité", "question secrète"],
        "security_answer": ["réponse de sécurité", "réponse", "votre réponse"],
    },
    "de": {
        "name": ["name", "vollständiger Name", "vor- und nachname"],
        "first_name": ["vorname", "erster Name"],
        "last_name": ["nachname", "familienname"],
        "email": ["e-mail", "email", "e-mail-adresse"],
        "password": ["passwort", "kennwort", "passwort", "passwort bestätigen"],
        "confirm_password": ["passwort bestätigen", "wiederholen Sie das passwort"],
        "zipcode": ["postleitzahl", "plz", "zip"],
        "address_line1": ["adresse", "straße", "adresszeile 1"],
        "address_line2": ["adresszeile 2", "apt", "suite", "etage"],
        "city": ["stadt", "ort"],
        "state": ["bundesland", "staat", "region"],
        "country": ["land"],
        "card_number": ["kartennummer", "kreditkartennummer", "kreditkarten-nummer"],
        "card_expiry_month": ["ablaufmonat", "monat", "ablauf monat"],
        "card_expiry_year": ["ablaufjahr", "jahr", "ablauf jahr"],
        "card_cvv": ["cvv", "sicherheitscode", "prüfziffer"],
        "security_question": ["sicherheitsfrage", "geheimfrage"],
        "security_answer": ["sicherheitsantwort", "antwort", "ihre antwort"],
    },
    # Add more languages as needed
}

# Fallback dictionary (English)
FALLBACK_DICT = LANGUAGE_DICTIONARIES.get("en", {})

# ------------------------------------------------------------------------------
# Helper functions for language detection
# ------------------------------------------------------------------------------
def detect_language(text: str) -> str:
    """
    Detect the language of a text using langdetect or fallback to heuristics.
    Returns a language code (ISO 639-1) or 'en' as default.
    """
    if not text or len(text.strip()) < 10:
        return "en"
    if detect is not None:
        try:
            lang = detect(text)
            # langdetect returns e.g., 'en', 'es', 'fr'
            return lang
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
    # Fallback: check for common words
    text_lower = text.lower()
    # Simple heuristic: look for common words
    if re.search(r'\b(the|and|you|for|with|this)\b', text_lower):
        return "en"
    if re.search(r'\b(el|la|los|las|un|una|y|que|en)\b', text_lower):
        return "es"
    if re.search(r'\b(le|la|les|et|pour|avec|sur|par)\b', text_lower):
        return "fr"
    if re.search(r'\b(der|die|das|und|zu|mit|von|für)\b', text_lower):
        return "de"
    return "en"

def get_dictionary_for_language(lang: str) -> Dict[str, List[str]]:
    """Return the semantic dictionary for a given language, or fallback."""
    return LANGUAGE_DICTIONARIES.get(lang, FALLBACK_DICT)

def normalize_field_label(label: str) -> str:
    """Normalize a label string for matching."""
    # Remove extra spaces, lower case, remove punctuation
    label = re.sub(r'[^\w\s]', '', label)
    label = label.lower().strip()
    return label

# ------------------------------------------------------------------------------
# Advanced Subscription Agent
# ------------------------------------------------------------------------------
class SubscriptionAgent:
    """
    Advanced agent with semantic web navigation and multi-language form processing.
    """

    def __init__(
        self,
        register_url: Optional[str] = None,
        login_url: Optional[str] = None,
        trial_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        user_agent: str = DEFAULT_USER_AGENT,
        use_selenium: bool = False,
        headless: bool = True,
    ):
        """
        Initialize the SubscriptionAgent.

        Args:
            register_url: URL for registration page.
            login_url: URL for login page.
            trial_url: URL for trial activation.
            timeout: Request timeout in seconds.
            max_retries: Number of retries for failed requests.
            user_agent: User-Agent string to use.
            use_selenium: If True, use Selenium for JavaScript-rendered pages.
            headless: Whether to run Selenium in headless mode.
        """
        self.register_url = register_url or DEFAULT_REGISTER_URL
        self.login_url = login_url or DEFAULT_LOGIN_URL
        self.trial_url = trial_url or DEFAULT_TRIAL_URL
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.headless = headless

        # Load profile
        self.profile = get_subscription_profile()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
        self.session.timeout = self.timeout

        # Selenium driver (lazy initialization)
        self.driver = None

        # Tokens
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

        logger.info("Advanced SubscriptionAgent initialized.")

    def _init_selenium(self):
        """Initialize the Selenium WebDriver if not already."""
        if not self.use_selenium:
            return
        if self.driver is not None:
            return
        if not SELENIUM_AVAILABLE:
            logger.warning("Selenium not available; falling back to requests-based navigation.")
            self.use_selenium = False
            return
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(self.timeout)
            logger.info("Selenium WebDriver initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium WebDriver: {e}")
            self.use_selenium = False
            self.driver = None

    def _get_field(self, path: str, default: Any = None) -> Any:
        """Retrieve a field from the subscription profile using dot notation."""
        return get_subscription_field(path, default)

    def _extract_forms_from_html(self, html: str, base_url: str) -> List[Dict]:
        """
        Parse HTML and extract forms with their fields, labels, and action URLs.
        Returns a list of form dictionaries.
        """
        if BeautifulSoup is None:
            raise ImportError("BeautifulSoup is required for HTML parsing.")
        soup = BeautifulSoup(html, 'html.parser')
        forms = []
        for form in soup.find_all('form'):
            form_data = {
                'action': urljoin(base_url, form.get('action', '')),
                'method': form.get('method', 'get').upper(),
                'fields': [],
                'security_questions': [],
            }
            # Find input elements
            inputs = form.find_all(['input', 'select', 'textarea'])
            for elem in inputs:
                field = {
                    'name': elem.get('name', ''),
                    'type': elem.get('type', 'text'),
                    'id': elem.get('id', ''),
                    'placeholder': elem.get('placeholder', ''),
                    'value': elem.get('value', ''),
                    'required': elem.get('required', False),
                    'multiple': elem.get('multiple', False),
                }
                # For select, get options
                if elem.name == 'select':
                    options = elem.find_all('option')
                    field['options'] = [opt.get('value', '') for opt in options if opt.get('value')]
                # Try to find associated label
                label_elem = None
                label_text = ''
                # 1. Check for label with 'for' attribute
                if field['id']:
                    label_elem = soup.find('label', {'for': field['id']})
                if not label_elem:
                    # 2. Check if input is inside a label
                    label_elem = elem.find_parent('label')
                if label_elem:
                    label_text = label_elem.get_text(strip=True)
                # 3. Check for placeholder as label proxy
                if not label_text and field['placeholder']:
                    label_text = field['placeholder']
                field['label'] = label_text
                form_data['fields'].append(field)
                # Detect security question fields based on label
                if 'question' in label_text.lower() or 'security' in label_text.lower():
                    form_data['security_questions'].append(field)
            forms.append(form_data)
        return forms

    def _detect_form_field_mapping(
        self,
        fields: List[Dict],
        language: str
    ) -> Dict[str, str]:
        """
        Map form fields to profile fields using semantic dictionaries.
        Returns a dict mapping form field names to profile field names.
        """
        dictionary = get_dictionary_for_language(language)
        # Build reverse mapping: label -> canonical key
        label_to_canonical = {}
        for canonical, labels in dictionary.items():
            for lbl in labels:
                normalized = normalize_field_label(lbl)
                label_to_canonical[normalized] = canonical

        mapping = {}
        for field in fields:
            label = field.get('label', '')
            name = field.get('name', '')
            placeholder = field.get('placeholder', '')
            # Combine label, name, placeholder for matching
            candidates = []
            if label:
                candidates.append(label)
            if name:
                candidates.append(name.replace('_', ' '))
            if placeholder:
                candidates.append(placeholder)
            # Try to find a match
            matched = False
            for candidate in candidates:
                normalized = normalize_field_label(candidate)
                if normalized in label_to_canonical:
                    canonical = label_to_canonical[normalized]
                    mapping[field['name']] = canonical
                    matched = True
                    logger.debug(f"Mapped form field '{field['name']}' -> '{canonical}'")
                    break
            # If no match, fallback to heuristic (e.g., contains 'email')
            if not matched:
                if 'email' in field['name'].lower() or 'e-mail' in field['name'].lower():
                    mapping[field['name']] = 'email'
                elif 'pass' in field['name'].lower():
                    mapping[field['name']] = 'password'
                elif 'name' in field['name'].lower():
                    # Might need to differentiate first/last
                    # We'll handle separately in fill logic
                    pass
        return mapping

    def _fill_form_fields(
        self,
        form_fields: List[Dict],
        mapping: Dict[str, str],
        profile_data: Dict[str, Any],
        language: str
    ) -> Dict[str, Any]:
        """
        Fill the form fields with values from the profile based on mapping.
        Returns a dictionary of field_name -> value to submit.
        """
        values = {}
        for field in form_fields:
            name = field['name']
            if not name:
                continue
            canonical = mapping.get(name)
            if not canonical:
                # Try to guess using name
                if 'email' in name.lower():
                    canonical = 'email'
                elif 'pass' in name.lower() and 'confirm' not in name.lower():
                    canonical = 'password'
                elif 'confirm' in name.lower():
                    canonical = 'confirm_password'
                elif 'zip' in name.lower() or 'postal' in name.lower():
                    canonical = 'zipcode'
                elif 'card' in name.lower() or 'credit' in name.lower():
                    canonical = 'card_number'
                elif 'cvv' in name.lower() or 'cvc' in name.lower():
                    canonical = 'card_cvv'
                elif 'expiry' in name.lower() or 'expiration' in name.lower():
                    if 'month' in name.lower():
                        canonical = 'card_expiry_month'
                    elif 'year' in name.lower():
                        canonical = 'card_expiry_year'
                elif 'security' in name.lower() and 'question' in name.lower():
                    canonical = 'security_question'
                elif 'answer' in name.lower():
                    canonical = 'security_answer'
                else:
                    continue  # skip unknown fields
            # Retrieve value from profile
            value = self._get_field(canonical, None)
            if value is not None:
                # Handle special fields like password
                if canonical == 'password':
                    # If we have a confirm password field, we can set same value
                    pass
                # For security questions, we might need to choose from options
                if canonical == 'security_question' and field.get('options'):
                    # Select first option as a fallback
                    options = field.get('options', [])
                    if options:
                        value = options[0]
                    else:
                        value = "What is your favorite color?"  # placeholder
                values[name] = value
                logger.debug(f"Set field '{name}' -> {canonical} (value: {value})")
            else:
                # If no value, maybe skip or set placeholder
                logger.warning(f"No profile value found for '{canonical}', skipping field '{name}'")
        return values

    def _submit_form_requests(self, form_data: Dict, values: Dict) -> requests.Response:
        """
        Submit the form using requests (GET/POST).
        """
        method = form_data.get('method', 'GET')
        action = form_data.get('action', '')
        if method.upper() == 'GET':
            response = self.session.get(action, params=values, timeout=self.timeout)
        else:
            response = self.session.post(action, data=values, timeout=self.timeout)
        return response

    def _submit_form_selenium(self, form_index: int, values: Dict) -> str:
        """
        Submit the form using Selenium WebDriver.
        Returns the final page HTML after submission.
        """
        if self.driver is None:
            self._init_selenium()
        if self.driver is None:
            raise RuntimeError("Selenium driver not available.")
        # Find all forms
        forms = self.driver.find_elements(By.TAG_NAME, "form")
        if form_index >= len(forms):
            raise ValueError(f"Form index {form_index} out of range.")
        form = forms[form_index]
        # Fill fields
        for name, value in values.items():
            try:
                # Try by name
                elem = self.driver.find_element(By.NAME, name)
                if elem.tag_name == 'select':
                    select = Select(elem)
                    select.select_by_value(str(value))
                elif elem.tag_name == 'input' and elem.get_attribute('type') == 'checkbox':
                    if value in (True, 'true', 'on', '1'):
                        if not elem.is_selected():
                            elem.click()
                else:
                    elem.clear()
                    elem.send_keys(str(value))
            except NoSuchElementException:
                # Try by id or other locator
                try:
                    elem = self.driver.find_element(By.ID, name)
                    elem.clear()
                    elem.send_keys(str(value))
                except NoSuchElementException:
                    logger.warning(f"Could not find field '{name}' for filling.")
        # Submit
        form.submit()
        # Wait for page load
        time.sleep(2)
        return self.driver.page_source

    def register(self) -> Dict[str, Any]:
        """
        Perform the advanced registration flow using semantic form analysis.
        """
        logger.info("Starting advanced registration flow...")
        # Determine if we use Selenium or requests
        if self.use_selenium:
            self._init_selenium()
            if self.driver is None:
                logger.warning("Selenium driver unavailable, falling back to requests.")
                self.use_selenium = False
        # Fetch registration page
        if self.use_selenium:
            self.driver.get(self.register_url)
            time.sleep(2)  # wait for dynamic content
            html = self.driver.page_source
        else:
            response = self.session.get(self.register_url)
            response.raise_for_status()
            html = response.text

        # Detect language of page
        page_text = BeautifulSoup(html, 'html.parser').get_text() if BeautifulSoup else html[:1000]
        language = detect_language(page_text)
        logger.info(f"Detected page language: {language}")

        # Extract forms
        forms = self._extract_forms_from_html(html, self.register_url)
        if not forms:
            raise RuntimeError("No forms found on registration page.")

        # Use the first form (often the registration form)
        form_data = forms[0]
        fields = form_data['fields']

        # Map fields
        mapping = self._detect_form_field_mapping(fields, language)

        # Prepare profile data (we already have self.profile)
        # Fill values
        values = self._fill_form_fields(fields, mapping, self.profile, language)

        # Submit form
        if self.use_selenium:
            # We need to submit the form using Selenium
            # We'll re-fill using Selenium (since we already have values)
            # We'll call _submit_form_selenium with index 0
            html_after = self._submit_form_selenium(0, values)
            # Parse response for success/error
            # We'll attempt to detect if registration succeeded
            if "success" in html_after.lower() or "thank" in html_after.lower():
                logger.info("Registration likely successful via Selenium.")
                # Extract any tokens from cookies or response
                # We can get cookies
                cookies = self.driver.get_cookies()
                # Store session cookies in requests session
                for cookie in cookies:
                    self.session.cookies.set(cookie['name'], cookie['value'])
                # Optionally retrieve redirect URL
                current_url = self.driver.current_url
                return {"status": "SUCCESS", "url": current_url, "cookies": cookies}
            else:
                raise RuntimeError("Registration failed. Check page for errors.")
        else:
            # Submit via requests
            response = self._submit_form_requests(form_data, values)
            # Check response
            if response.status_code in (200, 201, 302):
                logger.info("Registration request successful.")
                # Extract any tokens from response
                data = {}
                try:
                    data = response.json()
                except:
                    # Try to parse HTML for success message
                    soup = BeautifulSoup(response.text, 'html.parser')
                    if soup.find('div', class_='success') or "success" in response.text.lower():
                        data = {"message": "Registration successful"}
                return data
            else:
                raise RuntimeError(f"Registration failed with status {response.status_code}")

    def login(self) -> Dict[str, Any]:
        """Perform login (similar to registration but simpler)."""
        # For brevity, we assume login works similarly; we'll implement a simplified version
        logger.info("Performing login...")
        email = self._get_field("email")
        password = self._get_field("password")
        if not email or not password:
            raise ValueError("Email and password required.")
        payload = {"email": email, "password": password}
        response = self.session.post(self.login_url, json=payload)
        response.raise_for_status()
        data = response.json()
        self.access_token = data.get("access_token")
        self.refresh_token = data.get("refresh_token")
        if self.access_token:
            self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
        return data

    def activate_trial(self) -> Dict[str, Any]:
        """Activate trial using the session."""
        logger.info("Activating trial...")
        response = self.session.post(self.trial_url, json={})
        response.raise_for_status()
        return response.json()

    def run_full_workflow(self) -> Dict[str, Any]:
        """Execute the complete workflow: register, login, trial activation."""
        results = {"status": "PENDING", "steps": []}

        try:
            # Step 1: Register (using advanced semantic form filling)
            register_result = self.register()
            results["steps"].append({"step": "register", "status": "SUCCESS", "data": register_result})
        except Exception as e:
            logger.error(f"Registration step failed: {e}")
            results["steps"].append({"step": "register", "status": "FAILED", "error": str(e)})
            results["status"] = "FAILED"
            return results

        # Step 2: Login (if not already authenticated)
        try:
            if not self.access_token:
                login_result = self.login()
                results["steps"].append({"step": "login", "status": "SUCCESS", "data": login_result})
            else:
                results["steps"].append({"step": "login", "status": "SKIPPED", "reason": "Already authenticated"})
        except Exception as e:
            logger.error(f"Login step failed: {e}")
            results["steps"].append({"step": "login", "status": "FAILED", "error": str(e)})
            results["status"] = "FAILED"
            return results

        # Step 3: Activate trial
        try:
            trial_result = self.activate_trial()
            results["steps"].append({"step": "trial", "status": "SUCCESS", "data": trial_result})
        except Exception as e:
            logger.error(f"Trial activation step failed: {e}")
            results["steps"].append({"step": "trial", "status": "FAILED", "error": str(e)})
            results["status"] = "PARTIAL_FAILURE"
            return results

        results["status"] = "SUCCESS"
        return results

    def logout(self) -> None:
        """Clean up session and Selenium driver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
        self.session.close()
        logger.info("Logged out and cleaned up.")

# ------------------------------------------------------------------------------
# Command-line entry point for testing
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Example usage with environment variables
    agent = SubscriptionAgent(
        register_url=os.environ.get("SUBSCRIPTION_REGISTER_URL", "https://example.com/register"),
        login_url=os.environ.get("SUBSCRIPTION_LOGIN_URL", "https://example.com/login"),
        trial_url=os.environ.get("SUBSCRIPTION_TRIAL_URL", "https://example.com/trial"),
        use_selenium=os.environ.get("USE_SELENIUM", "false").lower() == "true"
    )
    try:
        result = agent.run_full_workflow()
        print("Workflow result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
    finally:
        agent.logout()
