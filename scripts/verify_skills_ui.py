from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    
    errors = []
    page.on("console", lambda msg: errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda err: errors.append(f"[PAGEERROR] {err}"))
    
    # LOGIN
    page.goto("http://localhost:3000/auth/signin")
    page.wait_for_load_state("networkidle")
    page.fill('input[name="email"]', "test@cogninets.local")
    page.fill('input[name="password"]', "Password123!")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2500)
    
    # SKILL TAB
    page.goto("http://localhost:3000/organization?org_id=4cb21885-2b74-435e-a997-f02f600945ac&tab=skills")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(4000)
    page.screenshot(path="/tmp/01_skills_tab.png", full_page=True)
    
    body_text = page.text_content("body")
    print("=== Page text (first 800 chars) ===")
    print(body_text[:800])
    
    print(f"\n=== Errors ({len(errors)}): ===")
    for e in errors:
        print(f"  {e}")
    
    if "Browse Platform Library" in body_text:
        print("\nSUCCESS: Browse Platform Library button present")
    elif "Library" in body_text:
        print("\nPARTIAL: Library-related text found but not exact match")
    else:
        print("\nMISSING: No Library button text found")
    
    if "No skills yet" in body_text:
        print("INFO: Empty state displayed")
    
    if "Something went wrong" in body_text.lower():
        print("WARNING: Error state detected")
    
    browser.close()
