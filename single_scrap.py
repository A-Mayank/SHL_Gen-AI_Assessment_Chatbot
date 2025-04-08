import json
import os
import re
from datetime import datetime
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# Base catalog URL
base_catalog_url = "https://www.shl.com/solutions/products/product-catalog/"
start_url = "https://www.shl.com/solutions/products/product-catalog/?page=1&type=2"

# Configure Selenium
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)

# Initialize webdriver
try:
    # Try with webdriver-manager if available
    from webdriver_manager.chrome import ChromeDriverManager

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=chrome_options
    )
except ImportError:
    # Fall back to regular ChromeDriver
    driver = webdriver.Chrome(options=chrome_options)


def validate_duration(text):
    """Validate if the text looks like a valid duration."""
    if not text:
        return False

    # Filter out cookie/storage related info
    if any(
        keyword in text.lower()
        for keyword in ["cookie", "storage", "token", "timestamp", "persistent"]
    ):
        return False

    # Should contain either numbers or time-related words
    has_numbers = bool(re.search(r"\d+", text))
    has_time_words = any(
        word in text.lower() for word in ["minute", "min", "hour", "time", "duration"]
    )

    # Should be relatively short
    is_short = len(text) < 100

    return (has_numbers or has_time_words) and is_short


def extract_assessment_links(soup):
    """Extract assessment links from a page."""
    assessment_links = []

    # Try to find assessment links in tables first
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:  # Skip header row
            cells = row.find_all("td")
            if cells:
                links = row.find_all("a", href=True)
                for link in links:
                    href = link.get("href")
                    name = link.get_text(strip=True)
                    if (
                        href
                        and name
                        and "/products/" in href
                        and name not in ["Products", "Assessments"]
                    ):
                        full_url = (
                            href
                            if href.startswith("http")
                            else f"https://www.shl.com{href}"
                        )
                        assessment_links.append((name, full_url))

    # If no assessments found in tables, try product cards or listings
    if not assessment_links:
        print("No assessments found in tables, trying alternative elements")
        # Look for product cards, lists, or grid items
        product_elements = soup.find_all(
            ["div", "li"],
            class_=lambda c: c
            and (
                "product" in str(c).lower()
                or "card" in str(c).lower()
                or "item" in str(c).lower()
                or "assessment" in str(c).lower()
            ),
        )

        for elem in product_elements:
            link = elem.find("a", href=True)
            if link:
                href = link.get("href")
                name = link.get_text(strip=True)
                if (
                    href
                    and name
                    and "/products/" in href
                    and name not in ["Products", "Assessments"]
                ):
                    if len(name) > 3 and href.count("/") >= 3:  # More specific path
                        full_url = (
                            href
                            if href.startswith("http")
                            else f"https://www.shl.com{href}"
                        )
                        assessment_links.append((name, full_url))

    # If still no assessments, scan all links with more stringent filtering
    if not assessment_links:
        print("Still no assessments found, scanning all links")
        for link in soup.find_all("a", href=True):
            href = link.get("href")
            name = link.get_text(strip=True)

            # Filter to likely assessment links
            if (
                href
                and name
                and "/products/" in href
                and "product-catalog" not in href
                and name not in ["Products", "Assessments"]
                and len(name) > 3
                and href.count("/") >= 3
            ):  # More specific paths
                full_url = (
                    href if href.startswith("http") else f"https://www.shl.com{href}"
                )
                assessment_links.append((name, full_url))

    return assessment_links


def get_next_page_url(soup, current_url):
    """Extract the next page URL from pagination."""
    next_page_url = None

    # Parse current URL to get current page number
    parsed_url = urlparse(current_url)
    query_params = parse_qs(parsed_url.query)

    # Get current page number, default to 1 if not found
    current_page = int(query_params.get("page", ["1"])[0])
    next_page_number = current_page + 1

    # Find pagination links
    pagination_elements = soup.find_all(
        class_=lambda c: c
        and ("pagination" in str(c).lower() or "pager" in str(c).lower())
    )

    # If pagination elements exist, look for next page link
    if pagination_elements:
        next_links = []
        for pagination in pagination_elements:
            next_links.extend(
                pagination.find_all(
                    "a", href=True, text=lambda t: t and str(next_page_number) in t
                )
            )
            next_links.extend(
                pagination.find_all("a", href=True, text=lambda t: t and "Next" in t)
            )

        if next_links:
            href = next_links[0].get("href")
            if href:
                next_page_url = (
                    href if href.startswith("http") else f"https://www.shl.com{href}"
                )
                return next_page_url

    # If no pagination links found, construct the next page URL
    query_params["page"] = [str(next_page_number)]
    # Make sure the 'type' parameter is included
    if "type" not in query_params:
        query_params["type"] = ["2"]

    # Rebuild the URL with updated query parameters
    new_query = urlencode(query_params, doseq=True)
    url_parts = list(parsed_url)
    url_parts[4] = new_query
    next_page_url = urlunparse(url_parts)

    return next_page_url


def scrape_assessment_details(name, url):
    """Scrape details for a specific assessment."""
    print(f"\nExamining assessment: {name} at {url}")

    try:
        # Visit the assessment detail page
        driver.get(url)
        time.sleep(3)  # Allow page to load fully

        # Get page source after JavaScript has executed
        detail_page = driver.page_source
        detail_soup = BeautifulSoup(detail_page, "html.parser")

        # Extract assessment description
        description = "Not found"
        # Try to find description in the specified class
        desc_containers = detail_soup.find_all(
            class_="product-catalogue-training-calendar__row"
        )
        for desc_container in desc_containers:
            text = desc_container.get_text(strip=True)
            if text and len(text) > 20:  # Reasonable description length
                description = text
                break

        # If still not found, look for paragraphs near the top of the page
        if description == "Not found":
            for p in detail_soup.find_all("p")[:5]:  # First few paragraphs
                text = p.get_text(strip=True)
                if text and len(text) > 40:  # Reasonable description length
                    description = text
                    break

        # Prepare assessment info dictionary
        assessment_info = {
            "name": name,
            "url": url,
            "description": description,
            "duration": "Not found",
            "test_type": "Not found",
            "remote_testing": "No",
            "adaptive_irt": "No",
            "job_levels": "Not found",  # Added field
            "languages": "Not found",  # Added field
        }

        # Get the full page text for later use
        page_text = detail_soup.get_text()

        # Look for duration using exact selectors and text patterns
        duration_elements = detail_soup.find_all(
            class_="product-catalogue-training-calendar__row"
        )
        for element in duration_elements:
            # Check if there's a <p> tag with the specific text format
            p_tags = element.find_all("p")
            for p in p_tags:
                p_text = p.get_text(strip=True)
                if "Approximate Completion Time in minutes" in p_text:
                    # Extract the minutes value
                    duration_match = re.search(r"minutes\s*=\s*(\d+)", p_text)
                    if duration_match:
                        minutes = duration_match.group(1)
                        assessment_info["duration"] = f"{minutes} minutes"
                        print(f"Found duration in p tag: {assessment_info['duration']}")
                        break

            # If not found in p tags, check the entire element text
            if assessment_info["duration"] == "Not found":
                time_text = element.get_text(strip=True)
                if "Approximate Completion Time in minutes" in time_text:
                    duration_match = re.search(r"minutes\s*=\s*(\d+)", time_text)
                    if duration_match:
                        minutes = duration_match.group(1)
                        assessment_info["duration"] = f"{minutes} minutes"
                        print(
                            f"Found duration in element text: {assessment_info['duration']}"
                        )
                        break

        # Additional duration extraction methods as fallbacks
        if assessment_info["duration"] == "Not found":
            # Try to find the duration in any text containing "Approximate"
            for element in detail_soup.find_all(
                text=re.compile("approximate", re.IGNORECASE)
            ):
                parent = element.parent
                if parent:
                    text = parent.get_text(strip=True)
                    if "time" in text.lower() and validate_duration(text):
                        duration_match = re.search(
                            r"(\d+)\s*(?:minute|min)", text, re.IGNORECASE
                        )
                        if duration_match:
                            minutes = duration_match.group(1)
                            assessment_info["duration"] = f"{minutes} minutes"
                            print(
                                f"Found duration in 'approximate' text: {assessment_info['duration']}"
                            )
                            break

        # Find elements containing "minutes" with numbers nearby
        if assessment_info["duration"] == "Not found":
            for element in detail_soup.find_all(
                text=re.compile("minutes|mins", re.IGNORECASE)
            ):
                parent = element.parent
                if parent:
                    text = parent.get_text(strip=True)
                    if validate_duration(text):
                        duration_match = re.search(
                            r"(\d+)[\s\-]*(?:minute|min)", text, re.IGNORECASE
                        )
                        if duration_match:
                            minutes = duration_match.group(1)
                            assessment_info["duration"] = f"{minutes} minutes"
                            print(
                                f"Found duration in minutes text: {assessment_info['duration']}"
                            )
                            break

        # Fallback: Look for duration using regex patterns across entire page
        if assessment_info["duration"] == "Not found":
            duration_patterns = [
                r"takes (\d+[\-\–]?\d*\s*minutes)",
                r"duration[:\s]+(\d+[\-\–]?\d*\s*(?:minute|min))",
                r"completion[:\s]+(\d+[\-\–]?\d*\s*(?:minute|min))",
                r"assessment (?:is|takes)[:\s]+(\d+[\-\–]?\d*\s*(?:minute|min))",
            ]

            for pattern in duration_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match and validate_duration(match.group(1)):
                    assessment_info["duration"] = match.group(1).strip()
                    print(f"Found duration with pattern: {assessment_info['duration']}")
                    break

        # Last attempt: Just find any number near "minutes"
        if assessment_info["duration"] == "Not found":
            minute_pattern = re.search(
                r"(\d+)[\s\-]*(?:minute|min)", page_text, re.IGNORECASE
            )
            if minute_pattern:
                minutes = minute_pattern.group(1)
                assessment_info["duration"] = f"{minutes} minutes"
                print(
                    f"Found duration as number near 'minutes': {assessment_info['duration']}"
                )

        # Extract test type using specific class
        test_type_elements = detail_soup.find_all(class_="d-flex ms-2")
        for element in test_type_elements:
            text = element.get_text(strip=True)
            if (
                text
                and not text.lower() in ["products", "assessments"]
                and len(text) < 50
            ):
                assessment_info["test_type"] = text
                print(f"Found test type with class 'd-flex ms-2': {text}")
                break

        # Look for alternate test type indicators
        if assessment_info["test_type"] == "Not found":
            test_type_patterns = [
                r"test type[:\s]+([^\.]+)",
                r"assessment type[:\s]+([^\.]+)",
                r"type of (test|assessment)[:\s]+([^\.]+)",
            ]

            for pattern in test_type_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    if len(match.groups()) > 1 and "test" in pattern:
                        test_type = match.group(2).strip()
                    else:
                        test_type = match.group(1).strip()

                    if len(test_type) < 50:
                        assessment_info["test_type"] = test_type
                        break

        # Check for remote testing indicators using specific classes
        remote_elements = detail_soup.find_all(
            class_=lambda c: c and ("ms-2" in c or "catalogue__circle -yes" in c)
        )
        for element in remote_elements:
            text = element.get_text(strip=True).lower()
            if "remote" in text or "online" in text or "web" in text:
                assessment_info["remote_testing"] = "Yes"
                print(f"Found remote testing indicator: {text}")
                break

        # Look for remote testing keywords in the page
        if assessment_info["remote_testing"] == "No":
            page_text_lower = page_text.lower()
            remote_keywords = [
                "remote testing",
                "online assessment",
                "browser-based",
                "web based",
                "digital assessment",
            ]
            for keyword in remote_keywords:
                if keyword in page_text_lower:
                    assessment_info["remote_testing"] = "Yes"
                    print(f"Found remote testing keyword: {keyword}")
                    break

        # Look for adaptive/IRT indicators
        adaptive_keywords = [
            "adaptive",
            "irt",
            "item response",
            "tailored",
            "personalized testing",
        ]
        for keyword in adaptive_keywords:
            if keyword in page_text.lower():
                assessment_info["adaptive_irt"] = "Yes"
                print(f"Found adaptive keyword: {keyword}")
                break

        # Extract job levels from product-catalogue-training-calendar__row elements
        job_levels_found = False
        job_levels = []

        # Look for rows containing job level information
        for element in detail_soup.find_all(
            class_="product-catalogue-training-calendar__row"
        ):
            text = element.get_text(strip=True).lower()
            if "job level" in text or "job levels" in text or "position level" in text:
                # Extract the content after the indicator
                job_level_match = re.search(
                    r"job levels?:?\s*(.+)", text, re.IGNORECASE
                )
                if job_level_match:
                    job_levels_content = job_level_match.group(1).strip()
                    if job_levels_content and job_levels_content != "Not found":
                        job_levels.append(job_levels_content)
                        job_levels_found = True
                        print(f"Found job levels: {job_levels_content}")

                # If not matched with regex, check if there are list items
                if not job_levels_found:
                    list_items = element.find_all("li")
                    if list_items:
                        for li in list_items:
                            job_level = li.get_text(strip=True)
                            if job_level:
                                job_levels.append(job_level)
                                job_levels_found = True
                                print(f"Found job level in list: {job_level}")

        # If job levels found, update the assessment info
        if job_levels_found:
            assessment_info["job_levels"] = ", ".join(job_levels)

        # If still not found, look for job level keywords in the page
        if assessment_info["job_levels"] == "Not found":
            job_level_keywords = [
                "entry level",
                "mid-level",
                "senior",
                "executive",
                "management",
                "individual contributor",
                "professional",
                "graduate",
                "experienced",
                "leadership",
            ]

            job_levels_found = []
            for keyword in job_level_keywords:
                if keyword in page_text.lower():
                    # Get surrounding context for better accuracy
                    pattern = r"[^.!?]*\b" + re.escape(keyword) + r"\b[^.!?]*[.!?]"
                    matches = re.findall(pattern, page_text.lower())
                    if matches:
                        job_levels_found.append(keyword)
                        print(f"Found job level keyword: {keyword}")

            if job_levels_found:
                assessment_info["job_levels"] = ", ".join(job_levels_found)

        # Extract languages from product-catalogue-training-calendar__row elements
        languages_found = False
        languages = []

        # Look for rows containing language information
        for element in detail_soup.find_all(
            class_="product-catalogue-training-calendar__row"
        ):
            text = element.get_text(strip=True).lower()
            if "language" in text or "languages" in text:
                # Extract the content after the indicator
                language_match = re.search(r"languages?:?\s*(.+)", text, re.IGNORECASE)
                if language_match:
                    languages_content = language_match.group(1).strip()
                    if languages_content and languages_content != "Not found":
                        languages.append(languages_content)
                        languages_found = True
                        print(f"Found languages: {languages_content}")

                # If not matched with regex, check if there are list items
                if not languages_found:
                    list_items = element.find_all("li")
                    if list_items:
                        for li in list_items:
                            language = li.get_text(strip=True)
                            if language:
                                languages.append(language)
                                languages_found = True
                                print(f"Found language in list: {language}")

        # If languages found, update the assessment info
        if languages_found:
            assessment_info["languages"] = ", ".join(languages)

        # If still not found, look for common language names in the page
        if assessment_info["languages"] == "Not found":
            common_languages = [
                "english",
                "spanish",
                "french",
                "german",
                "italian",
                "portuguese",
                "chinese",
                "japanese",
                "korean",
                "russian",
                "arabic",
                "hindi",
                "dutch",
                "swedish",
                "norwegian",
                "danish",
            ]

            languages_found = []
            # Look for a section that might list languages
            language_section_pattern = r"(?:available in|languages?:?)[^.!?]+"
            language_sections = re.findall(language_section_pattern, page_text.lower())

            if language_sections:
                for section in language_sections:
                    for language in common_languages:
                        if language in section.lower():
                            languages_found.append(language.capitalize())
                            print(f"Found language in section: {language}")

            # If no language section found, check for languages anywhere in the text
            if not languages_found:
                for language in common_languages:
                    if language in page_text.lower():
                        languages_found.append(language.capitalize())
                        print(f"Found language keyword: {language}")

            if languages_found:
                assessment_info["languages"] = ", ".join(languages_found)

        # Print summary of results
        print(f"\n✅ Results for: {assessment_info['name']}")
        print(f"📝 Description: {assessment_info['description'][:100]}...")
        print(f"🕒 Duration: {assessment_info['duration']}")
        print(f"🧪 Test Type: {assessment_info['test_type']}")
        print(f"📡 Remote Testing Support: {assessment_info['remote_testing']}")
        print(f"🔁 Adaptive/IRT Support: {assessment_info['adaptive_irt']}")
        print(f"👔 Job Levels: {assessment_info['job_levels']}")
        print(f"🌐 Languages: {assessment_info['languages']}")

        return assessment_info

    except Exception as e:
        print(f"Error scraping assessment {name}: {str(e)}")
        return {
            "name": name,
            "url": url,
            "description": "Error during scraping",
            "duration": "Error",
            "test_type": "Error",
            "remote_testing": "Error",
            "adaptive_irt": "Error",
            "job_levels": "Error",
            "languages": "Error",
            "error": str(e),
        }


def main():
    """Main function to scrape multiple pages and assessments."""
    try:
        # Initialize data structure for JSON
        all_assessment_data = {
            "scrape_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_url": start_url,
            "assessments": [],
        }

        # Set the starting URL
        current_url = start_url
        max_pages = 20  # Limit to prevent infinite loops
        page_counter = 1
        total_assessments_processed = 0

        while current_url and page_counter <= max_pages:
            print(f"\n{'='*80}")
            print(f"⏳ Processing page {page_counter}: {current_url}")
            print(f"{'='*80}")

            # Access the page
            driver.get(current_url)
            time.sleep(3)  # Allow page to load

            # Get page source
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")

            # Extract assessment links from current page
            assessment_links = extract_assessment_links(soup)
            print(
                f"📋 Found {len(assessment_links)} assessments on page {page_counter}"
            )

            # Process each assessment
            page_assessments_processed = 0
            for name, url in assessment_links:
                # Add a small delay to avoid overloading the server
                time.sleep(random.uniform(1, 2))

                # Scrape assessment details
                assessment_info = scrape_assessment_details(name, url)
                if assessment_info:
                    all_assessment_data["assessments"].append(assessment_info)
                    page_assessments_processed += 1
                    total_assessments_processed += 1

                # Optional: Limit number of assessments per page (for testing)
                # if page_assessments_processed >= 3:
                #     break

            print(
                f"✅ Processed {page_assessments_processed} assessments on page {page_counter}"
            )

            # Find next page URL
            next_url = get_next_page_url(soup, current_url)
            if next_url and next_url != current_url:
                current_url = next_url
                page_counter += 1
                print(f"⏭️ Moving to next page: {current_url}")
                # Add a delay between pages
                time.sleep(random.uniform(2, 4))
            else:
                print("🏁 No more pages found or reached last page")
                break

        # Save data to JSON file
        filename = (
            f"shl_assessment_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(all_assessment_data, f, indent=4, ensure_ascii=False)

        print(f"\n{'='*80}")
        print(
            f"🎉 Scraping completed! Processed {total_assessments_processed} assessments across {page_counter} pages"
        )
        print(f"💾 Data saved to {os.path.abspath(filename)}")
        print(f"{'='*80}")

    except Exception as e:
        print(f"Error in main scraping process: {str(e)}")
        import traceback

        traceback.print_exc()

    finally:
        # Clean up
        driver.quit()


# Run the main function
if __name__ == "__main__":
    main()
