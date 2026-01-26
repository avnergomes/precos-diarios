#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask API for SIMA Daily Quotations Dashboard
Serves processed data and handles daily updates.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
JSON_DIR = DATA_DIR / "json"

app = Flask(__name__)
CORS(app)

# Ensure directories exist
JSON_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def run_pipeline():
    """Run the complete ETL pipeline."""
    logger.info("Starting ETL pipeline...")

    try:
        # Import and run scraper
        from scraper import scrape_latest_quotations
        scrape_latest_quotations()
        logger.info("Scraping completed")
    except Exception as e:
        logger.error(f"Scraping error: {e}")

    try:
        # Import and run ETL
        from etl_process import process_all_files
        process_all_files()
        logger.info("ETL completed")
    except Exception as e:
        logger.error(f"ETL error: {e}")

    try:
        # Import and run preprocessing
        from preprocess_data import main as preprocess_main
        preprocess_main()
        logger.info("Preprocessing completed")
    except Exception as e:
        logger.error(f"Preprocessing error: {e}")

    logger.info("Pipeline completed")


def load_json_file(filename: str) -> dict:
    """Load a JSON file from the data directory."""
    filepath = JSON_DIR / filename
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


@app.route('/')
def index():
    """API health check."""
    return jsonify({
        'status': 'ok',
        'service': 'SIMA Daily Quotations API',
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            'data': '/api/data/<filename>',
            'aggregated': '/api/data/aggregated.json',
            'timeseries': '/api/data/timeseries.json',
            'filters': '/api/data/filters.json',
            'detailed': '/api/data/detailed.json',
            'refresh': '/api/refresh (POST)',
            'status': '/api/status',
        }
    })


@app.route('/api/status')
def status():
    """Get pipeline status and data info."""
    files_info = {}
    for filename in ['aggregated.json', 'timeseries.json', 'filters.json', 'detailed.json']:
        filepath = JSON_DIR / filename
        if filepath.exists():
            stat = filepath.stat()
            files_info[filename] = {
                'exists': True,
                'size_kb': round(stat.st_size / 1024, 1),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        else:
            files_info[filename] = {'exists': False}

    # Check consolidated.csv
    csv_path = PROCESSED_DIR / "consolidated.csv"
    if csv_path.exists():
        stat = csv_path.stat()
        files_info['consolidated.csv'] = {
            'exists': True,
            'size_kb': round(stat.st_size / 1024, 1),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
        }

    return jsonify({
        'status': 'ok',
        'files': files_info,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/data/<filename>')
def get_data(filename):
    """Serve JSON data files."""
    allowed_files = ['aggregated.json', 'timeseries.json', 'filters.json', 'detailed.json']

    if filename not in allowed_files:
        return jsonify({'error': 'File not found'}), 404

    filepath = JSON_DIR / filename
    if not filepath.exists():
        return jsonify({'error': 'Data not yet generated'}), 404

    return send_from_directory(JSON_DIR, filename, mimetype='application/json')


@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """Trigger a data refresh (protected in production)."""
    # In production, add authentication here
    api_key = os.environ.get('REFRESH_API_KEY')

    try:
        run_pipeline()
        return jsonify({
            'status': 'ok',
            'message': 'Pipeline executed successfully',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/aggregated')
def get_aggregated():
    """Get aggregated data."""
    data = load_json_file('aggregated.json')
    return jsonify(data)


@app.route('/api/timeseries')
def get_timeseries():
    """Get time series data."""
    data = load_json_file('timeseries.json')
    return jsonify(data)


@app.route('/api/filters')
def get_filters():
    """Get filter options."""
    data = load_json_file('filters.json')
    return jsonify(data)


@app.route('/api/forecast/<produto>')
def get_forecast(produto):
    """
    Get price forecast for a specific product.

    Args:
        produto: Product name (URL encoded)

    Query params:
        horizonte: Forecast horizon in days (default: 30)
        modelo: Model to use ('arima', 'prophet', 'all') (default: 'all')

    Returns:
        JSON with historical data, predictions, and metrics
    """
    from flask import request

    try:
        horizonte = request.args.get('horizonte', 30, type=int)
        modelo = request.args.get('modelo', 'all')

        # Validate horizon
        horizonte = max(7, min(365, horizonte))

        # Import forecasting module
        from api.forecast import generate_forecast, get_available_products

        # Check if product exists
        available = get_available_products()
        if produto not in available:
            return jsonify({
                'success': False,
                'error': f'Produto nao encontrado: {produto}',
                'produtos_disponiveis': available[:10],
            }), 404

        # Generate forecast
        result = generate_forecast(produto, horizonte)

        # Filter by model if specified
        if modelo != 'all' and modelo in result.get('modelos', {}):
            result['modelos'] = {modelo: result['modelos'][modelo]}

        return jsonify(result)

    except Exception as e:
        logger.error(f"Forecast error for {produto}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/forecast/produtos')
def get_forecast_products():
    """Get list of products available for forecasting."""
    try:
        from api.forecast import get_available_products
        products = get_available_products()
        return jsonify({
            'success': True,
            'produtos': products,
            'total': len(products),
        })
    except Exception as e:
        logger.error(f"Error getting forecast products: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Serve static dashboard files
@app.route('/dashboard')
@app.route('/dashboard/<path:path>')
def serve_dashboard(path='index.html'):
    """Serve the React dashboard."""
    dashboard_dir = BASE_DIR / "dashboard" / "dist"
    if not dashboard_dir.exists():
        return jsonify({'error': 'Dashboard not built'}), 404
    return send_from_directory(dashboard_dir, path)


def run_scraper():
    """Run only the scraper."""
    logger.info("Starting scraper...")
    try:
        from scraper import scrape_latest_quotations
        scrape_latest_quotations()
        logger.info("Scraping completed")
    except Exception as e:
        logger.error(f"Scraping error: {e}")


def init_scheduler():
    """Initialize the background scheduler for daily updates."""
    scheduler = BackgroundScheduler()

    # Run scraper daily at 12:30 (Brasilia time)
    scheduler.add_job(
        run_scraper,
        'cron',
        hour=12,
        minute=30,
        timezone='America/Sao_Paulo',
        id='daily_scraper'
    )

    # Run full pipeline daily at 13:00 (Brasilia time)
    scheduler.add_job(
        run_pipeline,
        'cron',
        hour=13,
        minute=0,
        timezone='America/Sao_Paulo',
        id='daily_pipeline'
    )

    scheduler.start()
    logger.info("Scheduler started - scraping at 12:30, pipeline at 13:00 BRT")


if __name__ == '__main__':
    # Initialize scheduler in production
    if os.environ.get('FLASK_ENV') == 'production':
        init_scheduler()

    # Run initial pipeline if no data exists
    if not (JSON_DIR / 'aggregated.json').exists():
        logger.info("No data found, running initial pipeline...")
        run_pipeline()

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_ENV') != 'production')
