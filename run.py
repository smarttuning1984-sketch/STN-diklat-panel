import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Get configuration from environment
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Run development server (not for production!)
    app.run(host='0.0.0.0', port=port, debug=debug)