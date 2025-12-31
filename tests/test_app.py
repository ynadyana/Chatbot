from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import os
from dotenv import load_dotenv
from openai import OpenAI
import requests

# Load environment variables
load_dotenv("app.env")

# Initialize the OpenAI client with your API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Flask app
app = Flask(__name__)

# Google Custom Search API Credentials
API_KEY = "AIzaSyAjWdELengH7vhX5soWOUQbrqG3sxQRdrQ"
SEARCH_ENGINE_ID = "658f42806ebe34c98"

# Load laptop dataset
data_path = "updated_laptop_dataset.csv"
try:
    laptop_data = pd.read_csv(data_path)
except FileNotFoundError:
    print(f"Error: File '{data_path}' not found. Please ensure it is in the correct location.")
    laptop_data = pd.DataFrame()  # Fallback to an empty DataFrame if the file doesn't exist.


def fetch_image_url(query):
    """
    Fetches the first image URL for a given laptop model using Google Custom Search API.
    """

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "cx": SEARCH_ENGINE_ID,
        "key": API_KEY,
        "searchType": "image",
        "num": 1,
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        if "items" in data and len(data["items"]) > 0:
            return data["items"][0]["link"]
        else:
            return "No image found"
    else:
        return "Error fetching image"


# Define LappyBot persona
persona = (
    "You are LappyBot, an AI assistant specializing in recommending laptops based on user preferences, "
    "including budget, use cases, and performance requirements. You can assist with specifications, pricing, "
    "brands, and features. Be helpful and professional, but ensure explanations are simple and clear. "
    "Always provide specific, detailed recommendations and explain why a laptop is suitable for a given use case. "
    "Do not answer if input is not related to laptops."
)

# Conversation history to maintain context
conversation_history = []


@app.route("/")
def home():
    # Link the CSS file here using Flask's `url_for` function
    return render_template("LappyBot_Final.html")


# Convert Markdown to HTML-friendly text
def convert_markdown_to_html(text):
    while "**" in text:
        text = text.replace("**", "<b>", 1).replace("**", "</b>", 1)
    return text.replace("\n", "<br>")


# Generate a response using GPT
def generate_response(user_input):
    global conversation_history
    conversation_history.append({"role": "user", "content": user_input})

    # Select top 200 rows of the dataset
    top_200_laptops = laptop_data.head(200)

    # Build the dataset context string with the top 10 rows
    dataset_context = ""
    for idx, row in top_200_laptops.iterrows():
        dataset_context += f"Brand: {row['brand']}, Model: {row['Model']}, Price: MYR {row['Price_MYR']}, RAM: {row['ram_memory']}GB\n"

    # Modify the system message to include comparison instructions
    system_message = (
        f"You are LappyBot, an assistant that provides laptop recommendations. "
        f"You have access to the following dataset with laptop information:\n"
        f"{dataset_context}\n"
        "If the user asks for a comparison, respond with a table format using HTML. "
        "Ensure the table includes relevant specifications like Brand, Model, Price, Processor, RAM, Storage, GPU, and Display. "
        "Otherwise, provide a detailed textual response."
    )

    messages = [{"role": "system", "content": persona + " " + system_message}] + conversation_history

    try:
        # Call GPT API
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
        )

        bot_response = response.choices[0].message.content.strip()
        conversation_history.append({"role": "assistant", "content": bot_response})

        # Limit conversation history to 6 messages
        if len(conversation_history) > 5:
            conversation_history = conversation_history[-5:]

        return bot_response
    except Exception as e:
        print(f"Error generating response: {e}")
        return "Sorry, I encountered an error while generating a response."


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_input = data.get("message", "")

        # for image
        if "image" in user_input.lower():
            laptop_model = user_input.split("image for the")[1].strip()
            image_url = fetch_image_url(laptop_model)

            return jsonify({"response": f"Here is the image for {laptop_model} : {image_url}"})

        response_text = generate_response(user_input)
        html_response = convert_markdown_to_html(response_text)
        return jsonify({"response": html_response})
    except Exception as e:
        print(f"Error in /chat: {e}")
        return jsonify({"response": "Oops! Something went wrong. Please try again."}), 500


@app.route("/compare", methods=["POST"])
def compare():
    try:
        data = request.json
        brands = data.get("brands", [])
        max_price = data.get("max_price", None)

        if laptop_data.empty:
            return jsonify({"error": "Laptop dataset is not available. Please check the server configuration."})

        filtered_data = laptop_data.copy()
        if brands:
            filtered_data = filtered_data[filtered_data["brand"].str.lower().isin([brand.lower() for brand in brands])]
        if max_price:
            try:
                max_price = float(max_price)
                filtered_data = filtered_data[filtered_data["Price_MYR"] <= max_price]
            except ValueError:
                return jsonify({"error": "Invalid max price format. Please provide a numeric value."})

        comparison_columns = laptop_data.columns
        filtered_data = filtered_data[comparison_columns]

        table_html = filtered_data.to_html(
            index=False,
            classes="table table-bordered table-hover",
            border=1
        )

        return jsonify({"comparison_table": table_html})
    except Exception as e:
        print(f"Error in /compare: {e}")
        return jsonify({"response": "Oops! Something went wrong while generating the comparison."}), 500


@app.route("/recommend", methods=["POST"])
def recommend():
    try:
        data = request.json
        budget = data.get("budget", None)
        use_case = data.get("use_case", "").lower()

        if not budget:
            return jsonify({"error": "Please provide a budget for the recommendation."})

        try:
            budget = float(budget)
        except ValueError:
            return jsonify({"error": "Invalid budget format. Please provide a numeric value."})

        budget_filtered = laptop_data[laptop_data["Price_MYR"] <= budget]

        use_case_requirements = {
            "science computer student": {
                "min_ram": 8,
                "min_cores": 4,
                "gpu_type": ["dedicated", "integrated"],
                "os": ["windows", "linux"],
            },
            "gaming": {
                "min_ram": 16,
                "min_cores": 6,
                "gpu_type": ["dedicated"],
                "os": ["windows"],
            },
        }

        if use_case in use_case_requirements:
            requirements = use_case_requirements[use_case]
            use_case_filtered = budget_filtered[
                (budget_filtered["ram_memory"] >= requirements["min_ram"]) &
                (budget_filtered["num_cores"] >= requirements["min_cores"]) &
                (budget_filtered["gpu_type"].str.lower().isin(requirements["gpu_type"])) &
                (budget_filtered["OS"].str.lower().isin(requirements["os"]))
                ]
        else:
            use_case_filtered = budget_filtered

        if not use_case_filtered.empty:
            recommendation = use_case_filtered.sample(1).iloc[0]
            laptop = {
                "brand": recommendation["brand"].capitalize(),
                "model": recommendation["Model"],
                "price": f"MYR {recommendation['Price_MYR']:.2f}",
                "processor": f"{recommendation['processor_brand'].capitalize()} {recommendation['processor_tier']}",
                "ram": f"{recommendation['ram_memory']}GB",
                "storage": f"{recommendation['primary_storage_capacity']}GB {recommendation['primary_storage_type']}",
                "gpu": f"{recommendation['gpu_brand'].capitalize()} {recommendation['gpu_type'].capitalize()}",
                "display": f"{recommendation['display_size']}-inch, "
                           f"{recommendation['resolution_width']}x{recommendation['resolution_height']} resolution",
                "os": recommendation["OS"].capitalize(),
            }

            prompt = (f"A {laptop['brand']} {laptop['model']} laptop with {laptop['display']} display, "
                      f"{laptop['processor']} processor, {laptop['ram']} RAM, {laptop['storage']} storage, "
                      f"and {laptop['gpu']} graphics, suitable for {use_case}.")

            response_text = f"""
            🎉 *Recommended Laptop for You* 🎉

            *Brand & Model*: {laptop['brand']} - {laptop['model']}  
            *Price*: {laptop['price']}

            *Specifications*:  
            - *Processor*: {laptop['processor']}  
            - *RAM*: {laptop['ram']}  
            - *Storage*: {laptop['storage']}  
            - *Graphics*: {laptop['gpu']}  
            - *Display*: {laptop['display']}  
            - *Operating System*: {laptop['os']}



            This laptop is perfect for your use case as it meets the performance and budget requirements. 
            Let me know if you need more details or additional options! 😊
            """

        return jsonify({"error": "No laptops found matching your budget and preferences."})
    except Exception as e:
        print(f"Error in /recommend: {e}")
        return jsonify({"response": "Oops! Something went wrong while generating the recommendation."}), 500


@app.route("/quiz", methods=["POST"])
def quiz():
    user_responses = request.json
    use_case = user_responses.get('0')  # Primary use case, like 'Work'
    budget = user_responses.get('1')  # Budget, like 'MYR 3000-5000'
    size = user_responses.get('2')  # Size, like '15-16 inch'

    filtered_laptops = laptop_data
    print(filtered_laptops.head(10))

    # Use case feature
    if use_case == "Gaming":
        filtered_laptops = filtered_laptops[filtered_laptops['ram_memory'] >= 8]
        filtered_laptops = filtered_laptops[filtered_laptops['gpu_type'] == "dedicated"]
        print("Filtered after Gaming:", filtered_laptops.shape)

    elif use_case == "Work":
        filtered_laptops = filtered_laptops[filtered_laptops['ram_memory'] >= 8]
        print("Filtered after Work:", filtered_laptops.shape)

    elif use_case == "School":
        filtered_laptops = filtered_laptops[filtered_laptops['ram_memory'] >= 4]
        print("Filtered after School:", filtered_laptops.shape)

    elif use_case == "Editing":
        filtered_laptops = filtered_laptops[filtered_laptops['ram_memory'] >= 16]
        filtered_laptops = filtered_laptops[filtered_laptops['gpu_type'] == "dedicated"]
        print("Filtered after Editing:", filtered_laptops.shape)

    # Filter by budget
    if budget == "Under MYR 3000":
        filtered_laptops = filtered_laptops[filtered_laptops['Price_MYR'] <= 3000]
    elif budget == "MYR 3000-5000":
        filtered_laptops = filtered_laptops[
            (filtered_laptops['Price_MYR'] > 3000) & (filtered_laptops['Price_MYR'] <= 5000)]
    elif budget == "Over MYR 5000":
        filtered_laptops = filtered_laptops[filtered_laptops['Price_MYR'] > 5000]
    print("Filtered after Budget:", filtered_laptops.shape)

    # Filter by size
    if size == "13-14 inch":
        filtered_laptops = filtered_laptops[
            (filtered_laptops['display_size'] >= 13.0) & (filtered_laptops['display_size'] < 15.0)]
    elif size == "15-16 inch":
        filtered_laptops = filtered_laptops[(filtered_laptops['display_size'] >= 15.0)]
    print("Filtered after Size:", filtered_laptops.shape)

    # Get the top 2 laptops (for simplicity, just select the first 2)
    top_laptops = filtered_laptops.head(3)

    # Check if there are any filtered laptops available
    if top_laptops.empty:
        return jsonify({"error": "No laptops match the selected criteria."}), 400
    else:
        print(top_laptops)

    # Format recommendations
    recommendations = []
    for _, row in top_laptops.iterrows():
        recommendations.append({
            "brand": row["brand"],
            "model": row["Model"],
            "price": f"MYR {row['Price_MYR']:.2f}",
            "processor": f"{row['processor_brand']} {row['processor_tier']}",
            "ram": f"{row['ram_memory']}GB",
            "gpu": row["gpu_type"],
            "storage": f"{row['primary_storage_capacity']}GB {row['primary_storage_type']}",
            "display": f"{row['display_size']}-inch, {row['resolution_width']}x{row['resolution_height']} resolution"
        })

    # Return the recommendations as JSON
    return jsonify({"recommendations": recommendations})


@app.route("/troubleshooting", methods=["POST"])
def troubleshooting():
    data = request.json
    issue = data.get("issue", "").lower()

    # Define common laptop issues and their solutions
    troubleshooting_guide = {
        "slow performance": "Try closing unnecessary applications, upgrading RAM, or checking for malware.",
        "battery draining fast": "Check your battery settings, reduce screen brightness, and close unused apps.",
        "overheating": "Ensure your laptop's vents are clear, use a cooling pad, and check for blocked air circulation.",
        "screen flickering": "Update your graphics driver, or try lowering the screen refresh rate.",
        "wifi not working": "Check your router, restart your laptop, and ensure your Wi-Fi driver is up to date.",
        "laptop not turning on": "Ensure the power cable is connected, the battery is charged, and perform a hard reset by holding down the power button for 30 seconds.",
    }

    solution = troubleshooting_guide.get(issue,
                                         "Sorry, I don't have a solution for that issue. Please contact customer support.")

    return jsonify({"solution": solution})


@app.route("/faq", methods=["POST"])
def faq():
    data = request.json
    question = data.get("question", "").lower()

    # Define common FAQ questions and answers about laptops
    faq_guide = {
        "what is the best laptop for gaming?": "For gaming, look for laptops with at least 16GB of RAM, a dedicated GPU (like Nvidia GTX/RTX or AMD Radeon), and a fast processor (i7 or Ryzen 7). Popular models include Alienware, ASUS ROG, and MSI.",
        "what is the best laptop for students?": "For students, a laptop with 8GB of RAM, a solid processor (i5 or Ryzen 5), and good battery life is ideal. Consider brands like Dell XPS, MacBook Air, or Lenovo ThinkPad.",
        "how much RAM is good for laptops?": "8GB of RAM is the minimum for smooth multitasking, while 16GB is ideal for heavy tasks like video editing or gaming. For gaming, go for 16GB or more.",
        "what is the difference between SSD and HDD?": "SSD (Solid State Drive) is faster, more reliable, and consumes less power than HDD (Hard Disk Drive). However, SSDs are more expensive and have less storage capacity compared to HDDs.",
        "how do I troubleshoot a laptop that's not turning on?": "First, check the power supply, and try a different charger. If the laptop still doesn't turn on, try removing the battery and holding the power button for 30 seconds before reattaching the battery.",
        "what are the different types of laptop processors?": "Laptop processors come in different tiers like Intel Core i3, i5, i7, and i9, and AMD Ryzen 3, 5, 7, and 9. Higher numbers generally indicate better performance, with i7/i9 or Ryzen 7/9 being suitable for power users.",
        "what is the best laptop for video editing?": "For video editing, a laptop with a powerful processor (i7 or Ryzen 7), 16GB or more of RAM, and a dedicated GPU (like Nvidia RTX) is essential. Popular models include MacBook Pro, Dell XPS 15, and ASUS ROG.",
        "what is the difference between integrated and dedicated graphics?": "Integrated graphics are built into the processor and are sufficient for light tasks, but dedicated graphics (like Nvidia or AMD) offer better performance for gaming, video editing, and graphics-intensive applications.",
        "how can I improve my laptop's performance?": "To improve laptop performance, you can upgrade RAM, replace the HDD with an SSD, clean out dust from the vents, update drivers, and remove unnecessary startup programs.",
    }

    answer = faq_guide.get(question,
                           "Sorry, I don't have an answer for that question. Please check our website for more information.")

    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(debug=True)
