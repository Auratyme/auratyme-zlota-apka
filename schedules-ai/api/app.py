from flask import Flask, jsonify
import os
import json

PORT=os.environ.get("PORT", "80")
print(PORT)
app = Flask(__name__)

@app.route('/')
def get_schedule():
    file_path = os.path.join('schedule-data', 'generated_schedule.json')
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=PORT, debug=True)