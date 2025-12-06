import os
import re
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import pytesseract
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure Tesseract path (adjust for your system)
# Windows: pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Mac: usually auto-detected if installed via brew
# Linux: usually auto-detected

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"

if not GEMINI_API_KEY:
    print("⚠️  WARNING: GEMINI_API_KEY not set. LLM features will fail.")

# Create temp directory
TEMP_DIR = os.path.join(os.path.dirname(__file__), 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════
# Gemini LLM Helper Function
# ═══════════════════════════════════════════════════════════
def call_gemini(prompt):
    """Call Google Gemini API"""
    if not GEMINI_API_KEY:
        return None
    
    try:
        headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': GEMINI_API_KEY
        }
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        # Extract text from Gemini response
        if 'candidates' in result and len(result['candidates']) > 0:
            candidate = result['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                text = candidate['content']['parts'][0].get('text', '')
                return text.strip()
        
        return None
    
    except Exception as e:
        print(f"⚠️  Gemini API error: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# STEP 1: OCR Layer (Tesseract)
# ═══════════════════════════════════════════════════════════
def extract_text_from_image(image_path):
    """Extract text using Tesseract OCR"""
    try:
        img = Image.open(image_path)
        
        # Get full OCR text
        full_text = pytesseract.image_to_string(img)
        
        # Get detailed data with confidence
        ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        # Extract line-level text with confidence
        lines = []
        current_line = []
        current_block = ocr_data['block_num'][0] if ocr_data['block_num'] else 0
        current_line_num = ocr_data['line_num'][0] if ocr_data['line_num'] else 0
        
        for i in range(len(ocr_data['text'])):
            if ocr_data['text'][i].strip():
                if (ocr_data['block_num'][i] != current_block or 
                    ocr_data['line_num'][i] != current_line_num):
                    if current_line:
                        lines.append({
                            'text': ' '.join(current_line),
                            'confidence': sum([ocr_data['conf'][j] for j in range(i-len(current_line), i) if ocr_data['conf'][j] != -1]) / len(current_line) if current_line else 0
                        })
                    current_line = [ocr_data['text'][i]]
                    current_block = ocr_data['block_num'][i]
                    current_line_num = ocr_data['line_num'][i]
                else:
                    current_line.append(ocr_data['text'][i])
        
        if current_line:
            lines.append({
                'text': ' '.join(current_line),
                'confidence': 0
            })
        
        return {
            'full_text': full_text,
            'lines': lines,
            'avg_confidence': sum([l['confidence'] for l in lines]) / len(lines) if lines else 0
        }
    except Exception as e:
        print(f"❌ OCR Error: {e}")
        return None


def extract_raw_tokens(text):
    """Extract raw numeric tokens using regex (no AI)"""
    patterns = [
        r'₹\s*[\d,\.]+',           # ₹1200, ₹ 1200
        r'INR\s*[\d,\.]+',         # INR1200, INR 1200
        r'Rs\.?\s*[\d,\.]+',       # Rs1200, Rs. 1200
        r'\d+[\.,]?\d*%',          # 10%, 10.5%
        r'\b\d+[\.,]?\d*\b',       # 1200, 1200.50
    ]
    
    raw_tokens = []
    currency_hint = None
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        raw_tokens.extend(matches)
    
    # Detect currency
    if re.search(r'₹|INR|Rs\.?', text, re.IGNORECASE):
        currency_hint = "INR"
    elif re.search(r'\$|USD', text, re.IGNORECASE):
        currency_hint = "USD"
    else:
        currency_hint = "INR"  # default
    
    return {
        'raw_tokens': list(set(raw_tokens)),  # remove duplicates
        'currency_hint': currency_hint,
        'token_count': len(raw_tokens)
    }


# ═══════════════════════════════════════════════════════════
# STEP 2: Normalization Layer (OCR Digit Fixing)
# ═══════════════════════════════════════════════════════════
def normalize_tokens_rule_based(tokens):
    """Rule-based OCR digit correction"""
    corrections = {
        'l': '1', 'I': '1', 'i': '1',
        'O': '0', 'o': '0',
        'S': '5', 's': '5',
        'B': '8', 'b': '8',
        'Z': '2', 'z': '2'
    }
    
    normalized = []
    for token in tokens:
        # Remove currency symbols for processing
        clean_token = re.sub(r'[₹$INRRs\.\s]', '', token)
        
        # Apply character corrections
        for old, new in corrections.items():
            clean_token = clean_token.replace(old, new)
        
        # Remove commas
        clean_token = clean_token.replace(',', '')
        
        # Try to convert to number
        try:
            if '%' in token:
                num = float(clean_token.replace('%', ''))
                normalized.append({'original': token, 'normalized': num, 'type': 'percentage'})
            else:
                num = float(clean_token)
                normalized.append({'original': token, 'normalized': num, 'type': 'amount'})
        except:
            pass  # skip if can't convert
    
    return normalized


def normalize_with_llm(normalized_tokens):
    """Use LLM for verification only, not generation"""
    if not GEMINI_API_KEY:
        return normalized_tokens
    
    try:
        token_list = [t['original'] for t in normalized_tokens]
        
        prompt = f"""Here are numeric tokens extracted from a document: {token_list}

Fix only OCR digit errors (like l→1, O→0, I→1, S→5).
Return ONLY corrected numbers in valid JSON format with no preamble or markdown.
Format: {{"corrected": [number1, number2, ...]}}"""

        response_text = call_gemini(prompt)
        
        if not response_text:
            return normalized_tokens
        
        # Remove markdown if present
        response_text = re.sub(r'```json\s*|\s*```', '', response_text)
        
        result = json.loads(response_text)
        
        # Update normalized values with LLM corrections
        if 'corrected' in result and len(result['corrected']) == len(normalized_tokens):
            for i, corrected_val in enumerate(result['corrected']):
                normalized_tokens[i]['normalized'] = corrected_val
        
        return normalized_tokens
    except Exception as e:
        print(f"⚠️  LLM normalization failed: {e}, using rule-based only")
        return normalized_tokens


# ═══════════════════════════════════════════════════════════
# STEP 3: Context Classification Layer
# ═══════════════════════════════════════════════════════════
def classify_amounts_with_context(normalized_tokens, ocr_lines):
    """Classify amounts using surrounding context"""
    if not GEMINI_API_KEY:
        # Fallback: simple keyword matching
        return fallback_classification(normalized_tokens, ocr_lines)
    
    try:
        # Extract context for each amount
        contexts = []
        for token in normalized_tokens:
            context = find_context_for_amount(token['original'], ocr_lines)
            contexts.append({
                'amount': token['normalized'],
                'context': context
            })
        
        prompt = f"""For each amount and its surrounding text, classify the type.

Amounts with context:
{json.dumps(contexts, indent=2)}

Classify each as: total_bill | paid | due | tax | discount | other
Return ONLY valid JSON with no preamble:
{{"classifications": [{{"type": "...", "value": number}}, ...]}}"""

        response_text = call_gemini(prompt)
        
        if not response_text:
            return fallback_classification(normalized_tokens, ocr_lines)
        
        # Remove markdown if present
        response_text = re.sub(r'```json\s*|\s*```', '', response_text)
        
        result = json.loads(response_text)
        return result.get('classifications', [])
    
    except Exception as e:
        print(f"⚠️  LLM classification failed: {e}, using fallback")
        return fallback_classification(normalized_tokens, ocr_lines)


def find_context_for_amount(amount_str, lines):
    """Find 1-2 lines around the amount"""
    for i, line in enumerate(lines):
        if amount_str in line['text']:
            # Get current line and maybe previous/next
            context_lines = []
            if i > 0:
                context_lines.append(lines[i-1]['text'])
            context_lines.append(line['text'])
            if i < len(lines) - 1:
                context_lines.append(lines[i+1]['text'])
            return ' '.join(context_lines)
    return ""


def fallback_classification(normalized_tokens, ocr_lines):
    """Simple keyword-based classification"""
    classifications = []
    full_text = ' '.join([l['text'].lower() for l in ocr_lines])
    
    keywords = {
        'total_bill': ['total', 'grand total', 'amount', 'bill'],
        'paid': ['paid', 'payment', 'received'],
        'due': ['due', 'balance', 'pending', 'outstanding'],
        'tax': ['tax', 'gst', 'vat', 'cgst', 'sgst'],
        'discount': ['discount', 'off', 'save']
    }
    
    for token in normalized_tokens:
        if token['type'] == 'percentage':
            classifications.append({'type': 'discount', 'value': token['normalized']})
        else:
            context = find_context_for_amount(token['original'], ocr_lines).lower()
            
            classified = False
            for type_name, kws in keywords.items():
                if any(kw in context for kw in kws):
                    classifications.append({'type': type_name, 'value': token['normalized']})
                    classified = True
                    break
            
            if not classified:
                classifications.append({'type': 'other', 'value': token['normalized']})
    
    return classifications


# ═══════════════════════════════════════════════════════════
# STEP 4: Final JSON Assembly (Code Only - No LLM)
# ═══════════════════════════════════════════════════════════
def assemble_final_output(currency, classifications, ocr_lines):
    """Assemble final JSON with provenance"""
    amounts = []
    
    for item in classifications:
        # Find source line
        source_line = "unknown"
        value_str = str(item['value'])
        
        for line in ocr_lines:
            if value_str in line['text'] or str(int(item['value'])) in line['text']:
                source_line = line['text']
                break
        
        amounts.append({
            'type': item['type'],
            'value': item['value'],
            'source': f"text: '{source_line}'"
        })
    
    return {
        'currency': currency,
        'amounts': amounts,
        'status': 'ok' if amounts else 'no_amounts_found',
        'reason': None if amounts else 'document too noisy or no amounts found'
    }


# ═══════════════════════════════════════════════════════════
# Flask Routes
# ═══════════════════════════════════════════════════════════
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'Python OCR service is running'})


@app.route('/process', methods=['POST'])
def process_image():
    temp_path = None
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        temp_path = os.path.join(TEMP_DIR, f"{os.urandom(8).hex()}_{file.filename}")
        file.save(temp_path)
        
        print("🔶 STEP 1: OCR Layer")
        ocr_result = extract_text_from_image(temp_path)
        if not ocr_result:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({'status': 'error', 'error': 'OCR failed'})
        
        raw_extraction = extract_raw_tokens(ocr_result['full_text'])
        print(f"   Found {raw_extraction['token_count']} raw tokens")
        
        if not raw_extraction['raw_tokens']:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({
                'status': 'no_amounts_found',
                'reason': 'document too noisy'
            })
        
        print("🔶 STEP 2: Normalization Layer")
        normalized = normalize_tokens_rule_based(raw_extraction['raw_tokens'])
        normalized = normalize_with_llm(normalized)
        print(f"   Normalized {len(normalized)} amounts")
        
        print("🔶 STEP 3: Context Classification Layer")
        classifications = classify_amounts_with_context(normalized, ocr_result['lines'])
        print(f"   Classified {len(classifications)} amounts")
        
        print("🔶 STEP 4: Final Assembly")
        final_output = assemble_final_output(
            raw_extraction['currency_hint'],
            classifications,
            ocr_result['lines']
        )
        
        # Cleanup
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        
        return jsonify(final_output)
    
    except Exception as e:
        print(f"❌ Processing error: {e}")
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({'status': 'error', 'error': str(e)}), 500


if __name__ == '__main__':
    print("🐍 Starting Python OCR Service on port 5000...")
    print("📝 Make sure Tesseract is installed:")
    print("   - Mac: brew install tesseract")
    print("   - Ubuntu: sudo apt install tesseract-ocr")
    print("   - Windows: https://github.com/UB-Mannheim/tesseract/wiki")
    app.run(host='0.0.0.0', port=5000, debug=True)