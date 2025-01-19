from flask import Flask, request, jsonify
from pathlib import Path
from processor import process_statement
from datetime import datetime

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "ibkr-processor"
    }), 200

@app.route('/process-statement', methods=['POST'])
def process_ib_statement():
    """
    Process IB statement from CSV content
    Expected JSON body: {
        "csv_content": "raw CSV content as string",
        "filename": "original filename for validation"
    }
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400

        data = request.get_json()
        
        if 'csv_content' not in data:
            return jsonify({"error": "Missing required fields: csv_content"}), 400
        if 'subject' not in data:
            return jsonify({"error": "Missing required fields: subject"}), 400

        subject = data['subject']
        date_str = subject.split(" ")[-1]
        parsed_date = datetime.strptime(date_str, '%m/%d/%Y').strftime('%Y%m%d')
        tmp_file = f"daily_csv.randomstuff.{parsed_date}.csv"
        # Create temporary directory if it doesn't exist
        app.logger.info("filename created")
        tmp_dir = Path("/app/tmp")
        tmp_dir.mkdir(exist_ok=True)
        tmp_file_path = tmp_dir / tmp_file
        app.logger.info("dirs created")
        with open(tmp_file_path, 'w', encoding='utf-8') as tmp_file:
            csv_content = data['csv_content'].replace('\ufeff', '')
            tmp_file.write(csv_content)
            print("DONE")
        with open(tmp_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"Number of lines written: {len(lines)}")
            print(f"First few lines: {lines[:3]}")
        
        app.logger.info(f"tmp file created {tmp_file_path}")
        processor = process_statement(tmp_file_path.as_posix())
       
        app.logger.info(f"file processed")
        response = {
            "status": "success",
            "message": "Statement processed successfully"
        }

        return jsonify(response), 200

    except Exception as e:
        app.logger.error(f"Error processing statement: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": "error",
            "message": "Failed to process statement"
        }), 500

    finally:
        try:
            Path(tmp_file_path).unlink(missing_ok=True)
        except Exception:
            pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)