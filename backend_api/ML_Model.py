import openai
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Function to classify email (Acceptance, Rejection, or Pending)
def classify_email(email_content):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an AI email classifier."},
            {"role": "user", "content": "Classify the following email into either 'acceptance', 'rejection', or 'pending'. If the email asks for an interview or more information, classify as 'pending'. Answer in one word only."},
            {"role": "user", "content": email_content}
        ]
    )

    # Extracting classification result
    return response.choices[0].message.content.strip()


# Function to classify if an email is from a company
def classify_company_email(sender, gmail_content):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an AI email classifier."},
            {"role": "user", "content": "You are analyzing an email to determine if it is about a job application. A job-related email includes acceptance, rejection, or an invitation to apply. If the email is job-related, respond with the company name. If the email is not job-related, respond with 'not job related'. No other response is allowed. "},
            {"role": "user", "content": f"Sender: {sender}\nContent: {gmail_content}"}
        ]
    )

    # Extracting classification result
    return response.choices[0].message.content.strip()


# Example emails for testing
email_to_classify = """
Subject: Interview Request for Software Developer Position

Dear Ivan,

Thank you for your interest in the Software Developer position at XYZ Corp. After reviewing your application, we would like to invite you to participate in an interview. Could you please provide your availability for this week?

Looking forward to hearing from you.

Best regards,  
Hiring Manager  
XYZ Corp.
"""

classification_result = classify_email(email_to_classify)
print("Email classification:", classification_result)

# Testing company email classification
test_emails = [
    {
        "subject": "Birthday Party Invitation",
        "content": """
        Hey Ivan,

        I wanted to invite you to my birthday party this weekend. It's going to be at my place on Saturday night. There will be food, drinks, and music – hope you can make it!

        Cheers,  
        Sarah
        """
    },
    {
        "subject": "Job Offer for Software Engineer",
        "content": """
        Dear Ivan,

        We are pleased to inform you that you have been selected for the Software Engineer position at ABC Tech Inc. We were impressed with your skills and experience during the interview process.

        Please find the offer letter and details about the next steps in the attached document. We look forward to working with you!

        Best regards,  
        Hiring Team  
        ABC Tech Inc.
        """
    }
]

for idx, email in enumerate(test_emails, start=1):
    result = classify_company_email(email["subject"], email["content"])
    print(f"Email {idx} classification: {result}")
