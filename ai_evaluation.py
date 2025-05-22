from openai import OpenAI

def analyze_email(email_body, openai_api_key):
    client = OpenAI(api_key=openai_api_key)
    prompt = f"""
You are a helpful assistant for a venture capital firm.

Given the body of an email, do the following:
Determine if the email is a cold outreach email. These are usually from startups, tech transfer offices, or entrepreneurs reaching out. Make sure not to confuse company newsletters, ads, etc. for cold outreach emails.
Reply with only one word first: "Yes" if it's a cold outreach email, "No" if it is not.
Then, on a new line, extract and write the summary of the company information in the email. If a summary isn't explicitly stated, infer or draft a 2-3 sentence summary.
If you find a link to their investment deck include it after the summary, if not then state that it is not present.

Here is the email:

\"\"\"{email_body}\"\"\"
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    print(email_body)
    print(response.choices[0].message.content.strip())
    return response.choices[0].message.content.strip()

def get_company_title(email_body, openai_api_key):
    client = OpenAI(api_key=openai_api_key)
    prompt = f"""
You are an assistant that extracts company names.

From the email below, identify the company name mentioned, or the company the sender is associated with.
Respond with the company name only, no extra text or explanation.
Ignore the company name "Taihill Venture" if it is present.
If no company name can be found, respond with "Unknown".

Email:
\"\"\"{email_body}\"\"\"
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    return response.choices[0].message.content.strip()