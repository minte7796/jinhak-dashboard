import os
import json
from flask import Flask, render_template, jsonify, request, redirect, abort
from scraper import get_latest_data, scrape_all_targets, TARGET_UNIVERSITIES, HISTORY_FILE

app = Flask(__name__)

# Ensure templates and static directories exist
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route('/')
def index():
    """Renders the main dashboard page."""
    return render_template('index.html')

@app.route('/api/ratios', methods=['GET'])
def get_ratios():
    """
    Returns latest competition data.
    Query parameter:
      force=true : Forces an immediate live scraping update
    """
    force = request.args.get('force', 'false').lower() == 'true'
    data = get_latest_data(force_refresh=force)
    return jsonify({
        "success": True,
        "data": data
    })

@app.route('/api/update', methods=['POST'])
def update_ratios():
    """
    Manual update endpoint triggered by the user clicking the '업데이트' button.
    Scrapes fresh live data from all official university ratio systems.
    """
    try:
        fresh_data = scrape_all_targets()
        return jsonify({
            "success": True,
            "message": "최신 경쟁률 데이터가 성공적으로 업데이트되었습니다.",
            "data": fresh_data
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"업데이트 중 오류가 발생했습니다: {str(e)}"
        }), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Returns historical competition data points."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
                return jsonify({
                    "success": True,
                    "history": history
                })
        except Exception:
            pass
    return jsonify({
        "success": True,
        "history": []
    })

@app.route('/redirect/<univ_id>')
def redirect_to_ratio(univ_id):
    """Convenience redirect to the target university's official live ratio page."""
    for item in TARGET_UNIVERSITIES:
        if item["id"] == univ_id:
            return redirect(item["ratio_url"])
    abort(404)

if __name__ == '__main__':
    # Initial data warm-up on startup
    print("Initializing 2027 수시모집 Smart Ratio Dashboard...")
    get_latest_data(force_refresh=True)
    port = int(os.environ.get('PORT', 5000))
    print(f"Server running at http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
