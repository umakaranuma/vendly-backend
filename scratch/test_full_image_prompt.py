import requests
import urllib.parse
import json

def test_full_image_generation():
    # Example event data
    event_type = "Wedding"
    headline = "Two hearts, one journey"
    subheadline = "Michael & Sarah's Wedding Ceremony"
    body = "Join us as we exchange vows and celebrate our love."
    date = "May 24, 2026"
    venue = "Grand Emerald Hotel"
    time = "4:00 PM"

    # Strategy: Use Gemini to create a "Design Prompt"
    # For this test, I'll manually create the prompt I think Gemini should generate
    design_prompt = (
        f"A complete, professional graphic design for a {event_type} invitation. "
        f"The card features an elegant, high-end {event_type} theme with icons like flowers, rings, and sparkles. "
        f"Typography is the main feature. The image MUST contain the following readable text clearly written in beautiful fonts: "
        f"'{headline}', '{subheadline}', 'Date: {date}', 'Venue: {venue}', 'Time: {time}'. "
        f"The layout should be centered, symmetrical, luxury invitation card, 4k resolution, graphic design masterpiece."
    )

    encoded_prompt = urllib.parse.quote(design_prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&enhance=true&model=flux"
    
    print(f"Proposed Image URL: {image_url}")

if __name__ == "__main__":
    test_full_image_generation()
