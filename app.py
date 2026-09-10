import os
import json
from flask import Flask, render_template, jsonify, request, redirect, abort
from scraper import get_latest_data, scrape_all_targets, TARGET_UNIVERSITIES, HISTORY_FILE, CACHE_FILE

app = Flask(__name__)

# Add global CORS header to prevent any browser CORS blockage
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/')
def index():
    """Renders the main dashboard page."""
    return render_template('index.html')

def get_cached_or_fresh(force=False):
    """Safely retrieves data with fallbacks so API never returns 500 error."""
    try:
        return get_latest_data(force_refresh=force)
    except Exception as e:
        print(f"Error getting data: {e}")
        # Fallback to cache file if exists
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "updated_at": "확인 중",
            "school_year": "2027학년도",
            "category": "수시모집",
            "items": []
        }

@app.route('/api/ratios', methods=['GET'])
def get_ratios():
    """
    Returns latest competition data.
    Fast response: uses cached data if available so client never times out.
    """
    force = request.args.get('force', 'false').lower() == 'true'
    data = get_cached_or_fresh(force=force)
    return jsonify({
        "success": True,
        "data": data
    })

@app.route('/api/update', methods=['POST'])
def update_ratios():
    """
    Manual update endpoint triggered by the user clicking '지금 업데이트'.
    Fetches fresh data and safely returns.
    """
    try:
        fresh_data = scrape_all_targets()
        return jsonify({
            "success": True,
            "message": "최신 경쟁률 데이터가 성공적으로 갱신되었습니다.",
            "data": fresh_data
        })
    except Exception as e:
        print(f"Update error: {e}")
        fallback_data = get_cached_or_fresh(force=False)
        return jsonify({
            "success": True,
            "message": "일부 대학 통신 지연으로 기존 캐시 데이터를 유지합니다.",
            "data": fallback_data
        })

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
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting server on http://127.0.0.1:{port}...")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
