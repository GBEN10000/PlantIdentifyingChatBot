from flask import Flask, request, render_template, jsonify
import openai
import requests
import os
import asyncio
import aiohttp

app = Flask(__name__)

# Set up OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY', 'API_KEY')

# Plant.ID API details
api_url = 'https://api.plant.id/v2/identify'
headers = {
    'Api-Key': os.getenv('PLANT_ID_API_KEY', 'Plant_API_KEY')
}

async def search_openai_api(user_query):
    try:
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {openai.api_key}'},
                json={
                    'model': 'gpt-3.5-turbo',
                    'messages': [{'role': 'user', 'content': user_query}]
                }
            )
            data = await response.json()
            return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def handle_image_upload():
    file = request.files['file']
    if file:
        img_path = 'uploaded_image.jpg'
        file.save(img_path)

        try:
            # Prepare the image for API request
            with open(img_path, 'rb') as img_file:
                files = {
                    'images': (img_path, img_file, 'image/jpeg')
                }
                data = {
                    "organs": ["flower"],
                    "latitude": 49.207,
                    "longitude": 16.608,
                    "similar_images": True
                }

                # Make API request
                response = requests.post(api_url, headers=headers, files=files, data=data)

            if response.status_code == 200:
                result = response.json()
                # Extract plant details from response
                if 'suggestions' in result and len(result['suggestions']) > 0:
                    suggestion = result['suggestions'][0]
                    flower_common_name = suggestion.get('plant_name', 'Unknown')

                    # Create a query for OpenAI
                    openai_query = f"What can you tell me about the plant '{flower_common_name}'?"

                    # Use the OpenAI API to get a response
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        ai_response = loop.run_until_complete(search_openai_api(openai_query))
                    finally:
                        loop.close()

                    return jsonify({
                        'flower_common_name': flower_common_name,
                        'ai_response': ai_response
                    })
                else:
                    flower_common_name = 'Unknown'
                    
            else:
                flower_common_name = 'Error: Could not identify flower'
        except Exception as e:
            flower_common_name = f'Error: {str(e)}'
        finally:
            # Remove the uploaded image file
            if os.path.exists(img_path):
                os.remove(img_path)

        return jsonify({
            'flower_common_name': flower_common_name,
            'ai_response': ''
        })

@app.route('/chat', methods=['POST'])
def chat_with_ai():
    user_query = request.json.get('user_query', '')
    # Create a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # Run the asynchronous function
    try:
        ai_response = loop.run_until_complete(search_openai_api(user_query))
    finally:
        # Close the loop
        loop.close()

    return jsonify({
        'ai_response': ai_response
    })

if __name__ == '__main__':
    app.run(debug=True)
